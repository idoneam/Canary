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
from discord import utils
from discord.ext import commands

import codecs
import configparser
from .utils.paginator import Pages


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roles = self.bot.config.roles

    async def toggleRole(self, ctx, transaction, requestedRole, category):
        """
        Assigs a single role to a user with no checks from a category of roles
        """
        member = ctx.message.author
        roles = self.roles.get(category).split(", ")

        # normalize user input to title case
        requestedRole = requestedRole.title()

        if (transaction == "add") and (requestedRole in roles):
            role = discord.utils.get(ctx.guild.roles, name=requestedRole)
            await member.add_roles(role, reason="Self Requested")
        elif (transaction == "remove") and (requestedRole in roles):
            role = discord.utils.get(ctx.guild.roles, name=requestedRole)
            await member.remove_roles(role, reason="Self Requested")
        else:
            await ctx.send("Error, that role doesn't exist in this category")
        return

    async def toggleRestrictedRole(self, ctx, transaction, requestedRole, category):
        """
        Assigs a single role to a user with no checks from a category of roles
        """
        member = ctx.message.author
        roles = self.roles.get(category).split(", ")

        # normalize user input to title case
        requestedRole = requestedRole.title()

        if (transaction == "add") and (requestedRole in roles):
            role = discord.utils.get(ctx.guild.roles, name=requestedRole)
            # Allow only a single faculty role per user.
            for category_roles in roles:
                old_role = discord.utils.get(
                    ctx.guild.roles, name=category_roles)
                if old_role is not None:
                    await member.remove_roles(old_role, reason="Self Requested")
            await member.add_roles(role, reason="Self Requested")
        elif (transaction == "remove") and (requestedRole in roles):
            role = discord.utils.get(ctx.guild.roles, name=requestedRole)
            await member.remove_roles(role, reason="Self Requested")
        else:
            await ctx.send("Error, that role doesn't exist in this category")
        return

    @commands.command()
    async def pronoun(self, ctx, transaction, pronoun):
        """
        Self-assign a pronoun role to a user. 
        """
        await Roles.toggleRole(self, ctx, transaction, pronoun, "pronouns")

    @commands.command()
    async def field(self, ctx, transaction, field):
        """
        Self-assign a field of study role to a user. 
        """
        await Roles.toggleRole(self, ctx, transaction, field, "fields")

    @commands.command()
    async def faculty(self, ctx, transaction, faculty):
        """
        Self-assign a faculty of study role to a user. 
        """
        await Roles.toggleRestrictedRole(self, ctx, transaction, faculty, "faculties")

    @commands.command()
    async def year(self, ctx, transaction, year):
        """
        Self-assign a year of study role to a user. 
        """
        await Roles.toggleRestrictedRole(self, ctx, transaction, year, "years")

    @commands.command()
    async def iam(self, ctx, transaction, generic):
        """
        Self-assign a generic role to a user. 
        """
        await Roles.toggleRole(self, ctx, transaction, generic, "generics")

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

        if (members is None):
            return

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


def setup(bot):
    bot.add_cog(Roles(bot))
