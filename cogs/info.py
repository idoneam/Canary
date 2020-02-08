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
import subprocess
from discord.ext import commands

from .utils.paginator import Pages


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roles(self, ctx):
        """Returns list of all roles in server"""
        roleNames = list(map(lambda role: role.name + "\n", ctx.guild.roles))
        roleNames.reverse()
        p = Pages(ctx,
                  item_list=roleNames,
                  title="All roles in server",
                  display_option=(3, 20),
                  editable_content=False)

        await p.paginate()

    @commands.command()
    async def inrole(self, ctx, *, queryRole):
        """Returns list of users in the specified role"""
        members = None
        for role in ctx.guild.roles:
            if role.name.lower() == queryRole.lower():
                members = role.members
                break

        if (members is None): return

        names = list(map(lambda m: str(m) + "\n", members))
        header = "List of users in {role} role - {num}".format(role=role.name,
                                                               num=len(names))

        # TODO remove for paginator take empty list for embed
        if (len(names) == 0):
            em = discord.Embed(title=header, colour=0xDA291C)
            em.set_footer(text="Page 01 of 01")
            await ctx.send(embed=em)
        else:
            pages = Pages(ctx,
                          item_list=names,
                          title=header,
                          display_option=(3, 20),
                          editable_content=False)
            await pages.paginate()

    @commands.command()
    async def version(self, ctx):
        version = subprocess.check_output(("git", "describe", "--tags"),
                                          universal_newlines=True).strip()
        commit, authored = subprocess.check_output(
            ("git", "log", "-1", "--pretty=format:%h %aI"),
            universal_newlines=True).strip().split(" ")
        await ctx.send("Version: `{}`\nCommit: `{}` authored `{}`".format(
            version, commit, authored))


def setup(bot):
    bot.add_cog(Info(bot))
