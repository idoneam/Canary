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
from .utils.hangman import HANG_LIST, MAX_GUESSES

ROLL_PATTERN = re.compile(r'^(\d*)d(\d*)([+-]?\d*)$')
HM_WIN_CHEEPS = 1024
HM_COOL_WIN_CHEEPS = 2048
DEFAULT_IMG_LINK = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Wikimedia_error_404.png/1920px-Wikimedia_error_404.png"

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
        Guesses must be single letters (guesses must be lower case letters to be valid) or the entire correct word
        Can either be called with "?{hm|hangman}" or "?{hm|hangman} x", where x is a valid category command
        Get all categories/help by typing "?{hm|hangman} help"
        """
        await ctx.trigger_typing()

        if command == "help":
            await ctx.send(
                f"rules: 6 wrong guesses are allowed, guesses must be either the entire correct word or a single lowercase letter\nhere is a list of valid category commands: {sorted(self.hangman_dict.keys())}"
            )
            return
        category: str = command or random.choice(list(
            self.hangman_dict.keys()))
        try:
            word_list, pretty_name = self.hangman_dict[category]
            hm_word, hm_img = random.choice(word_list)
        except KeyError:
            await ctx.send(
                f"invalid category command, here is a list of valid commands: {sorted(self.hangman_dict.keys())}"
            )
            return

        newline = "\n"
        hang_list = HANG_LIST
        max_guesses = MAX_GUESSES
        num_mistakes: int = 0
        not_guessed: Set[str] = set(re.sub(r"[^a-z]", "", hm_word))
        incorrect_guesses: Set[str] = set()
        first_line: str = " ".join(char if char not in not_guessed else "_"
                                   for char in hm_word)
        last_line: str = "incorrect guesses: "
        player_msg_list: List[str] = []
        invalid_msg_count: int = 0
        timeout_dict = {}
        curr_msg_valid = True
        winner = None
        cool_win: bool = False
        counter: int = 0

        def wait_for_check(msg) -> bool:
            if msg.channel != ctx.message.channel:
                return False
            nonlocal curr_msg_valid
            curr_msg_valid = (
                len(msg.content) == 1 and msg.content
                in "abcdefghikklmnopqrstuvwxyzABCDEFGHIJKLMNOPRSTUVWXYZ"
            ) or msg.content.lower() == hm_word
            if not curr_msg_valid:
                nonlocal invalid_msg_count
                invalid_msg_count += 1
            return curr_msg_valid or invalid_msg_count >= 3

        hm_embed = discord.Embed(colour=0xFF0000)
        hm_embed.add_field(
            name=f"hangman (category: {pretty_name})",
            value=
            f"`{first_line}`\n```{hang_list[num_mistakes]}```\n{newline.join(player_msg_list)}"
        )
        hm_embed.set_footer(text=last_line)
        hm_msg = await ctx.send(embed=hm_embed)

        while True:
            if counter > 7:    # so that users who see deleted messages still see the hangman
                await hm_msg.delete()
                hm_msg = await ctx.send(embed=hm_msg.embeds[0])
                counter = 0

            try:
                curr_msg = await self.bot.wait_for('message',
                                                   check=wait_for_check,
                                                   timeout=600)
            except TimeoutError:
                player_msg_list.append("the game has timed out")
                player_msg_list = player_msg_list[-3:]
                hm_embed.set_field_at(
                    0,
                    name=f"hangman (category: {pretty_name})",
                    value=
                    f"`{first_line}`\n```{hang_list[num_mistakes]}```\n{newline.join(player_msg_list)}"
                )
                await hm_msg.edit(embed=hm_embed)
                await ctx.send(
                    f"sorry everyone, no one has interacted with the hangman in 10 minutes, the game has timed out"
                )
                return

            curr_guess = curr_msg.content.lower()
            if not (curr_msg.author in timeout_dict and
                    (time() - timeout_dict[curr_msg.author]) < 3.0):
                if curr_guess == hm_word:
                    winner = curr_msg.author
                    cool_win = True
                    first_line = " ".join(char for char in hm_word)
                    player_msg_list.append(
                        f"{winner} guessed the entire word!")
                    player_msg_list = player_msg_list[-3:]
                    hm_embed.set_field_at(
                        0,
                        name=f"hangman (category: {pretty_name})",
                        value=
                        f"`{first_line}`\n```{hang_list[num_mistakes]}```\n{newline.join(player_msg_list)}"
                    )
                    hm_embed.set_image(url=hm_img if hm_img else DEFAULT_IMG_LINK)
                    await hm_msg.edit(embed=hm_embed)
                    await ctx.send(
                        f"congratulations {winner}, you solved the hangman{', but in a cool way' if len(not_guessed) > (len(set(hm_word)) // 2.5)  else ''}"
                    )
                    break
                if curr_msg_valid:
                    await curr_msg.delete()
                    if curr_guess in not_guessed:    # curr_guess in not_guessed => curr_guess is correct and new
                        not_guessed.remove(curr_guess)
                        first_line = " ".join(
                            char if char not in not_guessed else "_"
                            for char in hm_word)
                        player_msg_list.append(
                            f"{curr_msg.author} guessed '{curr_guess}' correctly!"
                        )
                        player_msg_list = player_msg_list[-3:]
                        hm_embed.set_field_at(
                            0,
                            name=f"hangman (category: {pretty_name})",
                            value=
                            f"`{first_line}`\n```{hang_list[num_mistakes]}```\n{newline.join(player_msg_list)}"
                        )
                        await hm_msg.edit(embed=hm_embed)
                        if len(not_guessed) == 0:
                            winner = curr_msg.author
                            player_msg_list.append(
                                f"{winner} finished solving the hangman!")
                            player_msg_list = player_msg_list[-3:]
                            hm_embed.set_field_at(
                                0,
                                name=f"hangman (category: {pretty_name})",
                                value=
                                f"`{first_line}`\n```{hang_list[num_mistakes]}```\n{newline.join(player_msg_list)}"
                            )
                            hm_embed.set_image(url=hm_img if hm_img else DEFAULT_IMG_LINK)
                            await hm_msg.edit(embed=hm_embed)
                            await ctx.send(
                                f"congratulations {winner}, you solved the hangman"
                            )
                            break
                    elif curr_guess in hm_word:    # curr_guess not in not_guessed (elif) and in word => curr_guess is correct but already made
                        player_msg_list.append(
                            f"{curr_msg.author}, '{curr_guess}' was already guessed"
                        )
                        player_msg_list = player_msg_list[-3:]
                        hm_embed.set_field_at(
                            0,
                            name=f"hangman (category: {pretty_name})",
                            value=
                            f"`{first_line}`\n```{hang_list[num_mistakes]}```\n{newline.join(player_msg_list)}"
                        )
                        await hm_msg.edit(embed=hm_embed)
                    elif curr_guess not in incorrect_guesses:    # curr_guess not in not_guessed and not in word (elif) and not in incorrect guesses => curr_guess is incorrect and new
                        num_mistakes += 1
                        incorrect_guesses.add(curr_guess)
                        last_line = f"incorrect guesses: {str(sorted(incorrect_guesses))[1:-1]}"
                        player_msg_list.append(
                            f"{curr_msg.author} guessed '{curr_guess}' wrong!")
                        player_msg_list = player_msg_list[-3:]
                        timeout_dict[curr_msg.author] = time()
                        hm_embed.set_field_at(
                            0,
                            name=f"hangman (category: {pretty_name})",
                            value=
                            f"`{first_line}`\n```{hang_list[num_mistakes]}```\n{newline.join(player_msg_list)}"
                        )
                        hm_embed.set_footer(text=last_line)
                        await hm_msg.edit(embed=hm_embed)
                        if num_mistakes == max_guesses:
                            player_msg_list.append(
                                f"{curr_msg.author} used your last chance!")
                            player_msg_list = player_msg_list[-3:]
                            hm_embed.set_field_at(
                                0,
                                name=f"hangman (category: {pretty_name})",
                                value=
                                f"`{first_line}`\n```{hang_list[num_mistakes]}```\n{newline.join(player_msg_list)}"
                            )
                            await hm_msg.edit(embed=hm_embed)
                            await ctx.send(
                                f"sorry everyone, {curr_msg.author} used your last chance, the right answer was `{hm_word}`"
                            )
                            break
                    else:    # curr_guess not in not_guessed and not in word and in incorrect_guesses (else) => curr_guess is incorrect but already made
                        timeout_dict[curr_msg.author] = time()
                        player_msg_list.append(
                            f"{curr_msg.author}, '{curr_guess}' was already guessed"
                        )
                        player_msg_list = player_msg_list[-3:]
                        hm_embed.set_field_at(
                            0,
                            name=f"hangman (category: {pretty_name})",
                            value=
                            f"`{first_line}`\n```{hang_list[num_mistakes]}```\n{newline.join(player_msg_list)}"
                        )
                        await hm_msg.edit(embed=hm_embed)
                else:
                    invalid_msg_count = 0
                    await hm_msg.delete()
                    hm_msg = await ctx.send(embed=hm_msg.embeds[0])
            elif curr_msg_valid:
                await curr_msg.delete()
                player_msg_list.append(
                    f"{curr_msg.author} you cannot guess right now!")
                player_msg_list = player_msg_list[-3:]
                hm_embed.set_field_at(
                    0,
                    name=f"hangman (category: {pretty_name})",
                    value=
                    f"`{first_line}`\n```{hang_list[num_mistakes]}```\n{newline.join(player_msg_list)}"
                )
                await hm_msg.edit(embed=hm_embed)
            counter += 1
        if winner is not None:    # placeholder for when currency function is completed
            if cool_win:
                pass
            else:
                pass

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
