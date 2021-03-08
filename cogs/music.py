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


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue: deque = deque()
        self.song_lock: asyncio.Lock = asyncio.Lock()
        self.queue_lock: asyncio.Lock = asyncio.Lock()

    async def get_info(self, url):
        return await self.bot.loop.run_in_executor(
            None, lambda: YTDL.extract_info(url, download=False))

    @commands.command()
    async def play(self, ctx, *, url: str = None):
        """Streams from a youtube url or track name, or if none is given, from the queue"""

        play_queue: bool = True

        if self.song_lock.locked():
            if url is None:
                ctx.send(
                    "bot is currently playing a song and you did not specify a new song to play."
                )
                return
            play_queue = False

        if ctx.voice_client is None:
            if ctx.author.voice is None:
                await ctx.send(
                    "you are not currently connected to a voice channel.")
                return
            await ctx.author.voice.channel.connect()
        else:
            if ctx.author.voice.channel != ctx.voice_client.channel:
                await ctx.send(
                    "bot is currently connected to another voice channel.")
                return
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()

        def after_check(_):
            self.song_lock.release()

        if url:
            await self.song_lock.acquire()
            await ctx.trigger_typing()
            data = await self.get_info(url)
            if "entries" in data:
                async with self.queue_lock:
                    self.song_queue.extendleft(reversed(data["entries"]))
                    if len(data["entries"]) > 1:
                        await ctx.send(
                            f"inserted playlist `{data.get('title')}` to start"
                        )
                    data = self.song_queue.popleft()
            player = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(data["url"], options=FFMPEG_OPTS))
            if ctx.voice_client is not None:    # make sure that bot has not been disconnected from voice
                ctx.voice_client.play(player, after=after_check)
                await ctx.send(f"now playing: `{data.get('title')}`")

        if play_queue:
            while self.song_queue:
                await self.song_lock.acquire()
                if ctx.voice_client is None:    # bot has been disconnected from voice, leave the loop
                    break
                await ctx.trigger_typing()
                async with self.queue_lock:
                    data = self.song_queue.popleft()
                player = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(data["url"], options=FFMPEG_OPTS))
                if ctx.voice_client is None:    # bot has been disconnected from voice, leave the loop
                    break
                ctx.voice_client.play(player, after=after_check)
                await ctx.send(f"now playing: `{data.get('title')}`")
            if ctx.voice_client is not None:
                async with self.song_lock:
                    await ctx.voice_client.disconnect()

    @commands.command(aliases=["pq"])
    async def print_queue(self, ctx):
        """Prints the current song queue"""

        async with self.queue_lock:
            await ctx.trigger_typing()
            await ctx.send(
                "```\n" +
                "\n".join(f"[{index}] {song.get('title') or 'title not found'}"
                          for index, song in enumerate(self.song_queue)) +
                "\n```" if self.song_queue else "no songs currently in queue")

    @commands.command(aliases=["rs"])
    async def remove_song(self, ctx, song_index: int):
        """Remove a song from the song queue by index"""

        async with self.queue_lock:
            await ctx.trigger_typing()
            if song_index < 0 or len(self.song_queue) <= song_index:
                await ctx.send(
                    f"supplied index `{song_index}` is not valid for current queue"
                )
                return
            del self.song_queue[song_index]
        await ctx.send(
            f"song at index `{song_index}` was removed from the queue")

    @commands.command(aliases=["iqs"])
    async def insert_song(self, ctx, song_index: int, *, url: str):
        """Insert a song into the song queue at a given index"""

        async with self.queue_lock:
            await ctx.trigger_typing()
            if song_index < 0 or len(self.song_queue) <= song_index:
                await ctx.send(
                    f"supplied index `{song_index}` is not valid for current queue"
                )
                return
            data = await self.get_info(url)
            entries = data.get("entries", [data])
            for track in reversed(entries):
                self.song_queue.insert(song_index, track)
        await ctx.send(
            f"inserted playlist `{data.get('title')}` at position `{song_index}`"
            if len(entries) > 1 else
            f"inserted track `{entries[0].get('title')}` at position `{song_index}`"
        )

    @commands.command(aliases=["cq"])
    async def clear_queue(self, ctx):
        """Clears current song queue"""

        async with self.queue_lock:
            await ctx.trigger_typing()
            self.song_queue.clear()
        await ctx.send("cleared current song queue")

    @commands.command(aliases=["qs"])
    async def queue_song(self, ctx, *, url):
        """Queue up a new song or a playlist"""

        async with self.queue_lock:
            await ctx.trigger_typing()
            data = await self.get_info(url)
            entries = data.get("entries", [data])
            self.song_queue.extend(entries)
        await ctx.send(f"queued up playlist: `{data.get('title')}`" if len(
            entries) > 1 else f"queued up track: `{entries[0].get('title')}`")

    @commands.command(aliases=["vol"])
    async def volume(self, ctx, volume: int):
        """Set volume to a different level"""

        if ctx.voice_client is None:
            await ctx.send("bot is not currently connected to a voice channel."
                           )
            return
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"changed volume to {volume}%")

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        if ctx.voice_client is None:
            await ctx.send("bot is not currently connected to a voice channel."
                           )
            return
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()

    @commands.command()
    async def skip(self, ctx):
        """Skips currently playing song"""

        if ctx.voice_client is None:
            await ctx.send("bot is not currently connected to a voice channel."
                           )
            return
        ctx.voice_client.stop()

    @commands.command()
    async def pause(self, ctx):
        """Pauses currently playing song"""
        if ctx.voice_client is None:
            await ctx.send("bot is not currently connected to a voice channel."
                           )
            return
        ctx.voice_client.pause()

    @commands.command()
    async def resume(self, ctx):
        """Resumes currently playing song"""

        if ctx.voice_client is None:
            await ctx.send("bot is not currently connected to a voice channel."
                           )
            return
        ctx.voice_client.resume()


def setup(bot):
    bot.add_cog(Music(bot))
