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

import aiosqlite
import asyncio
import discord
import re

from datetime import datetime, timedelta
from discord.ext import commands

from .base_cog import CanaryCog
from .utils.paginator import Pages


ONES_NAMES = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
# Haha English start at 20
TENS_NAMES = ("twenty", "thirty", "forty", "fifty")

REMINDER_LETTER_REPLACEMENTS = (
    [(rf"{TENS_NAMES[t-2]}[-\s]{ONES_NAMES[o-1]}", str((t * 10) + o)) for t in range(2, 6) for o in range(1, 10)]
    + [(TENS_NAMES[t - 2], str(t * 10)) for t in range(2, 6)]
    + [
        ("tomorrow", "1 day"),
        ("next week", "1 week"),
        ("later", "6 hours"),
        ("a", "1"),
        ("an", "1"),
        ("no", "0"),
        ("none", "0"),
        ("zero", "0"),
        *zip(ONES_NAMES, range(1, 10)),
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
    ]
)

# Regex for misspellings of time units
REMINDER_UNITS = {
    "years": "ye?a?r?s?",
    "days": "da?y?s?",
    "hours": "ho?u?r?s?",
    "seconds": "se?c?o?n?d?s?",
    "minutes": "mi?n?u?t?e?s?",
    "weeks": "we?e?k?s?",
}

PUNCTUATION_CHARS = ".,+&/ "
STRING_WORD_SEPARATOR_REGEX = re.compile(r"(\s|[" + PUNCTUATION_CHARS + "])+")
TIME_SEPARATOR_REGEX = re.compile(r"^(,|\+|&|and|plus|in)$")

# Matches a natural number. May be used in other regex, so not compiled.
NUMBER_REGEX = r"[1-9]+[0-9]*(|\.[0-9]+)"

# Regex to match units below (Which accounts for spelling mistakes!)
# May be used in other regex, so not compiled.
UNIT_REGEX = r"({})".format("|".join(list(REMINDER_UNITS.values())))

# Regex for format YYYY-MM-DD
# TODO: Fix redundant groups
YMD_REGEX = re.compile(r"(2[0-1][0-9][0-9])[\s./-]((1[0-2]|0?[1-9]))[\s./-]" r"(([1-2][0-9]|3[0-1]|0?[1-9]))")

# Regex for time HH:MM
HM_REGEX = re.compile(r"\b([0-1]?[0-9]|2[0-4]):([0-5][0-9])")

FREQUENCIES = {"daily": 1, "weekly": 7, "monthly": 30}


class Reminder(CanaryCog):
    async def check_reminders(self):
        """
        Co-routine that periodically checks if the bot must issue reminders to
        users.
        :return: None
        """

        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            if not (guild := self.guild):
                return

            async with self.db() as db:
                reminders = await self.fetch_list("SELECT * FROM Reminders", db=db)

                for i, reminder in enumerate(reminders):
                    member = discord.utils.get(guild.members, id=reminder[0])
                    now = datetime.now()

                    # If non-repeating reminder is found
                    if reminder[3] == "once":
                        # Check date to remind user
                        reminder_activation_date = datetime.strptime(reminder[4], "%Y-%m-%d %H:%M:%S.%f")
                        # Compute future_date and current_date and if past, means
                        # time is due to remind user.
                        if reminder_activation_date <= now:
                            await member.send(f"Reminding you to {reminder[2]}!")
                            # Remove from from DB non-repeating reminder
                            await db.execute(
                                "DELETE FROM Reminders WHERE Reminder=? AND ID=? AND DATE=?",
                                (reminder[2], reminder[0], reminder_activation_date),
                            )
                            await db.commit()
                            await asyncio.sleep(1)

                    else:
                        last_date = datetime.strptime(reminder[5], "%Y-%m-%d %H:%M:%S.%f")

                        if now - last_date > timedelta(days=FREQUENCIES[reminders[i][3]]):
                            await member.send(f"Reminding you to {reminder[2]}! [{i + 1:d}]")
                            await db.execute("UPDATE Reminders SET LastReminder=? WHERE Reminder=?", (now, reminder[2]))
                            await db.commit()
                            await asyncio.sleep(1)

            await asyncio.sleep(60)  # seconds

    @commands.command(aliases=["rm", "rem"])
    async def remindme(self, ctx: commands.Context, *, quote: str = ""):
        """
        Parses the reminder and adds a one-time reminder to the reminder
        database or calls remindme_repeating to deal with repetitive reminders
        when keyword "daily", "weekly" or "monthly" is found.
        """

        db: aiosqlite.Connection
        c: aiosqlite.Cursor

        if quote == "":
            await ctx.send(
                "**Usage:** \n"
                "`?remindme in 1 hour and 20 minutes and 20 seconds to eat` **or** \n"
                "`?remindme at 2020-04-30 11:30 to graduate` **or** \n"
                "`?remindme daily to sleep`"
            )
            return

        # Copies original reminder message and sets lowercase for regex.
        original_input_copy = quote.lower()

        # Stores units + number for calculating timedelta
        time_offset = {"years": 0, "days": 0, "hours": 0, "seconds": 0, "minutes": 0, "weeks": 0}

        # Replaces word representation of numbers into numerical representation
        for k, v in REMINDER_LETTER_REPLACEMENTS:
            original_input_copy = re.sub(r"\b{}\b".format(k), v, original_input_copy)

        # Split on spaces and other relevant punctuation
        input_segments = re.split(STRING_WORD_SEPARATOR_REGEX, original_input_copy)
        input_segments = [x.strip(PUNCTUATION_CHARS) for x in input_segments]

        # Remove empty strings from list
        input_segments = [x for x in input_segments if x != ""]

        time_segments = []
        last_number = "0"
        first_reminder_segment = ""
        """ Checks the following logic:
            1. If daily, weekly or monthly is specified, go to old reminder
               function for repetitive reminders for all input segments:
            2. If one of the keywords commonly used for listing times is there,
               continue
            3. If a number is found, save the number, mark that a number has
               been found for next iteration
            4. Elif: A "unit" (years, days ... etc.) has been found, append the
               last number + its unit
            5. Lastly: save beginning of "reminder quote" and end loop
        """

        if len(input_segments) > 0 and (input_segments[0] in ("daily", "weekly", "monthly")):
            await self.__remindme_repeating(ctx, input_segments[0], quote=quote[len(input_segments[0]) + 1 :])
            return

        for segment in input_segments:
            if re.match(TIME_SEPARATOR_REGEX, segment):
                continue
            if re.match(rf"^{NUMBER_REGEX}$", segment):
                last_number = segment
            elif re.match(rf"^{UNIT_REGEX}$", segment):
                time_segments.append(f"{last_number} {segment}")
            else:
                first_reminder_segment = segment
                break

        # They probably don't want their reminder nuked of punctuation, spaces
        # and formatting, so extract from original string.
        reminder = quote[quote.index(first_reminder_segment) :]

        msg_author = ctx.message.author

        # Date-based reminder triggered by "at" and "on" keywords
        if input_segments[0] in {"at", "on"}:
            # Gets YYYY-mm-dd
            date_result = re.search(YMD_REGEX, original_input_copy)
            # Gets HH:MM
            time_result = re.search(HM_REGEX, original_input_copy)

            if date_result is None or time_result is None:
                # Wrong input feedback depending on what is missing.
                await ctx.send("Check your private messages for info on correct syntax!")
                await ctx.author.send("Please double check the following: ")
                if not date_result:
                    await ctx.author.send("Make sure you have specified a date in the format: `YYYY-mm-dd`")
                if not time_result:
                    await ctx.author.send("Make sure you have specified a time in the 24H format: `HH:MM`")
                await ctx.author.send("E.g.: `?remindme on 2020-12-05 at 21:44 to feed Marty`")
                return

            # Otherwise, both a date and a time are found, so continue

            # Compute datetime.Object
            absolute_duedate = datetime.strptime(
                "{Y}-{m}-{d}-{H}-{M}-{S}".format(
                    Y=date_result.group(1),
                    m=date_result.group(2),
                    d=date_result.group(4),
                    H=time_result.group(1),
                    M=time_result.group(2),
                    S=0.1,
                ),
                "%Y-%m-%d-%H-%M-%S.%f",
            )

            # Strips "to" and dates from the reminder message
            time_input_end = time_result.span()[1]
            if re.match("to", reminder[time_input_end : time_input_end + 4].strip(), re.IGNORECASE):
                reminder = reminder[time_input_end + 3 :].strip()
            else:
                reminder = reminder[time_input_end + 1 :].strip()

            # Add message to database
            async with self.db() as db:
                t = (
                    msg_author.id,
                    msg_author.name,
                    reminder,
                    "once",
                    absolute_duedate,
                    datetime.now(),
                )
                await db.execute("INSERT INTO Reminders VALUES (?, ?, ?, ?, ?, ?)", t)
                await db.commit()

                # Send user information

                num_reminders = await self.get_num_reminders(db, msg_author)

            await ctx.author.send(
                f"Hi {ctx.author.name}! \nI will remind you to {reminder} on {date_result.group(0)} at "
                f"{time_result.group(0)} unless you send me a message to stop reminding you about it! "
                f"[{num_reminders + 1:d}]"
            )

            await ctx.send("Reminder added.")
            return

        # Regex for the number and time units and store in "match"
        for segment in time_segments:
            match = re.match(rf"^({NUMBER_REGEX})\s+{UNIT_REGEX}$", segment)
            number = float(match.group(1))

            # Regex potentially misspelled time units and match to proper
            # spelling.
            for regex in REMINDER_UNITS:
                if re.match(f"^{REMINDER_UNITS[regex]}$", match.group(3)):
                    time_offset[regex] += number

        # Convert years to a unit that datetime will understand
        time_offset["days"] = time_offset["days"] + time_offset["years"] * 365

        time_now = datetime.now()  # Current time
        reminder_time = time_now + timedelta(
            days=time_offset["days"],
            hours=time_offset["hours"],
            seconds=time_offset["seconds"],
            minutes=time_offset["minutes"],
            weeks=time_offset["weeks"],
        )  # Time to be reminded on

        if time_now == reminder_time:  # No time in argument, or it's zero.
            await ctx.send(f"Please specify a time! E.g.: `?remindme in 1 hour {reminder}`")
            return

        # Strips the string "to " from reminder messages
        if reminder[:3].lower() == "to ":
            reminder = reminder[3:]

        # DB: Date will hold TDELTA (When reminder is due), LastReminder will
        # hold datetime.datetime.now()
        async with self.db() as db:
            num_reminders = await self.get_num_reminders(db, msg_author)
            t = (msg_author.id, msg_author.name, reminder, "once", reminder_time, time_now)
            await db.execute("INSERT INTO Reminders VALUES (?, ?, ?, ?, ?, ?)", t)
            await db.commit()

        await ctx.author.send(
            f"Hi {ctx.author.name}! \nI will remind you to {reminder} on "
            f"{reminder_time.strftime('%Y-%m-%d at %H:%M')} unless you send me a message to stop "
            f"reminding you about it! [{num_reminders+1:d}]"
        )
        await ctx.send("Reminder added.")

    @staticmethod
    def formatted_reminder_list(rem_list):
        return [
            "[{num}] (Frequency: {freq}{opt_date}) - {rem_text}".format(
                num=i,
                freq=rem[3].capitalize(),
                opt_date=(" at {date}".format(date=rem[4].split(".")[0]) if rem[3] == "once" else ""),
                rem_text=rem[2],
            )
            for i, rem in enumerate(rem_list, 1)
        ]

    @commands.command(aliases=["lr"])
    async def list_reminders(self, ctx):
        """
        List reminders
        """

        db: aiosqlite.Connection
        c: aiosqlite.Cursor

        await ctx.trigger_typing()

        if not isinstance(ctx.message.channel, discord.DMChannel):
            await ctx.send(
                "Slide into my DMs ;). \n`List Reminder feature only "
                "available when DMing {}.`".format(self.bot.config.bot_name)
            )
            return

        rem_author = ctx.message.author

        rem_list = await self.fetch_list("SELECT * FROM Reminders WHERE ID = ?", (rem_author.id,))
        if not rem_list:
            await ctx.send("No reminder found.", delete_after=60)
            return

        p = Pages(
            ctx,
            item_list=self.formatted_reminder_list(rem_list),
            title=f"{rem_author.display_name}'s reminders",
        )

        await p.paginate()

        def msg_check(msg):
            try:
                return (
                    0 <= int(msg.content) <= len(rem_list)
                    and msg.author.id == rem_author.id
                    and msg.channel == ctx.message.channel
                )

            except ValueError:
                return False

        while p.edit_mode:
            await ctx.send(
                "Delete option selected. Enter a number to specify which "
                "reminder you want to delete, or enter 0 to return.",
                delete_after=60,
            )

            try:
                message = await self.bot.wait_for("message", check=msg_check, timeout=60)

            except asyncio.TimeoutError:
                await ctx.send("Command timeout. You may want to run the command again.", delete_after=60)
                break

            else:
                # Displays are 1-indexed.
                index = int(message.content) - 1

                if index == -1:
                    await ctx.send("Exit delq.", delete_after=60)

                else:
                    r = rem_list[index]

                    # Remove deleted reminder from list:
                    del rem_list[index]

                    async with self.db() as db:
                        await db.execute("DELETE FROM Reminders WHERE ID = ? AND Reminder = ?", (r[0], r[2]))
                        await db.commit()

                    await ctx.send("Reminder deleted", delete_after=60)

                    p.itemList = self.formatted_reminder_list(rem_list)

                await p.paginate()

    async def __remindme_repeating(self, ctx: commands.Context, freq: str = "", *, quote: str = ""):
        """
        Called by remindme to add a repeating reminder to the reminder
        database.
        """

        db: aiosqlite.Connection

        bad_input = False

        freq = freq.strip()
        quote = quote.strip()

        if freq not in FREQUENCIES.keys():
            await ctx.send(
                "Please ensure you specify a frequency from the following list: "
                "`daily`, `weekly`, `monthly`, before your message!"
            )
            bad_input = True

        if quote == "":
            if bad_input and freq == "" or not bad_input:
                await ctx.send("Please specify a reminder message!")
            bad_input = True

        if bad_input:
            return

        msg_author = ctx.message.author

        existing_reminder = await self.fetch_one(
            "SELECT * FROM Reminders WHERE Reminder = ? AND ID = ?", (quote, msg_author.id)
        )
        if existing_reminder is not None:
            await ctx.send(
                f"The reminder `{quote}` already exists in your database. Please specify a unique reminder message!"
            )
            return

        now = datetime.now()
        async with self.db() as db:
            num_reminders = await self.get_num_reminders(db, msg_author)
            await db.execute(
                "INSERT INTO Reminders VALUES (?, ?, ?, ?, ?, ?)",
                (msg_author.id, msg_author.name, quote, freq, now, now),
            )
            await db.commit()

        # Strips the string "to " from reminder messages
        if quote[:3].lower() == "to ":
            quote = quote[3:]

        await ctx.author.send(
            f"Hi {ctx.author.name}! \nI will remind you to {quote} {freq} until you send me a message "
            f"to stop reminding you about it! [{num_reminders+1:d}]"
        )

        await ctx.send("Reminder added.")

    async def get_num_reminders(self, db: aiosqlite.Connection, author: discord.Member | discord.User) -> int:
        num_reminders_t = await self.fetch_one("SELECT COUNT(*) FROM Reminders WHERE ID = ?", (author.id,), db=db)
        return num_reminders_t[0] if num_reminders_t is not None else 0


def setup(bot):
    database = Reminder(bot)
    bot.add_cog(database)
    bot.loop.create_task(database.check_reminders())