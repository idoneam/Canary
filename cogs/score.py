#!usr/bin python3

# discord.py requirements
import discord
from discord.ext import commands
import asyncio

# for DB
import sqlite3
from tabulate import tabulate
from .utils.paginator import Pages


class Score():
    def __init__(self, bot):
        self.bot = bot

    async def on_raw_reaction_add(self, payload):
        # Check for Martlet emoji + upmartletting yourself
        channel = self.bot.get_channel(payload.channel_id)
        try:
            message = await channel.get_message(payload.message_id)
        except discord.errors.NotFound:
            return
        user = self.bot.get_user(payload.user_id)
        emoji = payload.emoji

        if user == message.author:
            return
        if emoji.name == 'upmartlet':
            score = 1
        elif emoji.name == 'downmartlet':
            score = -1
        else:
            return

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        # uncomment to enable sqlite3 debugging
        # conn.set_trace_callback(print)
        t = (message.author.id, )
        if not c.execute('SELECT * FROM Members WHERE ID=?', t).fetchall():
            t = (message.author.id, message.author.display_name, score)
            c.execute('INSERT INTO Members VALUES (?,?,?)', t)
            conn.commit()
            conn.close()
        else:
            if score == 1:
                c.execute('UPDATE Members SET Score=Score+1 WHERE ID=?', t)
            else:
                c.execute('UPDATE Members SET Score=Score-1 WHERE ID=?', t)
            conn.commit()
            conn.close()

    async def on_raw_reaction_remove(self, payload):
        # Check for Martlet emoji + upmartletting yourself
        """Does the opposite thing when a user up/downmarlets a message
        """
        channel = self.bot.get_channel(payload.channel_id)
        try:
            message = await channel.get_message(payload.message_id)
        except discord.errors.NotFound:
            return
        user = self.bot.get_user(payload.user_id)
        emoji = payload.emoji

        if user == message.author:
            return
        if emoji.name == 'upmartlet':
            score = -1
        elif emoji.name == 'downmartlet':
            score = 1
        else:
            return

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        t = (message.author.id, )
        if not c.execute('SELECT * FROM Members WHERE ID=?', t).fetchall():
            t = (message.author.id, message.author.display_name, score)
            c.execute('INSERT INTO Members VALUES (?,?,?)', t)
            conn.commit()
            conn.close()
        else:
            if score == 1:
                c.execute('UPDATE Members SET Score=Score+1 WHERE ID=?', t)
            else:
                c.execute('UPDATE Members SET Score=Score-1 WHERE ID=?', t)
            conn.commit()
            conn.close()

    async def on_member_update(self, before, after):
        if before.display_name == after.display_name:
            return
        else:
            id = after.id
            new_nick = after.display_name
            conn = sqlite3.connect(self.bot.config.db_path)
            c = conn.cursor()
            if not c.execute("SELECT * FROM Members WHERE ID = ?", (id, )):
                c.execute("INSERT INTO Members VALUES (?,?,?)", (
                    id,
                    new_nick,
                    0,
                ))
                conn.commit()
            else:
                c.execute("UPDATE Members SET DisplayName = ? WHERE ID = ?", (
                    new_nick,
                    id,
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
                "Ranking is not yet available for this server, please upvote/downvote moar."
            )
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
            itemList=table_list,
            title="Upmartlet ranking",
            displayOption=(0, 1),
            editableContent=False)
        await p.paginate()

    @commands.command()
    async def score(self, ctx, member: discord.Member = None):
        member = member if member else ctx.message.author
        id = member.id
        nick = member.display_name
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT Score FROM Members WHERE ID = ?", (id, ))
        score = c.fetchone()
        if not score:
            t = (
                id,
                nick,
                0,
            )
            c.execute("INSERT INTO Members VALUES (?,?,?)", t)
            conn.commit()
            await ctx.send("{} score is 0.".format(nick))
        else:
            await ctx.send("{} score is {}".format(nick, score[0]))
        conn.close()


def setup(bot):
    bot.add_cog(Score(bot))
