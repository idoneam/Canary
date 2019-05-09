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

import discord
from discord.ext import commands
import asyncio


class Mod():
    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        ctx = await self.bot.get_context(message)
        if ctx.command:
            return
        if isinstance(message.channel, discord.DMChannel):
            channel_to_send = self.bot.get_channel(454061583874785280)
            msg = '{} 📣 {}'.format(str(message.author), message.content)
            await channel_to_send.send(msg)

    @commands.command(aliases=['dm'])
    @commands.has_role('Discord Moderator')
    async def pm(self, ctx, user: discord.User, *, message):
        """
        PM a user on the server using marty
        """
        dest = user
        await dest.send(message)
        channel_to_forward = self.bot.get_channel(454061583874785280)
        msg = '🐦 ({}) to {}: {}'.format(ctx.author.name, dest, message)
        await channel_to_forward.send(msg)
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Mod(bot))
