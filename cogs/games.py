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

# Other utilities
import random
import re


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def roll(self, ctx, arg: str = None):
        """
        Performs a DnD-style diceroll
        Supports modifiers, multiple rolls, any-sided dice
        """
        if arg == 'help' or arg == 'h':
            helpmsg = discord.Embed(title='DnD Dice Roller Help',
                                    description='Usage: `[r]d[s][+m]`\n'
                                                'Rolls an [s]-sided die [r] '
                                                'times, with modifier [+-m].\n'
                                                'Rolls one 20-sided die by default',
                                    colour=0x822AE0)
            await ctx.send(embed=helpmsg)
        else:
            await ctx.send(random.randint(1,20))
        
    
def setup(bot):
    bot.add_cog(Games(bot))
    