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

# Other utilities
import random
from .utils.auto_incorrect import auto_incorrect


class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def _delete_and_send(ctx, v):
        await ctx.send(v)
        await ctx.message.delete()

    @commands.command()
    async def bac(self, ctx, *, input_str: str = None):
        """
        Purposefully auto-incorrects inputted sentences
        """
        if input_str is None:
            await ctx.send()
        msg = auto_incorrect(input_str)
        self.bot.logger.info('?bac invoked: Author: {}, Message: {}'.format(
            ctx.message.author, ctx.message.content))
        await self._delete_and_send(ctx, msg)

    @commands.command()
    async def lenny(self, ctx):
        """
        Lenny face
        """
        await self._delete_and_send(ctx, "( ͡° ͜ʖ ͡°) ")

    @commands.command()
    async def license(self, ctx):
        """
        License
        """
        await self._delete_and_send(
            ctx,
            "This bot is free software: you can redistribute it and/or modify "
            "it under the terms of the GNU General Public License as published"
            " by the Free Software Foundation, either version 3 of the "
            "License, or (at your option) any later version. **This bot is "
            "distributed in the hope that it will be useful**, but WITHOUT "
            "ANY WARRANTY; without even the implied warranty of "
            "MERCHANTABILITY or **FITNESS FOR A PARTICULAR PURPOSE**.  See "
            "the GNU General Public License for more details. This bot is "
            "developed primarily by student volunteers with better things to "
            "do. A copy of the GNU General Public License is provided in the "
            "LICENSE.txt file along with this bot. The GNU General Public "
            "License can also be found at <http://www.gnu.org/licenses/>.")

    @commands.command()
    async def gohere(self, ctx):
        """
        for future mcgillians
        """
        await self._delete_and_send(ctx, "http://gph.is/1cN9wO1")

    @commands.command()
    async def tunak(self, ctx):
        """
        bitch pls
        """
        await self._delete_and_send(ctx, "http://i.imgur.com/rNNLyjK.gif")

    @commands.command()
    async def bb8(self, ctx):
        """
        nice job bb8
        """
        await self._delete_and_send(ctx, "http://i.imgur.com/SUvaUM2.gif")

    @commands.command()
    async def longtime(self, ctx):
        """
        That's a name I've not heard in a long time
        """
        await self._delete_and_send_(ctx, "http://i.imgur.com/e1T1xcq.mp4")

    @commands.command()
    async def thonk(self, ctx):
        """
        when thonking consumes you
        """
        await self._delete_and_send(ctx, "https://i.imgur.com/VADGUwj.gifv")

    @commands.command()
    async def dealwithit(self, ctx):
        """
        deal with it trump
        """
        await self._delete_and_send(ctx, "http://i.imgur.com/5jzN8zV.mp4")

    @commands.command()
    async def lmao(self, ctx):
        """
        that's hilarious
        """
        await self._delete_and_send(ctx, "http://i.imgur.com/o5Cc3i2.mp4")

    @commands.command()
    async def cheep(self, ctx):
        """:^)"""
        await ctx.send('CHEEP CHEEP')

    @commands.command()
    async def mix(self, ctx, *, input_str: str = None):
        """Alternates upper/lower case for input string. Input message
        disappears after."""
        if input_str is None:
            await ctx.send()
        self.bot.logger.info('?mix invoked: Author: {}, Message: {}'.format(
            ctx.message.author, ctx.message.content))
        msg = "".join((c.upper() if random.randint(0, 1) else c.lower())
                      for c in input_str)
        await self._delete_and_send(ctx, msg)

    @commands.command()
    async def boot(self, ctx, num: int = 2):
        """Draws a pyramid of boots, default is 3 unless user specifies
        an integer number of levels of boots."""

        num = max(min(num, 8), 1)    # Above 8, herre gets angry

        def booty(n, m):
            return "{spaces}{boots}".format(spaces=" " * ((m - n) * 3),
                                            boots="👢 " * n)

        msg = "\n".join(booty(ln, num) for ln in range(1, num + 1))
        await ctx.send("**\n{}**".format(msg))


def setup(bot):
    bot.add_cog(Memes(bot))
