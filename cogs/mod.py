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
from discord.ext import commands, tasks

from .utils.checks import is_moderator
from datetime import datetime, timedelta


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None
        self.verification_channel = None
        self.last_verification_purge_datetime = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.bot.config.server_id)
        self.verification_channel = utils.get(self.guild.text_channels, name=self.bot.config.verification_channel)
        if self.verification_channel:
            # arbitrary min date because choosing dates that predate discord will cause an httpexception
            # when fetching message history after that date later on
            self.last_verification_purge_datetime = datetime(2018, 1, 1)
            conn = sqlite3.connect(self.bot.config.db_path)
            c = conn.cursor()
            c.execute("SELECT Value FROM Settings WHERE Key = ?", ("last_verification_purge_timestamp",))
            fetched = c.fetchone()
            if fetched:
                last_purge_timestamp = float(fetched[0])
                if last_purge_timestamp:
                    self.last_verification_purge_datetime = datetime.fromtimestamp(last_purge_timestamp)
            else:
                # the verification purge info setting has not been added to db yet
                c.execute(
                    "INSERT INTO Settings VALUES (?, ?)",
                    ("last_verification_purge_timestamp", self.last_verification_purge_datetime.timestamp()),
                )
                conn.commit()
            conn.close()

            self.check_verification_purge.start()

    @tasks.loop(minutes=60)
    async def check_verification_purge(self):
        # todo: make general scheduled events db instead
        if not all((self.guild, self.verification_channel, self.last_verification_purge_datetime)):
            return

        if datetime.now() < self.last_verification_purge_datetime + timedelta(days=7):
            return

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        # delete everything since the day of the last purge, including that day itself
        await self.verification_purge_utility(self.last_verification_purge_datetime - timedelta(days=1))
        # update info
        c.execute("SELECT Value FROM Settings WHERE Key = ?", ("last_verification_purge_timestamp",))
        fetched = c.fetchone()
        if fetched:
            c.execute(
                "REPLACE INTO Settings VALUES (?, ?)", ("last_verification_purge_timestamp", datetime.now().timestamp())
            )
            conn.commit()
        conn.close()

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
        if c.fetchone():
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

    async def verification_purge_utility(self, after: datetime | discord.Message | None):
        # after can be None, a datetime or a discord message
        await self.verification_channel.send("Starting verification purge")
        channel = self.verification_channel
        deleted = 0
        async for message in channel.history(oldest_first=True, limit=None, after=after):
            if message.attachments or message.embeds:
                content = message.content
                if message.embeds:
                    thumbnail_found = False
                    for embed in message.embeds:
                        if embed.thumbnail:
                            thumbnail_found = True
                            content = content.replace(embed.thumbnail.url, "")
                    if not thumbnail_found:
                        continue
                if content:
                    await channel.send(
                        f"{message.author} sent the following purged message on "
                        f"{message.created_at.strftime('%Y/%m/%d, %H:%M:%S')}: {content}"
                    )
                await message.delete()
                deleted += 1

        await self.verification_channel.send(
            f"Verification purge completed. Deleted {deleted} message{'s' if deleted != 1 else ''}"
        )

    @commands.command()
    @is_moderator()
    async def verification_purge(self, ctx, id: int = None):
        """ "
        Manually start the purge of pictures in the verification channel.

        If a message ID is provided, every pictures after that message will be removed.
        If no message ID is provided, this will be done for the whole channel (may take time).
        """
        if not self.bot.config.verification_channel:
            await ctx.send("No verification channel set in config file")
            return
        if not self.verification_channel:
            # if no verification_channel was found on startup, we try to see if it exists now
            self.verification_channel = utils.get(self.guild.text_channels, name=self.bot.config.verification_channel)
            if not self.verification_channel:
                await ctx.send(f"Cannot find verification channel named {self.bot.config.verification_channel}")
                return
        message = None
        if id is not None:
            message = await self.verification_channel.fetch_message(id)
        await self.verification_purge_utility(message)


def setup(bot):
    bot.add_cog(Mod(bot))
