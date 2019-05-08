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
