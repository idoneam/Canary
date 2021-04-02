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

import asyncio
import random
from functools import wraps, partial
from collections import deque
import discord
import youtube_dl
from discord.ext import commands

FFMPEG_OPTS = "-nostats -loglevel quiet -vn"
FFMPEG_BEFORE_OPTS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

YTDL = youtube_dl.YoutubeDL({
    "format": "bestaudio/best",
    "restrictfilenames": True,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "geo_bypass": True,
})

QUEUE_ACTIONS = {
    "⏪": lambda _i, _m: 0,
    "◀": lambda i, _m: max(0, i - 1),
    "▶": lambda i, m: min(i + 1, m),
    "⏩": lambda _i, m: m
}


def check_playing(func):
    @wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        if self.playing is None or ctx.voice_client is None or (
                not self.song_lock.locked()):
            await ctx.send(
                "bot is not currently playing anything to a voice channel.")
        elif (ctx.author.voice is None
              or ctx.author.voice.channel != ctx.voice_client.channel) and len(
                  ctx.voice_client.channel.members) > 1:
            await ctx.send(
                "you must be listening to music with the bot do this.")
        else:
            await func(self, ctx, *args, **kwargs)

    return wrapper


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue: deque = deque()
        self.song_lock: asyncio.Lock = asyncio.Lock()
        self.playing = None
        self.looping = None
        self.volume_level: int = 100

    async def get_info(self, url: str):
        return await self.bot.loop.run_in_executor(
            None, partial(YTDL.extract_info, url, download=False))

    def check_reaction(self, embed_msg: discord.Message,
                       reaction: discord.Reaction, user: discord.User):
        return user != self.bot.user and reaction.message.id == embed_msg.id and str(
            reaction) in QUEUE_ACTIONS

    @commands.command()
    async def play(self, ctx, *, url: str = None):
        """Streams from a youtube url or track name, or if none is given, from the queue"""

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
            data = await self.get_info(url)
            entries = data.get("entries", [data])
            for track in reversed(entries):
                self.song_queue.insert(0, (track, str(ctx.author)))
            if not in_main:
                ctx.voice_client.stop()

        if in_main:
            await ctx.author.voice.channel.connect()

            while True:
                await self.song_lock.acquire()
                await ctx.trigger_typing()
                if ((not self.song_queue) and
                    (self.looping is None)) or ctx.voice_client is None:
                    break
                self.playing = self.looping or self.song_queue.popleft()
                now_playing = discord.Embed(
                    colour=random.randint(0, 0xFFFFFF),
                    title="now playing").add_field(
                        name="track title",
                        value=self.playing[0].get("title")
                        or "title not found",
                        inline=False).add_field(
                            name="volume",
                            value=f"{self.volume_level}%",
                            inline=True).add_field(
                                name="looping",
                                value="no" if self.looping is None else "yes",
                                inline=True).set_footer(
                                    text=f"submitted by: {self.playing[1]}")
                ctx.voice_client.play(discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(self.playing[0]["url"],
                                           before_options=FFMPEG_BEFORE_OPTS,
                                           options=FFMPEG_OPTS),
                    self.volume_level / 100),
                                      after=release_lock)
                await ctx.send(embed=now_playing)

            if ctx.voice_client is not None:
                await ctx.voice_client.disconnect()
                await ctx.send("queue is empty, finished playing all songs.")
            else:
                await ctx.send("stopped playing, disconnected.")

            self.playing = None
            self.song_lock.release()
            self.volume_level = 100

    @commands.command()
    @check_playing
    async def loop(self, ctx):
        """Changes looping state"""

        if self.looping is None:
            self.looping = self.playing
            await ctx.send("current song will now loop.")
        else:
            self.looping = None
            await ctx.send("current song will now no longer loop.")

    @commands.command(aliases=["pq"])
    async def print_queue(self, ctx: commands.Context):
        """Displays the current song queue"""

        queue_embed = discord.Embed(
            colour=random.randint(0, 0xFFFFFF),
            title=
            f"song queue as of {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        if not self.song_queue:
            queue_embed.add_field(name="song queue status",
                                  value="song queue is currently empty")
            await ctx.send(embed=queue_embed)
            return
        curr_index: int = 0
        change_state: bool = True
        queue_copy = list(self.song_queue)
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
                    value=track.get("title") or "title not found").set_footer(
                        text=f"submitted by: {user}")
                await queue_msg.edit(embed=queue_embed)
            try:
                react, author = await self.bot.wait_for(
                    "reaction_add",
                    timeout=60.0,
                    check=partial(self.check_reaction, queue_msg))
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
                name="track title",
                value=self.playing[0].get("title") or "title not found",
                inline=False).add_field(
                    name="volume", value=f"{self.volume_level}%",
                    inline=True).add_field(
                        name="looping",
                        value="no" if self.looping is None else "yes",
                        inline=True).set_footer(
                            text=f"submitted by: {self.playing[1]}")
            if playing:
                status_embed.insert_field_at(1,
                                             name="status",
                                             value="playing",
                                             inline=True)
            else:
                status_embed.insert_field_at(1,
                                             name="status",
                                             value="paused",
                                             inline=True)
        else:
            status_embed.add_field(
                name="status",
                value=
                "not playing but connected [ERROR STATE SHOULD NEVER OCCUR]")
        await ctx.send(embed=status_embed)

    @commands.command(aliases=["rs"])
    async def remove_song(self, ctx, song_index: int):
        """Remove a song from the song queue by index"""

        if song_index < 0 or len(self.song_queue) <= song_index:
            await ctx.send(
                f"supplied index {song_index} is not valid for current queue.")
            return
        removed = discord.Embed(
            colour=random.randint(0, 0xFFFFFF),
            title=f"removed track at index {song_index}").add_field(
                name="track name",
                value=self.song_queue[song_index][0].get("title")
                or "title not found").set_footer(
                    text=f"removed by: {ctx.author}")
        del self.song_queue[song_index]
        await ctx.send(embed=removed)

    @commands.command(aliases=["iqs"])
    async def insert_song(self, ctx, song_index: int, *, url: str):
        """Insert a song into the song queue at a given index"""

        await ctx.trigger_typing()
        if song_index < 0 or len(self.song_queue) <= song_index:
            await ctx.send(
                f"supplied index {song_index} is not valid for current queue.")
            return
        data = await self.get_info(url)
        entries = data.get("entries", [data])
        author_str = str(ctx.author)
        for track in reversed(entries):
            self.song_queue.insert(song_index, (track, author_str))
        if len(entries) > 1:
            inserted = discord.Embed(
                colour=random.randint(0, 0xFFFFFF),
                title=f"inserted playlist at index {song_index}")
            inserted.add_field(name="playlist name",
                               value=data.get("title") or "title not found")
        else:
            inserted = discord.Embed(
                colour=random.randint(0, 0xFFFFFF),
                title=f"inserted track at index {song_index}")
            inserted.add_field(name="track name",
                               value=entries[0].get("title")
                               or "title not found")
        inserted.set_footer(text=f"submitted by: {author_str}")
        await ctx.send(embed=inserted)

    @commands.command(aliases=["cq"])
    async def clear_queue(self, ctx):
        """Clears current song queue"""

        self.song_queue.clear()
        await ctx.send("cleared current song queue.")

    @commands.command(aliases=["qs"])
    async def queue_song(self, ctx, *, url):
        """Queue up a new song or a playlist"""

        await ctx.trigger_typing()
        data = await self.get_info(url)
        entries = data.get("entries", [data])
        author_str = str(ctx.author)
        for track in entries:
            self.song_queue.append((track, author_str))
        if len(entries) > 1:
            queued = discord.Embed(colour=random.randint(0, 0xFFFFFF),
                                   title="queued up playlist")
            queued.add_field(name="playlist name",
                             value=data.get("title") or "title not found")
        else:
            queued = discord.Embed(colour=random.randint(0, 0xFFFFFF),
                                   title="queued up track")
            queued.add_field(name="track name",
                             value=entries[0].get("title")
                             or "title not found")
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
    async def skip(self, ctx):
        """Skips currently playing song"""

        self.looping = None
        ctx.voice_client.stop()
        await ctx.send("skipped current song.")

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
