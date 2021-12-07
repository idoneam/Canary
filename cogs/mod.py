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
import sqlite3
import random
from discord import utils
from discord.ext import commands

from .utils.checks import is_moderator


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def answer(self, ctx, *args):
        if isinstance(ctx.message.channel, discord.DMChannel):
            channel_to_send = utils.get(
                self.bot.get_guild(self.bot.config.server_id).text_channels, name=self.bot.config.reception_channel
            )
            # to work regardless of whether the person uses apostrophes
            msg = f"{ctx.author.name} 📣 {' '.join(args)}"
            await channel_to_send.send(content=msg)
            await ctx.send("```Message sent```")

    @commands.command(aliases=["dm"])
    @is_moderator()
    async def pm(self, ctx, user: discord.User, *, message):
        """
        PM a user on the server using the bot
        """
        await user.send(
            content=f"{message}\n*To answer write* "
            f"`{self.bot.config.command_prefix[0]}answer "
            f'"your message here"`'
        )
        channel_to_forward = utils.get(
            self.bot.get_guild(self.bot.config.server_id).text_channels, name=self.bot.config.reception_channel
        )
        msg = f"🐦 ({ctx.author.name}) to {user.name}: {message}"
        await channel_to_forward.send(msg)
        await ctx.message.delete()

    @commands.command()
    @is_moderator()
    async def initiate_crabbo(self, ctx):
        """Initiates secret crabbo ceremony"""

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT Value FROM Settings WHERE Key = ?", ("CrabboMsgID",))
        check_msg = c.fetchone()
        if check_msg:
            await ctx.send("secret crabbo has already been started.")
            conn.close()
            return
        crabbo_msg = await ctx.send(
            "🦀🦀🦀 crabbo time 🦀🦀🦀\n<@&"
            f"{discord.utils.get(ctx.guild.roles, name=self.bot.config.crabbo_role).id}"
            "> react to this message with 🦀 to enter the secret crabbo festival\n"
            "🦀🦀🦀 crabbo time 🦀🦀🦀"
        )
        c.execute("REPLACE INTO Settings VALUES (?, ?)", ("CrabboMsgID", crabbo_msg.id))
        conn.commit()
        conn.close()
        await ctx.message.delete()

    @commands.command()
    @is_moderator()
    async def finalize_crabbo(self, ctx):
        """Sends crabbos their secret crabbo"""

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT Value FROM Settings WHERE Key = ?", ("CrabboMsgID",))
        msg_id = c.fetchone()
        c.execute("DELETE FROM Settings WHERE Key = ?", ("CrabboMsgID",))
        conn.commit()
        conn.close()
        if not msg_id:
            await ctx.send("secret crabbo is not currently occurring.")
            return
        crabbos = None
        for react in (await ctx.fetch_message(int(msg_id[0]))).reactions:
            if str(react) == "🦀":
                crabbos = await react.users().flatten()
                break
        if crabbos is None or (num_crabbos := len(crabbos)) < 2:
            await ctx.send("not enough people participated in the secret crabbo festival.")
            return
        random.shuffle(crabbos)
        for index, crabbo in enumerate(crabbos):
            await self.bot.get_user(crabbo.id).send(
                f"🦀🦀🦀\nyou have been selected to give a gift to: {crabbos[(index+1)%num_crabbos]}\n🦀🦀🦀"
            )

        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Mod(bot))
