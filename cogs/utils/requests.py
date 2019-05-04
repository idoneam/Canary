import aiohttp
import asyncio
import async_timeout


class InvalidTypeException(Exception)
    """
    Thrown when an invalid type is passed.
    """
    pass


async def fetch(url, type: str):
    """
    Helper function asynchronously fetch content of a url.
    """
    async with aiohttp.ClientSession() as session:
        with async_timeout.timeout(10):
            async with session.get(url) as response:
                if type.lower() == "text":
                    return await response.text()
                elif type.lower() == "json":
                    return await response.json()
                else:
                    raise InvalidTypeException