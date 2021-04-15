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

# TODO: add playlist looping, speed, current song time to music status
# TODO: add playlist sum length to print queue
# TODO: add playlist declaration to play
# TODO: maintain pause on goto
# TODO: clean up code + further testing

import asyncio
import random
import time
from functools import partial
from collections import deque
from typing import Optional
import discord
import youtube_dl
from discord.ext import commands
from .utils.music_helpers import (FFMPEG_BEFORE_OPTS, FFMPEG_OPTS, YTDL,
                                  QUEUE_ACTIONS, check_playing, parse_time,
                                  mk_title_string, mk_duration_string,
                                  time_func)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue: deque = deque()
        self.backup: deque = deque()
        self.loop_queue: bool = False
        self.song_lock: asyncio.Lock = asyncio.Lock()
        self.playing = None
        self.looping = None
        self.volume_level: int = 100
        self.speed_flag: str = "atempo=1"
        self.skip_opts: Optional[tuple[str, int]] = None
        self.song_start_time: float = 0
        self.ban_role = self.bot.config.music["ban_role"]

    async def get_info(self, url: str):
        return await self.bot.loop.run_in_executor(
            None, partial(YTDL.extract_info, url, download=False))

    def check_reaction(self, embed_msg: discord.Message,
                       reaction: discord.Reaction, user: discord.User):
        return (user != self.bot.user and reaction.message.id == embed_msg.id
                and str(reaction) in QUEUE_ACTIONS)

    @commands.command()
    async def play(self, ctx, *, url: str = None):
        """Streams from a youtube url or track name, or if none is given, from the queue"""

        if discord.utils.get(ctx.author.roles, name=self.ban_role):
            await ctx.send("you cannot decide which songs to play.")
            return

        in_main: bool = ctx.voice_client is None

        if ctx.author.voice is None:
            await ctx.send(
                "you are not currently connected to a voice channel.")
            return

        if in_main and (not self.song_queue) and url is None:
            await ctx.send("you did not specify a song to play.")
            return

        if not in_main:
            if ctx.voice_client.is_paused():
                await ctx.send(
                    "bot is currently paused, please use `resume` before playing."
                )
                return
            if ctx.author.voice.channel != ctx.voice_client.channel:
                if len(ctx.voice_client.channel.members) > 1:
                    await ctx.send(
                        "bot is currently playing music for users in another voice channel."
                    )
                    return
                ctx.voice_client.pause()
                await ctx.voice_client.move_to(ctx.author.voice.channel)
                if not url:
                    ctx.voice_client.resume()
            elif url is None:
                await ctx.send(
                    "bot is currently playing a song and you did not specify a new song to play."
                )
                return

        def release_lock(_):
            self.song_lock.release()

        if url:
            await ctx.trigger_typing()
            try:
                data = await self.get_info(url)
            except youtube_dl.utils.DownloadError:
                await ctx.send("could not find track.")
                return
            entries = data.get("entries", [data])
            if not entries:
                await ctx.send("could not find track.")
                return
            author_str = str(ctx.author)
            self.song_queue.extendleft(
                (track, author_str) for track in reversed(entries))
            if not in_main:
                ctx.voice_client.stop()

        if not in_main:
            return

        await ctx.author.voice.channel.connect()

        while True:
            await self.song_lock.acquire()
            now_playing = None
            if self.skip_opts is None:
                await ctx.trigger_typing()
                if ctx.voice_client is None:
                    break
                if (not self.song_queue) and (self.looping is None):
                    if not self.loop_queue:
                        break
                    self.song_queue = self.backup
                    self.backup = deque()
                if self.looping is None:
                    self.playing = self.song_queue.popleft()
                    self.backup.append(self.playing)
                else:
                    self.playing = self.looping
                now_playing = discord.Embed(
                    colour=random.randint(0, 0xFFFFFF),
                    title="now playing").add_field(
                        name="track title",
                        value=mk_title_string(self.playing[0]),
                        inline=False,
                    ).add_field(
                        name="volume",
                        value=f"{self.volume_level}%",
                        inline=True).add_field(
                            name="duration",
                            value=mk_duration_string(self.playing[0]),
                            inline=True,
                        ).add_field(
                            name="looping",
                            value="no" if self.looping is None else "yes",
                            inline=True,
                        ).set_footer(text=f"submitted by: {self.playing[1]}")
                ctx.voice_client.play(
                    discord.PCMVolumeTransformer(
                        discord.FFmpegPCMAudio(
                            self.playing[0]["url"],
                            before_options=FFMPEG_BEFORE_OPTS,
                            options=
                            f'-filter:a "{self.speed_flag}" {FFMPEG_OPTS}',
                        ),
                        self.volume_level / 100,
                    ),
                    after=release_lock,
                )
                self.song_start_time = time.perf_counter()
                await ctx.send(embed=now_playing)
            else:
                skip_str, delta = self.skip_opts
                ctx.voice_client.play(
                    discord.PCMVolumeTransformer(
                        discord.FFmpegPCMAudio(
                            self.playing[0]["url"],
                            before_options=
                            f"{FFMPEG_BEFORE_OPTS} -ss {skip_str}",
                            options=
                            f'-filter:a "{self.speed_flag}" {FFMPEG_OPTS}',
                        ),
                        self.volume_level / 100,
                    ),
                    after=release_lock,
                )
                self.song_start_time = time.perf_counter() - delta
            self.skip_opts = None

        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()
            await ctx.send("queue is empty, finished playing all songs.")
        else:
            await ctx.send("stopped playing, disconnected.")

        self.playing = None
        self.song_lock.release()
        self.volume_level = 100
        self.backup = deque()
        self.speed_flag = "atempo=1"

    @commands.command(aliases=["ps"])
    @check_playing
    async def playback_speed(self, ctx, speed: float):
        """Go to a specific timestamp in currently playing track (clamped 0.25 between 4)"""

        speed = max(0.25, min(speed, 4.0))
        self.speed_flag = f"atempo=sqrt({speed}),atempo=sqrt({speed})" if (
            speed > 2 or speed < 0.5) else f"atempo={speed}"
        parsed = parse_time(
            str(round(time.perf_counter() - self.song_start_time)))
        self.skip_opts = time.strftime("%H:%M:%S", time.gmtime(parsed)), parsed
        ctx.voice_client.stop()
        await ctx.send(f"changed playback speed to {speed}")

    @commands.command(aliases=["gt"])
    @check_playing
    @time_func
    def goto_time(self, seconds: int):
        """Go to a specific timestamp in currently playing track"""

        return seconds

    @commands.command(aliases=["ft"])
    @check_playing
    @time_func
    def forward_time(self, seconds: int):
        """Move forwards in currently playing track"""

        return max(0,
                   round(time.perf_counter() - self.song_start_time + seconds))

    @commands.command(aliases=["bt"])
    @check_playing
    @time_func
    def backward_time(self, seconds: int):
        """Move backwards in currently playing track"""

        return max(0,
                   round(time.perf_counter() - self.song_start_time - seconds))

    @commands.command(aliases=["sl"])
    @check_playing
    async def song_loop(self, ctx):
        """Changes song looping state"""

        if self.looping is None:
            self.looping = self.playing
            await ctx.send("current song will now loop.")
        else:
            self.looping = None
            await ctx.send("current song will now no longer loop.")

    @commands.command(aliases=["ql"])
    async def queue_loop(self, ctx):
        """Changes queue looping state"""

        self.loop_queue = not self.loop_queue
        await ctx.send(
            f"queue will now {'' if self.loop_queue else 'no longer '}loop.")

    @commands.command(aliases=["pq"])
    async def print_queue(self, ctx: commands.Context):
        """Displays the current song queue"""

        queue_embed = discord.Embed(
            colour=random.randint(0, 0xFFFFFF),
            title=
            f"song queue as of {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        )
        if not self.song_queue:
            queue_embed.add_field(name="song queue status",
                                  value="song queue is currently empty")
            await ctx.send(embed=queue_embed)
            return
        curr_index: int = 0
        change_state: bool = True
        queue_copy = list(self.song_queue +
                          self.backup if self.loop_queue else self.song_queue)
        max_index = len(queue_copy) - 1
        queue_embed.description = f"song queue length: {max_index + 1}"
        queue_msg = await ctx.send(embed=queue_embed)
        for reaction in QUEUE_ACTIONS:
            await queue_msg.add_reaction(reaction)
        while True:
            if change_state:
                queue_embed.clear_fields()
                track, user = queue_copy[curr_index]
                queue_embed.add_field(
                    name=f"track title at index {curr_index}",
                    value=mk_title_string(track),
                    inline=False).add_field(
                        name="duration",
                        value=mk_duration_string(track),
                        inline=False).set_footer(text=f"submitted by: {user}")
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
            new_index = QUEUE_ACTIONS[str(react)](curr_index, max_index)
            change_state = new_index != curr_index
            curr_index = new_index
            await react.remove(author)

    @commands.command(aliases=["ms", "currently_playing", "cps"])
    async def music_status(self, ctx):
        """Displays the currently playing song"""

        status_embed = discord.Embed(colour=random.randint(0, 0xFFFFFF),
                                     title="music status")
        if ctx.voice_client is None:
            status_embed.add_field(name="status", value="not playing")
            await ctx.send(embed=status_embed)
            return
        playing = ctx.voice_client.is_playing()
        paused = ctx.voice_client.is_paused()
        if playing or paused:
            status_embed.add_field(
                name=f"currently {'playing' if playing else 'paused'} track",
                value=mk_title_string(self.playing[0]),
                inline=False,
            ).add_field(
                name="volume", value=f"{self.volume_level}%",
                inline=True).add_field(
                    name="duration",
                    value=mk_duration_string(self.playing[0]),
                    inline=True).add_field(
                        name="looping",
                        value="no" if self.looping is None else "yes",
                        inline=True,
                    ).set_footer(text=f"submitted by: {self.playing[1]}")
        else:
            status_embed.add_field(
                name="status",
                value=
                "not playing but connected [ERROR STATE SHOULD NEVER OCCUR]",
            )
        await ctx.send(embed=status_embed)

    @commands.command(aliases=["rs"])
    async def remove_song(self, ctx, song_index: int):
        """Remove a song from the song queue by index"""

        if song_index < 0 or (len(self.song_queue) +
                              len(self.backup) if self.loop_queue else len(
                                  self.song_queue)) <= song_index:
            await ctx.send(
                f"supplied index {song_index} is not valid for current queue.")
            return

        song_list, del_index = (self.song_queue, song_index) if (
            song_index < len(self.song_queue)) else (self.backup, song_index -
                                                     len(self.song_queue))
        removed = discord.Embed(
            colour=random.randint(0, 0xFFFFFF),
            title=f"removed track at index {song_index}",
        ).add_field(
            name="track name",
            value=mk_title_string(song_list[del_index][0]),
            inline=False).add_field(
                name="duration",
                value=mk_duration_string(song_list[del_index][0]),
                inline=False).set_footer(text=f"removed by: {ctx.author}")
        del song_list[del_index]
        await ctx.send(embed=removed)

    @commands.command(aliases=["iqs"])
    async def insert_song(self, ctx, song_index: int, *, url: str):
        """Insert a song into the song queue at a given index"""

        await ctx.trigger_typing()
        if discord.utils.get(ctx.author.roles, name=self.ban_role):
            await ctx.send("you cannot add songs to the queue.")
            return
        if song_index < 0 or len(self.song_queue) <= song_index:
            await ctx.send(
                f"supplied index {song_index} is not valid for current queue.")
            return
        try:
            data = await self.get_info(url)
        except youtube_dl.utils.DownloadError:
            await ctx.send("could not find track.")
            return
        entries = data.get("entries", [data])
        if not entries:
            await ctx.send("could not find track.")
            return
        author_str = str(ctx.author)
        for track in reversed(entries):
            self.song_queue.insert(song_index, (track, author_str))
        if len(entries) > 1:
            inserted = discord.Embed(
                colour=random.randint(0, 0xFFFFFF),
                title=f"inserted playlist at index {song_index}").add_field(
                    name="playlist name",
                    value=mk_title_string(data),
                    inline=False).add_field(name="duration",
                                            value=mk_duration_string(data),
                                            inline=False)
        else:
            inserted = discord.Embed(
                colour=random.randint(0, 0xFFFFFF),
                title=f"inserted track at index {song_index}",
            ).add_field(name="track name",
                        value=mk_title_string(entries[0]),
                        inline=False).add_field(name="duration",
                                                value=mk_duration_string(
                                                    entries[0]),
                                                inline=False)
        inserted.set_footer(text=f"submitted by: {author_str}")
        await ctx.send(embed=inserted)

    @commands.command(aliases=["cq"])
    async def clear_queue(self, ctx):
        """Clears current song queue"""

        self.song_queue.clear()
        self.backup.clear()
        await ctx.send("cleared current song queue.")

    @commands.command(aliases=["qs"])
    async def queue_song(self, ctx, *, url):
        """Queue up a new song or a playlist"""

        await ctx.trigger_typing()
        if discord.utils.get(ctx.author.roles, name=self.ban_role):
            await ctx.send("you cannot add songs to the queue.")
            return
        try:
            data = await self.get_info(url)
        except youtube_dl.utils.DownloadError:
            await ctx.send("could not find track.")
            return
        entries = data.get("entries", [data])
        if not entries:
            await ctx.send("could not find track.")
            return
        author_str = str(ctx.author)
        self.song_queue.extend((track, author_str) for track in entries)
        if len(entries) > 1:
            queued = discord.Embed(colour=random.randint(0, 0xFFFFFF),
                                   title="queued up playlist").add_field(
                                       name="playlist name",
                                       value=mk_title_string(data),
                                       inline=False).add_field(
                                           name="duration",
                                           value=mk_duration_string(data),
                                           inline=False)
        else:
            queued = discord.Embed(colour=random.randint(0, 0xFFFFFF),
                                   title="queued up track").add_field(
                                       name="track name",
                                       value=mk_title_string(entries[0]),
                                       inline=False).add_field(
                                           name="duration",
                                           value=mk_duration_string(
                                               entries[0]),
                                           inline=False)
        queued.set_footer(text=f"submitted by: {author_str}")
        await ctx.send(embed=queued)

    @commands.command(aliases=["vol", "v"])
    @check_playing
    async def volume(self, ctx, new_vol: int):
        """Set volume to a different level"""

        self.volume_level = new_vol
        ctx.voice_client.source.volume = new_vol / 100
        await ctx.send(f"changed volume to {self.volume_level}%.")

    @commands.command()
    @check_playing
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        self.looping = None
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()

    @commands.command(aliases=["next"])
    @check_playing
    async def skip(self, ctx, queue_amount: int = 0):
        """
        Skips currently playing song and skips the amount
        provided in argument (if any) from the queue
        """

        if queue_amount < 0:
            await ctx.send("cannot skip a negative amount of songs.")
            return
        len_q: int = len(self.song_queue)
        if (not self.loop_queue) and queue_amount > len_q:
            await ctx.send(
                f"cannot skip more songs than there are songs in the queue ({len_q})."
            )
            return
        self.looping = None
        for _ in range(queue_amount % (len_q + 1)):
            self.backup.append(self.song_queue.popleft())
        ctx.voice_client.stop()
        await ctx.send(
            f"skipped current song{f' and {queue_amount} more from the queue' if queue_amount else ''}."
        )

    @commands.command(aliases=["prev", "previous", "rev"])
    @check_playing
    async def rewind(self, ctx, queue_amount: int = 1):
        """
        Rewinds to some amount of songs previously
        """
        queue_amount += 1

        if queue_amount < 1:
            await ctx.send("cannot rewind to less than one song ago.")
            return
        if queue_amount > len(self.backup):
            await ctx.send(
                f"cannot rewind to more than {len(self.backup)} songs.")
            return

        self.looping = None
        for _ in range(queue_amount):
            self.song_queue.appendleft(self.backup.pop())
        ctx.voice_client.stop()
        await ctx.send(
            f"moved backwards by {queue_amount-1} song{'s' if queue_amount == 2 else ''} in the queue."
        )

    @commands.command()
    @check_playing
    async def pause(self, ctx):
        """Pauses currently playing song"""

        ctx.voice_client.pause()
        await ctx.send("paused current song.")

    @commands.command()
    async def resume(self, ctx):
        """Resumes currently playing song.
        If no one else is present in the current channel, and
        author is in a different channel, moves to that one"""

        if ctx.voice_client is None or not ctx.voice_client.is_paused():
            await ctx.send("bot is not currently paused in a voice channel.")
        elif ctx.author.voice is None:
            await ctx.send("you must be in a voice channel to do this.")
        elif ctx.author.voice.channel != ctx.voice_client.channel:
            if len(ctx.voice_client.channel.members) > 1:
                await ctx.send(
                    "you must be listening to music with the bot do this.")
                return
            await ctx.voice_client.move_to(ctx.author.voice.channel)
            ctx.voice_client.resume()
            await ctx.send("moved to your channel, and resumed current song.")
        else:
            ctx.voice_client.resume()
            await ctx.send("resumed current song.")


def setup(bot):
    bot.add_cog(Music(bot))
