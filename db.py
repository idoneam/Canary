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
             str(ctx.message.created_at))
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
        if str1 is None:    # no argument
            quotes = c.execute('SELECT Quote FROM Quotes').fetchall()
            quote = random.choice(quotes)
            Name = c.execute('SELECT Name FROM Quotes WHERE Quote LIKE ?',
                             quote).fetchall()[0][0]
            quote_split = quote[0].replace('"', '')
            if (len(quote_split) > 500):
                yield from ctx.send(
                    "%(ID)s :mega: %(quote)s" % {
                        "ID": Name,
                        "quote": quote[0]
                    },
                    delete_after=600)
            else:
                yield from ctx.send(
                    "%(ID)s :mega: %(quote)s" % {
                        "ID": Name,
                        "quote": quote[0]
                    },
                    delete_after=3600)

            conn.close()
            return
        elif str2 is None:  # 1 argument
            numArgs = 1
            args = str1
        else:   # 2 arguments
            numArgs = 2
            argl = [str1, str2]
            args = ' '.join(argl)
        if (args[1] == '@'):    # member argument supplied
            args = args.split()
            if numArgs == 2:    # has query
                t = ((args[0][3:(len(args[0])-1)]),
                     '%'+(' '.join(args[1:]))+'%')
            qId = ''
            for i in range(len(args[0])):
                if (args[0][i] in '0123456789'):
                    qId = qId + args[0][i]
            if numArgs == 2:    # query
                t = (qId, '%'+(' '.join(args[1:]))+'%')
                quoteslist = c.execute(
                    'SELECT Quote FROM Quotes WHERE ID=? AND Quote LIKE ?',
                    t).fetchall()
            else:   # no query
                t = (qId,)
                quoteslist = c.execute(
                    'SELECT Quote FROM Quotes WHERE ID=?', t).fetchall()
            if not quoteslist:  # no result
                yield from ctx.send('No quotes found.')
                conn.close()
                return
            else:   # result
                quote = random.choice(quoteslist)
                quote_stripped = quote[0].replace('"', '')
                if (len(quote_stripped) > 500):
                    yield from ctx.send(":mega: %s" % quote, delete_after=600)
                else:
                    yield from ctx.send(":mega: %s" % quote, delete_after=3600)

                conn.close()
                return
        else:   # no member argument - only query
            t = ('%'+args[0:]+'%',)
            quoteslist = c.execute(
                'SELECT Quote FROM Quotes WHERE Quote LIKE ?', t).fetchall()
            if not quoteslist:
                yield from ctx.send('No quotes found.')
                conn.close()
                return
            else:
                quote = random.choice(quoteslist)
                Name = c.execute(
                    'SELECT Name FROM Quotes WHERE Quote LIKE ?',
                    quote).fetchall()[0][0]
                quote_stripped = quote[0].replace('"', '')
                if (len(quote_stripped) > 500):
                    yield from ctx.send("%(ID)s :mega: %(quote)s"
                                        % {
                                            "ID": Name,
                                            "quote": quote[0]
                                        },
                                        delete_after=600)
                else:
                    yield from ctx.send("%(ID)s :mega: %(quote)s"
                                        % {
                                            "ID": Name,
                                            "quote": quote[0]
                                        },
                                        delete_after=3600)

                conn.close()
                return

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def lq(self, ctx, str1: str=None):
        """
        List your quotes or the quotes of a mentioned user.
        """
        if str1 is None:
            member = ctx.message.author
            t = (member.id,)
        else:
            t = ((str1[2:(len(str1[0])-2)]),)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        quoteslist = c.execute('SELECT Quote FROM Quotes WHERE ID=?',
                               t).fetchall()
        msg = "```Quotes: \n"
        for i in range(len(quoteslist)):
            if ((len(msg) + len('[%d] %s\n' %
                                (i+1, quoteslist[i][0]))) > 1996):
                msg += '```'
                yield from ctx.send(msg, delete_after=30)
                msg = '```[%d] %s\n' % (i+1, quoteslist[i][0])
            else:
                msg += '[%d] %s\n' % (i+1, quoteslist[i][0])
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
                    msg = '```[%d] %s\n' % (i+1, quoteslist[i][0])
                else:
                    msg += '[%d] %s\n' % (i+1, quoteslist[i][0])
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


def setup(bot):
    bot.add_cog(Db(bot))
