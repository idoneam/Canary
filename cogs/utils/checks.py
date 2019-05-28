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

import discord
from discord.ext import commands

from Main import developer_role, moderator_role


def is_moderator():
    """Returns True if user has a moderator role, raises an exception otherwise
    """

    def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name=moderator_role)
        if role is None:
            raise commands.MissingRole(moderator_role)
        return True

    return commands.check(predicate)


def is_developer():
    """Returns True if user is a bot developer, raises an exception otherwise
    """

    def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name=developer_role)
        if role is None:
            raise commands.MissingRole(moderator_role)
        return True

    return commands.check(predicate)
