#!/usr/bin/env python3
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

from discord.ext import commands

from config import parser
import logging
import sqlite3
import traceback

# For log webhook
import requests
from discord import Webhook, RequestsWebhookAdapter

__all__ = ['bot', 'developer_role', 'moderator_role']

_parser = parser.Parser()
command_prefix = _parser.command_prefix

_logger = logging.getLogger('Canary')
_logger.setLevel(_parser.log_level)
_file_handler = logging.FileHandler(filename=_parser.log_file,
                                    encoding='utf-8',
                                    mode='a')
_file_handler.setFormatter(
    logging.Formatter('[%(levelname)s] %(asctime)s: %(message)s'))
_logger.addHandler(_file_handler)


class _WebhookHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.webhook = Webhook.partial(_parser.log_webhook_id,
                                       _parser.log_webhook_token,
                                       adapter=RequestsWebhookAdapter())

    def emit(self, record):
        msg = self.format(record)
        self.webhook.send(f"```\n{msg}```",
                          username=f"{_parser.bot_name} Logs")


if _parser.log_webhook_id and _parser.log_webhook_token:
    _webhook_handler = _WebhookHandler()
    _webhook_handler.setFormatter(
        logging.Formatter('[%(levelname)s] %(asctime)s:\n%(message)s'))
    _logger.addHandler(_webhook_handler)


class Canary(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(command_prefix, *args, **kwargs)
        self.logger = _logger
        self.config = _parser
        self._start_database()

    def _start_database(self):
        if not self.config.db_path:
            self.logger.warning('No path to database configuration file')
            return

        self.logger.debug('Initializing SQLite database')
        conn = sqlite3.connect(self.config.db_path)
        c = conn.cursor()
        with open(self.config.db_schema_path) as fp:
            c.executescript(fp.read())
        conn.commit()
        conn.close()
        self.logger.debug('Database is ready')

    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""

        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (commands.CommandNotFound, commands.UserInputError)
        error = getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send('{} has been disabled.'.format(ctx.command))

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.author.send(
                    '{} can not be used in Private Messages.'.format(
                        ctx.command))
            except Exception:
                pass

        elif isinstance(error, commands.BadArgument):
            if ctx.command.qualified_name == 'tag list':
                return await ctx.send(
                    'I could not find that member. Please try again.')

        self.logger.error('Ignoring exception in command {}:'.format(
            ctx.command))
        self.logger.error(''.join(
            traceback.format_exception(type(error), error,
                                       error.__traceback__)))


# predefined variables to be imported
bot = Canary(case_insensitive=True)
moderator_role = bot.config.moderator_role
developer_role = bot.config.developer_role
