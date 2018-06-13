#!/usr/bin/python3

# discord-py requirements
import discord
from discord.ext import commands
import asyncio

# For DB Functionality
import sqlite3
from tabulate import tabulate

# Other utilities
import random

# Set path to your .db file here
DB_PATH = './Martlet.db'


class Db():
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def addq(self, ctx, member: discord.Member, *, quote: str):
        """
        Add a quote to a user's quote database.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        t = (member.id, member.name, quote,
             ctx.message.created_at.strftime("%c"))
        c.execute('INSERT INTO Quotes VALUES (?,?,?,?)', t)
        yield from ctx.send('`Quote added.`')
        conn.commit()
        conn.close()

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def q(self, ctx, str1: str=None, *, str2: str=None):
        """
        Retrieve a quote with a specified keyword / mention.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        t = None
        mentions = ctx.message.mentions
        if str1 is None:        # No argument passed
            quotes = c.execute('SELECT ID, Name, Quote FROM Quotes').fetchall()
        elif mentions and mentions[0].mention == str1:  # Has args
            id = mentions[0].id
            if str2 is None:    # query for user only
                t = (id, '%%',)
            else:               # query for user and quote
                t = (id, '%{}%'.format(str2))
            c.execute('SELECT ID, Name, Quote FROM Quotes WHERE ID = ? AND Quote LIKE ?', t)
            quotes = c.fetchall()
        else:                   # query for quote only
            query = str1 if str2 is None else str1 + ' ' + str2
            t = ('%{}%'.format(query),)
            c.execute('SELECT ID, Name, Quote FROM Quotes WHERE Quote LIKE ?', t)
            quotes = c.fetchall()
        if not quotes:
            conn.close()
            yield from ctx.send('Quote not found.')
        else:
            conn.close()
            quote_tuple = random.choice(quotes)
            author_id = int(quote_tuple[0])
            name = quote_tuple[1]
            quote = quote_tuple[2]
            author = discord.utils.get(ctx.guild.members, id = author_id)
            # get author name, if the user is still on the server, their current nick will be displayed, otherwise use the name stored in db
            author_name = author.display_name if author else name
            yield from ctx.send('{} 📣 {}'.format(author_name, quote))

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def lq(self, ctx, author: discord.User=None):
        """
        List your quotes or the quotes of a mentioned user.
        """
        quote_author = author if author else ctx.message.author
        author_id = quote_author.id
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        quoteslist = c.execute('SELECT Quote FROM Quotes WHERE ID=?',
                               (author_id,)).fetchall()
        msg = "```Quotes: \n"
        for i in range(len(quoteslist)):
            if ((len(msg) + len('[%d] %s\n' %
                                (i+1, quoteslist[i][0]))) > 1996):
                msg += '```'
                yield from ctx.send(msg, delete_after=30)
                msg = '```[%d] %s\n' % (i+1, quoteslist[i][0].replace('```', ''))
            else:
                msg += '[%d] %s\n' % (i+1, quoteslist[i][0].replace('```', ''))
        if ((len(msg) + len('\n ~ End of Quotes ~```')) < 1996):
            msg += '\n ~ End of Quotes ~```'
            yield from ctx.send(msg, delete_after=30)
        else:
            msg += '```'
            yield from ctx.send(msg, delete_after=30)
            msg = '```\n ~ End of Quotes ~```'
            yield from ctx.send(msg, delete_after=30)

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def delq(self, ctx):
        """
        Delete a specific quote from your quotes.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        t = (ctx.message.author.id,)
        quoteslist = c.execute('SELECT Quote FROM Quotes WHERE ID=?',
                               t).fetchall()
        if not quoteslist:
            yield from ctx.send('No quotes found.')
            conn.close()
            return
        else:
            # print the quotes of the user in pages
            msg = "Please choose a quote you would like to delete.\n\n```"
            for i in range(len(quoteslist)):
                if ((len(msg) + len('[%d] %s\n' %
                                    (i+1, quoteslist[i][0]))) > 1996):
                    msg += '```'
                    yield from ctx.send(msg, delete_after=30)
                    msg = '```[%d] %s\n' % (i+1, quoteslist[i][0].replace('```', ''))
                else:
                    msg += '[%d] %s\n' % (i+1, quoteslist[i][0].replace('```', ''))
            if ((len(msg) +
                 len('\n[0] Exit without deleting quotes```')) < 1996):
                msg += '\n[0] Exit without deleting quotes```'
                yield from ctx.send(msg, delete_after=30)
            else:
                msg += '```'
                yield from ctx.send(msg, delete_after=30)
                msg = '```\n[0] Exit without deleting quotes```'
                yield from ctx.send(msg, delete_after=30)

        def check(message):
            if 0 <= int(message.content) <= (
                    1 + len(
                        quoteslist)) and message.author == ctx.message.author:
                return True
            else:
                yield from ctx.send("Invalid input.")
                return False

        response = yield from self.bot.wait_for("message", check=check)
        choice = int(response.content)
        if choice == 0:
            yield from ctx.send("Exited quote deletion menu.")
            conn.close()
            return
        else:
            t = (quoteslist[choice-1][0], ctx.message.author.id)
            c.execute('DELETE FROM Quotes WHERE Quote=? AND ID=?', t)
            yield from ctx.send("Quote successfully deleted.")
            conn.commit()
            conn.close()

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def ranking(self, ctx):
        """
        Upmartlet Rankings! :^)
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM Members ORDER BY Upmartlet DESC;")
        members = c.fetchall()[:7]
        table = []
        for (ID, DisplayName, Upmartlet) in members:
            table.append((DisplayName, Upmartlet))
        yield from ctx.send('```Java\n' +
                            tabulate(table, headers=["NAME", "#"],
                                     tablefmt="fancy_grid") +
                            '```', delete_after=30)

    # @asyncio.coroutine
    # def on_member_join(self, member):
    #     conn = sqlite3.connect(DB_PATH)
    #     c = conn.cursor()
    #     c.execute("SELECT * FROM Welcome")
    #     greetings = c.fetchall()
    #     msg = random.choice(greetings)[0]
    #     msg = msg.replace('$user$', member.mention)
    #     general = self.bot.get_channel(236668784948019202)
    #     yield from general.send(msg)
    #
    # @asyncio.coroutine
    # def on_member_leave(self, member):
    #     conn = sqlite3.connect(DB_PATH)
    #     c = conn.cursor()
    #     c.execute("SELECT * FROM Bye")
    #     farewell = c.fetchall()
    #     msg = random.choice(farewell)[0]
    #     msg = msg.replace('$user$', member.mention)
    #     general = self.bot.get_channel(236668784948019202)
    #     yield from general.send(msg)

def setup(bot):
    bot.add_cog(Db(bot))
