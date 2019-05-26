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

import asyncio
import discord
from discord.ext import commands

from config import parser
import logging
import sqlite3

_parser = parser.Parser()
command_prefix = _parser.command_prefix

_logger = logging.getLogger('discord')
_logger.setLevel(_parser.log_level)
_handler = logging.FileHandler(
    filename=_parser.log_file, encoding='utf-8', mode='a')
_handler.setFormatter(
    logging.Formatter('[%(levelname)s] %(asctime)s: %(message)s'))
_logger.addHandler(_handler)


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

        self.logger.info('Initializing SQLite database')
        conn = sqlite3.connect(self.config.db_path)
        c = conn.cursor()
        with open(self.config.db_schema_path) as fp:
            c.executescript(fp.read())
        conn.commit()
        conn.close()
        self.logger.info('Database is ready')