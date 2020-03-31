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


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roles = self.bot.config.roles

    @commands.command()
    async def pronoun(self, ctx, transaction, pronoun):
        """
        Self-assign a pronoun role to a user. 
        """
        member = ctx.message.author

        # normalize pronoun
        pronoun = pronoun.title()

        pronouns = self.roles.get("pronouns").split(", ")

        if (transaction == "add") and (pronoun in pronouns):
            role = discord.utils.get(ctx.guild.roles, name=pronoun)

            await member.add_roles(role, reason="Self Requested")
        elif (transaction == "remove") and (pronoun in pronouns):
            role = discord.utils.get(ctx.guild.roles, name=pronoun)
            await member.remove_roles(role, reason="Self Requested")

        else:
            await ctx.send("Error, that role doesn't exist")

    @commands.command()
    async def field(self, ctx, transaction, field):
        """
        Self-assign a field of study role to a user. 
        """
        member = ctx.message.author

        # normalize field
        field = field.title()

        fields = self.roles.get("fields").split(", ")

        if (transaction == "add") and (field in fields):
            role = discord.utils.get(ctx.guild.roles, name=field)
            await member.add_roles(role, reason="Self Requested")

        elif (transaction == "remove") and (field in fields):
            role = discord.utils.get(ctx.guild.roles, name=field)
            await member.remove_roles(role, reason="Self Requested")
        else:
            await ctx.send("Error, that role doesn't exist")

    @commands.command()
    async def faculty(self, ctx, transaction, faculty):
        """
        Self-assign a faculty of study role to a user. 
        """
        member = ctx.message.author

        # normalize field
        faculty = faculty.title()

        faculties = self.roles.get("faculties").split(", ")

        if (transaction == "add") and (faculty in faculties):
            role = discord.utils.get(ctx.guild.roles, name=faculty)

            # Allow only a single faculty role per user.
            for item in faculties:
                role_item = discord.utils.get(ctx.guild.roles, name=item)
                if role_item is not None:
                    await member.remove_roles(role_item,
                                              reason="Self Requested")

            await member.add_roles(role, reason="Self Requested")

        elif (transaction == "remove") and (faculty in faculties):
            role = discord.utils.get(ctx.guild.roles, name=faculty)
            await member.remove_roles(role, reason="Self Requested")

        else:
            await ctx.send("Error, that role doesn't exist")

    @commands.command()
    async def year(self, ctx, transaction, year):
        """
        Self-assign a year of study role to a user. 
        """
        member = ctx.message.author

        # normalize year
        year = year.title()

        years = self.roles.get("years").split(", ")

        if (transaction == "add") and (year in years):
            role = discord.utils.get(ctx.guild.roles, name=year)

            # Allow only a single year role per user.
            for item in years:
                role_item = discord.utils.get(ctx.guild.roles, name=item)
                if role_item is not None:
                    await member.remove_roles(role_item,
                                              reason="Self Requested")

            await member.add_roles(role, reason="Self Requested")

        elif (transaction == "remove") and (year in years):
            role = discord.utils.get(ctx.guild.roles, name=year)
            await member.remove_roles(role, reason="Self Requested")

        else:
            await ctx.send("Error, that role doesn't exist")

    @commands.command()
    async def iam(self, ctx, transaction, generic):
        """
        Self-assign a generic role to a user. 
        """
        member = ctx.message.author

        generics = self.roles.get("generics").split(", ")

        if (transaction == "add") and (generic in generics):
            role = discord.utils.get(ctx.guild.roles, name=generic)
            await member.add_roles(role, reason="Self Requested")

        elif (transaction == "remove") and (generic in generics):
            role = discord.utils.get(ctx.guild.roles, name=generic)
            await member.remove_roles(role, reason="Self Requested")

        else:
            await ctx.send("Error, that role doesn't exist")


def setup(bot):
    bot.add_cog(Roles(bot))