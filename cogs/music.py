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

DISABLE_FFMPEG_VID = {"options": "-vn"}

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

    @commands.command()
    async def play(self, ctx: commands.Context, *, url=None):
        """Streams from a url or name"""

        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send(
                    "you are not currently connected to a voice channel.")
                return
        else:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            if ctx.author.voice:
                ctx.voice_client.move_to(ctx.author.voice.channel)

        song_lock = asyncio.Lock()

        def after_check(_):
            song_lock.release()

        if url:
            await song_lock.acquire()
            await ctx.trigger_typing()
            data = await self.bot.loop.run_in_executor(
                None, lambda: YTDL.extract_info(url, download=False))
            if "entries" in data:
                self.song_queue.extend(data["entries"])
                if len(data["entries"]) > 1:
                    await ctx.send(f"queued up playlist: {data.get('title')}")
                data = self.song_queue.pop()
            player = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(data["url"], **DISABLE_FFMPEG_VID))
            ctx.voice_client.play(player, after=after_check)
            await ctx.send(f"now playing: {data.get('title')}")

        while self.song_queue and ctx.voice_client:
            await song_lock.acquire()
            await ctx.trigger_typing()
            data = self.song_queue.pop()
            player = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(data["url"], **DISABLE_FFMPEG_VID))
            ctx.voice_client.play(player, after=after_check)
            await ctx.send(f"now playing: {data.get('title')}")

        await song_lock.acquire()
        await ctx.voice_client.disconnect()

    @commands.command(aliases=["pq"])
    async def print_queue(self, ctx):
        """Prints the current song queue"""

        await ctx.send(
            "```\n" +
            "\n".join(f"[{index}] {song.get('title') or 'title not found'}"
                      for index, song in enumerate(self.song_queue)) +
            "\n```" if self.song_queue else "no songs currently in queue")

    @commands.command(aliases=["rs"])
    async def remove_song(self, ctx, song_index: int):
        """Remove a song from the song queue by index"""

        await ctx.trigger_typing()
        if 0 <= song_index < len(self.song_queue):
            del self.song_queue[song_index]
            await ctx.send(
                f"song at index `{song_index}` was removed from the queue")
        else:
            await ctx.send(
                f"supplied index: `{song_index}` is not valid for current queue"
            )

    @commands.command(aliases=["cq"])
    async def clear_queue(self, ctx):
        """Clears current song queue"""

        await ctx.trigger_typing()
        self.song_queue.clear()
        await ctx.send("cleared current song queue")

    @commands.command(aliases=["qs"])
    async def queue_song(self, ctx, *, url):
        """Queue up a new song or a playlist"""

        await ctx.trigger_typing()
        data = await self.bot.loop.run_in_executor(
            None, lambda: YTDL.extract_info(url, download=False))
        if "entries" in data:
            if len(data["entries"]) > 1:
                self.song_queue.extendleft(reversed(data["entries"]))
                await ctx.send(f"queued up playlist: {data.get('title')}")
            else:
                data = data["entries"][0]
                self.song_queue.appendleft(data)
                await ctx.send(f"queued up audio: {data.get('title')}")
        else:
            self.song_queue.appendleft(data)
            await ctx.send(f"queued up audio: {data.get('title')}")

    @commands.command()
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
