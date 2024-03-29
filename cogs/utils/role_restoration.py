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

from discord import utils
from discord.ext import commands

from .paginator import Pages
from .mock_context import MockContext
from bot import muted_role as muted_role_name
import datetime


def save_existing_roles(bot, user: discord.Member, muted: bool = False, appeal_channel: discord.TextChannel = None):
    roles_id = [role.id for role in user.roles if role.name not in ("@everyone", muted_role_name)]

    if not roles_id and not muted:
        return

    conn = sqlite3.connect(bot.config.db_path)
    try:
        c = conn.cursor()
        # store roles as a string of IDs separated by spaces
        if muted:
            now = datetime.datetime.now()
            if is_in_muted_table(bot, user):
                t = (appeal_channel.id, user.id)
                c.execute(f"UPDATE MutedUsers SET AppealChannelID = ? WHERE UserID = ?", t)
            else:
                t = (user.id, appeal_channel.id, " ".join(str(e) for e in roles_id), now)
                c.execute(f"REPLACE INTO MutedUsers VALUES (?, ?, ?, ?)", t)
        else:
            t = (user.id, " ".join(str(e) for e in roles_id))
            c.execute(f"REPLACE INTO PreviousRoles VALUES (?, ?)", t)
        conn.commit()
    finally:
        conn.close()


def fetch_saved_roles(bot, guild, user: discord.Member, muted: bool = False) -> list[discord.Role] | None:
    conn = sqlite3.connect(bot.config.db_path)
    try:
        c = conn.cursor()
        if muted:
            fetched_roles = c.execute(f"SELECT Roles FROM MutedUsers WHERE UserID = ?", (user.id,)).fetchone()
        else:
            fetched_roles = c.execute(f"SELECT Roles FROM PreviousRoles WHERE ID = ?", (user.id,)).fetchone()
        # the above returns a tuple with a string of IDs separated by spaces

        # Return list of all valid roles restored from the DB
        #  - filter(None, ...) strips false-y elements
        return (
            list(
                filter(None, (guild.get_role(int(role_id)) for role_id in fetched_roles[0].split(" ") if role_id != ""))
            )
            if fetched_roles
            else None
        )

    finally:
        conn.close()


def has_muted_role(user: discord.Member):
    muted_role = utils.get(user.guild.roles, name=muted_role_name)
    return muted_role and next((r for r in user.roles if r == muted_role), None) is not None


def is_in_muted_table(bot, user: discord.Member):
    conn = sqlite3.connect(bot.config.db_path)
    try:
        c = conn.cursor()
        muted = c.execute("SELECT * FROM MutedUsers WHERE UserID = ?", (user.id,)).fetchone()
        return muted is not None
    finally:
        conn.close()


def remove_from_muted_table(bot, user: discord.Member):
    conn = sqlite3.connect(bot.config.db_path)
    try:
        c = conn.cursor()
        c.execute("DELETE FROM MutedUsers WHERE UserID = ?", (user.id,))
        conn.commit()
    finally:
        conn.close()


async def role_restoring_page(
    bot,
    ctx: discord.ext.commands.Context | MockContext,
    user: discord.Member,
    roles: list[discord.Role] | None,
    muted: bool = False,
):
    channel = ctx.channel
    if roles is None:
        # No row found in DB, as opposed to empty list
        if not muted:  # don't say anything if this is while unmuting
            embed = discord.Embed(title=f"Could not find any roles for {user.display_name}")
            await channel.send(embed=embed)
        return

    roles_name = [f"[{i}] {role.name}\n" for i, role in enumerate(roles, 1)]

    embed = discord.Embed(title="Loading...")
    message = await channel.send(embed=embed)

    if len(roles) > 20:
        await message.add_reaction("◀")
        await message.add_reaction("▶")
    await message.add_reaction("🆗")

    title = (
        f"{user.display_name} had the following roles before "
        f"{'leaving' if not muted else 'being muted'}."
        f"\nA {bot.config.moderator_role} can add these roles "
        f"back by reacting with 🆗"
        f"{'' if not muted else ' (Delete this message to continue unmuting without adding the roles back)'}"
    )
    p = Pages(
        ctx,
        item_list=roles_name,
        title=title,
        msg=message,
        display_option=(3, 20),
        editable_content=True,
        editable_content_emoji="🆗",
        return_user_on_edit=True,
    )
    ok_user = await p.paginate()

    while p.edit_mode:
        if not discord.utils.get(ok_user.roles, name=bot.config.moderator_role):
            # User is not moderator, simply paginate and return
            await p.paginate()
            continue

        # Add a loading message until role-restoring is done
        await message.edit(embed=discord.Embed(title="Restoring roles..."))

        # User is a moderator, so restore the roles
        failed_roles: list[str] = []
        for role in roles:
            try:
                await user.add_roles(role, reason=f"{ok_user.name} restored roles via command")
            except (discord.Forbidden, discord.HTTPException):
                failed_roles.append(str(role))
        if failed_roles:
            embed.add_field(
                name=f"Role{'s' if len(failed_roles) > 0 else ''} not given back", value=", ".join(failed_roles)
            )

        embed = discord.Embed(
            title=f"{user.display_name}'s previous roles were " f"successfully added back by {ok_user.display_name}"
        )
        await message.edit(embed=embed)
        await message.clear_reaction("◀")
        await message.clear_reaction("▶")
        await message.clear_reaction("🆗")
        return
