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

# for the alphabet list
import string

# for the timeout
import time

ALPHABET = list(string.ascii_uppercase)
EMOJI_ALPHABET = [
    u"\U0001F1E6", u"\U0001F1E7", u"\U0001F1E8", u"\U0001F1E9", u"\U0001F1EA", u"\U0001F1EB",
    u"\U0001F1EC", u"\U0001F1ED", u"\U0001F1EE", u"\U0001F1EF", u"\U0001F1F0", u"\U0001F1F1",
    u"\U0001F1F2", u"\U0001F1F3", u"\U0001F1F4", u"\U0001F1F5", u"\U0001F1F6", u"\U0001F1F7"
]  # :regional_indicator_a: to :regional_indicator_r:
TIME_UNITS = {
    "second": 1, "seconds": 1,
    "minute": 60, "minutes": 60,
    "hour": 60 * 60, "hours": 60 * 60,
    "day": 24 * 60 * 60, "days": 24 * 60 * 60
}


class Poll:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def poll(self, ctx, *args):
        """
        Creates a poll with a maximum of 18 options.
        ==Examples==
        ?poll "Question" "Option 1" "Option 2" "..."
        ?poll -t 30 minutes "Question" "Option 1" "..."
        ?poll "Question" "Option 1" "..." -t 1.5 hours
        ==Switches (can be put anywhere)==
        -t [time] [unit]: changes the duration of the poll (Maximum 1 day)
            Units: second(s), minute(s), hour(s), day(s).
            Default: 1 day
        """
        question = ""
        # default timeout:
        timeout = 1
        timeout_unit = "day"
        skip = 0
        choices = []
        # look for switches
        for arg in range(len(args)):
            if skip > 0:
                skip -= 1
            elif args[arg][0] == '-':
                try:
                    if args[arg][1] == 't':
                        try:
                            timeout = float(args[arg+1])
                            timeout_unit = args[arg+2]
                            if timeout_unit not in TIME_UNITS:
                                raise ValueError
                        except (ValueError, IndexError):
                            await ctx.send(content='Invalid input: Please write a time and a unit of time after -t\n'
                                                   'Available units: `second(s), minute(s), hour(s), day(s)`\n'
                                                   'Examples: `-t 5 minutes` `-t 1 hour`')
                            return
                        skip = 2
                    else:
                        raise ValueError
                except (ValueError, IndexError):
                    await ctx.send(content='Invalid input: Could not recognize switch `{}`\nNote: Any argument '
                                           'beginning with a dash is interpreted to be a switch.'.format(args[arg]))
                    return
            elif question:
                if len(args[arg]) <= 1024:
                    choices.append(args[arg])
                else:
                    await ctx.send(content='Invalid input: Options must be 1024 characters or less')
                    return
            else:
                question = args[arg]

        # Length must be less or equal to 18 because there is a maximum of 20 emojis on a discord message
        # and the arrows for pages take 2 spots
        if len(choices) > 18:
            await ctx.send("Invalid input: Please use 18 options or less")
            return
        username = ctx.message.author.name
        pfp = ctx.message.author.avatar_url
        embed = discord.Embed(
            colour=discord.Colour(0x972b67),
            description="```{}```**To vote, click on one or many emojis**".
                        format(question))  # if single choice is implemented, don't forget to correct this
        embed.set_author(
            name="{} created a poll with {} choices!".format(
                username, len(choices)),
            icon_url=pfp)
        # eventually add this: embed.set_footer(text="5 users voted • Current winner: D (or top n if specified) •
        # Options: Non-anonymous, Multiple choice")

        # Dividing the options into pages. A new page is created when there is more than 7 options OR 550 characters
        # (including the question) on a page. However, a page always contains at least the question and one option
        # even if they use more than 550 characters.
        options_list = [[]]
        page_number = 1
        options_on_page = 0
        char_on_page = len(question)
        for arg in choices:
            if options_on_page == 0 or (char_on_page + len(arg) < 550 and options_on_page < 7):
                options_list[page_number - 1].append(arg)
                options_on_page += 1
                char_on_page += len(arg)
            else:
                page_number += 1
                options_list.append([])
                options_list[page_number - 1].append(arg)
                options_on_page = 1
                char_on_page = len(question) + len(arg)

        embed.set_footer(text="Initializing... Please wait, options will soon appear (Try 1/3)"
                         .format(len(options_list)))
        msg = await ctx.send(embed=embed)

        # add the emojis to the message
        failed = False
        tries = 0
        while msg:
            try:
                pos = 0
                for arg in choices:
                    await msg.add_reaction(EMOJI_ALPHABET[pos])
                    pos += 1
                if len(options_list) > 1:
                    await msg.add_reaction('◀')
                    await msg.add_reaction('▶')
                break
            except discord.errors.Forbidden:
                tries += 1
                if tries == 3:
                    failed = True
                    break
                else:
                    embed.set_footer(text="Was unable to put all reactions on message. Please don't add any emoji "
                                          "until this text disappears. (Try {}/3)".format(tries+1))
                    await msg.edit(embed=embed)
                    await msg.clear_reactions()

        # paginate
        p = Pages(ctx, msg, options_list, embed, timeout, timeout_unit, failed)

        await p.paginate()
        return
        # need to also eventually add options for anonymous voting in DMs
        # restricting to only one choice only and
        # add a duration for polls.


class Pages:
    def __init__(self, ctx, msg, options_list, embed, timeout, timeout_unit, failed=False):
        self.bot = ctx.bot
        self.user = ctx.author
        self.message = msg
        self.options_list = options_list
        self.embed = embed
        self.failed = failed
        self.actions = [
            ('◀', self._prev_page),
            ('▶', self._next_page)
        ]
        self.currentPage = 0
        self.lastPage = len(options_list) - 1
        self.timeout = timeout
        self.timeout_unit = timeout_unit
        self.timeout_end = time.time() + timeout * TIME_UNITS[timeout_unit]
        self.no_pages = False

    async def _print_fully(self):
        pos = 0
        # edit the message with the options
        for pages in range(len(self.options_list)):
            for options in self.options_list[pages]:
                self.embed.add_field(name="Option {}".format(ALPHABET[pos]), value=options)
                pos += 1
        if self.failed:
            self. embed.set_footer(text="Was unable to put all reactions on message and create pages. All 3 tries "
                                        "failed. Next time, please don't add any emoji before the poll has been "
                                        "completely initialized")
        elif self.no_pages:
            self.embed.set_footer()
        else:
            self.embed.set_footer(text="Timeout reached after {} {}. Showing all pages."
                                  .format(self.timeout, self.timeout_unit))
        await self.message.edit(embed=self.embed)
        self.embed.clear_fields()
        return

    async def _show_page(self, page):
        self.currentPage = max(0, min(page, self.lastPage))
        # find the number of the first option of the page
        pos = 0
        for pages in range(len(self.options_list)):
            if pages == self.currentPage:
                break
            pos += len(self.options_list[pages])
        # edit the message with the options
        for options in self.options_list[self.currentPage]:
            self.embed.add_field(name="Option {}".format(ALPHABET[pos]), value=options)
            pos += 1
        self.embed.set_footer(text="Page {} of {} • Will timeout on {}"
                              .format(self.currentPage+1, len(self.options_list),
                                      time.asctime(time.localtime(self.timeout_end))))
        await self.message.edit(embed=self.embed)
        self.embed.clear_fields()
        return

    async def _prev_page(self):
        await self._show_page(max(0, self.currentPage - 1))

    async def _next_page(self):
        await self._show_page(min(self.lastPage, self.currentPage + 1))

    def _react_check(self, reaction, user):
        if user == self.bot.user:
            return False
        if reaction.message.id != self.message.id:
            return False
        for (emoji, action) in self.actions:
            if reaction.emoji != emoji:
                continue
            self.user = user
            self._turn_page = action
            return True
        return False

    async def paginate(self):
        if self.failed:
            await self._print_fully()
            return
        if self.timeout * TIME_UNITS[self.timeout_unit] > 60*60*24:
            await self.message.edit(content="Invalid input: The maximum duration is a day")
            return
        if len(self.options_list) == 1:
            self.no_pages = True
            await self._print_fully()
            return
        await self._show_page(0)
        while self.message and time.time() < self.timeout_end:
            try:
                # wait for a user to put a reaction on a message and
                # call _react_check to check if we must change the page
                reaction, user = await self.bot.wait_for(
                        'reaction_add', check=self._react_check, timeout=(self.timeout * TIME_UNITS[self.timeout_unit]))
            except:
                break
            await self._turn_page()
            try:
                await self.message.remove_reaction(reaction, user)
            except:
                pass
        if self.message:
            await self._print_fully()
            await self.message.remove_reaction('◀', self.bot.user)
            await self.message.remove_reaction('▶', self.bot.user)


def setup(bot):
    bot.add_cog(Poll(bot))
