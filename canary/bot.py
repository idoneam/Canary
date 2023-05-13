# Copyright (C) idoneam (2016-2023)
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

import aiosqlite
import contextlib
import logging
import traceback

from canary.config import Config
from discord import Webhook, RequestsWebhookAdapter, Intents
from discord.ext import commands
from pathlib import Path
from typing import AsyncGenerator

__all__ = ["Canary", "bot", "developer_role", "moderator_role", "muted_role"]

config = Config()
command_prefix = config.command_prefix

# Create parent logger, which will send all logs from the "sub-loggers"
# to the specified log file
logger = logging.getLogger("Canary")
logger.setLevel(config.log_level)
file_handler = logging.FileHandler(filename=config.log_file, encoding="utf-8", mode="a")
file_handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s: %(message)s"))
logger.addHandler(file_handler)

# Create dev (sub-)logger, which is where errors and messages are logged
# If a dev webhook is specified, logs sent to the dev logger will be
# sent to the webhook
dev_logger = logging.getLogger("Canary.Dev")
dev_logger.setLevel(config.log_level)

# Create mod (sub-)logger, where info for mods will be logged
# If a mod webhook is specified, logs sent to the mod logger will be
# sent to the webhook. This is always set to the INFO level, since this is
# where info for mods is logged
mod_logger = logging.getLogger("Canary.Mod")
mod_logger.setLevel(logging.INFO)


class _WebhookHandler(logging.Handler):
    def __init__(self, webhook_id, webhook_token, username=None):
        self.username = username or "Bot Logs"
        logging.Handler.__init__(self)
        self.webhook = Webhook.partial(webhook_id, webhook_token, adapter=RequestsWebhookAdapter())

    def emit(self, record):
        msg = self.format(record)
        self.webhook.send(f"```\n{msg}```", username=self.username)


if config.dev_log_webhook_id and config.dev_log_webhook_token:
    dev_webhook_username = f"{config.bot_name} Dev Logs"
    dev_webhook_handler = _WebhookHandler(
        config.dev_log_webhook_id, config.dev_log_webhook_token, username=dev_webhook_username
    )
    dev_webhook_handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s:\n%(message)s"))
    dev_logger.addHandler(dev_webhook_handler)

if config.mod_log_webhook_id and config.mod_log_webhook_token:
    mod_webhook_username = f"{config.bot_name} Mod Logs"
    mod_webhook_handler = _WebhookHandler(
        config.mod_log_webhook_id, config.mod_log_webhook_token, username=mod_webhook_username
    )
    mod_webhook_handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s:\n%(message)s"))
    mod_logger.addHandler(mod_webhook_handler)


class Canary(commands.Bot):
    SCHEMA_PATH = Path(__file__).parent / "Martlet.schema"

    def __init__(self, *args, **kwargs):
        super().__init__(command_prefix, *args, **kwargs)
        self.logger = logger
        self.dev_logger = dev_logger
        self.mod_logger = mod_logger
        self.config = config

    async def start(self, *args, **kwargs):  # TODO: discordpy 2.0: use setup_hook for database setup
        await self._start_database()
        await super().start(*args, **kwargs)
        await self.health_check()

    @contextlib.asynccontextmanager
    async def db(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        conn: aiosqlite.Connection
        async with aiosqlite.connect(self.config.db_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            yield conn

    async def db_nocm(self) -> aiosqlite.Connection:
        return await aiosqlite.connect(self.config.db_path)

    async def _start_database(self):
        if not self.config.db_path:
            self.dev_logger.warning("No path to database configuration file")
            return

        self.dev_logger.debug("Initializing SQLite database")

        db: aiosqlite.Connection
        async with self.db() as db:
            with open(Canary.SCHEMA_PATH) as fp:
                await db.executescript(fp.read())
                await db.commit()

        self.dev_logger.debug("Database is ready")

    async def health_check(self):
        guild = self.get_guild(self.config.server_id)
        if not guild:
            self.dev_logger.error(f"Could not get guild for bot (specified server ID {self.config.server_id})")

    def log_traceback(self, exception):
        self.dev_logger.error("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))

    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""

        if hasattr(ctx.command, "on_error"):
            return

        ignored = (commands.CommandNotFound, commands.UserInputError)
        error = getattr(error, "original", error)

        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send(f"{ctx.command} has been disabled.")

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.author.send(f"{ctx.command} can not be used in Private Messages.")
            except Exception:
                pass

        elif isinstance(error, commands.BadArgument):
            if ctx.command.qualified_name == "tag list":
                return await ctx.send("I could not find that member. Please try again.")

        elif isinstance(error, commands.MaxConcurrencyReached):
            return await ctx.send(
                f"The {ctx.command} command cannot be used "
                f"more than {error.number} "
                f"time{'s' if error.number != 1 else ''} "
                f"per {error.per.name}"
            )

        self.dev_logger.error(f"Ignoring exception in command {ctx.command}:")
        self.log_traceback(error)


# predefined variables to be imported
intents = Intents.default()
intents.members = True
intents.presences = True
bot = Canary(case_insensitive=True, intents=intents)
moderator_role = bot.config.moderator_role
developer_role = bot.config.developer_role
muted_role = bot.config.muted_role
