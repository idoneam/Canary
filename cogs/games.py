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
from .utils.dnd_roll import dnd_roll


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def roll(self, ctx, arg: str = ''):
        """
        Performs a DnD-style diceroll
        Supports modifiers, multiple rolls, any-sided dice
        """
        roll_pattern = re.compile(r'^(\d*)d(\d*)([+-]?\d*)$')
        roll_cmd = roll_pattern.match(arg)
        params = {'sides' : 20, # Default parameters
                  'repeat': 1,
                  'mod'   : 0}
        if arg == 'help' or arg == 'h':
            helpmsg = discord.Embed(title='DnD Dice Roller Help',
                                    description='Usage: `[r]d[s][+m]`\n'
                                                'Rolls an [s]-sided die [r] '
                                                'times, with modifier [+-m].\n'
                                                'Rolls one 20-sided die by default',
                                    colour=0x822AE0)
            await ctx.send(embed=helpmsg)
            return
        elif roll_cmd != None: # Applying some bounds on parameters
            if roll_cmd.group(1) != '':
                params['repeat'] = min(max(1,int(roll_cmd.group(1))), 10000)
            if roll_cmd.group(2) != '':
                params['sides'] = min(max(1,int(roll_cmd.group(2))), 100)
            if roll_cmd.group(3) != '':
                params['mod'] = min(max(-100,int(roll_cmd.group(3))), 100)
                
        roll_list, total, maximum, minimum = dnd_roll(params['sides'],
                                                      params['repeat'],
                                                      params['mod'])
        # Now that we have our rolls, prep the embed:
        resultsmsg = discord.Embed(description='Rolling {} {}-sided dice'
                                               ', with a {} modifier'.format(
                                                    params['repeat'],
                                                    params['sides'],
                                                    params['mod']),
                                   colour=0x822AE0)
        if params['repeat'] <= 10: # Anything more and the roll list is too long
            resultsmsg.add_field(name='Rolls', value=str(roll_list)[1:-1], inline=False)
        if params['repeat'] > 1:
            resultsmsg.add_field(name='Sum', value=total)
            resultsmsg.add_field(name='Minimum', value=minimum)
            resultsmsg.add_field(name='Maximum', value=maximum)
        await ctx.send(embed=resultsmsg)

    
def setup(bot):
    bot.add_cog(Games(bot))
    