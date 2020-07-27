# Copyright (C) idoneam (2016-2020)
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
import functools
from typing import Callable

__all__ = [
    "CanarySubscriberException",
    "canary_subscriber",
]


class CanarySubscriberException(Exception):
    pass


NO_BOT = CanarySubscriberException("Could not get bot from wrapped function")


def canary_subscriber(sleep_time: int):
    def _canary_subscriber(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not args:
                raise NO_BOT

            try:
                bot = getattr(args[0], "bot")
            except AttributeError:
                raise NO_BOT

            await bot.wait_until_ready()
            while not bot.is_closed():
                try:
                    await func(*args, **kwargs)
                except Exception as e:
                    bot.logger.error("Subscriber encountered error:")
                    bot.log_traceback(e)
                await asyncio.sleep(sleep_time)

        return wrapper

    return _canary_subscriber
