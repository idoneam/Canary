import os
from time import time
from typing import Optional
import discord
from .requests import fetch
from functools import wraps


def site_save(link):
    def deco(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except Exception as exception:
                fname: str = f"data/runtime/crash_dump_{func.__name__}_{time()}.html"
                if self.bot.dev_logger.handlers:
                    with open(fname, "w") as crash_file:
                        crash_file.write(await fetch(link))
                    self.bot.dev_logger.handlers[0].webhook.send(
                        file=discord.File(fname),
                        username=self.bot.dev_logger.handlers[0].username)
                    os.remove(fname)
                raise exception

        return wrapper

    return deco
