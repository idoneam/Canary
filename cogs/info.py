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

# discord-py requirements
import discord
from discord.ext import commands
import asyncio

from .utils.paginator import Pages
import math

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def inrole(self, ctx, *, r):
        """Returns list of users in the specified role"""
        members = []
        for role in ctx.guild.roles:
            if role.name.lower() == r.lower():
                members = role.members
                break

        if (len(members) == 0): return

        names = list(map(lambda m: str(m) + "\n", members))
        numNames = len(names)
        pages = math.ceil(numNames/20) # 20 names per page
        header = "List of users in {role} role - {num}".format(
                role = role.name, 
                num = numNames)
        
        p = Pages(ctx,
                item_list=names,
                title=header,
                display_option=(3,20),
                editable_content=False)

        await p.paginate()

def setup(bot):
    bot.add_cog(Info(bot))
