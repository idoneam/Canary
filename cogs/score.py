# -*- coding: utf-8 -*-
#
# Copyright (C) idoneam (2016-2019)
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
import asyncio

# for DB
import sqlite3
from tabulate import tabulate
from .utils.paginator import Pages


class Score(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None
        self.UPMARTLET = None
        self.DOWNMARTLET = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.bot.config.server_id)
        self.UPMARTLET = discord.utils.get(
            self.guild.emojis, name=self.bot.config.upvote_emoji)
        self.DOWNMARTLET = discord.utils.get(
            self.guild.emojis, name=self.bot.config.downvote_emoji)

    def _get_score(self, emoji):
        if emoji.id == self.UPMARTLET.id:
            return 1

        elif emoji.id == self.DOWNMARTLET.id:
            return -1

        return 0

    async def _update_score_if_needed(self, payload, negated=False):
        # Check for Martlet emoji + upmartletting yourself

        channel = self.bot.get_channel(payload.channel_id)

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.errors.NotFound:
            return

        user = self.bot.get_user(payload.user_id)
        emoji = payload.emoji

        if user == message.author:
            return

        score = self._get_score(emoji) * (-1 if negated else 1)
        if score == 0:
            return

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        t = (score, message.author.id)

        if c.execute('SELECT * FROM Members WHERE ID=?', t[1:]).fetchall():
            # Member record already exists
            c.execute('UPDATE Members SET Score=Score+? WHERE ID=?', t)
        else:
            # No record exists for the user yet
            c.execute('INSERT INTO Members VALUES (?, ?, ?)',
                      (message.author.id, message.author.display_name, score))

        conn.commit()
        conn.close()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self._update_score_if_needed(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self._update_score_if_needed(payload, negated=True)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.display_name == after.display_name:
            return

        m_id = after.id
        new_nick = after.display_name
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        if not c.execute("SELECT * FROM Members WHERE ID = ?", (m_id, )):
            c.execute("INSERT INTO Members VALUES (?, ?, ?)", (
                m_id,
                new_nick,
                0,
            ))
            conn.commit()

        else:
            c.execute("UPDATE Members SET DisplayName = ? WHERE ID = ?", (
                new_nick,
                m_id,
            ))
            conn.commit()

        conn.close()

    @commands.command()
    async def ranking(self, ctx):
        """
        Upmartlet Rankings! :^)
        """
        await ctx.trigger_typing()

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM Members ORDER BY Score DESC;")
        members = c.fetchall()

        if not members:
            await ctx.send(
                "Ranking is not yet available for this server, please "
                "upvote/downvote moar.")
            return

        table = []
        table_list = []
        counter = 1

        for (ID, DisplayName, Upmartlet) in members:
            table.append((counter, DisplayName, Upmartlet))
            if counter % 7 == 0 or counter == len(members):
                table_list.append(
                    tabulate(
                        table[:counter],
                        headers=["Rank", "Name", "Score"],
                        tablefmt="fancy_grid"))
                del table[:]
            counter += 1

        p = Pages(
            ctx,
            item_list=table_list,
            title="Upmartlet ranking",
            display_option=(0, 1),
            editable_content=False)

        await p.paginate()

    @commands.command()
    async def score(self, ctx, member: discord.Member = None):
        """Displays member's score in upmartlet rankings."""

        member = member if member else ctx.message.author
        m_id = member.id
        nick = member.display_name

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        c.execute("SELECT Score FROM Members WHERE ID = ?", (m_id, ))
        score = c.fetchone()

        if not score:
            score = (0, )
            c.execute("INSERT INTO Members VALUES (?, ?, ?)", (m_id, nick, 0))
            conn.commit()

        await ctx.send("{} score is {}.".format(nick, score[0]))

        conn.close()


def setup(bot):
    bot.add_cog(Score(bot))
