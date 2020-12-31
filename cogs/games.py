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

# discord-py requirements
import discord
from discord.ext import commands

# Other utilities
import re
import os
from time import time
import pickle
import random
from asyncio import TimeoutError
from typing import Dict, List, Set, Tuple
from .utils.dice_roll import dice_roll
from .utils.clamp_default import clamp_default
from .utils.hangman import LOSS_MISTAKES, mk_hangman_str
from .currency import HANGMAN_REWARD

ROLL_PATTERN = re.compile(r'^(\d*)d(\d*)([+-]?\d*)$')
HM_WIN_CHEEPS = 10
HM_COOL_WIN_CHEEPS = 20
TIMEOUT_TIME = 600


class Games(commands.Cog):
    def __init__(self, bot, hangman_tbl_name: str):
        self.bot = bot
        with open(f"{os.getcwd()}/pickles/premade/{hangman_tbl_name}.obj",
                  "rb") as hangman_pkl:
            self.hangman_dict: Dict[str, Tuple[str,
                                               str]] = pickle.load(hangman_pkl)

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.command(aliases=["hm"])
    async def hangman(self, ctx, *, command: str = None):
        """
        Play a nice game of hangman with internet strangers!
        Guesses must be single letters (interpreted in a case insensitive manner) or the entire correct word
        Can either be called with "?{hm|hangman}" or "?{hm|hangman} x", where x is a valid category command
        Get all categories/help by typing "?{hm|hangman} help"
        """
        await ctx.trigger_typing()

        if command == "help":
            cat_list: str = ', '.join(
                '`' + hm_cat + '` (length: ' +
                str(len(self.hangman_dict[hm_cat][0])) + ')'
                for hm_cat in sorted(self.hangman_dict.keys()))
            await ctx.send(
                f"rules: {LOSS_MISTAKES - 1} wrong guesses are allowed, "
                f"guesses must be either the entire correct word or a "
                f"single letter (interpreted in a case insensitive manner)\n"
                f"here is a list of valid category commands: {cat_list}")
            return
        category: str = command or random.choice(list(
            self.hangman_dict.keys()))
        try:
            word_list, pretty_name = self.hangman_dict[category]
        except KeyError:
            await ctx.send(f"invalid category command, "
                           f"here is a list of valid commands: "
                           f"{sorted(self.hangman_dict.keys())}")
            return

        hm_word, hm_img = random.choice(word_list)
        lowered_word = hm_word.lower()

        num_mistakes: int = 0
        not_guessed: Set[str] = set(re.sub(r"[^a-z]", "", lowered_word))
        incorrect_guesses: Set[str] = set()
        first_line: str = " ".join(
            char if lowered_char not in not_guessed else "_"
            for char, lowered_char in zip(hm_word, lowered_word))
        last_line: str = "incorrect guesses: "
        player_msg_list: List[str] = []
        timeout_dict: Dict[discord.Member, float] = {}
        winner: discord.Member = None
        cool_win: bool = False

        def append_and_slice(new_msg):
            nonlocal player_msg_list
            player_msg_list.append(new_msg)
            player_msg_list = player_msg_list[-3:]

        def wait_for_check(msg) -> bool:
            return msg.channel == ctx.message.channel and (
                (len(msg.content) == 1 and msg.content.isalpha())
                or msg.content.lower() == lowered_word)

        hm_embed = discord.Embed(colour=0xFF0000)
        hm_embed.add_field(
            name=f"hangman (category: {pretty_name})",
            value=mk_hangman_str(
                first_line, num_mistakes,
                "\n".join(player_msg_list))).set_footer(text=last_line)
        await ctx.send(embed=hm_embed)

        while True:

            try:
                curr_msg = await self.bot.wait_for('message',
                                                   check=wait_for_check,
                                                   timeout=TIMEOUT_TIME)
            except TimeoutError:
                player_msg_list.append("the game has timed out")
                player_msg_list = player_msg_list[-3:]
                hm_embed.set_field_at(
                    0,
                    name=f"hangman (category: {pretty_name})",
                    value=mk_hangman_str(first_line, num_mistakes,
                                         "\n".join(player_msg_list)))
                await ctx.send(embed=hm_embed)
                await ctx.send(
                    f"sorry everyone, no one has interacted with the "
                    f"hangman in {TIMEOUT_TIME//60} minutes, "
                    f"the game has timed out")
                return

            curr_guess = curr_msg.content.lower()
            if not (curr_msg.author in timeout_dict and
                    (time() - timeout_dict[curr_msg.author]) < 3.0
                    ):    # check that user isn't time'd out
                if curr_guess == lowered_word:
                    winner = curr_msg.author
                    cool_win = len(not_guessed) > (len(set(lowered_word)) //
                                                   2.5)
                    first_line = " ".join(hm_word)
                    append_and_slice(f"{winner} guessed the entire word!")
                    hm_embed.set_field_at(
                        0,
                        name=f"hangman (category: {pretty_name})",
                        value=mk_hangman_str(first_line, num_mistakes,
                                             "\n".join(player_msg_list)))
                    if hm_img is not None:
                        hm_embed.set_image(url=hm_img)
                    await ctx.send(embed=hm_embed)
                    await ctx.send(
                        f"congratulations {winner}, you solved the hangman"
                        f"{', but in a cool way' if  cool_win else ''}, "
                        f"earning you "
                        f"{HM_COOL_WIN_CHEEPS if cool_win else HM_WIN_CHEEPS}"
                        f" cheeps")
                    break
                if curr_guess in not_guessed:
                    # curr_guess in not_guessed
                    # => curr_guess is correct and new
                    not_guessed.remove(curr_guess)
                    first_line = " ".join(
                        char if lowered_char not in not_guessed else "_"
                        for char, lowered_char in zip(hm_word, lowered_word))
                    append_and_slice(
                        f"{curr_msg.author} guessed '{curr_guess}' correctly!")
                    hm_embed.set_field_at(
                        0,
                        name=f"hangman (category: {pretty_name})",
                        value=mk_hangman_str(first_line, num_mistakes,
                                             "\n".join(player_msg_list)))
                    await ctx.send(embed=hm_embed)
                    if len(not_guessed) == 0:
                        winner = curr_msg.author
                        player_msg_list.append(
                            f"{winner} finished solving the hangman!")
                        player_msg_list = player_msg_list[-3:]
                        hm_embed.set_field_at(
                            0,
                            name=f"hangman (category: {pretty_name})",
                            value=mk_hangman_str(first_line, num_mistakes,
                                                 "\n".join(player_msg_list)))
                        if hm_img is not None:
                            hm_embed.set_image(url=hm_img)
                        await ctx.send(embed=hm_embed)
                        await ctx.send(
                            f"congratulations {winner}, you solved the hangman, "
                            f"earning you {HM_WIN_CHEEPS} cheeps")
                        break
                elif curr_guess in lowered_word:
                    # curr_guess not in not_guessed (elif) and in word
                    # => curr_guess is correct but already made
                    append_and_slice(
                        f"{curr_msg.author}, '{curr_guess}' was already guessed"
                    )
                    hm_embed.set_field_at(
                        0,
                        name=f"hangman (category: {pretty_name})",
                        value=mk_hangman_str(first_line, num_mistakes,
                                             "\n".join(player_msg_list)))
                    await ctx.send(embed=hm_embed)
                elif curr_guess not in incorrect_guesses:
                    # curr_guess not in not_guessed
                    # and not in word (elif) and
                    # not in incorrect guesses
                    # => curr_guess is incorrect and new
                    num_mistakes += 1
                    incorrect_guesses.add(curr_guess)
                    last_line = f"incorrect guesses: {str(sorted(incorrect_guesses))[1:-1]}"
                    append_and_slice(
                        f"{curr_msg.author} guessed '{curr_guess}' wrong!")
                    timeout_dict[curr_msg.author] = time()
                    hm_embed.set_field_at(
                        0,
                        name=f"hangman (category: {pretty_name})",
                        value=mk_hangman_str(
                            first_line, num_mistakes,
                            "\n".join(player_msg_list))).set_footer(
                                text=last_line)
                    await ctx.send(embed=hm_embed)
                    if num_mistakes == LOSS_MISTAKES:
                        append_and_slice(
                            f"{curr_msg.author} used your last chance!")
                        hm_embed.set_field_at(
                            0,
                            name=f"hangman (category: {pretty_name})",
                            value=mk_hangman_str(first_line, num_mistakes,
                                                 "\n".join(player_msg_list)))
                        await ctx.send(embed=hm_embed)
                        await ctx.send(
                            f"sorry everyone, {curr_msg.author} used your "
                            f"last chance, the right answer was `{hm_word}`")
                        break
                else:
                    # curr_guess not in not_guessed and
                    # not in word and in incorrect_guesses (else)
                    # => curr_guess is incorrect but already made
                    timeout_dict[curr_msg.author] = time()
                    append_and_slice(
                        f"{curr_msg.author}, '{curr_guess}' was already guessed"
                    )
                    hm_embed.set_field_at(
                        0,
                        name=f"hangman (category: {pretty_name})",
                        value=mk_hangman_str(first_line, num_mistakes,
                                             "\n".join(player_msg_list)))
                    await ctx.send(embed=hm_embed)
            else:
                # message from a user in time out
                append_and_slice(
                    f"{curr_msg.author} you cannot guess right now!")
                hm_embed.set_field_at(
                    0,
                    name=f"hangman (category: {pretty_name})",
                    value=mk_hangman_str(first_line, num_mistakes,
                                         "\n".join(player_msg_list)))
                await ctx.send(embed=hm_embed)
        if winner is not None:
            currency_cog = self.bot.get_cog('Currency')
            if cool_win:
                await currency_cog.give_user_cheeps(ctx, HM_COOL_WIN_CHEEPS,
                                                    HANGMAN_REWARD,
                                                    {"cool": cool_win})
            else:
                await currency_cog.give_user_cheeps(ctx, HM_WIN_CHEEPS,
                                                    HANGMAN_REWARD,
                                                    {"cool": cool_win})

    @commands.command()
    async def roll(self, ctx, arg: str = '', mpr: str = ''):
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
        if arg == 'safe':    # nice meme bro
            await ctx.send('https://media.giphy.com/media/'
                           'd3mlE7uhX8KFgEmY/giphy.gif')
            return
        # Applying some bounds on parameters
        if roll_cmd is not None:
            repeat = clamp_default(roll_cmd.group(1), 1, 10000, 1)
            sides = clamp_default(roll_cmd.group(2), 1, 100, 20)
            mod = clamp_default(roll_cmd.group(3), -100, 100, 0)
        else:    # Necessary for empty roll commands - regex won't even match
            repeat = 1
            sides = 20
            mod = 0

        if mpr == 'each':
            roll_list, total, maximum, minimum = dice_roll(sides,
                                                           repeat,
                                                           mod,
                                                           mpr=True)
            mod_desc = ' to each roll'
        else:
            roll_list, total, maximum, minimum = dice_roll(sides, repeat, mod)
            mod_desc = ' to the sum of rolls'
        # Now that we have our rolls, prep the embed:
        resultsmsg = discord.Embed(description='Rolling {} {}-sided dice'
                                   ', with a {} modifier{}'.format(
                                       repeat, sides, mod, mod_desc),
                                   colour=0x822AE0)
        if repeat <= 10:    # Anything more and the roll list is too long
            resultsmsg.add_field(name='Rolls',
                                 value=str(roll_list)[1:-1],
                                 inline=False)
        # Want the modified sum to be shown even for single rolls:
        if repeat > 1 or mod != 0:
            resultsmsg.add_field(name='Sum', value=total)
            if repeat > 1:
                resultsmsg.add_field(name='Minimum', value=minimum)
                resultsmsg.add_field(name='Maximum', value=maximum)
        await ctx.send(embed=resultsmsg)


def setup(bot):
    bot.add_cog(Games(bot, "hangman_dict"))
