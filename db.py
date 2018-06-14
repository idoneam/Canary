#!/usr/bin/python3

# discord-py requirements
import discord
from discord.ext import commands
import asyncio

# For DB Functionality
import sqlite3
from tabulate import tabulate
import datetime

# Other utilities
import random

# Set path to your .db file here
DB_PATH = './Martlet.db'


class Db():
    def __init__(self, bot):
        self.bot = bot
        self.frequencies = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30
        }

    @asyncio.coroutine
    def check_reminders(self):
        """
        Co-routine that periodically checks if the bot must issue reminders to users.
        :return: None
        """
        yield from self.bot.wait_until_ready()
        while not self.bot.is_closed():
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            g = (guild for guild in self.bot.guilds if guild.name == 'McGill University')
            guild = next(g)
            try:
                reminders = c.execute('SELECT * FROM Reminders').fetchall()
            except sqlite3.OperationalError:
                c.execute("CREATE TABLE 'Reminders' ('ID'INTEGER,'Name'TEXT,'Reminder'TEXT,'Frequency'TEXT,'Date'TEXT,"
                          "'LastReminder'TEXT)")
                reminders = c.execute('SELECT * FROM Reminders').fetchall()
                conn.commit()
            for i in range(len(reminders)):
                member = discord.utils.get(guild.members, id=reminders[i][0])
                last_date = datetime.datetime.strptime(reminders[i][5], "%Y-%m-%d %H:%M:%S.%f")
                if datetime.datetime.now() - last_date > datetime.timedelta(days=self.frequencies[reminders[i][3]]):
                    yield from member.send("Reminding you to {}! [{:d}]".format(reminders[i][2], i + 1))

                    c.execute("UPDATE 'Reminders' SET LastReminder = ? WHERE Reminder = ?", (datetime.datetime.now(),
                                                                                             reminders[i][2]))
                    conn.commit()
                    yield from asyncio.sleep(1)
            conn.close()
            yield from asyncio.sleep(60 * 10)

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def stop_reminder(self, ctx, reminder: str):
        """
        [DM Only] Delete the specified reminder
        :param reminder: An integer choice for reminder based on Martlet's last set of DM's with reminders.
        """
        if isinstance(ctx.message.channel, discord.DMChannel):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            try:
                reminders = c.execute('SELECT * FROM Reminders WHERE ID = ?', (ctx.message.author.id,)).fetchall()
            except sqlite3.OperationalError:
                c.execute("CREATE TABLE 'Reminders' ('ID'INTEGER,'Name'TEXT,'Reminder'TEXT,'Frequency'TEXT,'Date'TEXT,"
                          "'LastReminder'TEXT)")
                yield from ctx.send("Database created.")
                return
            try:
                choice = int(reminder)
                if choice < 1 or choice > len(reminders):
                    raise ValueError
            except ValueError:
                yield from ctx.send("Please specify a choice number between 1 and {:d}!"
                                    .format(len(reminders)))
                conn.close()
                return
            t = (reminders[choice - 1][2], ctx.message.author.id, reminders[choice - 1][3])
            c.execute('DELETE FROM Reminders WHERE Reminder=? AND ID=? AND DATE=?', t)
            conn.commit()
            conn.close()
            yield from ctx.send("Reminder successfully removed!")
        else:
            yield from ctx.send("Slide into my DM's ;) (Please respond to my DM messages to stop "
                                "reminders!)")

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def remindme(self, ctx, freq: str, *, quote: str):
        """
        Add a reminder to the reminder database.
        """
        if freq not in self.frequencies.keys():
            yield from ctx.send("Please ensure you specify a frequency from the following list: `daily`, `weekly`, "
                                "`monthly`!")
            return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        t = (ctx.message.author.id, ctx.message.author.name, quote, freq, datetime.datetime.now(),
             datetime.datetime.now())
        reminders = c.execute('SELECT * FROM Reminders WHERE Reminder =? AND ID = ?',
                              (quote, ctx.message.author.id)).fetchall()
        if len(reminders) > 0:
            yield from ctx.send("The reminder `{}` already exists in your database. Please specify a unique reminder "
                                "message!".format(quote))
            return
        reminders = c.execute('SELECT * FROM Reminders WHERE ID =?', (ctx.message.author.id,)).fetchall()
        try:
            c.execute('INSERT INTO Reminders VALUES (?, ?, ?, ?, ?, ?)', t)
        except sqlite3.OperationalError:
            c.execute("CREATE TABLE 'Reminders' ('ID'INTEGER,'Name'TEXT,'Reminder'TEXT,'Frequency'TEXT,'Date'\
                        TEXT,'LastReminder'TEXT)")
            c.execute('INSERT INTO Reminders VALUES (?, ?, ?, ?, ?. ?)', t)
        yield from ctx.author.send('Hi {}! \n I will remind you to {} {} until you send me a message to stop '
                                   'reminding you about it! [{:d}]'
                                   .format(ctx.author.name,  quote, freq, len(reminders)+1))
        yield from ctx.send('Reminder added.')
        conn.commit()
        conn.close()

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def addq(self, ctx, member: discord.Member, *, quote: str):
        """
        Add a quote to a user's quote database.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        t = (member.id, member.name, quote,
             datetime.date.today())
        c.execute('INSERT INTO Quotes VALUES (?,?,?,?)', t)
        yield from ctx.send('`Quote added.`')
        conn.commit()
        conn.close()

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def q(self, ctx, str1: str = None, *, str2: str = None):
        """
        Retrieve a quote with a specified keyword / mention.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if str1 is None:  # no argument
            quotes = c.execute('SELECT Quote FROM Quotes').fetchall()
            quote = random.choice(quotes)
            Name = c.execute('SELECT Name FROM Quotes WHERE Quote LIKE ?',
                             quote).fetchall()[0][0]
            quote_split = quote[0].replace('"', '')
            if (len(quote_split) > 500):
                yield from ctx.send("%(ID)s :mega: %(quote)s" %
                                    {"ID": Name, "quote": quote[0]}, delete_after=600)
            else:
                yield from ctx.send("%(ID)s :mega: %(quote)s" %
                                    {"ID": Name, "quote": quote[0]}, delete_after=3600)

            conn.close()
            return
        elif str2 is None:  # 1 argument
            numArgs = 1
            args = str1
        else:  # 2 arguments
            numArgs = 2
            argl = [str1, str2]
            args = ' '.join(argl)
        if (args[1] == '@'):  # member argument supplied
            args = args.split()
            if numArgs == 2:  # has query
                t = ((args[0][3:(len(args[0]) - 1)]),
                     '%' + (' '.join(args[1:])) + '%')
            qId = ''
            for i in range(len(args[0])):
                if (args[0][i] in '0123456789'):
                    qId = qId + args[0][i]
            if numArgs == 2:  # query
                t = (qId, '%' + (' '.join(args[1:])) + '%')
                quoteslist = c.execute(
                    'SELECT Quote FROM Quotes WHERE ID=? AND Quote LIKE ?',
                    t).fetchall()
            else:  # no query
                t = (qId,)
                quoteslist = c.execute(
                    'SELECT Quote FROM Quotes WHERE ID=?', t).fetchall()
            if not quoteslist:  # no result
                yield from ctx.send('No quotes found.')
                conn.close()
                return
            else:  # result
                quote = random.choice(quoteslist)
                quote_stripped = quote[0].replace('"', '')
                if (len(quote_stripped) > 500):
                    yield from ctx.send(":mega: %s" % quote, delete_after=600)
                else:
                    yield from ctx.send(":mega: %s" % quote, delete_after=3600)

                conn.close()
                return
        else:  # no member argument - only query
            t = ('%' + args[0:] + '%',)
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
                                        % {"ID": Name, "quote": quote[0]}, delete_after=600)
                else:
                    yield from ctx.send("%(ID)s :mega: %(quote)s"
                                        % {"ID": Name, "quote": quote[0]}, delete_after=3600)

                conn.close()
                return

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def lq(self, ctx, str1: str = None):
        """
        List your quotes or the quotes of a mentioned user.
        """
        if str1 is None:
            member = ctx.message.author
            t = (member.id,)
        else:
            t = ((str1[3:(len(str1[0]) - 2)]),)
            print(t)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        quoteslist = c.execute('SELECT Quote FROM Quotes WHERE ID=?',
                               t).fetchall()
        msg = "```Quotes: \n"
        for i in range(len(quoteslist)):
            if ((len(msg) + len('[%d] %s\n' %
                                (i + 1, quoteslist[i][0]))) > 1996):
                msg += '```'
                yield from ctx.send(msg, delete_after=30)
                msg = '```[%d] %s\n' % (i + 1, quoteslist[i][0])
            else:
                msg += '[%d] %s\n' % (i + 1, quoteslist[i][0])
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
                                    (i + 1, quoteslist[i][0]))) > 1996):
                    msg += '```'
                    yield from ctx.send(msg, delete_after=30)
                    msg = '```[%d] %s\n' % (i + 1, quoteslist[i][0])
                else:
                    msg += '[%d] %s\n' % (i + 1, quoteslist[i][0])
            if ((len(msg) +
                 len('\n[0] Exit without deleting quotes```')) < 1996):
                msg += '\n[0] Exit without deleting quotes```'
                yield from ctx.send(msg, delete_after=30)
            else:
                msg += '```'
                yield from ctx.send(msg, delete_after=30)
                msg = '```\n[0] Exit without deleting quotes```'
                yield from ctx.send(msg, delete_after=30)

        def check(choice):
            if 0 <= int(choice.content) <= (1 + len(quoteslist)) and choice.author == message.author:
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
            t = (quoteslist[choice - 1][0], ctx.message.author.id)
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
    database = Db(bot)
    bot.add_cog(database)
    bot.loop.create_task(database.check_reminders())
