#!/usr/bin/python3

# discord-py requirements
import discord
from discord.ext import commands
import asyncio

# For DB Functionality
import sqlite3
import datetime

# Other utilities
import random
from .utils.paginator import Pages

# For remindme functionality
import re

class Reminder():
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

                # If non-repeating reminder is found
                if reminders[i][3] == 'once':
                    # Check date to remind user
                    reminder_activation_date = datetime.datetime.strptime(reminders[i][4], "%Y-%m-%d %H:%M:%S.%f")
                    # Compute future_date-current_date and if <= 0:00:00, means time is due to remind user
                    if reminder_activation_date - datetime.datetime.now() <= datetime.timedelta(0):
                        await member.send("Reminding you to {}!".format(reminders[i][2]))
                        # Remove from from DB non-repeating reminder
                        c.execute('DELETE FROM Reminders WHERE Reminder=? AND ID=? AND DATE=?', (reminders[i][2], reminders[i][0],
                                                                                                    reminder_activation_date))
                        conn.commit()
                        await asyncio.sleep(1)
                else:
                    last_date = datetime.datetime.strptime(reminders[i][5], "%Y-%m-%d %H:%M:%S.%f")
                    if datetime.datetime.now() - last_date > datetime.timedelta(days=self.frequencies[reminders[i][3]]):
                        await member.send("Reminding you to {}! [{:d}]".format(reminders[i][2], i + 1))

                        c.execute("UPDATE 'Reminders' SET LastReminder = ? WHERE Reminder = ?", (datetime.datetime.now(),
                                                                                                 reminders[i][2]))
                        conn.commit()
                        await asyncio.sleep(1)
            conn.close()
            await asyncio.sleep(60 * 1)

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
    async def remindme(self, ctx, *, quote: str = ""):
        """
        Parses the reminder and adds a one-time reminder to the reminder database or
        calls remindme_repeating to deal with repetitive reminders when keyword
        "daily", "weekly" or "monthly" is found.
        """

        # Copies original reminder message and sets lowercase for regex.
        original_input_copy = quote.lower()

        # Letter numbers to number numbers
        replacements = [
            (r"twenty[-\s]one", "21"),
            (r"twenty[-\s]two", "22"),
            (r"twenty[-\s]three", "23"),
            (r"twenty[-\s]four", "24"),
            (r"twenty[-\s]five", "25"),
            (r"twenty[-\s]six", "26"),
            (r"twenty[-\s]seven", "27"),
            (r"twenty[-\s]eight", "28"),
            (r"twenty[-\s]nine", "29"),

            (r"thirty[-\s]one", "31"),
            (r"thirty[-\s]two", "32"),
            (r"thirty[-\s]three", "33"),
            (r"thirty[-\s]-four", "34"),
            (r"thirty[-\s]four", "34"),
            (r"thirty[-\s]five", "35"),
            (r"thirty[-\s]six", "36"),
            (r"thirty[-\s]seven", "37"),
            (r"thirty[-\s]eight", "38"),
            (r"thirty[-\s]nine", "39"),

            (r"forty[-\s]one", "41"),
            (r"forty[-\s]two", "42"),
            (r"forty[-\s]three", "43"),
            (r"forty[-\s]four", "44"),
            (r"forty[-\s]five", "45"),
            (r"forty[-\s]six", "46"),
            (r"forty[-\s]seven", "47"),
            (r"forty[-\s]eight", "48"),
            (r"forty[-\s]nine", "49"),

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
            ("thirty", "30"),
            ("forty", "40"),
            ("fifty", "50")
        ]

        # Regex for misspellings of time units
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
        # Regex for format YYYY-MM-DD
        YMDRegex = r"(2[0-1][0-9][0-9])[\s./-]((1[0-2]|0?[1-9]))[\s./-](([1-2][0-9]|3[0-1]|0?[1-9]))"
        # Regex for time HH:MM
        HMRegex = r"\b([0-1]?[0-9]|2[0-4]):([0-5][0-9])"

        # Replaces word representation of numbers into numerical representation
        for k, v in replacements:
            original_input_copy = re.sub(r"\b"+k+r"\b", v, original_input_copy)

        # Split on spaces and other relevant punctuation
        input_segments = re.split(string_word_separator_regex, original_input_copy)
        input_segments = [x.strip(punctuation_chars) for x in input_segments]

        # Remove empty strings from list
        input_segments = [x for x in input_segments if x != ""]

        time_segments = []
        last_number = "0"
        last_item_was_number = False
        first_reminder_segment = ""

        """ Checks the following logic:
            1. If daily, weekly or monthly is specified, go to old reminder function for repetitive reminders
        for all input segments:
            2. If one of the keywords commonly used for listing times is there, continue
            3. If a number is found, save the number, mark that a number has been found for next iteration
            4. Elif: A "unit" (years, days ... etc.) has been found, append the last number + its unit
            5. Lastly: save beginning of "reminder quote" and end loop
        """

        if len(input_segments) > 0 and (input_segments[0] == "daily" or input_segments[0] == "weekly" or
                                        input_segments[0] == "monthly"):
            await remindme_repeating(self, ctx, input_segments[0], quote=quote[len(input_segments[0])+1:])
            return
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

        # Date-based reminder triggered by "at" and "on" keywords
        if input_segments[0] == 'at' or input_segments[0] == 'on':
            date_result = re.search(YMDRegex, original_input_copy) # Gets YYYY-mm-dd
            time_result = re.search(HMRegex, original_input_copy) # Gets HH:MM

            # If both a date and a time is found, continue
            if date_result and time_result:
                # Compute datetime.Object
                absolute_duedate = datetime.datetime.strptime(date_result.group(1)+"-"+date_result.group(2)+"-"+
                        date_result.group(4)+"-"+time_result.group(1)+"-"+time_result.group(2)+"-"+str(0.1),
                            "%Y-%m-%d-%H-%M-%S.%f")

                # Strips "to" and dates from the reminder message
                time_input_end = time_result.span()[1]
                if re.match("to", reminder[time_input_end:time_input_end+4].strip(), re.IGNORECASE):
                    reminder = reminder[time_input_end+3:].strip()
                else:
                    reminder = reminder[time_input_end+1:].strip()

                # Add message to database
                conn = sqlite3.connect(self.bot.config.db_path)
                c = conn.cursor()
                t = (ctx.message.author.id, ctx.message.author.name, reminder, "once", absolute_duedate, datetime.datetime.now())
                try:
                    c.execute('INSERT INTO Reminders VALUES (?, ?, ?, ?, ?, ?)', t)
                except sqlite3.OperationalError:
                    c.execute("CREATE TABLE 'Reminders' ('ID'INTEGER,'Name'TEXT,'Reminder'TEXT,'Frequency'TEXT,'Date'\
                                TEXT,'LastReminder'TEXT)")
                    c.execute('INSERT INTO Reminders VALUES (?, ?, ?, ?, ?. ?)', t)

                # Send user information and close database
                reminders = c.execute('SELECT * FROM Reminders WHERE ID =?', (ctx.message.author.id,)).fetchall()
                await ctx.author.send('Hi {}! \nI will remind you to {} on {} at {} unless you send me a message to stop '
                                   'reminding you about it! [{:d}]'
                                   .format(ctx.author.name,  reminder, date_result.group(0), time_result.group(0), len(reminders)+1))
                await ctx.send('Reminder added.')
                conn.commit()
                conn.close()
                return

            # Wrong input feedback depending on what is missing.
            await ctx.send("Please check your private messages for information on correct syntax!")
            await ctx.author.send("Please double check the following: ")
            if not date_result:
                await ctx.author.send("Make sure you have specified a date in the format: `YYYY-mm-dd`")
            if not time_result:
                await ctx.author.send("Make sure you have specified a time in the 24H format: `HH:MM`")
            await ctx.author.send("E.g.: `?remindme on 2020-12-05 at 21:44 to feed Marty`")
            return

        # Regex for the number and time units and store in "match"
        for segment in time_segments:
            match = re.match("^("+number_regex+")"+r"\s+"+unit_regex+"$", segment)
            number = float(match.group(1))
            unit = "minutes" # default but should always be overridden

            # Regex potentially misspelled time units and match to proper spelling
            for regex in units:
                if re.match("^"+units[regex]+"$", match.group(3)):
                    time_offset[regex] += number


        # Convert years to a unit that datetime will understand
        time_offset["days"] = time_offset["days"] + time_offset["years"] * 365

        time_now = datetime.datetime.now() # Current time
        reminder_time = time_now + datetime.timedelta(days = time_offset["days"], hours = time_offset["hours"],
                                                        seconds = time_offset["seconds"], minutes = time_offset["minutes"],
                                                        weeks = time_offset["weeks"]) # Time to be reminded on
        if time_now == reminder_time: # No time in argument, or it's zero.
            await ctx.send("Please specify a time! E.g.: `?remindme in 1 hour " + reminder + "`")
            return
        # Strips the string "to " from reminder messages
        if reminder[:3].lower() == 'to ':
            reminder = reminder[3:]
        # DB: Date will hold TDELTA (When reminder is due), LastReminder will hold datetime.datetime.now()
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        t = (ctx.message.author.id, ctx.message.author.name, reminder, "once", reminder_time, time_now)
        reminders = c.execute('SELECT * FROM Reminders WHERE ID =?', (ctx.message.author.id,)).fetchall()
        try:
            c.execute('INSERT INTO Reminders VALUES (?, ?, ?, ?, ?, ?)', t)
        except sqlite3.OperationalError:
            c.execute("CREATE TABLE 'Reminders' ('ID'INTEGER,'Name'TEXT,'Reminder'TEXT,'Frequency'TEXT,'Date'\
                        TEXT,'LastReminder'TEXT)")
            c.execute('INSERT INTO Reminders VALUES (?, ?, ?, ?, ?. ?)', t)

        # Gets reminder date in YYYY-MM-DD format
        due_date = str(datetime.date(reminder_time.year, reminder_time.month, reminder_time.day))
        # Gets reminder time in HH:MM
        due_time = str(reminder_time).split()[1].split(":")[0] + ":" + str(reminder_time).split()[1].split(":")[1]
        await ctx.author.send('Hi {}! \nI will remind you to {} on {} at {} unless you send me a message to stop '
                                   'reminding you about it! [{:d}]'
                                   .format(ctx.author.name,  reminder, due_date, due_time, len(reminders)+1))
        await ctx.send('Reminder added.')
        conn.commit()
        conn.close()


    async def remindme_repeating(self, ctx, freq: str = "", *, quote: str = ""):
        """
        Called by remindme to add a repeating reminder to the reminder database.
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
        # Strips the string "to " from reminder messages
        if quote[:3].lower() == "to ":
            quote = quote[3:]
        await ctx.author.send('Hi {}! \nI will remind you to {} {} until you send me a message to stop '
                                   'reminding you about it! [{:d}]'
                                   .format(ctx.author.name,  quote, freq, len(reminders)+1))
        await ctx.send('Reminder added.')
        conn.commit()
        conn.close()


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
    database = Reminder(bot)
    bot.add_cog(database)
    bot.loop.create_task(database.check_reminders())
