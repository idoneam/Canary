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
    async def roles(self, ctx):
        """Returns list of all roles in server"""
        role_names = [role.name + "\n" for role in reversed(ctx.guild.roles)]
        p = Pages(ctx,
                  item_list=role_names,
                  title="All roles in server",
                  display_option=(3, 20),
                  editable_content=False)

        await p.paginate()

    @commands.command()
    async def inrole(self, ctx, *, query_role):
        """Returns list of users in the specified role"""

        # Get first matching role if one exists
        try:
            role = next(role for role in ctx.guild.roles
                        if role.name.lower() == query_role.lower())
        except StopIteration:
            # No matching role exists
            return

        names = [str(m) + "\n" for m in role.members]
        header = "List of users in {role} role - {num}".format(role=role.name,
                                                               num=len(names))

        # TODO remove for paginator take empty list for embed
        if len(names) == 0:
            em = discord.Embed(title=header, colour=0xDA291C)
            em.set_footer(text="Page 01 of 01")
            await ctx.send(embed=em)
            return

        pages = Pages(ctx,
                      item_list=names,
                      title=header,
                      display_option=(3, 20),
                      editable_content=False)
        await pages.paginate()


def setup(bot):
    bot.add_cog(Info(bot))
