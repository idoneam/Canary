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
from functools import wraps
from collections import deque
import discord
import youtube_dl
from discord.ext import commands

FFMPEG_OPTS = "-nostats -loglevel quiet -vn"

YTDL = youtube_dl.YoutubeDL({
    "format": "bestaudio/best",
    "restrictfilenames": True,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "geo_bypass": True,
})


def check_playing(func):
    @wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        await ctx.trigger_typing()
        if self.playing is None or ctx.voice_client is None or (
                not self.song_lock.locked()) or (
                    not ctx.voice_client.is_playing()):
            await ctx.send(
                "bot is not currently playing anything to a voice channel.")
        elif (ctx.author.voice is None
              or ctx.author.voice.channel != ctx.voice_client.channel):
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

    async def get_info(self, url):
        return await self.bot.loop.run_in_executor(
            None, lambda: YTDL.extract_info(url, download=False))

    @commands.command()
    async def play(self, ctx, *, url: str = None):
        """Streams from a youtube url or track name, or if none is given, from the queue"""

        play_queue: bool = ctx.voice_client is None

        if ctx.author.voice is None:
            await ctx.send(
                "you are not currently connected to a voice channel.")
            return

        if play_queue and url is None:
            await ctx.send("you did not specify a song to play.")
            return

        if not play_queue:
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
                self.song_queue.insert(0, track)
            if not play_queue:
                ctx.voice_client.stop()

        if play_queue:
            await ctx.author.voice.channel.connect()

            while True:
                await self.song_lock.acquire()
                await ctx.trigger_typing()
                if ((not self.song_queue) and
                    (self.looping is None)) or ctx.voice_client is None:
                    break
                self.playing = self.looping or self.song_queue.popleft()
                ctx.voice_client.play(discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(self.playing["url"],
                                           options=FFMPEG_OPTS)),
                                      after=release_lock)
                await ctx.send(
                    f"now playing: `{self.playing.get('title') or 'title not found'}`."
                )

            if ctx.voice_client is not None:
                await ctx.voice_client.disconnect()
                await ctx.send("queue is empty, finished playing all songs.")
            else:
                await ctx.send("stopped playing, disconnected.")

            self.playing = None
            self.song_lock.release()

    @commands.command()
    @check_playing
    async def loop(self, ctx):
        """Changes looping state"""

        self.looping = self.playing if self.looping is None else None
        await ctx.send(
            f"`{self.playing.get('title') or 'title not found'}` is now set to{' ' if self.looping else ' no longer '}loop."
        )

    @commands.command(aliases=["pq"])
    async def print_queue(self, ctx):
        """Displays the current song queue"""

        await ctx.trigger_typing()
        await ctx.send(
            "```\n" +
            "\n".join(f"[{index}] {track.get('title') or 'title not found'}"
                      for index, track in enumerate(self.song_queue)) +
            "\n```" if self.song_queue else "no songs currently in queue.")

    @commands.command(aliases=["ms", "currently_playing", "cps"])
    async def music_status(self, ctx):
        """Displays the currently playing song"""

        if ctx.voice_client is None:
            await ctx.send("bot is not currently playing anything.")
        elif ctx.voice_client.is_paused():
            await ctx.send(
                f"currently playing (paused){' on loop' if self.looping else ''}: `{self.playing.get('title') or 'title not found'}`."
            )
        elif ctx.voice_client.is_playing():
            await ctx.send(
                f"currently playing{' on loop' if self.looping else ''}: `{self.playing.get('title') or 'title not found'}`."
            )
        else:
            await ctx.send(
                "bot connected to voice, but not currently playing anything (should never happen)."
            )

    @commands.command(aliases=["rs"])
    async def remove_song(self, ctx, song_index: int):
        """Remove a song from the song queue by index"""

        await ctx.trigger_typing()
        if song_index < 0 or len(self.song_queue) <= song_index:
            await ctx.send(
                f"supplied index `{song_index}` is not valid for current queue."
            )
            return
        title = self.song_queue[song_index].get("title")
        del self.song_queue[song_index]
        await ctx.send(
            f"`{title or 'title not found'}` at index `{song_index}` was removed from the queue."
        )

    @commands.command(aliases=["iqs"])
    async def insert_song(self, ctx, song_index: int, *, url: str):
        """Insert a song into the song queue at a given index"""

        await ctx.trigger_typing()
        if song_index < 0 or len(self.song_queue) <= song_index:
            await ctx.send(
                f"supplied index `{song_index}` is not valid for current queue."
            )
            return
        data = await self.get_info(url)
        entries = data.get("entries", [data])
        for track in reversed(entries):
            self.song_queue.insert(song_index, track)
        await ctx.send(
            f"inserted playlist `{data.get('title') or 'title not found'}` at position `{song_index}`."
            if len(entries) > 1 else
            f"inserted track `{entries[0].get('title') or 'title not found'}` at position `{song_index}`."
        )

    @commands.command(aliases=["cq"])
    async def clear_queue(self, ctx):
        """Clears current song queue"""

        await ctx.trigger_typing()
        self.song_queue.clear()
        await ctx.send("cleared current song queue.")

    @commands.command(aliases=["qs"])
    async def queue_song(self, ctx, *, url):
        """Queue up a new song or a playlist"""

        await ctx.trigger_typing()
        data = await self.get_info(url)
        entries = data.get("entries", [data])
        for track in entries:
            self.song_queue.append(track)
        await ctx.send(
            f"queued up playlist: `{data.get('title') or 'title not found'}`."
            if len(entries) > 1 else
            f"queued up track: `{entries[0].get('title') or 'title not found'}`."
        )

    @commands.command(aliases=["vol"])
    @check_playing
    async def volume(self, ctx, volume: int):
        """Set volume to a different level"""

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"changed volume to {volume}%.")

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

        await ctx.trigger_typing()
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
