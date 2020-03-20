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
from discord.ext import commands

# Other utilities
import random
from .utils.auto_incorrect import auto_incorrect


class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        await ctx.send(msg)
        await ctx.message.delete()

    @commands.command()
    async def lenny(self, ctx):
        """
        Lenny face
        """
        await ctx.send("( ͡° ͜ʖ ͡°) ")
        await ctx.message.delete()

    @commands.command()
    async def license(self, ctx):
        """
        License
        """
        await ctx.send("This bot is free software: you can redistribute"
                       " it and/or modify it under the terms of the GNU"
                       " General Public License as published by the "
                       "Free Software Foundation, either version 3 of "
                       "the License, or (at your option) any later "
                       "version. **This bot is distributed in the hope "
                       "that it will be useful**, but WITHOUT ANY "
                       "WARRANTY; without even the implied warranty of "
                       "MERCHANTABILITY or **FITNESS FOR A PARTICULAR "
                       "PURPOSE**.  See the GNU General Public License "
                       "for more details. This bot is developed "
                       "primarily by student volunteers with better "
                       "things to do. A copy of the GNU General Public "
                       "License is provided in the LICENSE.txt file "
                       "along with this bot. The GNU General Public "
                       "License can also be found at "
                       "<http://www.gnu.org/licenses/>.")
        await ctx.message.delete()

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
        msg = "".join([(c.upper() if random.randint(0, 1) else c.lower())
                       for c in input_str])
        self.bot.logger.info('?mix invoked: Author: {}, Message: {}'.format(
            ctx.message.author, ctx.message.content))
        await ctx.send(msg)
        await ctx.message.delete()

    @commands.command(aliases=['boot'])
    async def pyramid(self, ctx, num: int = 2, emoji: str = "👢"):
        """Draws a pyramid of boots, default is 2 unless user specifies an integer number of levels of boots between -8 and 8. Also accepts any other emoji, word or multiword (in quotes) string."""
        def pyramidy(n, m):
            return "{spaces}{emojis}".format(spaces=" " * ((m - n) * 3),
                                             emojis=(emoji + " ") * n)

        if (num > 0):
            num = max(min(num, 8), 1)    # Above 8, herre gets angry
            msg = "\n".join(pyramidy(ln, num) for ln in range(1, num + 1))
        else:
            num = min(max(num, -8), -1)    # Below -8, herre gets angry
            msg = "\n".join(
                pyramidy(ln, abs(num))
                for ln in reversed(range(1,
                                         abs(num) + 1)))

        await ctx.send("**\n{}**".format(msg))


def setup(bot):
    bot.add_cog(Memes(bot))
