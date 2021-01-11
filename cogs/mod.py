# Copyright (C) idoneam (2016-2021)
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
from discord import utils
from discord.ext import commands

from .utils.checks import is_moderator


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def answer(self, ctx, *args):
        if isinstance(ctx.message.channel, discord.DMChannel):
            channel_to_send = utils.get(self.bot.get_guild(
                self.bot.config.server_id).text_channels,
                                        name=self.bot.config.reception_channel)
            # to work regardless of whether the person uses apostrophes
            msg = f"{ctx.author.name} 📣 {' '.join(args)}"
            await channel_to_send.send(content=msg)
            await ctx.send("```Message sent```")

    @commands.command(aliases=['dm'])
    @is_moderator()
    async def pm(self, ctx, user: discord.User, *, message):
        """
        PM a user on the server using the bot
        """
        await user.send(content=f'{message}\n*To answer write* '
                        f'`{self.bot.config.command_prefix[0]}answer '
                        f'"your message here"`')
        channel_to_forward = utils.get(self.bot.get_guild(
            self.bot.config.server_id).text_channels,
                                       name=self.bot.config.reception_channel)
        msg = f'🐦 ({ctx.author.name}) to {user.name}: {message}'
        await channel_to_forward.send(msg)
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Mod(bot))
