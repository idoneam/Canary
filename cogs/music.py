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
from inspect import getdoc
from functools import partial
from collections import deque
from typing import Callable, Optional, Iterable
import discord
import yt_dlp
from discord.ext import commands
from .utils.music_helpers import (
    FFMPEG_BEFORE_OPTS,
    FFMPEG_OPTS,
    YTDL,
    QUEUE_ACTIONS,
    check_playing,
    insert_converter,
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
        self.track_history: deque = deque()
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
        return (self.pause_start if paused else time.perf_counter()) - self.track_start_time

    def total_queue(self) -> Iterable:
        return chain(self.track_queue, self.track_history) if self.looping_queue else self.track_queue

    def total_len(self) -> int:
        return len(self.track_queue) + len(self.track_history) if self.looping_queue else len(self.track_queue)

    def play_track(self, ctx, *, skip_str: Optional[str] = None, delta: int = 0):
        ctx.voice_client.play(
            discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    self.playing[0]["url"],
                    before_options=FFMPEG_BEFORE_OPTS if skip_str is None else f"{FFMPEG_BEFORE_OPTS} -ss {skip_str}",
                    options=f'-filter:a "{self.speed_flag}" {FFMPEG_OPTS}',
                ),
                self.volume_level / 100,
            ),
            after=self.release_lock,
        )
        self.track_start_time = time.perf_counter() - delta

    def from_total(self, idx):
        q_len: int = self.total_len()
        if idx >= q_len or idx < -q_len:
            return None
        idx = idx % q_len
        return (
            (self.track_queue, idx)
            if (idx < len(self.track_queue))
            else (self.track_history, idx - len(self.track_queue))
        )

    def subc_decision(self, subc: str) -> tuple[Callable, Optional[Callable]]:
        match subc:
            case "play":
                return (self.play, lambda x: x)
            case "playback_speed" | "playbackspeed" | "ps" | "speed":
                return (self.playback_speed, conv_arg(float, True))
            case "goto_time" | "gototime" | "gt":
                return (self.goto_time, conv_arg(lambda x: x, True))
            case "forward_time" | "forwardtime" | "ft":
                return (self.forward_time, conv_arg(lambda x: x, True))
            case "backward_time" | "backwardtime" | "bt" | "rewind":
                return (self.backward_time, conv_arg(lambda x: "30" if x is None else x, False))
            case "loop":
                return (self.loop, conv_arg(lambda x: x, True))
            case "print_queue" | "printqueue" | "pq":
                return (self.print_queue, conv_arg(lambda x: 0 if x is None else int(x), False))
            case "status" | "now_playing" | "nowplaying" | "np":
                return (self.music_status, None)
            case "remove" | "pop":
                return (self.remove_track, conv_arg(int, True))
            case "insert":
                return (self.insert_track, conv_arg(insert_converter, True))
            case "clear_queue" | "clearqueue" | "cq":
                return (self.clear_queue, None)
            case "clear_hist" | "clearhist" | "ch":
                return (self.clear_hist, None)
            case "queue" | "q":
                return (self.queue_track, lambda x: x)
            case "volume" | "vol" | "v":
                return (self.volume, conv_arg(lambda x: float(x.strip("%")), True))
            case "stop":
                return (self.stop, None)
            case "skip" | "next":
                return (self.skip, conv_arg(lambda x: 0 if x is None else int(x), False))
            case "back" | "previous":
                return (self.backtrack, conv_arg(lambda x: None if x is None else int(x), False))
            case "pause":
                return (self.pause, None)
            case "resume":
                return (self.resume, None)
            case _:
                raise ValueError

    @commands.command(aliases=["m"])
    async def music(self, ctx, subcommand: Optional[str] = None, *, args: Optional[str] = None):
        """
        monocommand used for music features.
        use `music help subcommand` for details on how each command works (arguments are shown as semicolon separated list).
        available subcommands are:
        - `play` (note: this will interrupt the currently playing song)
        - `playback_speed` | `playbackspeed` | `speed` | `ps`
        - `goto_time` | `gototime` | `gt`
        - `forward_time` | `forwardtime` | `ft`
        - `backward_time` | `backwardtime` | `bt` | `rewind`
        - `loop`
        - `print_queue` | `printqueue` | `pq`
        - `status` | `now_playing` | `nowplaying` | `np`
        - `remove` | `pop`
        - `insert`
        - `clear_queue` | `clearqueue` | `cq`
        - `clear_history` | `clearhistory` | `ch`
        - `queue` | `q`
        - `volume` | `vol` | `v`
        - `stop`
        - `skip` | `next`
        - `back` | `previous`
        - `pause`
        - `resume`
        - `help`
        """

        if subcommand is None:
            return await ctx.send(self.music.help)
        if subcommand == "help":
            if args is None:
                return await ctx.send(self.music.help)
            try:
                fn, _ = self.subc_decision(args)
            except ValueError:
                return await ctx.send(f"music subcommand `{args}` could not be found.")
            return await ctx.send(getdoc(fn))

        try:
            fn, conv = self.subc_decision(subcommand)
        except ValueError:
            return await ctx.send(f"music subcommand `{subcommand}` could not be found.")

        if conv is None:
            return await fn(ctx)
        try:
            converted = conv(args)
        except MusicArgConvertError:
            pass  # for proper argument parsing
        else:
            match converted:
                case (*_,):
                    await fn(ctx, *converted)
                case _:
                    await fn(ctx, converted)

    @check_banned
    async def play(self, ctx, url: Optional[str] = None):
        """
        streams from a youtube url or track name, or if none is given, from the queue
        arguments: (optional: link or title of track)
        """

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
            msg = await ctx.send("fetching request data, please be patient.")
            ret = await self.get_info(url)
            if ret is None:
                return await ctx.send("could not find track/playlist.")
            data, entries, single = ret
            author_str = str(ctx.author)
            self.track_queue.extendleft((track, author_str) for track in reversed(entries))
            self.looping_track = False
            if single:
                await msg.delete()
            else:
                await msg.edit(
                    content=None,
                    embed=mk_change_embed(data, entries, "playing playlist", f"submitted by: {author_str}"),
                )
            if not in_main:
                ctx.voice_client.stop()

        if not in_main:
            return

        await ctx.author.voice.channel.connect()

        while True:
            await self.track_lock.acquire()

            if ctx.voice_client is not None and len(ctx.voice_client.channel.members) == 1:
                break

            if self.skip_opts is None:

                if ctx.voice_client is None:
                    break

                if self.looping_track:
                    if self.playing is None:
                        self.playing = self.track_queue.popleft()
                        self.track_history.append(self.playing)
                    self.play_track(ctx)
                    await ctx.send(
                        embed=mk_change_embed(
                            self.playing[0], [self.playing[0]], "now playing", f"submitted by: {self.playing[1]}"
                        )
                    )
                elif not self.track_queue:
                    if not self.looping_queue:
                        break
                    self.track_queue = self.track_history
                    self.track_history = deque()
                    self.track_lock.release()
                else:
                    self.playing = self.track_queue.popleft()
                    self.track_history.append(self.playing)
                    self.play_track(ctx)
                    await ctx.send(
                        embed=mk_change_embed(
                            self.playing[0], [self.playing[0]], "now playing", f"submitted by: {self.playing[1]}"
                        )
                    )
            else:
                skip_str, delta = self.skip_opts
                self.play_track(ctx, skip_str=skip_str, delta=delta)
                if self.pause_start is not None:
                    ctx.voice_client.pause()
                    self.pause_start -= delta
                self.skip_opts = None

        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()
            await ctx.send(
                "no one is in the voice channel, disconnecting."
                if self.track_queue
                else "finished playing all tracks, disconnecting."
            )
        else:
            await ctx.send("disconnected from voice channel.")

        self.playing = None
        self.track_lock.release()
        self.volume_level = self.bot.config.music["start_vol"]
        self.speed_flag = "atempo=1"

    @check_playing
    async def playback_speed(self, ctx, speed: float):
        """
        changes track playback speed (clamped 0.25 between 4)
        arguments: (float)
        """

        self.speed_val = max(0.25, min(speed, 4.0))
        self.speed_flag = (
            f"atempo={self.speed_val}"
            if 0.5 < self.speed_val < 2
            # note: ffmpeg only allows speed changes between 0.5 and 2
            # however, ffmpeg does allow for successive chaining if speed changes
            # thus, for speed changes outside of [0.5,2], we chain two changes
            # using the sqrt of the input value, since successive changes are multiplicative
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
        """
        go to a specific timestamp in currently playing track
        arguments: (timestamp of format H:M:S)
        """
        return seconds

    @check_playing
    @check_banned
    @time_func
    def forward_time(self, seconds: int, paused: bool):
        """
        move forwards in currently playing track
        arguments: (timestamp of format H:M:S)
        """
        return max(0, round(self.compute_curr_time(paused) + seconds))

    @check_playing
    @check_banned
    @time_func
    def backward_time(self, seconds: int, paused: bool):
        """
        move backwards in currently playing track
        arguments: (timestamp of format H:M:S [defaults to 30 seconds])
        """

        return max(0, round(self.compute_curr_time(paused) - seconds))

    @check_banned
    async def loop(self, ctx, target: str):
        """
        changes looping state
        arguments: (either `track` or `queue`)
        """

        match target:
            case "queue" | "q":
                self.looping_queue = not self.looping_queue
                await ctx.send(f"queue will now{' ' if self.looping_queue else ' no longer '}loop.")
            case "track" | "t" | "song":
                self.looping_track = not self.looping_track
                await ctx.send(f"individual track will now{' ' if self.looping_track else ' no longer '}loop.")

    async def print_queue(self, ctx, start_idx: int):
        """
        displays the current track queue
        arguments: (optional: start index of message)
        """

        queue_embed = discord.Embed(
            colour=random.randint(0, 0xFFFFFF),
            title=f"track queue as of {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        )

        queue_copy = list(self.total_queue())

        if not queue_copy:
            queue_embed.add_field(name="track queue status", value="track queue is currently empty")
            return await ctx.send(embed=queue_embed)

        q_len = len(queue_copy)

        if start_idx >= q_len or start_idx < -q_len:
            return await ctx.send("start index out of bounds.")

        curr_index: int = start_idx % q_len
        change_state: bool = True
        queue_embed.description = (
            f"duration: {mk_duration_string(queue_copy)}, "
            f"length: {q_len} track{'' if q_len == 1 else 's'}"
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
        """
        displays current status of the bot
        arguments: none
        """

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
                value=(
                    f"{mk_duration_string(self.total_queue())} "
                    f"({self.total_len()} track{'' if self.total_len() == 1 else 's'})"
                ),
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
        """
        remove a track from the track queue by index
        arguments: (integer)
        """

        ltup = self.from_total(track_index)
        if ltup is None:
            return await ctx.send("insertion index out of bounds.")
        track_list, ins_index = ltup

        msg = await ctx.send("fetching request data, please be patient.")
        ret = await self.get_info(url)
        if ret is None:
            return await msg.edit(content="could not find track/playlist.")
        data, entries, single = ret
        author_str = str(ctx.author)
        for track in reversed(entries):
            track_list.insert(ins_index, (track, author_str))

        await msg.edit(
            content=None,
            embed=mk_change_embed(
                data,
                entries,
                f"inserted {'song' if single else 'playlist'} at index {track_index}",
                f"submitted by: {author_str}",
            ),
        )

    @check_banned
    async def clear_queue(self, ctx):
        """
        clears current track queue
        arguments: none
        """

        self.track_queue.clear()
        if self.looping_queue:
            self.track_history.clear()
        await ctx.send("cleared current track queue.")

    async def clear_hist(self, ctx):
        """
        clears current track history
        arguments: none
        """

        self.track_history.clear()
        await ctx.send("cleared current track history.")

    @check_banned
    async def queue_track(self, ctx, url: Optional[str]):
        """
        adds a track to the end of the queue
        arguments: (link or title of track)
        """

        if url is None:
            return await self.print_queue(ctx, 0)

        msg = await ctx.send("fetching request data, please be patient.")
        ret = await self.get_info(url)
        if ret is None:
            return await msg.edit(content="could not find track/playlist.")
        data, entries, single = ret
        author_str = str(ctx.author)
        self.track_queue.extend((track, author_str) for track in entries)
        await msg.edit(
            content=None,
            embed=mk_change_embed(
                data, entries, f"queued up {'song' if single else 'playlist'}", f"submitted by: {author_str}"
            ),
        )

    @check_playing
    @check_banned
    async def volume(self, ctx, new_vol: float):
        """
        set volume to a different level (clamped between 0% and 500%)
        arguments: (float)
        """

        self.volume_level = max(0, min(500, new_vol))
        ctx.voice_client.source.volume = self.volume_level / 100
        await ctx.send(f"changed volume to {self.volume_level}%.")

    @check_playing
    @check_banned
    async def stop(self, ctx):
        """
        stops and disconnects the bot from voice
        arguments: none
        """

        self.looping_track = False
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()

    @check_playing
    @check_banned
    async def skip(self, ctx, queue_amount: int):
        """
        skips some amount of songs in the queue
        arguments: (optional: int [defaults to 0, going forward a single track])
        """

        if queue_amount < 0:
            return await ctx.send("cannot skip a negative amount of tracks.")

        len_q: int = len(self.track_queue)
        if (not self.looping_queue) and queue_amount > len_q:
            return await ctx.send(f"cannot skip more tracks than there are tracks in the queue ({len_q}).")

        self.looping_track = False
        for _ in range(queue_amount % (len_q + 1)):
            self.track_history.append(self.track_queue.popleft())

        ctx.voice_client.stop()
        await ctx.send(f"skipped current track{f' and {queue_amount} more from the queue' if queue_amount else ''}.")

    @check_playing
    @check_banned
    async def backtrack(self, ctx, queue_amount: Optional[int]):
        """
        goes backwards in history by some amount of tracks
        arguments: (optional: int [defaults to 0 if track has been playing for more than 10 seconds, otherwise 1])
        """

        if queue_amount is None:
            queue_amount = 0 if self.compute_curr_time(ctx.voice_client.is_paused()) > 10 else 1

        queue_amount += 1

        if queue_amount < 1:
            return await ctx.send("cannot rewind to less than one track ago.")
        if queue_amount > len(self.track_history):
            return await ctx.send(f"cannot rewind to more than {len(self.track_history)} tracks.")

        self.looping_track = False
        for _ in range(queue_amount):
            self.track_queue.appendleft(self.track_history.pop())
        ctx.voice_client.stop()
        await ctx.send(
            f"moved backwards by {queue_amount - 1} track{'s' if queue_amount == 2 else ''} in the queue."
            if queue_amount > 1
            else "restarted currently playing track."
        )

    @check_playing
    @check_banned
    async def pause(self, ctx):
        """
        pauses currently playing track
        arguments: none
        """

        ctx.voice_client.pause()
        self.pause_start = time.perf_counter()
        await ctx.send("paused current track.")

    async def resume(self, ctx):
        """
        resumes currently paused track
        arguments: none
        """

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
