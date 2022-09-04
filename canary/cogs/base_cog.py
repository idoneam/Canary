import aiosqlite
import contextlib
import discord
import os

from discord.ext import commands
from typing import AsyncGenerator, Iterable

from ..bot import Canary

__all__ = [
    "CanaryCog",
]


class CanaryCog(commands.Cog):
    def __init__(self, bot: Canary):
        self.bot: Canary = bot
        self.guild: discord.Guild | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.bot.config.server_id)

        # Make temporary directory, used mostly by images cog
        if not os.path.exists("./tmp/"):
            os.mkdir("./tmp/", mode=0o755)

    @contextlib.asynccontextmanager
    async def db(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        async with self.bot.db() as conn:
            yield conn

    async def fetch_list(
        self,
        query: str,
        params: tuple[str | int | float | bool, ...] = (),
        db: aiosqlite.Connection | None = None,
    ) -> list[tuple]:
        if fresh_db := db is None:
            db = await self.bot.db_nocm()
        try:
            async with db.execute(query, params) as c:
                return [tuple(r) for r in await c.fetchall()]
        finally:
            if fresh_db:
                await db.close()

    async def get_settings_key(self, key: str) -> str | None:
        db: aiosqlite.Connection
        async with self.db() as db:
            c: aiosqlite.Cursor
            async with db.execute("SELECT Value FROM Settings WHERE Key = ?", (key,)) as c:
                fetched = await c.fetchone()
                return fetched[0] if fetched is not None else None

    async def set_settings_key(self, key: str, value: str, pre_commit: Iterable | None = None) -> None:
        db: aiosqlite.Connection
        async with self.db() as db:
            c: aiosqlite.Cursor
            await db.execute("REPLACE INTO Settings VALUES (?, ?)", (key, value))

            if pre_commit:
                for s in pre_commit:
                    await db.execute(s)

            await db.commit()

    async def del_settings_key(self, key: str, pre_commit: Iterable | None = None) -> None:
        db: aiosqlite.Connection
        async with self.db() as db:
            c: aiosqlite.Cursor
            await db.execute("DELETE FROM Settings WHERE Key = ? LIMIT 1", (key,))

            if pre_commit:
                for s in pre_commit:
                    await db.execute(s)

            await db.commit()
