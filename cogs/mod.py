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

from .utils.checks import is_moderator


class Mod():
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def answer(self, ctx, *args):
        if isinstance(ctx.message.channel, discord.DMChannel):
            message = "{}".format(
                " ".join(args)
            )    # to work regardless of whether the person uses apostrophes
            channel_to_send = self.bot.get_channel(
                self.bot.config.reception_channel_id)
            msg = '{} 📣 {}'.format(str(ctx.author.name), message)
            await channel_to_send.send(content=msg)
            await ctx.send("`Message sent`")

    @commands.command(aliases=['dm'])
    @is_moderator()
    async def pm(self, ctx, user: discord.User, *, message):
        """
        PM a user on the server using the bot
        """
        dest = user
        await dest.send(
            content='{}\n*To answer write* `{}answer "your message here"`'.
            format(message, self.bot.config.command_prefix))
        channel_to_forward = self.bot.get_channel(
            self.bot.config.reception_channel_id)
        msg = '🐦 ({}) to {}: {}'.format(ctx.author.name, dest.name, message)
        await channel_to_forward.send(msg)
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Mod(bot))
