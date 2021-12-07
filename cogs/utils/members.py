# Copyright (C) idoneam (2016-2021)
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


async def _get_name_from_id(self, user_id) -> str:
    user = self.bot.get_user(user_id)
    if user is not None:
        return str(user)
    try:
        user = await self.bot.fetch_user(user_id)
        name = str(user)
        if "Deleted User" in name:
            return str(user_id)
        return name
    except discord.errors.NotFound:
        return str(user_id)


async def add_member_if_needed(self, c, user_id) -> None:
    c.execute("SELECT Name FROM Members WHERE ID = ?", (user_id,))
    if not c.fetchone():
        name = await _get_name_from_id(self, user_id)
        c.execute("INSERT OR IGNORE INTO Members VALUES (?,?)", (user_id, name))
