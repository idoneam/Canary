# Copyright (C) idoneam (2016-2022)
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

import time
from functools import wraps
from typing import Iterable
import yt_dlp
import discord
import random


class MusicArgConvertError(ValueError):
    pass


FFMPEG_OPTS = "-nostats -loglevel quiet -vn"
FFMPEG_BEFORE_OPTS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

YTDL = yt_dlp.YoutubeDL(
    {
        "format": "bestaudio/best",
        "restrictfilenames": True,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "geo_bypass": True,
    }
)

# dict used in print_queue subcommand, determines the next index
# based on the react (keys) and whether the message needs to change
# first argument (i) stands for index
# second argument (l) stands for length of list
QUEUE_ACTIONS = {
    "⏪": lambda i, _l: (0, i != 0),
    "◀": lambda i, l: ((i - 1) % l, True),
    "▶": lambda i, l: ((i + 1) % l, True),
    "⏩": lambda i, l: (l - 1, i != l - 1),
}


def conv_arg(conv, raise_on_none):
    def inner(trg):
        if raise_on_none and trg is None:
            raise MusicArgConvertError
        try:
            return conv(trg)
        except ValueError as e:
            raise MusicArgConvertError(e)

    return inner


def insert_converter(arg: str):
    try:
        idx, url = arg.split(maxsplit=1)
    except ValueError as e:
        raise MusicArgConvertError(e)
    return int(idx), url


def check_playing(func):
    @wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        if self.playing is None or ctx.voice_client is None or (not self.track_lock.locked()):
            await ctx.send("bot is not currently playing anything to a voice channel.")
        elif (ctx.author.voice is None or ctx.author.voice.channel != ctx.voice_client.channel) and len(
            ctx.voice_client.channel.members
        ) > 1:
            await ctx.send("you must be listening to music with the bot do this.")
        else:
            await func(self, ctx, *args, **kwargs)

    return wrapper


def mk_title_string(inf_dict: dict) -> str:
    url = inf_dict.get("webpage_url")
    return (
        inf_dict.get("title", "title not found")
        if url is None
        else "[{}]({})".format(
            inf_dict.get("title", "title not found")
            .replace("*", "\\*")
            .replace("|", "\\|")
            .replace("_", "\\_")
            .replace("~", "\\~"),
            url,
        )
    )


def mk_duration_string(track_iter: Iterable) -> str:
    total: int = 0
    for track in track_iter:
        if isinstance(track, tuple):
            track = track[0]
        dur = track.get("duration")
        if dur is None:
            return "n/a (livestream)"
        total += dur
    return time.strftime("%H:%M:%S", time.gmtime(total)) if (total > 0 or not list(track_iter)) else "n/a (livestream)"


def parse_time(time_str: str) -> int:
    total_seconds: int = 0
    for index, substr in enumerate(reversed(time_str.split(":"))):
        if substr.isdigit():
            total_seconds += int(substr) * (60**index)
        else:
            raise ValueError
    return total_seconds


def time_func(func):
    async def wrapper(self, ctx, time_str: str):
        try:
            parsed = parse_time(time_str)
        except ValueError:
            await ctx.send(f"could not parse `{time_str}` to a time value.")
            return
        seconds = func(self, parsed, ctx.voice_client.is_paused())
        self.skip_opts = time.strftime("%H:%M:%S", time.gmtime(seconds)), seconds
        self.track_start_time = time.perf_counter() - seconds
        ctx.voice_client.stop()
        await ctx.send(f"moved to `{self.skip_opts[0]}` in currently playing track.")

    # note: not using functools.wraps so that
    # function type signature gets changed
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__

    return wrapper


def mk_change_embed(data, track_list, title_str: str, footer_str: str) -> discord.Embed:
    return (
        discord.Embed(
            colour=random.randint(0, 0xFFFFFF),
            title=title_str,
        )
        .add_field(name="track name", value=mk_title_string(data), inline=False)
        .add_field(name="duration", value=mk_duration_string(track_list), inline=False)
        .set_footer(text=footer_str)
    )


def check_banned(func):
    @wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        if discord.utils.get(ctx.author.roles, name=self.ban_role):
            return await ctx.send(f"you have the role `{self.ban_role}`, you are not allowed to do this.")
        return await func(self, ctx, *args, **kwargs)

    return wrapper
