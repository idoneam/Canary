# -*- coding: utf-8 -*-
#
# Copyright (C) idoneam (2016-2020)
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

# discord.py requirements
import discord
from discord.ext import commands

# for DB
import sqlite3
from tabulate import tabulate
from .utils.paginator import Pages
from collections import Counter

from itertools import chain


class Score(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None
        self.UPMARTLET = None
        self.DOWNMARTLET = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.bot.config.server_id)
        self.UPMARTLET = discord.utils.get(self.guild.emojis,
                                           name=self.bot.config.upvote_emoji)
        self.DOWNMARTLET = discord.utils.get(
            self.guild.emojis, name=self.bot.config.downvote_emoji)

    async def _get_name_from_id(self, user_id):
        try:
            user = self.bot.get_user(user_id)
            if user is None:
                raise AttributeError
            name = str(user)
        except AttributeError:
            try:
                user = await self.bot.fetch_user(user_id)
                name = str(user)
                if "Deleted User" in username:
                    name = str(user_id)
            except discord.errors.NotFound:
                name = str(user_id)
        return name

    async def _add_member_if_needed(self, user_id):
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT Name FROM Members WHERE ID = ?", (user_id, ))
        if not c.fetchone():
            name = await self._get_name_from_id(user_id)
            c.execute('INSERT OR IGNORE INTO Members VALUES (?,?)',
                      (user_id, name))
        conn.commit()
        conn.close()

    async def _add_or_remove_reaction_from_db(self, payload, remove=False):
        channel = self.bot.get_channel(payload.channel_id)
        message_id = payload.message_id

        try:
            message = await channel.fetch_message(message_id)
        except discord.errors.NotFound:
            return

        reacter_id = self.bot.get_user(payload.user_id).id
        await self._add_member_if_needed(reacter_id)
        reactee_id = message.author.id
        await self._add_member_if_needed(reactee_id)

        emoji = payload.emoji

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        if remove:
            c.execute(
                'DELETE FROM Reactions WHERE ReacterID = ? AND ReacteeID = ? '
                'AND ReactionName = ? AND MessageID = ?',
                (reacter_id, reactee_id, str(emoji), message_id))
        else:
            c.execute('INSERT OR IGNORE INTO Reactions VALUES (?,?,?,?)',
                      (reacter_id, reactee_id, str(emoji), message_id))
        conn.commit()
        conn.close()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.guild_id == self.guild.id:
            await self._add_or_remove_reaction_from_db(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.guild_id == self.guild.id:
            await self._add_or_remove_reaction_from_db(payload, remove=True)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if str(before) == str(after):
            return

        user_id = after.id
        new_name = str(after)
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO Members VALUES (?,?)',
                  (user_id, new_name))
        conn.commit()
        conn.close()

    @commands.command()
    async def score(self, ctx, str1: str = None, *, str2: str = None):
        """Display your score for a given emoji. If no arguments are given,
           displays your total upmartlet/downmartlet score.
           Arguments: An emoji (optional) and a mention (optional), in any order
        """
        mentions = ctx.message.mentions
        member = ctx.message.author
        emoji = None

        if mentions:
            member = mentions[0]
            if str1 and str1.replace("!", "") != mentions[0].mention.replace(
                    "!", ""):
                emoji = str1

            if str2 and str2.replace("!", "") != mentions[0].mention.replace(
                    "!", ""):
                emoji = str2
        elif str1:
            emoji = str1

        if emoji:
            try:
                await ctx.message.remove_reaction(emoji, self.bot.user)
            except discord.errors.HTTPException:
                await ctx.send("Invalid emoji or username")
                return

        m_id = member.id
        nick = member.display_name

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        if not emoji:
            emoji = "total"
            c.execute(
                "SELECT count(ReacteeID) FROM Reactions WHERE ReacteeID = ? "
                "AND ReactionName = ? AND ReacterID != ReacteeID",
                (m_id, str(self.UPMARTLET)))
            upmartlets = c.fetchone()[0]
            c.execute(
                "SELECT count(ReacteeID) FROM Reactions WHERE ReacteeID = ? "
                "AND ReactionName = ? AND ReacterID != ReacteeID",
                (m_id, str(self.DOWNMARTLET)))
            downmartlets = c.fetchone()[0]
            react_count = upmartlets - downmartlets
        else:
            c.execute(
                "SELECT count(ReacteeID) FROM Reactions WHERE ReacteeID = ? "
                "AND ReactionName = ? AND ReacterID != ReacteeID",
                (m_id, emoji))
            react_count = c.fetchone()[0]

        await ctx.send("{}'s {} score is {}.".format(nick, emoji, react_count))

        conn.close()

    @commands.command()
    async def ranking(self, ctx, emoji: str = None):
        """Get the ranking for a given emoji. If no arguments are given,
           displays your total upmartlet/downmartlet score.
           Arguments: An emoji (optional)
        """
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        if not emoji:
            c.execute(
                "SELECT M.Name, count(*) "
                "FROM Reactions AS R, Members as M "
                "WHERE R.ReactionName = ? "
                "AND R.ReacterID != R.ReacteeID "
                "AND R.ReacteeID = M.ID "
                "GROUP BY R.ReacteeID "
                "ORDER BY count(*) DESC", (str(self.UPMARTLET), ))
            upmartlet_dict = dict(c.fetchall())
            c.execute(
                "SELECT M.Name, count(*) "
                "FROM Reactions AS R, Members as M "
                "WHERE R.ReactionName = ? "
                "AND R.ReacterID != R.ReacteeID "
                "AND R.ReacteeID = M.ID "
                "GROUP BY R.ReacteeID "
                "ORDER BY count(*) DESC", (str(self.DOWNMARTLET), ))
            downmartlet_dict = dict(c.fetchall())
            total_score_dict = {
                key: upmartlet_dict.get(key, 0) - downmartlet_dict.get(key, 0)
                for key in chain(upmartlet_dict, downmartlet_dict)
            }

            sorted_score_dict = dict(Counter(total_score_dict).most_common())

            names = list(
                map(lambda x, y: f"{y}. {x}", sorted_score_dict,
                    range(1,
                          len(sorted_score_dict) + 1)))
            values = list(sorted_score_dict.values())
            emoji = "Total"
        else:
            try:
                await ctx.message.remove_reaction(emoji, self.bot.user)
            except discord.errors.HTTPException:
                await ctx.send("Invalid emoji")
                return
            c.execute(
                "SELECT M.Name, count(*) "
                "FROM Reactions AS R, Members as M "
                "WHERE R.ReactionName = ? "
                "AND R.ReacterID != R.ReacteeID "
                "AND R.ReacteeID = M.ID "
                "GROUP BY R.ReacteeID "
                "ORDER BY count(*) DESC", (emoji, ))
            counts = list(zip(*c.fetchall()))
            if not counts:
                await ctx.send(embed=discord.Embed(
                    title="This reaction was never used on this server."))
                return
            names = list(
                map(lambda x, y: f"{y}. {x}", counts[0],
                    range(1,
                          len(counts[0]) + 1)))
            values = counts[1]

        paginator_dict = {"names": names, "values": values}
        p = Pages(ctx,
                  item_list=paginator_dict,
                  title="{} score ranking".format(emoji),
                  display_option=(2, 9),
                  editable_content=False)

        await p.paginate()
        conn.close()


def setup(bot):
    bot.add_cog(Score(bot))
