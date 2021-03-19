import os
from time import time
from typing import Optional
import discord
from .requests import fetch
from functools import wraps


def site_save(link):
    def deco(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            try:
                return await func(self, ctx, *args, **kwargs)
            except Exception as exception:
                fname: str = f"data/runtime/crash_dump_{time()}.html"
                dump_channel: Optional[discord.TextChannel] = None
                for channel in ctx.guild.text_channels:
                    if channel.name == "marty_dev_log":
                        dump_channel = channel
                if dump_channel:
                    with open(fname, "w") as crash_file:
                        crash_file.write(await fetch(link))
                    await dump_channel.send(file=discord.File(fname))
                    os.remove(fname)
                raise exception

        return wrapper

    return deco
