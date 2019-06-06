# -*- coding: utf-8 -*-
#
# Copyright (C) idoneam (2016-2019)
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

import aiohttp
import asyncio
import async_timeout


class InvalidTypeException(Exception):
    """
    Thrown when an invalid type is passed.
    """
    pass


async def fetch(url, type="content"):
    """
    Asynchronously fetch content from URL endpoint.

    Args:
        url (str): URL endpoint to fetch from.
        type (str): Specify type of content to be fetched. Default = "content". Possible = ["content", "json"]
    """
    async with aiohttp.ClientSession() as session:
        with async_timeout.timeout(10):
            async with session.get(url) as response:
                if type.lower() == "content":
                    return await response.text()
                elif type.lower() == "json":
                    return await response.json()
                else:
                    raise InvalidTypeException
