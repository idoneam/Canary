# Copyright (C) idoneam (2016-2022)
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
from .utils.role_restoration import (
    save_existing_roles,
    fetch_saved_roles,
    has_muted_role,
    is_in_muted_table,
    remove_from_muted_table,
    role_restoring_page,
)
from .utils.mock_context import MockContext
from bidict import bidict
import datetime


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None
        self.muted_users_to_appeal_channels = {}
        self.appeals_log_channel = None
        self.muted_role = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.bot.config.server_id)
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM MutedUsers")
        self.muted_users_to_appeal_channels = bidict(
            [
                (self.bot.get_user(user_id), self.bot.get_channel(appeal_channel_id))
                for (user_id, appeal_channel_id, roles, date) in c.fetchall()
            ]
        )
        conn.close()
        self.appeals_log_channel = utils.get(self.guild.text_channels, name=self.bot.config.appeals_log_channel)
        self.muted_role = utils.get(self.guild.roles, name=self.bot.config.muted_role)

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

    async def mute_utility(self, user: discord.Member, ctx=None):
        # note that this is made such that if a user is already muted
        # we make sure the user still has the role, is still in the db, and still has a channel
        confirmation_channel = ctx.channel if ctx else self.appeals_log_channel
        appeals_category = utils.get(self.guild.categories, name=self.bot.config.appeals_category)
        moderator_role = utils.get(self.guild.roles, name=self.bot.config.moderator_role)
        reason_message = (
            f"{ctx.author} used the mute function on {user}"
            if ctx
            else f"Mute function used on {user} (by adding role directly)"
        )
        now = datetime.datetime.now()

        # create appeals channel if not exists (it might if the user was already muted)
        channel = None
        if self.muted_users_to_appeal_channels:
            channel = self.muted_users_to_appeal_channels[user]
        if channel not in self.guild.text_channels:
            channel_name = f"appeal-{user.name[0]}{user.discriminator}-{now.strftime('%Y-%m-%d')}"
            channel = await self.guild.create_text_channel(
                channel_name, reason=reason_message, category=appeals_category, slowmode_delay=30
            )

            # note that we can only deny permissions that the bot knows about, so if discord.py isn't updated to the latest
            # version some permissions will have to be set manually by moderators
            await channel.set_permissions(
                self.guild.default_role,
                overwrite=discord.PermissionOverwrite.from_pair(allow=[], deny=discord.Permissions.all()),
            )
            await channel.set_permissions(
                user,
                overwrite=discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, read_message_history=True
                ),
            )
            await channel.set_permissions(
                moderator_role,
                overwrite=discord.PermissionOverwrite.from_pair(allow=discord.Permissions.all_channel(), deny=[]),
            )
            await channel.send(
                "You have been muted from this server. You may appeal this decision here. "
                "Please note that all messages written in this channel are automatically logged "
                "to another channel accessible by Discord Moderators only, including edits."
            )

        # save existing roles and add muted user to database (with the attached appeal channel)
        # note that this function is such that if the user was already in the db, only the appeal channel is updated
        # (i.e, the situation where a mod had manually deleted the appeal channel)
        save_existing_roles(self.bot, user, muted=True, appeal_channel=channel)

        # Remove all roles
        failed_roles: list[str] = []
        for role in user.roles:
            if role.name == "@everyone" or role == self.muted_role:
                continue
            try:
                await user.remove_roles(role, reason=reason_message)
            except (discord.Forbidden, discord.HTTPException):
                failed_roles.append(str(role))
        # update dict
        self.muted_users_to_appeal_channels[user] = channel

        # Add the muted role to the user (Note that it is important that this is the last thing that we do
        # because this will trigger on_member_update below, which then calls this function again if the user isn't
        # properly muted yet)
        await user.add_roles(self.muted_role, reason=reason_message)

        # Send confirmation messages
        await confirmation_channel.send(reason_message)
        if failed_roles:
            await confirmation_channel.send(
                f"The following role{'s' if len(failed_roles) > 0 else ''} could not be removed: {', '.join(failed_roles)}"
            )
        await self.appeals_log_channel.send(
            f"User {user.mention} ({user}) has been muted. Appeal channel: {channel.mention}"
        )

    async def unmute_utility(self, user: discord.Member, ctx=None):
        confirmation_channel = ctx.channel if ctx else self.appeals_log_channel
        reason_message = (
            f"{ctx.author} used the unmute function on {user}"
            if ctx
            else f"Unmute function used on {user} (by removing role directly)"
        )

        # Restore old roles from the database
        valid_roles = fetch_saved_roles(self.bot, self.guild, user, muted=True)
        # for the following, if ctx is provided then the optional bot, guild, channel and restored_by values are ignored
        # if there is no ctx, it means that the user was unmuted because a mod removed the role manually
        # to know which mod did it, we would have to go through the audit log and try the find the log entry. Instead,
        # we just say marty did it, and mods can check in the discord log themselves.
        await role_restoring_page(
            self.bot,
            MockContext(bot=self.bot, guild=self.guild, channel=confirmation_channel, author=self.bot.user),
            user,
            valid_roles,
            muted=True,
        )

        # Remove entry from the database
        remove_from_muted_table(self.bot, user)

        # Delete appeal channel
        if user in self.muted_users_to_appeal_channels:
            try:
                await self.muted_users_to_appeal_channels[user].delete(reason=reason_message)
            except discord.NotFound:
                pass

        # Remove entry from the dictionary
        self.muted_users_to_appeal_channels.pop(user, None)

        # Remove the muted role (as in mute_utility, this must be done last)
        await user.remove_roles(self.muted_role, reason=reason_message)

        await confirmation_channel.send(reason_message)
        await self.appeals_log_channel.send(f"User {user.mention} ({user}) has been unmuted. Appeal channel deleted.")

    @commands.command()
    @is_moderator()
    async def mute(self, ctx, user: discord.Member):
        """
        Mute a user and create an appeal channel (mod-only). The user's current roles are saved.

        Can also be done by adding the muted role directly.
        """
        await self.mute_utility(user, ctx=ctx)

    @commands.command()
    @is_moderator()
    async def unmute(self, ctx, user: discord.Member):
        """
        Unmute a user and delete the appeal channel (mod-only). The user's previous roles are restored after confirmation.

        Can also be done by removing the muted role directly.
        """
        await self.unmute_utility(user, ctx=ctx)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        muted_role_before = self.muted_role in before.roles
        muted_role_after = self.muted_role in after.roles

        # if muted role was added, mute the user, except if the user is already muted properly
        if (
            not muted_role_before
            and muted_role_after
            and not (
                is_in_muted_table(self.bot, after)
                and has_muted_role(after)
                and after in self.muted_users_to_appeal_channels
                and self.muted_users_to_appeal_channels[after] in self.guild.text_channels
            )
        ):
            await self.mute_utility(after)

        # if muted role was removed, unmute the user, except if the user is already unmuted properly
        if (
            muted_role_before
            and not muted_role_after
            and (
                is_in_muted_table(self.bot, after)
                or has_muted_role(after)
                or after in self.muted_users_to_appeal_channels
            )
        ):
            await self.unmute_utility(after)

    # the next three functions are used for appeals logging
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel in self.muted_users_to_appeal_channels.values():
            muted_user = self.muted_users_to_appeal_channels.inverse[message.channel]
            if message.author == muted_user:
                # only pings if the user is the one that is muted
                log_message = f"Muted user {message.author.mention} ({message.author}) sent the following message ({message.id}) in {message.channel.mention}:\n{message.content}"
            else:
                log_message = f"User {message.author} sent the following message ({message.id}) in the appeal channel for muted user {muted_user.mention} ({muted_user}), {message.channel.mention}:\n{message.content}"
            if len(log_message) > 2000:
                log_message = log_message[:1995] + "[...]"
            await self.appeals_log_channel.send(log_message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.channel in self.muted_users_to_appeal_channels.values():
            muted_user = self.muted_users_to_appeal_channels.inverse[after.channel]
            if after.author == muted_user:
                # only pings if the user is the one that is muted
                log_message = f"Muted user {after.author.mention} ({after.author}) edited message {after.id} in {after.channel.mention}. New content:\n{after.content}"
            else:
                log_message = f"User {after.author} edited message {after.id} in the appeal channel for muted user {muted_user.mention} ({muted_user}), {after.channel.mention}. New content:\n{after.content}"
            if len(log_message) > 2000:
                log_message = log_message[:1995] + "[...]"
            await self.appeals_log_channel.send(log_message)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.channel in self.muted_users_to_appeal_channels.values():
            muted_user = self.muted_users_to_appeal_channels.inverse[message.channel]
            if message.author == muted_user:
                # only pings if the user is the one that is muted
                log_message = f"Muted user {message.author.mention} ({message.author}) deleted message {message.id} in {message.channel.mention}"
            else:
                log_message = f"User {message.author} deleted message {message.id} in the appeal channel for muted user {muted_user.mention} ({muted_user}), {message.channel.mention}"
            await self.appeals_log_channel.send(log_message)

    @commands.Cog.listener()
    async def on_member_join(self, user: discord.Member):
        # If the user was already muted, restore the muted role
        if is_in_muted_table(self.bot, user):
            await user.add_roles(muted_role, reason="Restored muted status")


def setup(bot):
    bot.add_cog(Mod(bot))
