# Copyright (C) idoneam (2021-2021)
#
# This file is part of Canary
#
# Canary is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Canary is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Canary. If not, see <https://www.gnu.org/licenses/>.

# TODO: determine and (if possible) fix source of lack of precision in relative time skips

import asyncio
import random
import time
from itertools import chain
from functools import partial
from collections import deque
from typing import Optional, Iterable
import discord
import yt_dlp
from discord.ext import commands
from .utils.music_helpers import (
    FFMPEG_BEFORE_OPTS,
    FFMPEG_OPTS,
    YTDL,
    QUEUE_ACTIONS,
    check_playing,
    parse_time,
    mk_title_string,
    mk_duration_string,
    time_func,
    mk_change_embed,
    check_banned,
    conv_arg,
    MusicArgConvertError,
)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.track_queue: deque = deque()
        self.backup: deque = deque()
        self.looping_queue: bool = False
        self.track_lock: asyncio.Lock = asyncio.Lock()
        self.playing = None
        self.looping_track = False
        self.volume_level: float = self.bot.config.music["start_vol"]
        self.speed_flag: str = "atempo=1"
        self.speed_val: float = 1.0
        self.skip_opts: Optional[tuple[str, int]] = None
        self.track_start_time: float = 0.0
        self.ban_role = self.bot.config.music["ban_role"]
        self.pause_start: Optional[float] = None

    async def get_info(self, url: str):
        try:
            data = await self.bot.loop.run_in_executor(None, partial(YTDL.extract_info, url, download=False))
        except yt_dlp.utils.DownloadError:
            return None
        entries = data.get("entries", [data])
        if not entries:
            return None
        is_single: bool = len(entries) == 1
        if is_single:
            data = entries[0]
        return data, entries, is_single

    def release_lock(self, _):
        self.track_lock.release()

    def check_reaction(self, embed_msg: discord.Message, reaction: discord.Reaction, user: discord.User):
        return user != self.bot.user and reaction.message.id == embed_msg.id and str(reaction) in QUEUE_ACTIONS

    def resume_playing(self, ctx):
        ctx.voice_client.resume()
        self.track_start_time += time.perf_counter() - self.pause_start
        self.pause_start = None

    def compute_curr_time(self, paused: bool) -> float:
        return (self.pause_start - self.track_start_time) if paused else (time.perf_counter() - self.track_start_time)

    def total_queue(self) -> Iterable:
        return chain(self.track_queue, self.backup) if self.looping_queue else self.track_queue

    def total_len(self) -> int:
        return len(self.track_queue) + len(self.backup) if self.looping_queue else len(self.track_queue)

    def play_track(self, ctx, *, after=None, skip_str: Optional[str] = None, delta: int = 0):
        ctx.voice_client.play(
            discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    self.playing[0]["url"],
                    before_options=FFMPEG_BEFORE_OPTS if skip_str is None else f"{FFMPEG_BEFORE_OPTS} -ss {skip_str}",
                    options=f'-filter:a "{self.speed_flag}" {FFMPEG_OPTS}',
                ),
                self.volume_level / 100,
            ),
            after=after or self.release_lock,
        )
        self.track_start_time = time.perf_counter() - delta

    def from_total(self, idx):

        q_len: int = self.total_len()
        if idx >= q_len or idx < -q_len:
            return None
        idx = idx % q_len
        return (self.track_queue, idx) if (idx < len(self.track_queue)) else (self.backup, idx - len(self.track_queue))

    @commands.command(aliases=["m"])
    async def music(self, ctx, subcommand: str, *, args: Optional[str] = None):
        """
        monocommand used for music features.
        write `?music help subcommand` for details on how each command works (arguments are shown as semicolon separated list).
        available subcommands are:
        - play
        - playback_speed | ps
        - goto_time | gt
        - backwards_time | bt | rewind
        - loop
        - print_queue | pq
        - status | now_playing | np
        - remove | pop
        - insert
        - clear_queue | cq
        - clear_history | ch
        - volume | vol | v
        - stop
        - next | next
        - back | previous
        - pause
        - resume
        - help
        """
        try:
            match subcommand:
                case "play":
                    await self.play(ctx, args)
                case "playback_speed" | "ps":
                    await self.playback_speed(ctx, conv_arg(float, args, True))
                case "goto_time" | "gt":
                    await self.goto_time(ctx, conv_arg(lambda x: x, args, True))
                case "forward_time" | "ft":
                    await self.forward_time(ctx, conv_arg(lambda x: x, args, True))
                case "backwards_time" | "bt" | "rewind":
                    await self.backwards_time(ctx, conv_arg(lambda x: "30" if x is None else x, args, False))
                case "loop":
                    await self.loop(ctx, conv_arg(lambda x: x, args, True))
                case "print_queue" | "pq":
                    await self.print_queue(ctx, conv_arg(lambda x: 0 if x is None else int(x), args, False))
                case "status" | "now_playing" | "np":
                    await self.music_status(ctx)
                case "remove" | "pop":
                    await self.remove_track(ctx, conv_arg(int, args, True))
                case "insert":
                    await self.insert_track(
                        ctx, *conv_arg(lambda x: (lambda y, z: (int(y), z))(*x.split(maxsplit=1)), args, True)
                    )
                case "clear_queue" | "cq":
                    await self.clear_queue(ctx)
                case "clear_hist" | "ch":
                    await self.clear_hist(ctx)
                case "queue" | "q":
                    await self.queue_track(ctx, conv_arg(lambda x: x, args, True))
                case "volume" | "vol" | "v":
                    await self.volume(ctx, conv_arg(lambda x: float(x.strip("%")), args, True))
                case "stop":
                    await self.stop(ctx)
                case "skip" | "next":
                    await self.skip(ctx, conv_arg(lambda x: 0 if x is None else int(x), args, False))
                case "back" | "previous":
                    await self.backtrack(ctx, conv_arg(lambda x: None if x is None else int(x), args, False))
                case "pause":
                    await self.pause(ctx)
                case "resume":
                    await self.resume(ctx)
                case "help":
                    match args:
                        case "play":
                            await ctx.send(
                                "streams from a youtube url or track name, or if none is given, from the queue\n"
                                "arguments: (optional: link or title of track)"
                            )
                        case "playback_speed" | "ps":
                            await ctx.send(
                                "changes track playback speed (clamped 0.25 between 4)\n" "arguments: (float)"
                            )
                        case "goto_time" | "gt":
                            await ctx.send(
                                "go to a specific timestamp in currently playing track\n"
                                "arguments: (timestamp of format H:M:S)"
                            )
                        case "forward_time" | "ft":
                            await ctx.send(
                                "move forwards in currently playing track\n" "arguments: (timestamp of format H:M:S)"
                            )
                        case "backwards_time" | "bt" | "rewind":
                            await ctx.send(
                                "move backwards in currently playing track\n"
                                "arguments: (timestamp of format H:M:S [defaults to 30 seconds])"
                            )
                        case "loop":
                            await ctx.send("changes looping state\n" "arguments: (either `track` or `queue`)")
                        case "print_queue" | "pq":
                            await ctx.send(
                                "displays the current track queue\n" "arguments: (optional: start index of message)"
                            )
                        case "status" | "now_playing" | "np":
                            await ctx.send("displays current status of the bot\n" "arguments: none" "")
                        case "remove" | "pop":
                            await ctx.send("remove a track from the track queue by index\n" "arguments: (integer)")
                        case "insert":
                            await ctx.send(
                                "insert a track into the track queue at a given index\n"
                                "arguments: (integer; link or title of track)"
                            )
                        case "clear_queue" | "cq":
                            await ctx.send("clears current track queue\n" "arguments: none")
                        case "clear_hist" | "ch":
                            await ctx.send("clears current track history\n" "arguments: none")
                        case "queue" | "q":
                            await ctx.send(
                                "adds a track to the end of the queue\n" "arguments: (link or title of track)"
                            )
                        case "volume" | "vol" | "v":
                            await ctx.send(
                                "set volume to a different level (clamped between 0% and 500%)\n" "arguments: (float)"
                            )
                        case "stop":
                            await ctx.send("stops and disconnects the bot from voice\n" "arguments: none")
                        case "skip" | "next":
                            await ctx.send(
                                "skips some amount of songs in the queue\n"
                                "arguments: (optional: int [defaults to 0, going forward a single track])"
                            )
                        case "back" | "previous":
                            await ctx.send(
                                "goes backwards in history by some amount of tracks\n"
                                "arguments: (optional: int [defaults to 0 if track has been playing for more than 10 seconds, otherwise 1])"
                            )
                        case "pause":
                            await ctx.send("pauses currently playing track\n" "arguments: none")
                        case "resume":
                            await ctx.send("resumes currently paused track.\n" "arguments: none")

        except MusicArgConvertError:
            pass  # for proper argument parsing

    @check_banned
    async def play(self, ctx, url: Optional[str] = None):

        in_main: bool = ctx.voice_client is None

        if ctx.author.voice is None:
            return await ctx.send("you are not currently connected to a voice channel.")

        if in_main and (not self.track_queue) and url is None:
            return await ctx.send("you did not specify a track to play.")

        if not in_main:
            if ctx.voice_client.is_paused():
                return await ctx.send("bot is currently paused, please use `resume` before playing.")
            if ctx.author.voice.channel != ctx.voice_client.channel:
                if len(ctx.voice_client.channel.members) > 1:
                    return await ctx.send("bot is currently playing music for users in another voice channel.")
                ctx.voice_client.pause()
                await ctx.voice_client.move_to(ctx.author.voice.channel)
                if url is None:
                    ctx.voice_client.resume()
            elif url is None:
                return await ctx.send("bot is currently playing a track and you did not specify a new track to play.")

        if url:
            await ctx.trigger_typing()
            ret = await self.get_info(url)
            if ret is None:
                return await ctx.send("could not find track/playlist.")
            data, entries, single = ret
            author_str = str(ctx.author)
            self.track_queue.extendleft((track, author_str) for track in reversed(entries))
            self.looping_track = False
            if not single:
                await ctx.send(embed=mk_change_embed(data, entries, "playing playlist", f"submitted by: {author_str}"))
            if not in_main:
                ctx.voice_client.stop()

        if not in_main:
            return

        await ctx.author.voice.channel.connect()

        while True:
            await self.track_lock.acquire()
            now_playing = None
            if self.skip_opts is None:
                await ctx.trigger_typing()

                if ctx.voice_client is None:
                    break

                if self.looping_track:
                    self.play_track(ctx)
                elif not self.track_queue:
                    if not self.looping_queue:
                        break
                    self.track_queue = self.backup
                    self.backup = deque()
                else:
                    self.playing = self.track_queue.popleft()
                    self.backup.append(self.playing)
                    now_playing = (
                        discord.Embed(colour=random.randint(0, 0xFFFFFF), title="now playing")
                        .add_field(
                            name="track title",
                            value=mk_title_string(self.playing[0]),
                            inline=False,
                        )
                        .set_footer(text=f"submitted by: {self.playing[1]}")
                    )
                    self.play_track(ctx)
                    await ctx.send(embed=now_playing)
            else:
                skip_str, delta = self.skip_opts
                self.play_track(ctx, skip_str=skip_str, delta=delta)
                if self.pause_start is not None:
                    ctx.voice_client.pause()
                    self.pause_start -= delta
                self.skip_opts = None

        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()
            await ctx.send("queue is empty, finished playing all tracks.")
        else:
            await ctx.send("stopped playing, disconnected.")

        self.playing = None
        self.track_lock.release()
        self.volume_level = self.bot.config.music["start_vol"]
        self.speed_flag = "atempo=1"

    @check_playing
    async def playback_speed(self, ctx, speed: float):

        self.speed_val = max(0.25, min(speed, 4.0))
        self.speed_flag = (
            f"atempo={self.speed_val}"
            if 0.5 < self.speed_val < 2
            else f"atempo=sqrt({self.speed_val}),atempo=sqrt({self.speed_val})"
        )
        parsed = parse_time(str(round(self.compute_curr_time(ctx.voice_client.is_paused()))))
        self.skip_opts = time.strftime("%H:%M:%S", time.gmtime(parsed)), parsed
        ctx.voice_client.stop()
        await ctx.send(f"changed playback speed to {self.speed_val}")

    @check_playing
    @check_banned
    @time_func
    def goto_time(self, seconds: int, _: bool):

        return seconds

    @check_playing
    @check_banned
    @time_func
    def forward_time(self, seconds: int, paused: bool):

        return max(0, round(self.compute_curr_time(paused) + seconds))

    @check_playing
    @check_banned
    @time_func
    def backwards_time(self, seconds: int, paused: bool):

        return max(0, round(self.compute_curr_time(paused) - seconds))

    @check_banned
    async def loop(self, ctx, target: str):

        match target:
            case "queue" | "q":
                self.looping_queue = not self.looping_queue
                await ctx.send(f"queue will now{' ' if self.looping_queue else ' no longer '}loop.")
            case "track" | "t":
                self.looping_track = not self.looping_track
                await ctx.send(f"invididual track will now{' ' if self.looping_track else ' no longer '}loop.")

    async def print_queue(self, ctx, start_idx: int):

        queue_embed = discord.Embed(
            colour=random.randint(0, 0xFFFFFF),
            title=f"track queue as of {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        )

        if not self.track_queue:
            queue_embed.add_field(name="track queue status", value="track queue is currently empty")
            return await ctx.send(embed=queue_embed)

        queue_copy = list(self.total_queue() if self.looping_queue else self.track_queue)

        q_len = len(queue_copy)

        if start_idx >= q_len or start_idx < -q_len:
            return await ctx.send("start index out of bounds.")

        curr_index: int = start_idx % q_len
        change_state: bool = True
        queue_embed.description = (
            f"duration: {mk_duration_string(self.track_queue)}, "
            f"length: {len(self.track_queue)} tracks"
            f"{' (looping)' if self.looping_queue else ''}"
        )
        queue_msg = await ctx.send(embed=queue_embed)
        for reaction in QUEUE_ACTIONS:
            await queue_msg.add_reaction(reaction)
        while True:
            if change_state:
                queue_embed.clear_fields()
                track, user = queue_copy[curr_index]
                queue_embed.add_field(
                    name=f"track title at index {curr_index}", value=mk_title_string(track), inline=False
                ).add_field(name="duration", value=mk_duration_string([track]), inline=False).set_footer(
                    text=f"submitted by: {user}"
                )
                await queue_msg.edit(embed=queue_embed)
            try:
                react, author = await self.bot.wait_for(
                    "reaction_add",
                    timeout=60.0,
                    check=partial(self.check_reaction, queue_msg),
                )
            except asyncio.TimeoutError:
                for reaction in QUEUE_ACTIONS:
                    await queue_msg.remove_reaction(reaction, self.bot.user)
                queue_embed.title += " (no longer responsive)"
                await queue_msg.edit(embed=queue_embed)
                break
            curr_index, change_state = QUEUE_ACTIONS[str(react)](curr_index, q_len)
            await react.remove(author)

    async def music_status(self, ctx):

        status_embed = discord.Embed(colour=random.randint(0, 0xFFFFFF), title="music status")
        if ctx.voice_client is None:
            return await ctx.send(embed=status_embed.add_field(name="status", value="not playing"))

        playing = ctx.voice_client.is_playing()
        paused = ctx.voice_client.is_paused()
        if playing or paused:
            status_embed.add_field(
                name=f"currently {'playing' if playing else 'paused'} track",
                value=mk_title_string(self.playing[0]),
                inline=False,
            ).add_field(name="volume", value=f"{self.volume_level}%", inline=True).add_field(
                name="track location",
                value=f"{time.strftime('%H:%M:%S', time.gmtime(self.compute_curr_time(paused)))}/"
                f"{mk_duration_string([self.playing[0]])}",
                inline=True,
            ).add_field(
                name="looping track", value="yes" if self.looping_track else "no", inline=True
            ).add_field(
                name="playback speed", value=str(self.speed_val), inline=True
            ).add_field(
                name="loop length" if self.looping_queue else "remaining queue length",
                value=f"{mk_duration_string(self.total_queue())}" f" ({self.total_len()} tracks)",
                inline=True,
            ).add_field(
                name="track submitter", value=str(self.playing[1]), inline=True
            )
        else:
            status_embed.add_field(
                name="status",
                value="not playing but connected [ERROR STATE SHOULD NEVER OCCUR]",
            )
        await ctx.send(embed=status_embed)

    async def remove_track(self, ctx, track_index: int):

        ltup = self.from_total(track_index)
        if ltup is None:
            return await ctx.send("removal index out of bounds.")
        track_list, del_index = ltup

        removed = mk_change_embed(
            track_list[del_index][0],
            [track_list[del_index][0]],
            f"removed track at index {track_index}",
            f"removed by: {ctx.author}",
        )
        del track_list[del_index]
        await ctx.send(embed=removed)

    @check_banned
    async def insert_track(self, ctx, track_index: int, url: str):

        await ctx.trigger_typing()

        ltup = self.from_total(track_index)
        if ltup is None:
            return await ctx.send("insertion index out of bounds.")
        track_list, ins_index = ltup

        ret = await self.get_info(url)
        if ret is None:
            return await ctx.send("could not find track/playlist.")
        data, entries, single = ret
        author_str = str(ctx.author)
        for track in reversed(entries):
            track_list.insert(ins_index, (track, author_str))

        await ctx.send(
            embed=mk_change_embed(
                data,
                entries,
                f"inserted {'song' if single else 'playlist'} at index {track_index}",
                f"submitted by: {author_str}",
            )
        )

    @check_banned
    async def clear_queue(self, ctx):

        self.track_queue.clear()
        if self.looping_queue:
            self.backup.clear()
        await ctx.send("cleared current track queue.")

    async def clear_hist(self, ctx):

        self.backup.clear()
        await ctx.send("cleared current track history.")

    @check_banned
    async def queue_track(self, ctx, url: str):

        await ctx.trigger_typing()

        ret = await self.get_info(url)
        if ret is None:
            return await ctx.send("could not find track/playlist.")
        data, entries, single = ret
        author_str = str(ctx.author)
        self.track_queue.extend((track, author_str) for track in entries)
        await ctx.send(
            embed=mk_change_embed(
                data, entries, f"queued up {'song' if single else 'playlist'}", f"submitted by: {author_str}"
            )
        )

    @check_playing
    @check_banned
    async def volume(self, ctx, new_vol: float):

        self.volume_level = max(0, min(500, new_vol))
        ctx.voice_client.source.volume = self.volume_level / 100
        await ctx.send(f"changed volume to {self.volume_level}%.")

    @check_playing
    @check_banned
    async def stop(self, ctx):

        self.looping_track = False
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()

    @check_playing
    @check_banned
    async def skip(self, ctx, queue_amount: int):

        if queue_amount < 0:
            return await ctx.send("cannot skip a negative amount of tracks.")
        len_q: int = len(self.track_queue)
        if (not self.looping_queue) and queue_amount > len_q:
            return await ctx.send(f"cannot skip more tracks than there are tracks in the queue ({len_q}).")
        self.looping_track = False
        for _ in range(queue_amount % (len_q + 1)):
            self.backup.append(self.track_queue.popleft())
        ctx.voice_client.stop()
        await ctx.send(f"skipped current track{f' and {queue_amount} more from the queue' if queue_amount else ''}.")

    @check_playing
    @check_banned
    async def backtrack(self, ctx, queue_amount: Optional[int]):

        if queue_amount is None:
            queue_amount = 0 if self.compute_curr_time(ctx.voice_client.is_paused()) > 10 else 1

        queue_amount += 1

        if queue_amount < 1:
            return await ctx.send("cannot rewind to less than one track ago.")
        if queue_amount > len(self.backup):
            return await ctx.send(f"cannot rewind to more than {len(self.backup)} tracks.")

        self.looping_track = False
        for _ in range(queue_amount):
            self.track_queue.appendleft(self.backup.pop())
        ctx.voice_client.stop()
        await ctx.send(
            f"moved backwards by {queue_amount - 1} track{'s' if queue_amount == 2 else ''} in the queue."
            if queue_amount > 1
            else "restarted currently playing track."
        )

    @check_playing
    @check_banned
    async def pause(self, ctx):

        ctx.voice_client.pause()
        self.pause_start = time.perf_counter()
        await ctx.send("paused current track.")

    async def resume(self, ctx):

        if ctx.voice_client is None or not ctx.voice_client.is_paused():
            await ctx.send("bot is not currently paused in a voice channel.")
        elif ctx.author.voice is None:
            await ctx.send("you must be in a voice channel to do this.")
        elif ctx.author.voice.channel != ctx.voice_client.channel:
            if len(ctx.voice_client.channel.members) > 1:
                return await ctx.send("you must be listening to music with the bot do this.")
            await ctx.voice_client.move_to(ctx.author.voice.channel)
            self.resume_playing(ctx)
            await ctx.send("moved to your channel, and resumed current track.")
        else:
            self.resume_playing(ctx)
            await ctx.send("resumed current track.")


def setup(bot):
    bot.add_cog(Music(bot))
