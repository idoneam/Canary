# Copyright (C) idoneam (2016-2022)
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

import asyncio

import aiosqlite
import discord
import os
import pickle
import random
import re

from discord.ext import commands
from time import time
from functools import partial

from .base_cog import CanaryCog
from .utils.dice_roll import dice_roll
from .utils.clamp_default import clamp_default
from .utils.hangman import HangmanState
from .currency import HANGMAN_REWARD

ROLL_PATTERN = re.compile(r"^(\d*)d(\d*)([+-]?\d*)$")
CATEGORY_SYNONYMS = {
    "movies": "movie",
    "kino": "movie",
    "elements": "element",
    "countries": "country",
    "animals": "animal",
}


class Games(CanaryCog):
    def __init__(self, bot, hangman_tbl_name: str):
        super().__init__(bot)

        self.hm_cool_win: int = bot.config.games["hm_cool_win"]
        self.hm_norm_win: int = bot.config.games["hm_norm_win"]
        self.hm_timeout: int = bot.config.games["hm_timeout"]
        self.hm_locks: dict[discord.TextChannel, asyncio.Lock] = dict()

        with open(f"{os.getcwd()}/data/premade/{hangman_tbl_name}.obj", "rb") as hangman_pkl:
            self.hangman_dict: dict[str, tuple[list[tuple[str, str | None]], str]] = pickle.load(hangman_pkl)

    def help_str(self):
        cat_list: str = ", ".join(
            f"`{hm_cat}` (length: {len(self.hangman_dict[hm_cat][0])})" for hm_cat in sorted(self.hangman_dict.keys())
        )
        return (
            "rules: 5 wrong guesses are allowed, guesses "
            "must be either the entire correct word or a "
            "single letter (interpreted in a case insensitive manner)\n"
            f"here is a list of valid category arguments: {cat_list}.\n"
            "quit an ongoing game by typing `?{hm|hangman} quit`.\n"
            "resend this message by typing `?{hm|hangman} help`."
        )

    @staticmethod
    def hm_msg_check(hm_channel: discord.TextChannel, lowered: str, msg: discord.Message):
        return msg.channel == hm_channel and (
            (len(msg.content) == 1 and msg.content.isalpha()) or msg.content.lower() == lowered
        )

    @commands.command(aliases=["hm"])
    async def hangman(self, ctx, command: str | None = None):
        """
        play a nice game of hangman with internet strangers!
        guesses must be single letters (interpreted in a case-insensitive manner) or the entire correct word.
        can either be called with "?{hm|hangman}" or "?{hm|hangman} x", where x is a valid category argument.
        see all categories by typing "?{hm|hangman} help".
        quit an ongoing game by typing "?{hm|hangman} quit".

        rules:
            - 5 wrong guesses allowed
            - for a guess to be registered, it must either be the full correct word or a single letter
            - guesses are interpreted in a case-insensitive manner
        """

        await ctx.trigger_typing()

        if command == "help":
            await ctx.send(self.help_str())
            return

        if command == "quit":
            if ctx.message.channel in self.hm_locks:
                self.hm_locks[ctx.message.channel].release()
            else:
                await ctx.send("no game is currently being played in this channel")
            return

        category: str = CATEGORY_SYNONYMS.get(command, command) or random.choice(list(self.hangman_dict.keys()))
        try:
            word_list, pretty_name = self.hangman_dict[category]
        except KeyError:
            await ctx.send(f"command `{command}` is not valid\n" + "\n".join(self.help_str().split("\n")[1:]))
            return

        if ctx.message.channel in self.hm_locks:
            await ctx.send("command `hm|hangman` cannot be used to start a new game while one is already going on")
            return

        channel_lock = asyncio.Lock()
        self.hm_locks[ctx.message.channel] = channel_lock
        await channel_lock.acquire()

        game_state = HangmanState("[REDACTED]" if command is None else pretty_name, word_list)
        timeout_dict: dict[discord.Member, float] = {}
        winner: discord.Member | None = None
        cool_win: bool = False

        msg_check = partial(self.hm_msg_check, ctx.message.channel, game_state.lword)

        await ctx.send(embed=game_state.embed)

        while True:

            msg_task = asyncio.create_task(self.bot.wait_for("message", check=msg_check, timeout=self.hm_timeout))
            quit_task = asyncio.create_task(channel_lock.acquire())
            done, _ = await asyncio.wait([msg_task, quit_task], return_when=asyncio.FIRST_COMPLETED)

            if quit_task in done:
                del self.hm_locks[ctx.message.channel]
                msg_task.cancel()
                await ctx.send("current hangman game ended.")
                return

            quit_task.cancel()

            try:
                curr_msg = await msg_task
            except asyncio.exceptions.TimeoutError:
                del self.hm_locks[ctx.message.channel]
                game_state.add_msg("the game has timed out")
                await ctx.send(embed=game_state.embed)
                await ctx.send(
                    f"sorry everyone, no one has interacted with the "
                    f"hangman in {round(self.hm_timeout/60, 2)} minutes, "
                    f"the game has timed out"
                )
                return

            curr_guess = curr_msg.content.lower()

            if curr_msg.author in timeout_dict and (time() - timeout_dict[curr_msg.author]) < 1.5:
                game_state.add_msg(f"{curr_msg.author} you cannot guess right now!")
                await ctx.send(embed=game_state.embed)
                continue

            if curr_guess == game_state.lword:
                winner = curr_msg.author
                cool_win = game_state.full()
                if command is None:
                    game_state.field_name = f"hangman (category: {pretty_name})"
                game_state.add_msg(f"{winner} guessed the entire word!")
                if game_state.img:
                    game_state.embed.set_image(url=game_state.img)
                await ctx.send(embed=game_state.embed)
                await ctx.send(
                    f"congratulations `{winner}`, you solved the hangman"
                    + (
                        f" (in a cool way), earning you {self.hm_cool_win} cheeps"
                        if cool_win
                        else f", earning you {self.hm_norm_win} cheeps"
                    )
                )
                break

            if curr_guess in game_state.previous_guesses:
                timeout_dict[curr_msg.author] = time()
                game_state.add_msg(f"{curr_msg.author}, '{curr_guess}' was already guessed")
                await ctx.send(embed=game_state.embed)
            elif curr_guess in game_state.not_guessed:
                continue_game = game_state.correct(curr_guess)
                game_state.add_msg(f"{curr_msg.author} guessed '{curr_guess}' correctly!")
                await ctx.send(embed=game_state.embed)
                if not continue_game:
                    winner = curr_msg.author
                    if command is None:
                        game_state.field_name = f"hangman (category: {pretty_name})"
                    game_state.add_msg(f"{winner} finished solving the hangman!")
                    if game_state.img:
                        game_state.embed.set_image(url=game_state.img)
                    await ctx.send(embed=game_state.embed)
                    await ctx.send(
                        f"congratulations `{winner}`, you solved the hangman, earning you {self.hm_norm_win} cheeps"
                    )
                    break
            else:
                timeout_dict[curr_msg.author] = time()
                continue_game = game_state.mistake(curr_guess)
                game_state.add_msg(f"{curr_msg.author} guessed '{curr_guess}' wrong!")
                await ctx.send(embed=game_state.embed)
                if not continue_game:
                    if command is None:
                        game_state.field_name = f"hangman (category: {pretty_name})"
                    game_state.add_msg(f"{curr_msg.author} used your last chance!")
                    if game_state.img:
                        game_state.embed.set_image(url=game_state.img)
                    await ctx.send(embed=game_state.embed)
                    await ctx.send(
                        f"sorry everyone, `{curr_msg.author}` used your "
                        f"last chance, the right answer was `{game_state.word}`"
                    )
                    break

        del self.hm_locks[ctx.message.channel]

        if winner is not None:
            db: aiosqlite.Connection
            async with self.db() as db:
                await self.bot.get_cog("Currency").create_bank_transaction(
                    db,
                    winner,
                    self.hm_cool_win if cool_win else self.hm_norm_win,
                    HANGMAN_REWARD,
                    {"cool": cool_win},
                )
                await db.commit()

    @commands.command()
    async def roll(self, ctx, arg: str = "", mpr: str = ""):
        """
        Perform a DnD-style diceroll
        [r]d[s][+m] ['each']    Rolls an [s]-sided die [r] times, with modifier
                                [+-m]. If 'each' is specified, applies modifier
                                to each roll rather than the sum of all rolls.
                                All parameters are optional.
                                Defaults to rolling one 20-sided die.

                                Dice can have 1 to 100 sides
                                Rolls 1 to 10000 dice at once
                                Modifier can be any int between -100 and +100
          Examples:
           roll             rolls a d20
           roll d6          rolls one 6-sided die
           roll 3d          rolls 3 20-sided dice
           roll 5d12-4      rolls 5 12-sided dice, subtracting 4 from the total
           roll 5d+3 each   rolls 5 20-sided dice, adding 3 to each roll
        """
        roll_cmd = ROLL_PATTERN.match(arg)
        if arg == "safe":  # nice meme bro
            await ctx.send("https://media.giphy.com/media/" "d3mlE7uhX8KFgEmY/giphy.gif")
            return
        # Applying some bounds on parameters
        if roll_cmd is not None:
            repeat = clamp_default(roll_cmd.group(1), 1, 10000, 1)
            sides = clamp_default(roll_cmd.group(2), 1, 100, 20)
            mod = clamp_default(roll_cmd.group(3), -100, 100, 0)
        else:  # Necessary for empty roll commands - regex won't even match
            repeat = 1
            sides = 20
            mod = 0

        if mpr == "each":
            roll_list, total, maximum, minimum = dice_roll(sides, repeat, mod, mpr=True)
            mod_desc = " to each roll"
        else:
            roll_list, total, maximum, minimum = dice_roll(sides, repeat, mod)
            mod_desc = " to the sum of rolls"
        # Now that we have our rolls, prep the embed:
        resultsmsg = discord.Embed(
            description="Rolling {} {}-sided dice" ", with a {} modifier{}".format(repeat, sides, mod, mod_desc),
            colour=0x822AE0,
        )
        if repeat <= 10:  # Anything more and the roll list is too long
            resultsmsg.add_field(name="Rolls", value=str(roll_list)[1:-1], inline=False)
        # Want the modified sum to be shown even for single rolls:
        if repeat > 1 or mod != 0:
            resultsmsg.add_field(name="Sum", value=total)
            if repeat > 1:
                resultsmsg.add_field(name="Minimum", value=minimum)
                resultsmsg.add_field(name="Maximum", value=maximum)
        await ctx.send(embed=resultsmsg)


def setup(bot):
    bot.add_cog(Games(bot, "hangman_dict"))
