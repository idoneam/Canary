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

# For remindme functionality
import re


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
            reminders = c.execute('SELECT * FROM Reminders').fetchall()
            for i in range(len(reminders)):
                member = discord.utils.get(guild.members, id=reminders[i][0])
                if reminders[i][3] == 'once':
                    # TO be implemented
                    pass
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
            reminders = c.execute('SELECT * FROM Reminders WHERE ID = ?', (ctx.message.author.id,)).fetchall()

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
    async def remindme2(self, ctx, *, quote: str = ""):
        """
        Add a reminder to the reminder database.
        """

        # Copies original reminder message
        original_input_copy = quote

        replacements = {
            ("tomorrow", "1 day"),
            ("next week", "1 week"),
            ("later", "6 hours"),

            ("a", "1"),
            ("an", "1"),

            ("zero", "0"),
            ("no", "0"),
            ("none", "0"),
            ("one", "1"),
            ("two", "2"),
            ("three", "3"),
            ("four", "4"),
            ("five", "5"),
            ("six", "6"),
            ("seven", "7"),
            ("eight", "8"),
            ("nine", "9"),
            ("ten", "10"),
            ("eleven", "11"),
            ("twelve", "12"),
            ("thirteen", "13"),
            ("fourteen", "14"),
            ("fifteen", "15"),
            ("sixteen", "16"),
            ("seventeen", "17"),
            ("eighteen", "18"),
            ("nineteen", "19"),
            ("twenty", "20"),
            ("twenty-one", "21"),
            ("twenty one", "21"),
            ("twenty-two", "22"),
            ("twenty two", "22"),
            ("twenty-three", "23"),
            ("twenty three", "23"),
            ("twenty-four", "24"),
            ("twenty four", "24"),
            ("twenty-five", "25"),
            ("twenty five", "25"),
            ("twenty-six", "26"),
            ("twenty six", "26"),
            ("twenty-seven", "27"),
            ("twenty seven", "27"),
            ("twenty-eight", "28"),
            ("twenty eight", "28"),
            ("twenty-nine", "29"),
            ("twenty nine", "29"),
            ("thirty", "30"),
            ("thirty-one", "31"),
            ("thirty one", "31"),
            ("thirty-two", "32"),
            ("thirty two", "32"),
            ("thirty-three", "33"),
            ("thirty three", "33"),
            ("thirty-four", "34"),
            ("thirty four", "34"),
            ("thirty-five", "35"),
            ("thirty five", "35"),
            ("thirty-six", "36"),
            ("thirty six", "36"),
            ("thirty-seven", "37"),
            ("thirty seven", "37"),
            ("thirty-eight", "38"),
            ("thirty eight", "38"),
            ("thirty-nine", "39"),
            ("thirty nine", "39"),
            ("forty", "40"),
            ("forty-one", "41"),
            ("forty one", "41"),
            ("forty-two", "42"),
            ("forty two", "42"),
            ("forty-three", "43"),
            ("forty three", "43"),
            ("forty-four", "44"),
            ("forty four", "44"),
            ("forty-five", "45"),
            ("forty five", "45"),
            ("forty-six", "46"),
            ("forty six", "46"),
            ("forty-seven", "47"),
            ("forty seven", "47"),
            ("forty-eight", "48"),
            ("forty eight", "48"),
            ("forty-nine", "49"),
            ("forty nine", "49"),
            ("fifty", "50")
        }

        units = {
            "years": "ye?a?r?s?",
            "days": "da?y?s?",
            "hours": "ho?u?r?s?",
            "seconds": "se?c?o?n?d?s?",
            "minutes": "mi?n?u?t?e?s?",
            "weeks": "we?e?k?s?"
        }

        # Stores units + number for calculating timedelta
        time_offset = {
            "years": 0,
            "days": 0,
            "hours": 0,
            "seconds": 0,
            "minutes": 0,
            "weeks": 0
        }

        punctuation_chars = ".,+&/ "
        string_word_separator_regex = r"(\s|["+punctuation_chars+"])+"
        time_separator_regex = r"(,|\+|&|and|plus|in)"
        # Regex to match units below (Which accounts for spelling mistakes!) 
        unit_regex = r"("+"|".join(list(units.values()))+")"
        # Matches a natural number
        number_regex = r"[1-9]+[0-9]*(|\.[0-9]+)"

        # Replaces word representation of numbers into numerical representation
        for k, v in replacements:
            original_input_copy = re.sub(r"\b"+k+r"\b", v, original_input_copy)

        # Split on spaces and other relevant punctuation
        input_segments = re.split(string_word_separator_regex, original_input_copy)
        input_segments = list(map(lambda x: x.strip(punctuation_chars), input_segments))

        # Remove empty strings from list
        input_segments = list(filter(lambda x: x != "", input_segments))

        time_segments = []
        last_number = "0"
        last_item_was_number = False
        first_reminder_segment = ""

        """ Checks the following logic: 
            1. If one of the keywords commonly used for listing times is there, continue
            2. If a number is found, save the number, mark that a number has been found for next iteration
            3. Elif: A "unit" (years, days ... etc.) has been found, append the last number + its unit
            4. Lastly: save beginning of "reminder quote" and end loop
        """        
        for segment in input_segments:
            if re.match("^"+time_separator_regex+"$", segment):
                continue
            if re.match("^"+number_regex+"$", segment):
                last_number = segment
                last_item_was_number = True
            elif re.match("^"+unit_regex+"$", segment):
                time_segments.append(last_number+" "+segment)
            else:
                first_reminder_segment = segment
                break

        # They probably dont want their reminder nuked of punctuation, spaces and formatting, so extract from original string
        reminder = quote[quote.index(first_reminder_segment):]

        # Regex for the number and time units and store in "match"
        for segment in time_segments:
            match = re.match("^("+number_regex+")"+r"\s+"+unit_regex+"$", segment)
            number = float(match.group(1))
            unit = "minutes" # default but should always be overridden
            # Might wanna add default numbers to this too, in case no time is specified.

            # Regex potentially misspelled time units and match to proper spelling
            for regex in units:
                if re.match("^"+regex+"$", match.group(3)):
                    unit = match.group(3)
            time_offset[unit] += number

        time_now = datetime.datetime.now() # Current time
        reminder_time = time_now + datetime.timedelta(days = time_offset["days"], hours = time_offset["hours"], 
                                                        seconds = time_offset["seconds"], minutes = time_offset["minutes"],
                                                        weeks = time_offset["weeks"])
        
        # date will hold tDELTA, lastReminder will hold time.now()
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        t = (ctx.message.author.id, ctx.message.author.name, reminder, "once", reminder_time, time_now)
        # Could strip word "to" from reminder message.
        reminders = c.execute('SELECT * FROM Reminders WHERE ID =?', (ctx.message.author.id,)).fetchall()
        

        try:
            c.execute('INSERT INTO Reminders VALUES (?, ?, ?, ?, ?, ?)', t)
        except sqlite3.OperationalError:
            c.execute("CREATE TABLE 'Reminders' ('ID'INTEGER,'Name'TEXT,'Reminder'TEXT,'Frequency'TEXT,'Date'\
                        TEXT,'LastReminder'TEXT)")
            c.execute('INSERT INTO Reminders VALUES (?, ?, ?, ?, ?. ?)', t)

        # Format reminder_time properly so that it is user friendly.
        await ctx.author.send('Hi {}! \n I will remind you to {} on {} unless you send me a message to stop '
                                   'reminding you about it! [{:d}]'
                                   .format(ctx.author.name,  reminder, reminder_time, len(reminders)+1))
        await ctx.send('Reminder added.')
        conn.commit()
        conn.close()

        # More test outputs
        await ctx.send("NOW: " + str(datetime.datetime.now()))
        await ctx.send("tDELTA: " + str(reminder_time)) # Testing timedelta
        await ctx.send("Reminder: " + reminder) # Testing reminder message
        await ctx.send("DIFF (NOW-tDELTA): " + str(datetime.datetime.now()-reminder_time))

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
