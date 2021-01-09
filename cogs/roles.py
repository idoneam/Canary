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

from discord import utils
from discord.ext import commands
from enum import Enum
from typing import Optional, Tuple

from .utils.checks import is_moderator
from .utils.paginator import Pages

PENALTY_ROLE_ERROR = "Mis-configured penalty role in config.ini"


class RoleTransaction(Enum):
    ADD = "add"
    REMOVE = "remove"


class Roles(commands.Cog):
    ALL_CATEGORIES = (
        "pronouns",
        "fields",
        "faculties",
        "years",
        "generics",
    )

    CATEGORY_LIMITS = {
        "pronouns": None,
        "fields": 3,
        "faculties": 1,
        "years": 1,
        "generics": None,
    }

    def __init__(self, bot):
        self.bot = bot
        self.roles = self.bot.config.roles
        self.mod_role = self.bot.config.moderator_role
        self.penalty_role = self.bot.config.penalty_role

    @staticmethod
    async def paginate_roles(ctx, roles, title="All roles in server"):
        p = Pages(ctx,
                  item_list=[r + "\n" for r in roles],
                  title=title,
                  display_option=(3, 20),
                  editable_content=False)
        await p.paginate()

    async def toggle_role(self, ctx, transaction: RoleTransaction,
                          requested_role: Optional[str],
                          categories: Tuple[str, ...]):
        """
        Assigns a single role to a user with no checks from a category of roles
        """

        fcategory = 'categories' if len(categories) > 1 else 'category'
        if not requested_role:
            roles = []
            for c in categories:
                roles += self.roles[c]    # All roles in the category

            # If no role is specified, list what is available in all possible
            # categories for the command.
            await Roles.paginate_roles(
                ctx,
                roles,
                title=f"Roles in {fcategory} `{', '.join(categories)}`")
            return

        # If a role is specified, narrow the category down to the one with the
        # role in it to impose a proper limit.
        try:
            category = next((c for c in categories if requested_role.lower() in
                             {r.lower()
                              for r in self.roles[c]}))
        except StopIteration:
            await ctx.send(
                f"Invalid role for {fcategory} `{', '.join(categories)}`.")
            return

        roles = self.roles[category]

        roles_lower = [r.lower() for r in roles]
        requested_role = roles[roles_lower.index(requested_role.lower())]

        limit = Roles.CATEGORY_LIMITS[category]

        role = utils.get(ctx.guild.roles, name=requested_role)
        member = ctx.message.author

        if not role:
            await ctx.send(f"Error: Role `{requested_role}` is self-assignable"
                           f" but does not exist on the server... "
                           f"Please contact your local {self.mod_role}.")
            return

        existing_roles = [
            rr for rr in (utils.get(member.roles, name=r) for r in roles)
            if rr is not None
        ]

        if transaction == RoleTransaction.ADD:
            # Find existing roles in the category the user has
            if role in existing_roles:
                await ctx.send("You already have this role.")
                return

            if limit == 1 and existing_roles:
                # Treat as exclusive, simply replace roles
                # For roles defined as "exclusive" only one in that category
                # may be applied at a time.
                for old_role in existing_roles:
                    await member.remove_roles(old_role,
                                              reason="Self Requested")
                await member.add_roles(role, reason="Self Requested")
                await ctx.send(f"Replaced role for category `{category}`.")
                return

            elif limit and len(existing_roles) == limit:
                await ctx.send(f"You have too many roles in category "
                               f"`{category}` (limit is `{limit}`). "
                               f"Please remove one.")
                return

            await member.add_roles(role, reason="Self Requested")
            await ctx.send("Role added.")

        elif transaction == RoleTransaction.REMOVE:
            if role not in existing_roles:
                await ctx.send("You do not have this role.")
                return
            await member.remove_roles(role, reason="Self Requested")
            await ctx.send("Role removed.")

        else:
            await ctx.send("Must `add` or `remove` a role.")

    async def add_role(self, ctx, requested_role: Optional[str],
                       categories: Tuple[str, ...]):
        """
        Wrapper for toggle_role to make calling it cleaner
        """
        return await self.toggle_role(ctx, RoleTransaction.ADD, requested_role,
                                      categories)

    @commands.command(aliases=["pronouns"])
    async def pronoun(self, ctx, *, pronoun: Optional[str] = None):
        """
        Self-assign a pronoun role to a user.
        If no argument is given, returns a list of roles that can be used with this command.
        """
        await self.add_role(ctx, pronoun, ("pronouns", ))

    @commands.command(
        aliases=["fields", "program", "programs", "major", "majors"])
    async def field(self, ctx, *, field: Optional[str] = None):
        """
        Self-assign a field of study role to a user.
        If no argument is given, returns a list of roles that can be used with this command.
        """
        await self.add_role(ctx, field, ("fields", ))

    @commands.command(aliases=["faculties"])
    async def faculty(self, ctx, *, faculty: Optional[str] = None):
        """
        Self-assign a faculty of study role to a user.
        If no argument is given, returns a list of roles that can be used with this command.
        """
        await self.add_role(ctx, faculty, ("faculties", ))

    @commands.command(aliases=["years"])
    async def year(self, ctx, year: Optional[str] = None):
        """
        Self-assign a year of study role to a user.
        If no argument is given, returns a list of roles that can be used with this command.
        """
        await Roles.add_role(self, ctx, year, ("years", ))

    @commands.command(aliases=["iam", "generic", "generics"])
    async def i_am(self, ctx, *, role: Optional[str]):
        """
        Self-assign a generic role to a user.
        If no argument is given, returns a list of roles that can be used with this command.
        """
        await self.add_role(ctx, role, Roles.ALL_CATEGORIES)

    @commands.command(aliases=["iamn"])
    async def i_am_not(self, ctx, *, role: Optional[str]):
        """
        Self-unassign a generic role to a user.
        """
        await self.toggle_role(ctx, RoleTransaction.REMOVE, role,
                               Roles.ALL_CATEGORIES)

    @commands.command()
    async def roles(self, ctx, user: discord.Member = None):
        """Returns list of all roles in server or
        the list of a specific user's roles"""
        role_names = [
            role.name
            for role in (ctx.guild.roles if user is None else user.roles)
            if role != ctx.guild.default_role
        ]
        role_names.reverse()
        await Roles.paginate_roles(
            ctx,
            role_names,
            title=("all roles in server" if user is None else
                   f"{user.display_name}'s roles") + f" ({len(role_names)})")

    @commands.command(aliases=["inrole"])
    async def in_role(self, ctx, *, query_role):
        """Returns list of users in the specified role"""

        role = next((role for role in ctx.guild.roles
                     if role.name.lower() == query_role.lower()), None)

        if role is None:
            return

        names = [str(m) + "\n" for m in role.members]
        header = f"List of users in {role.name} role - {len(names)}"

        # TODO remove for paginator take empty list for embed
        if not names:
            em = discord.Embed(title=header, colour=0xDA291C)
            em.set_footer(text="Page 01 of 01")
            await ctx.send(embed=em)
            return

        pages = Pages(ctx,
                      item_list=names,
                      title=header,
                      display_option=(3, 20),
                      editable_content=False)
        await pages.paginate()

    @commands.command(aliases=["cr", "createrole"])
    @is_moderator()
    async def create_role(self, ctx, *, role: Optional[str] = None):
        role = (role or "").strip()
        if not role:
            await ctx.send("Please specify a role name.")
            return

        role_obj = utils.get(ctx.guild.roles, name=role)
        if role_obj is not None:
            await ctx.send(f"Role `{role}` already exists!")
            return

        await ctx.guild.create_role(name=role, reason="Created with Canary")
        await ctx.send("Role created successfully.")

    def _save_existing_roles(self,
                             user: discord.Member,
                             penalty: bool = False):
        table = "PenaltyUsers" if penalty else "PreviousRoles"

        roles_id = [
            role.id for role in user.roles
            if role.name not in ("@everyone", self.penalty_role)
        ]

        if not roles_id and not penalty:
            return

        conn = sqlite3.connect(self.bot.config.db_path)
        try:
            c = conn.cursor()
            # store roles as a string of IDs separated by spaces
            t = (user.id, " ".join(str(e) for e in roles_id))
            c.execute(f"REPLACE INTO {table} VALUES (?, ?)", t)
            conn.commit()
        finally:
            conn.close()

    def _fetch_saved_roles(self,
                           guild,
                           user: discord.Member,
                           penalty: bool = False) -> Optional[list]:
        table = "PenaltyUsers" if penalty else "PreviousRoles"

        conn = sqlite3.connect(self.bot.config.db_path)
        try:
            c = conn.cursor()
            fetched_roles = c.execute(
                f"SELECT Roles FROM {table} WHERE ID = ?",
                (user.id, )).fetchone()
            # the above returns a tuple with a string of IDs separated by spaces

            # Return list of all valid roles restored from the DB
            #  - filter(None, ...) strips false-y elements
            return list(
                filter(None, (guild.get_role(int(role_id))
                              for role_id in fetched_roles[0].split(" ")
                              ))) if fetched_roles else None

        finally:
            conn.close()

    def _has_penalty_role(self, user: discord.Member):
        penalty_role = utils.get(user.guild.roles, name=self.penalty_role)
        return penalty_role and next(
            (r for r in user.roles if r == penalty_role), None) is None

    def _is_in_penalty_table(self, user: discord.Member):
        conn = sqlite3.connect(self.bot.config.db_path)
        try:
            c = conn.cursor()
            penalty = c.execute("SELECT * FROM PenaltyUsers WHERE ID = ?",
                                (user.id, )).fetchone()
            return penalty is not None
        finally:
            conn.close()

    def _remove_from_penalty_table(self, user: discord.Member):
        conn = sqlite3.connect(self.bot.config.db_path)
        try:
            c = conn.cursor()
            c.execute("DELETE FROM PenaltyUsers WHERE ID = ?", (user.id, ))
            conn.commit()
        finally:
            conn.close()

    @commands.Cog.listener()
    async def on_member_join(self, user: discord.Member):
        # If the user was already in the penalty box, restore the penalty role

        if not self._is_in_penalty_table(user):
            return

        penalty_role = utils.get(user.guild.roles, name=self.penalty_role)
        if penalty_role:
            await user.add_roles(penalty_role,
                                 reason="Restored penalty status")

    @commands.Cog.listener()
    async def on_member_remove(self, user: discord.Member):
        penalty_role = utils.get(user.guild.roles, name=self.penalty_role)

        if not penalty_role:
            return

        if not self._has_penalty_role(user):
            # Check if user has penalty entry but no penalty role. If so,
            # remove their penalty entry. This can occur if a mod manually
            # removed the penalty role instead of using ?unmute.
            self._remove_from_penalty_table(user)

        elif not self._is_in_penalty_table(user):
            # Check if the user has no penalty entry but the penalty role.
            # If so, save all roles BUT the penalty role into the
            # PreviousRoles table, and add a penalty entry to the database.
            self._save_existing_roles(user, penalty=True)

        # Save existing roles
        self._save_existing_roles(user)

    async def _role_restoring_page(self, ctx, user: discord.Member,
                                   roles: Optional[list]):
        if roles is None:
            # No row found in DB, as opposed to empty list
            embed = discord.Embed(
                title=f"Could not find any roles for {user.display_name}")
            await ctx.send(embed=embed)
            return

        roles_name = [
            f"[{i}] {role.name}\n" for i, role in enumerate(roles, 1)
        ]

        embed = discord.Embed(title="Loading...")
        message = await ctx.send(embed=embed)

        if len(roles) > 20:
            await message.add_reaction("◀")
            await message.add_reaction("▶")
        await message.add_reaction("🆗")

        p = Pages(
            ctx,
            item_list=roles_name,
            title=f"{user.display_name} had the following roles before leaving."
            f"\nA {self.bot.config.moderator_role} can add these roles "
            f"back by reacting with 🆗",
            msg=message,
            display_option=(3, 20),
            editable_content=True,
            editable_content_emoji="🆗",
            return_user_on_edit=True)
        ok_user = await p.paginate()

        while p.edit_mode:
            if not discord.utils.get(ok_user.roles,
                                     name=self.bot.config.moderator_role):
                # User is not moderator, simply paginate and return
                await p.paginate()
                return

            # Add a loading message until role-restoring is done
            await message.edit(embed=discord.Embed(title="Restoring roles..."))

            # User is a moderator, so restore the roles
            await user.add_roles(
                *roles, reason=f"{ok_user} restored roles via command")
            embed = discord.Embed(
                title=f"{user.display_name}'s previous roles were "
                f"successfully added back by {ok_user.display_name}")
            await message.edit(embed=embed)
            await message.clear_reaction("◀")
            await message.clear_reaction("▶")
            await message.clear_reaction("🆗")

    @commands.command(aliases=["previousroles", "giverolesback", "rolesback"])
    async def previous_roles(self, ctx, user: discord.Member):
        """Show the list of roles that a user had before leaving, if possible.
        A moderator can click the OK react on the message to give these roles back
        """

        if self._is_in_penalty_table(user):
            await ctx.send("Cannot restore roles to a user in the penalty box")
            return

        valid_roles = self._fetch_saved_roles(ctx.guild, user)
        await self._role_restoring_page(ctx, user, valid_roles)

    @commands.command(aliases=["penalty"])
    @is_moderator()
    async def mute(self, ctx, user: discord.Member):
        penalty_role = utils.get(ctx.guild.roles, name=self.penalty_role)

        if penalty_role is None:
            self.bot.dev_logger.error(PENALTY_ROLE_ERROR)
            await ctx.send(PENALTY_ROLE_ERROR)
            return

        # Save existing roles
        self._save_existing_roles(user, penalty=True)

        reason_message = f"{ctx.author} put {user} in the penalty box"

        # Remove all roles
        await user.remove_roles(*(r for r in user.roles
                                  if r.name != "@everyone"),
                                reason=reason_message)

        # Add the penalty role to the user
        await user.add_roles(penalty_role, reason=reason_message)
        await ctx.send(reason_message)

    @commands.command(aliases=["unpenalty"])
    @is_moderator()
    async def unmute(self, ctx, user: discord.Member):
        penalty_role = utils.get(ctx.guild.roles, name=self.penalty_role)

        if penalty_role is None:
            self.bot.dev_logger.error(PENALTY_ROLE_ERROR)
            await ctx.send(PENALTY_ROLE_ERROR)
            return

        if self._is_in_penalty_table(user) and \
                not self._has_penalty_role(user):
            # User had penalty role manually removed already
            self._remove_from_penalty_table(user)
            await ctx.send(f"{user.display_name} was already unmuted manually;"
                           f" removed role history from database")
            return

        reason_message = f"{ctx.author} removed {user} from the penalty box"

        # Restore old roles from the database
        valid_roles = self._fetch_saved_roles(ctx.guild, user, penalty=True)
        await self._role_restoring_page(ctx, user, valid_roles)

        # Remove the penalty role
        await user.remove_roles(penalty_role, reason=reason_message)

        # Remove entry from the database
        self._remove_from_penalty_table(user)

        await ctx.send(reason_message)

    @commands.command(aliases=["inchannel"])
    async def in_channel(self, ctx):
        """Returns list of users in current channel"""
        channel = ctx.message.channel
        members = channel.members

        channel_users = list(map(lambda m: str(m) + "\n", members))
        header = f"List of users in #{channel} - {len(members)}"

        pages = Pages(ctx,
                      item_list=channel_users,
                      title=header,
                      display_option=(3, 20),
                      editable_content=False)
        await pages.paginate()


def setup(bot):
    bot.add_cog(Roles(bot))
