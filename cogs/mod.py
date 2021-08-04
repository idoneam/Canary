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

import requests
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

    @commands.command()
    @is_moderator()
    async def update_rules(self, ctx, *args):
        rules_file = requests.get(url = self.bot.config.rules_url).text  # TODO: use async "GET" from our utils
        channel = discord.utils.get(ctx.guild.channels, name=self.bot.config.rules_channel)
        deleted = await channel.purge(limit=10000)
        rules = rules_file.split("#NEWMSG")
        for rule in rules:
            # parse any channel references in the messages (i.e. "#bots", "#verified_general", etc)
            flag = "#CHANNEL"
            rule = self.parseAndReplace(rule, flag, self.lookupChannel, ctx)

            await ctx.send(content=rule, embed=None)


    # Handler function for responding to #CHANNEL directive
    def lookupChannel(self, ctx, channelName: str):
        channel = discord.utils.get(ctx.guild.channels, name=channelName)
        if hasattr(channel, "id"):
            return f"<#{channel.id}>"
        else:
            return f"#{channelName}"


    # Overengineered helper function that replaces every instance of "flag" with "handler(flagContents)"
    # i.e. goes through "mainStr" and wherever there's an instance of flag, it takes the contents
    # of flag and runs the handler on them, and then places the output at the flags location in the string
    #
    # ex: mainStr = "1234#MYFLAG(AAA)5678#MYFLAG(BBBB)91011", flag = "#MYFLAG", handler = toLower function
    # result: 1234aaa5678bbbb91011
    def parseAndReplace(self, mainStr: str, flag: str, handler, ctx):
        while flag in mainStr:
            channel_i = mainStr.find(flag, 0, len(mainStr))
            end_i = mainStr[channel_i:].find(")") + channel_i
            contents = mainStr[channel_i + len(flag) + 1:end_i]
            contents = handler(ctx, contents)
            mainStr = mainStr[:channel_i] + contents + mainStr[end_i + 1:]
        return mainStr


def setup(bot):
    bot.add_cog(Mod(bot))
