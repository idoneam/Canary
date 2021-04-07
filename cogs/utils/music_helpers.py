import time
from functools import wraps
import youtube_dl

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
    "⏩": lambda _i, m: m,
}


def check_playing(func):
    @wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        if (self.playing is None or ctx.voice_client is None
                or (not self.song_lock.locked())):
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


def mk_title_string(inf_dict) -> str:
    url = inf_dict.get("webpage_url")
    return (inf_dict.get("title", "title not found") if url is None else
            f"[{inf_dict.get('title', 'title not found')}]({url})")


def mk_duration_string(inf_dict) -> str:
    total: int = 0
    for track in inf_dict.get("entries", [inf_dict]):
        dur = track.get("duration")
        if dur is None:
            return "duration not found"
        total += dur
    return time.strftime(
        "%H:%M:%S", time.gmtime(total)) if total > 0 else "n/a (livestream)"


def parse_time(time_str: str) -> int:
    total: int = 0
    for index, substr in enumerate(reversed(time_str.split(":"))):
        if substr.isdigit():
            total += int(substr) * (60**index)
        else:
            raise ValueError
    return total


def time_func(func):
    async def wrapper(self, ctx, time_str: str):
        try:
            parsed = parse_time(time_str)
        except ValueError:
            await ctx.send(f"could not parse `{time_str}` to a time value.")
            return
        seconds = func(self, parsed)
        self.skip_opts = time.strftime("%H:%M:%S",
                                       time.gmtime(seconds)), seconds
        ctx.voice_client.stop()
        await ctx.send(
            f"moved to `{self.skip_opts[0]}` in currently playing track.")

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__

    return wrapper
