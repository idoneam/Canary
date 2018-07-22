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
from utils.paginator import Pages


class Db():
    def __init__(self, bot):
        self.bot = bot
        self.frequencies = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30
        }

    async def check_reminders(self):
        """
        Co-routine that periodically checks if the bot must issue reminders to users.
        :return: None
        """
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            conn = sqlite3.connect(self.bot.config.db_path)
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
                    await member.send("Reminding you to {}! [{:d}]".format(reminders[i][2], i + 1))

                    c.execute("UPDATE 'Reminders' SET LastReminder = ? WHERE Reminder = ?", (datetime.datetime.now(),
                                                                                             reminders[i][2]))
                    conn.commit()
                    await asyncio.sleep(1)
            conn.close()
            await asyncio.sleep(60 * 10)

    @commands.command()
    async def stop_reminder(self, ctx, reminder: str = ""):
        """
        [DM Only] Delete the specified reminder
        :param reminder: An integer choice for reminder based on Martlet's last set of DM's with reminders.
        """
        if isinstance(ctx.message.channel, discord.DMChannel):
            conn = sqlite3.connect(self.bot.config.db_path)
            c = conn.cursor()
            try:
                reminders = c.execute('SELECT * FROM Reminders WHERE ID = ?', (ctx.message.author.id,)).fetchall()
            except sqlite3.OperationalError:
                c.execute("CREATE TABLE 'Reminders' ('ID'INTEGER,'Name'TEXT,'Reminder'TEXT,'Frequency'TEXT,'Date'TEXT,"
                          "'LastReminder'TEXT)")
                await ctx.send("Database created.")
                return
            try:
                choice = int(reminder)
                if choice < 1 or choice > len(reminders):
                    raise ValueError
            except ValueError:
                await ctx.send("Please specify a choice number between 1 and {:d}!"
                                    .format(len(reminders)))
                conn.close()
                return
            t = (reminders[choice - 1][2], ctx.message.author.id, reminders[choice - 1][4])
            c.execute('DELETE FROM Reminders WHERE Reminder=? AND ID=? AND DATE=?', t)
            conn.commit()
            conn.close()
            await ctx.send("Reminder successfully removed!")
        else:
            await ctx.send("Slide into my DM's ;) (Please respond to my DM messages to stop "
                                "reminders!)")

    @commands.command()
    async def remindme(self, ctx, freq: str = "", *, quote: str = ""):
        """
        Add a reminder to the reminder database.
        """

        bad_input = False
        if freq not in self.frequencies.keys():
            await ctx.send("Please ensure you specify a frequency from the following list: `daily`, `weekly`, "
                                "`monthly`, before your message!")
            bad_input = True
        if quote == "":
            if bad_input and freq == "" or not bad_input:
                await ctx.send("Please specify a reminder message!")
            else:
                pass
            bad_input = True
        if bad_input:
            return

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        t = (ctx.message.author.id, ctx.message.author.name, quote, freq, datetime.datetime.now(),
             datetime.datetime.now())
        reminders = c.execute('SELECT * FROM Reminders WHERE Reminder =? AND ID = ?',
                              (quote, ctx.message.author.id)).fetchall()
        if len(reminders) > 0:
            await ctx.send("The reminder `{}` already exists in your database. Please specify a unique reminder "
                                "message!".format(quote))
            return
        reminders = c.execute('SELECT * FROM Reminders WHERE ID =?', (ctx.message.author.id,)).fetchall()
        try:
            c.execute('INSERT INTO Reminders VALUES (?, ?, ?, ?, ?, ?)', t)
        except sqlite3.OperationalError:
            c.execute("CREATE TABLE 'Reminders' ('ID'INTEGER,'Name'TEXT,'Reminder'TEXT,'Frequency'TEXT,'Date'\
                        TEXT,'LastReminder'TEXT)")
            c.execute('INSERT INTO Reminders VALUES (?, ?, ?, ?, ?. ?)', t)
        await ctx.author.send('Hi {}! \n I will remind you to {} {} until you send me a message to stop '
                                   'reminding you about it! [{:d}]'
                                   .format(ctx.author.name,  quote, freq, len(reminders)+1))
        await ctx.send('Reminder added.')
        conn.commit()
        conn.close()

    @commands.command()
    async def addq(self, ctx, member: discord.Member, *, quote: str):
        """
        Add a quote to a user's quote database.
        """
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        t = (member.id, member.name, quote,
             str(ctx.message.created_at))
        c.execute('INSERT INTO Quotes VALUES (?,?,?,?)', t)
        await ctx.send('`Quote added.`')
        conn.commit()
        conn.close()

    @commands.command()
    async def q(self, ctx, str1: str = None, *, str2: str = None):
        """
        Retrieve a quote with a specified keyword / mention.
        """
        conn = sqlite3.connect(self.bot.config.db_path)
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
            await ctx.send('Quote not found.')
        else:
            conn.close()
            quote_tuple = random.choice(quotes)
            author_id = int(quote_tuple[0])
            name = quote_tuple[1]
            quote = quote_tuple[2]
            author = discord.utils.get(ctx.guild.members, id = author_id)
            # get author name, if the user is still on the server, their current nick will be displayed, otherwise use the name stored in db
            author_name = author.display_name if author else name
            await ctx.send('{} 📣 {}'.format(author_name, quote))

    @commands.command(aliases=['lq'])
    async def listQuote(self, ctx, author: discord.User=None):
        '''
        List quotes
        '''
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        quoteAuthor = author if author else ctx.message.author
        author_id = quoteAuthor.id
        t = (author_id,)
        c.execute('SELECT * FROM Quotes WHERE ID = ?', t)
        quoteList = c.fetchall()
        if quoteList:
            quoteListText = ['[{}] {}'.format(i+1, quote[2]) for i,quote in zip(range(len(quoteList)),quoteList)]
            p = Pages(ctx,
                itemList=quoteListText,
                title='Quotes from {}'.format(quoteAuthor.display_name)
            )
            await p.paginate()
            index = 0
            def msgCheck(message):
                try:
                    if (1 <= int(message.content) <= len(quoteList)) and message.author.id == author_id:
                        return True
                    return False
                except ValueError:
                    return False
            while p.delete:
                await ctx.send('Delete option selected. Enter a number to specify which quote you want to delete', delete_after=60)
                try:
                    message = await self.bot.wait_for('message', check=msgCheck, timeout=60)
                except asyncio.TimeoutError:
                    await ctx.send('Command timeout. You may want to run the command again.', delete_after=60)
                    break
                else:
                    index = int(message.content)-1
                    t = (quoteList[index][0], quoteList[index][2],)
                    del quoteList[index]
                    c.execute('DELETE FROM Quotes WHERE ID = ? AND Quote = ?', t)
                    conn.commit()
                    await ctx.send('Quote deleted', delete_after=60)
                    await message.delete()
                    p.itemList = ['[{}] {}'.format(i+1, quote[2]) for i,quote in zip(range(len(quoteList)),quoteList)]
                    await p.paginate()
            await ctx.message.delete()
            conn.commit()
            conn.close()
        else:
            await ctx.send('No quote found.', delete_after=60)

    @commands.command()
    async def ranking(self, ctx):
        """
        Upmartlet Rankings! :^)
        """
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM Members ORDER BY Upmartlet DESC;")
        members = c.fetchall()[:7]
        table = []
        for (ID, DisplayName, Upmartlet) in members:
            table.append((DisplayName, Upmartlet))
        await ctx.send('```Java\n' +
                            tabulate(table, headers=["NAME", "#"],
                                     tablefmt="fancy_grid") +
                            '```', delete_after=30)

    # @asyncio.coroutine
    # def on_member_join(self, member):
    #     conn = sqlite3.connect(self.bot.config.db_path)
    #     c = conn.cursor()
    #     c.execute("SELECT * FROM Welcome")
    #     greetings = c.fetchall()
    #     msg = random.choice(greetings)[0]
    #     msg = msg.replace('$user$', member.mention)
    #     general = self.bot.get_channel(236668784948019202)
    #     await general.send(msg)
    #
    # @asyncio.coroutine
    # def on_member_leave(self, member):
    #     conn = sqlite3.connect(self.bot.config.db_path)
    #     c = conn.cursor()
    #     c.execute("SELECT * FROM Bye")
    #     farewell = c.fetchall()
    #     msg = random.choice(farewell)[0]
    #     msg = msg.replace('$user$', member.mention)
    #     general = self.bot.get_channel(236668784948019202)
    #     await general.send(msg)

def setup(bot):
    database = Db(bot)
    bot.add_cog(database)
    bot.loop.create_task(database.check_reminders())
