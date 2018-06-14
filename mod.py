#!/usr/bin/python3

import discord
from discord.ext import commands
import asyncio


class Mod():
    def __init__(self, bot):
        self.bot = bot

    @asyncio.coroutine
    def on_message(self, message):
        if message.author == self.bot.user:
            return
        if isinstance(message.channel, discord.DMChannel):
            channelToSend = self.bot.get_channel(326524201987211267)
            msg = '{} 📣 {}'.format(str(message.author), message.content)
            yield from channelToSend.send(msg)

    @commands.command(pass_context=True)
    @commands.has_role('Discord Moderator')
    @asyncio.coroutine
    def pm(self, ctx, user: discord.User, *, message):
        '''
        PM a user on the server using marty
        '''
        dest = user
        yield from dest.send(message)

    # @commands.command(pass_context=True, aliases=['cid'])
    # @commands.has_role('Discord Moderator')
    # @asyncio.coroutine
    # def get_channel_id(self, ctx):
    #     yield from ctx.send(ctx.channel.id)


def setup(bot):
    bot.add_cog(Mod(bot))
