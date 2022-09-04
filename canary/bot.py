# Copyright (C) idoneam (2016-2022)
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

from canary.config import parser
from discord import Webhook, RequestsWebhookAdapter, Intents
from discord.ext import commands
from pathlib import Path

__all__ = ["Canary", "bot", "developer_role", "moderator_role", "muted_role"]

_parser = parser.Parser()
command_prefix = _parser.command_prefix

# Create parent logger, which will send all logs from the "sub-loggers"
# to the specified log file
_logger = logging.getLogger("Canary")
_logger.setLevel(_parser.log_level)
_file_handler = logging.FileHandler(filename=_parser.log_file, encoding="utf-8", mode="a")
_file_handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s: %(message)s"))
_logger.addHandler(_file_handler)

# Create dev (sub-)logger, which is where errors and messages are logged
# If a dev webhook is specified, logs sent to the dev logger will be
# sent to the webhook
_dev_logger = logging.getLogger("Canary.Dev")
_dev_logger.setLevel(_parser.log_level)

# Create mod (sub-)logger, where info for mods will be logged
# If a mod webhook is specified, logs sent to the mod logger will be
# sent to the webhook. This is always set to the INFO level, since this is
# where info for mods is logged
_mod_logger = logging.getLogger("Canary.Mod")
_mod_logger.setLevel(logging.INFO)


class _WebhookHandler(logging.Handler):
    def __init__(self, webhook_id, webhook_token, username=None):
        self.username = username or "Bot Logs"
        logging.Handler.__init__(self)
        self.webhook = Webhook.partial(webhook_id, webhook_token, adapter=RequestsWebhookAdapter())

    def emit(self, record):
        msg = self.format(record)
        self.webhook.send(f"```\n{msg}```", username=self.username)


if _parser.dev_log_webhook_id and _parser.dev_log_webhook_token:
    _dev_webhook_username = f"{_parser.bot_name} Dev Logs"
    _dev_webhook_handler = _WebhookHandler(
        _parser.dev_log_webhook_id, _parser.dev_log_webhook_token, username=_dev_webhook_username
    )
    _dev_webhook_handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s:\n%(message)s"))
    _dev_logger.addHandler(_dev_webhook_handler)

if _parser.mod_log_webhook_id and _parser.mod_log_webhook_token:
    _mod_webhook_username = f"{_parser.bot_name} Mod Logs"
    _mod_webhook_handler = _WebhookHandler(
        _parser.mod_log_webhook_id, _parser.mod_log_webhook_token, username=_mod_webhook_username
    )
    _mod_webhook_handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s:\n%(message)s"))
    _mod_logger.addHandler(_mod_webhook_handler)


class Canary(commands.Bot):
    SCHEMA_PATH = Path(__file__).parent / "Martlet.schema"

    def __init__(self, *args, **kwargs):
        super().__init__(command_prefix, *args, **kwargs)
        self.logger = _logger
        self.dev_logger = _dev_logger
        self.mod_logger = _mod_logger
        self.config = _parser

    async def start(self, *args, **kwargs):  # TODO: discordpy 2.0: use setup_hook for database setup
        await self._start_database()
        await super().start(*args, **kwargs)

    @contextlib.asynccontextmanager
    async def db(self) -> aiosqlite.Connection:
        conn: aiosqlite.Connection
        async with aiosqlite.connect(self.config.db_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            yield conn

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
