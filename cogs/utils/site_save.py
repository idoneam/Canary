import os
from time import time
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
                fname = f"data/runtime/crash_dump_{time()}.html"
                with open(fname, "w") as crash_file:
                    crash_file.write(await fetch(link))
                self.bot.dev_logger.webhook_handler.webhook.send(
                    file=discord.File(fname),
                    username=self.bot.dev_logger.webhook_handler.username)
                os.remove(fname)
                raise exception

        return wrapper

    return deco
