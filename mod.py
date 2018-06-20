#!/usr/bin/python3

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
            channelToSend = self.bot.get_channel(326524201987211267)
            msg = '{} 📣 {}'.format(str(message.author), message.content)
            await channelToSend.send(msg)

    @commands.command(pass_context=True)
    @commands.has_role('Discord Moderator')
    async def pm(self, ctx, user: discord.User, *, message):
        '''
        PM a user on the server using marty
        '''
        dest = user
        await dest.send(message)

    # @commands.command(pass_context=True, aliases=['cid'])
    # @commands.has_role('Discord Moderator')
    # @asyncio.coroutine
    # def get_channel_id(self, ctx):
    #     await ctx.send(ctx.channel.id)


def setup(bot):
    bot.add_cog(Mod(bot))
