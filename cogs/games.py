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
import re
from .utils.dice_roll import dice_roll
from .utils.clamp_default import clamp_default

ROLL_PATTERN = re.compile(r'^(\d*)d(\d*)([+-]?\d*)$')


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, ctx, arg: str = '', mpr: str = ''):
        """
        Perform a DnD-style diceroll
        [r]d[s][+m] ['each']    Rolls an [s]-sided die [r] times, with modifier
                                [+-m]. If 'each' is specified, applies modifier
                                to each roll rather than the sum of all rolls.
                                All parameters are optional.
                                Defaults to rolling one 20-sided die.
          Examples:
           roll             rolls a d20
           roll d6          rolls one 6-sided die
           roll 3d          rolls 3 20-sided dice
           roll 5d12-4      rolls 5 12-sided dice, subtracting 4 from the total
           roll 5d+3 each   rolls 5 20-sided dice, adding 3 to each roll
        """
        roll_cmd = ROLL_PATTERN.match(arg)
        if arg == 'safe':    # nice meme bro
            await ctx.send('https://media.giphy.com/media/'
                           'd3mlE7uhX8KFgEmY/giphy.gif')
            return
        # Applying some bounds on parameters
        if roll_cmd is not None:
            repeat = clamp_default(roll_cmd.group(1), 1, 10000, 1)
            sides = clamp_default(roll_cmd.group(2), 1, 100, 20)
            mod = clamp_default(roll_cmd.group(3), -100, 100, 0)
        else:    # Necessary for empty roll commands - regex won't even match
            repeat = 1
            sides = 20
            mod = 0

        if mpr == 'each':
            roll_list, total, maximum, minimum = dice_roll(sides,
                                                           repeat,
                                                           mod,
                                                           mpr=True)
            mod_desc = ' to each roll'
        else:
            roll_list, total, maximum, minimum = dice_roll(sides, repeat, mod)
            mod_desc = ' to the sum of rolls'
        # Now that we have our rolls, prep the embed:
        resultsmsg = discord.Embed(
            description='Rolling {} {}-sided dice'
            ', with a {} modifier{}'.format(repeat, sides, mod, mod_desc),
            colour=0x822AE0)
        if repeat <= 10:    # Anything more and the roll list is too long
            resultsmsg.add_field(name='Rolls',
                                 value=str(roll_list)[1:-1],
                                 inline=False)
        if repeat > 1:
            resultsmsg.add_field(name='Sum', value=total)
            resultsmsg.add_field(name='Minimum', value=minimum)
            resultsmsg.add_field(name='Maximum', value=maximum)
        await ctx.send(embed=resultsmsg)


def setup(bot):
    bot.add_cog(Games(bot))
