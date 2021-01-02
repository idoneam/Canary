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

# discord-py requirements
import discord
from discord.ext import commands
import asyncio

# Other utilities
import random
import sqlite3
from .utils.paginator import Pages
import time
from .utils.p_strings import PStringEncodings

EMOJI = {
    "new": "🆕",
    "mag": "🔍",
    "pencil": "📝",
    "stop_button": "⏹",
    "ok": "🆗",
    "white_check_mark": "✅",
    "x": "❌",
    "put_litter_in_its_place": "🚮",
    "rewind": "⏪",
    "arrow_backward": "◀",
    "arrow_forward": "▶",
    "fast_forward": "⏩",
    "grey_question": "❔",
    "zero": "0️⃣",
    "one": "1️⃣",
    "two": "2️⃣",
    "three": "3️⃣",
    "four": "4️⃣",
    "five": "5️⃣",
}

NUMBERS = (EMOJI['zero'], EMOJI['one'], EMOJI['two'], EMOJI['three'],
           EMOJI['four'], EMOJI['five'])

CUSTOM_REACTION_TIMEOUT = ("Custom Reaction timed out. "
                           "You may want to run the command again.")
STOP_TEXT = "stop"
LOADING_EMBED = discord.Embed(title="Loading...")


class CustomReactions(commands.Cog):
    # Written by @le-potate
    def __init__(self, bot):
        self.bot = bot
        self.reaction_list = []
        self.proposal_list = []
        self.p_strings = None
        self.rebuild_lists()

    def rebuild_lists(self):
        self.rebuild_reaction_list()
        self.rebuild_proposal_list()

    def rebuild_reaction_list(self):
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM CustomReactions WHERE Proposal = 0')
        self.reaction_list = c.fetchall()
        prompts = [row[1].lower() for row in self.reaction_list]
        responses = [row[2].lower() for row in self.reaction_list]
        anywhere_values = [row[5] for row in self.reaction_list]
        additional_info_list = [(row[4], row[6]) for row in self.reaction_list]
        self.p_strings = PStringEncodings(
            prompts,
            responses,
            anywhere_values,
            additional_info_list=additional_info_list)
        conn.close()

    def rebuild_proposal_list(self):
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM CustomReactions WHERE Proposal = 1')
        self.proposal_list = c.fetchall()
        conn.close()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        response = self.p_strings.parser(message.content,
                                         user=message.author.mention,
                                         channel=str(message.channel))
        if response:
            # delete the prompt if DeletePrompt option is activated
            if response.additional_info[0] == 1:
                await message.delete()

            # send the response if DM option selected,
            # send in the DM of the user who wrote the prompt
            if response.additional_info[1] == 1:
                await message.author.send(str(response))
            else:
                await message.channel.send(str(response))

    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    @commands.command(
        aliases=['customreaction', 'customreacts', 'customreact'])
    async def customreactions(self, ctx):
        current_options = []
        main_user = ctx.message.author
        await ctx.message.delete()

        def get_number_of_proposals():
            return len(self.proposal_list)

        def get_reaction_check(moderators=False, reaction_user=None):
            def reaction_check(reaction, user):
                return all(
                    (reaction.emoji in current_options,
                     reaction.message.id == initial_message.id, not moderators
                     or discord.utils.get(user.roles,
                                          name=self.bot.config.moderator_role),
                     not reaction_user or user == reaction_user))

            return reaction_check

        def get_msg_check(msg_user=None):
            def msg_check(msg):
                if all(
                    (not msg_user
                     or msg.author == msg_user, msg.channel == ctx.channel)):
                    if msg.attachments:
                        # in python 3.7, rewrite as
                        # asyncio.create_task(ctx.send([...]))
                        # (the get_event_loop() part isn't necessary)
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            ctx.send("Attachments cannot be used, "
                                     "but you may use URLs"))
                    else:
                        return True

            return msg_check

        def get_number_check(msg_user=None, number_range=None):
            def number_check(msg):
                if msg.content.isdigit():
                    return all((not msg_user
                                or msg.author == msg_user, not number_range
                                or int(msg.content) in number_range,
                                msg.channel == ctx.channel))

            return number_check

        async def wait_for_reaction(message):
            try:
                reaction, user = await self.bot.wait_for(
                    'reaction_add',
                    check=get_reaction_check(reaction_user=main_user),
                    timeout=60)
            except asyncio.TimeoutError:
                await message.clear_reactions()
                await message.edit(
                    embed=discord.Embed(title=CUSTOM_REACTION_TIMEOUT),
                    delete_after=60)
                return
            return reaction, user

        async def wait_for_message(message):
            try:
                msg = await self.bot.wait_for(
                    'message',
                    check=get_msg_check(msg_user=main_user),
                    timeout=60)
            except asyncio.TimeoutError:
                await message.clear_reactions()
                await message.edit(
                    embed=discord.Embed(title=CUSTOM_REACTION_TIMEOUT),
                    delete_after=60)
                return
            content = msg.content
            await msg.delete()
            return content

        async def add_multiple_reactions(message, reactions):
            for reaction in reactions:
                await message.add_reaction(reaction)

        async def add_yes_or_no_reactions(message):
            await add_multiple_reactions(
                message, (EMOJI['zero'], EMOJI['one'], EMOJI['stop_button']))

        async def add_control_reactions(message):
            await add_multiple_reactions(
                message, (EMOJI['rewind'], EMOJI['arrow_backward'],
                          EMOJI['arrow_forward'], EMOJI['fast_forward'],
                          EMOJI['stop_button'], EMOJI['ok']))

        async def create_assistant(message, is_moderator):
            if is_moderator:
                description = (
                    f"{EMOJI['new']} Add a new custom reaction\n"
                    f"{EMOJI['mag']} See the list of current reactions "
                    f"and modify them\n"
                    f"{EMOJI['pencil']} See the list of proposed reactions "
                    f"({get_number_of_proposals()}) "
                    f"and approve or reject them\n"
                    f"{EMOJI['grey_question']} List of placeholders")
            else:
                description = (
                    f"{EMOJI['new']} Propose a new custom reaction\n"
                    f"{EMOJI['mag']} See the list of current reactions\n"
                    f"{EMOJI['pencil']} See the list of proposed reactions "
                    f"({get_number_of_proposals()})\n"
                    f"{EMOJI['grey_question']} List of placeholders")
            current_options.extend(
                (EMOJI['new'], EMOJI['mag'], EMOJI['pencil'],
                 EMOJI['grey_question'], EMOJI['stop_button']))
            await add_multiple_reactions(
                message, (EMOJI['new'], EMOJI['mag'], EMOJI['pencil'],
                          EMOJI['grey_question'], EMOJI['stop_button']))
            await message.edit(embed=discord.Embed(
                title="Custom Reactions", description=description).set_footer(
                    text=f"{main_user}: Click on an emoji to choose an "
                    f"option (If a list is chosen, all users "
                    f"will be able to interact with it)",
                    icon_url=main_user.avatar_url))
            try:
                reaction, user = await wait_for_reaction(message)
            except TypeError:
                return
            current_options.clear()
            await message.clear_reactions()
            # Add/Propose a new custom reaction
            if reaction.emoji == EMOJI['new']:
                await add_custom_react(message, is_moderator)
                return
            # List custom reactions
            if reaction.emoji == EMOJI['mag']:
                await list_custom_reacts(message, proposals=False)
                return
            # List proposals
            if reaction.emoji == EMOJI['pencil']:
                await list_custom_reacts(message, proposals=True)
                return
            # List placeholders
            if reaction.emoji == EMOJI['grey_question']:
                await list_placeholders(message)
                return
            # Stop
            if reaction.emoji == EMOJI['stop_button']:
                await leave(message)
                return True

        async def add_custom_react(message, is_moderator):
            if is_moderator:
                title = "Add a custom reaction"
                footer = (
                    f"{main_user} is currently adding a custom reaction. \n"
                    f"Write '{STOP_TEXT}' to cancel.")
            else:
                title = "Propose a custom reaction"
                footer = (f"{main_user} is currently proposing a custom "
                          f"reaction. \n"
                          f"Write '{STOP_TEXT}' to cancel.")
            description = "Write the prompt the bot will react to"
            await message.edit(
                embed=discord.Embed(title=title, description=description).
                set_footer(text=footer, icon_url=main_user.avatar_url))
            prompt_message = await wait_for_message(message)
            if prompt_message is None:
                return
            if prompt_message.lower() == STOP_TEXT:
                await leave(message)
                return True
            description = (f"Prompt: {prompt_message}\nWrite the response "
                           f"the bot will send")
            await message.edit(
                embed=discord.Embed(title=title, description=description).
                set_footer(text=footer, icon_url=main_user.avatar_url))
            response = await wait_for_message(message)
            if response is None:
                return
            if response.lower() == STOP_TEXT:
                await leave(message)
                return True
            await message.edit(embed=LOADING_EMBED)
            description = (f"Prompt: {prompt_message}\nResponse: {response}\n"
                           f"React with the options "
                           f"you want and click {EMOJI['ok']} "
                           f"when you are ready\n"
                           f"{EMOJI['one']} Delete the message "
                           f"that calls the reaction\n"
                           f"{EMOJI['two']} Activate the custom "
                           f"reaction if the prompt is "
                           f"anywhere in a message \n"
                           f"{EMOJI['three']} React in the DMs of "
                           f"the user who calls the "
                           f"reaction instead of the channel\n")
            if is_moderator:
                footer = f"{main_user} is currently adding a custom reaction."
            else:
                footer = (f"{main_user} is currently "
                          f"proposing a custom reaction.")
            current_options.extend((EMOJI['ok'], EMOJI['stop_button']))
            await add_multiple_reactions(
                message, (*NUMBERS[1:4], EMOJI['ok'], EMOJI['stop_button']))
            await message.edit(
                embed=discord.Embed(title=title, description=description).
                set_footer(text=footer, icon_url=main_user.avatar_url))
            try:
                reaction, user = await wait_for_reaction(message)
            except TypeError:
                return

            # If the user clicked OK, check if delete/anywhere/dm are checked
            if reaction.emoji == EMOJI['ok']:
                delete = False
                anywhere = False
                dm = False
                cache_msg = await message.channel.fetch_message(message.id)
                for reaction in cache_msg.reactions:
                    users_who_reacted = await reaction.users().flatten()
                    if main_user in users_who_reacted:
                        delete = delete or reaction.emoji == EMOJI['one']
                        anywhere = anywhere or reaction.emoji == EMOJI['two']
                        dm = dm or reaction.emoji == EMOJI['three']

                current_options.clear()
                await message.clear_reactions()
                conn = sqlite3.connect(self.bot.config.db_path)
                c = conn.cursor()
                t = (prompt_message, response, main_user.id, delete, anywhere,
                     dm, not is_moderator)
                c.execute(
                    'INSERT INTO CustomReactions(Prompt, Response, UserID, '
                    'DeletePrompt, Anywhere, DM, Proposal) '
                    'VALUES(?,?,?,?,?,?,?)', t)
                conn.commit()
                conn.close()
                self.rebuild_lists()

                if is_moderator:
                    title = "Custom reaction successfully added!"
                else:
                    title = f"Custom reaction proposal successfully submitted!"
                description = (f"-Prompt: {prompt_message}\n"
                               f"-Response: {response}")
                if delete:
                    description = (f"{description}\n-Will delete the "
                                   f"message that calls the reaction")
                if anywhere:
                    description = (f"{description}\n"
                                   f"-Will activate the custom reaction "
                                   "if the prompt is anywhere in a message")
                if dm:
                    description = (f"{description}\n"
                                   f"-Will react in the DMs of the user "
                                   f"who calls the reaction instead of the "
                                   f"channel")

                await message.edit(
                    embed=discord.Embed(title=title, description=description).
                    set_footer(text=f"Added by {main_user}.",
                               icon_url=main_user.avatar_url))

                return

            # Stop
            if reaction.emoji == EMOJI['stop_button']:
                await leave(message)
                return True

        async def list_custom_reacts(message, proposals):
            current_list = (self.proposal_list
                            if proposals else self.reaction_list)

            if not current_list:
                if proposals:
                    title = ("There are currently no custom reaction "
                             "proposals in this server")
                else:
                    title = ("There are currently no custom reactions in "
                             "this server")
                await message.edit(embed=discord.Embed(title=title),
                                   delete_after=60)
                return

            reaction_dict = {
                "names": [f"[{i + 1}]" for i in range(len(current_list))],
                "values": [
                    f'Prompt: '
                    f'{reaction[1][:min(len(reaction[1]), 287)]}'
                    f'{"..." if len(reaction[1]) > 287 else ""}'
                    f'\nResponse: '
                    f'{reaction[2][:min(len(reaction[2]), 287)]}'
                    f'{"..." if len(reaction[2]) > 287 else ""}'
                    for reaction in current_list
                ]
            }

            await message.edit(embed=LOADING_EMBED)

            await add_control_reactions(message)

            if proposals:
                title = (f"Current custom reaction proposals\n"
                         f"Click on {EMOJI['ok']} "
                         f"to approve, reject, edit, or see more "
                         f"information on one of them")
            else:
                title = (f"Current custom reactions\nClick on {EMOJI['ok']} "
                         f"to edit or see more information on one of them")

            p = Pages(ctx,
                      msg=message,
                      item_list=reaction_dict,
                      title=title,
                      display_option=(2, 10),
                      editable_content_emoji=EMOJI['ok'],
                      return_user_on_edit=True)

            user_modifying = await p.paginate()
            while p.edit_mode:
                await message.clear_reactions()
                if proposals:
                    title = (f"Current custom reaction proposals\n"
                             f"{user_modifying}: Write the number of the "
                             f"custom reaction "
                             f"proposal you want to approve, reject, edit, or "
                             f"see more information on")
                else:
                    title = (f"Current custom reactions\n"
                             f"{user_modifying}: Write the number of the "
                             f"custom reaction "
                             f"you want to edit or see more "
                             f"information on")
                message.embeds[0].title = title
                await message.edit(embed=message.embeds[0])
                number = 0
                try:
                    msg = await self.bot.wait_for(
                        'message',
                        check=get_number_check(msg_user=user_modifying,
                                               number_range=range(
                                                   1,
                                                   len(current_list) + 1)),
                        timeout=60)
                    number = int(msg.content)
                    await msg.delete()
                except asyncio.TimeoutError:
                    pass

                if number == 0:
                    if proposals:
                        title = (f"Current custom reaction proposals\n"
                                 f"Click on {EMOJI['ok']} "
                                 f"to approve, reject, edit, or "
                                 f"see more information on one of them "
                                 f"(Previous attempt received invalid input "
                                 f"or timed out)")
                    else:
                        title = (f"Current custom reactions\n"
                                 f"Click on {EMOJI['ok']} "
                                 f"to edit or see more information on one of "
                                 f"them (Previous attempt received invalid "
                                 f"input or timed out)")
                    p = Pages(ctx,
                              msg=message,
                              item_list=reaction_dict,
                              title=title,
                              display_option=(2, 10),
                              editable_content_emoji=EMOJI['ok'],
                              return_user_on_edit=True)
                else:
                    left = await information_on_react(message, current_list,
                                                      number, proposals)
                    if left:
                        return True
                    if proposals:
                        title = (f"Current custom reaction proposals\n"
                                 f"Click on {EMOJI['ok']} "
                                 f"to approve, reject, edit, or "
                                 f"see more information on one of them")
                    else:
                        title = (f"Current custom reactions\n"
                                 f"Click on {EMOJI['ok']} "
                                 f"to edit or see more information "
                                 f"on one of them")

                    # update dictionary since a custom reaction might have been
                    # modified
                    current_list = (self.proposal_list
                                    if proposals else self.reaction_list)

                    if not current_list:
                        if proposals:
                            title = ("There are currently no custom "
                                     "reaction proposals in this server")
                        else:
                            title = ("There are currently no custom "
                                     "reactions in this server")
                        await message.edit(embed=discord.Embed(title=title),
                                           delete_after=60)
                        return

                    reaction_dict = {
                        "names":
                        [f"[{i + 1}]" for i in range(len(current_list))],
                        "values": [
                            f'Prompt: '
                            f'{reaction[1][:min(len(reaction[1]), 287)]}'
                            f'{"..." if len(reaction[1]) > 287 else ""}'
                            f'\nResponse: '
                            f'{reaction[2][:min(len(reaction[2]), 287)]}'
                            f'{"..." if len(reaction[2]) > 287 else ""}'
                            for reaction in current_list
                        ]
                    }

                    p = Pages(ctx,
                              msg=message,
                              item_list=reaction_dict,
                              title=title,
                              display_option=(2, 10),
                              editable_content_emoji=EMOJI['ok'],
                              return_user_on_edit=True)
                await message.edit(embed=LOADING_EMBED)

                await add_control_reactions(message)

                user_modifying = await p.paginate()

        async def information_on_react(message, current_list, number,
                                       proposals):
            await message.edit(embed=LOADING_EMBED)

            custom_react = current_list[number - 1]
            prompt = custom_react[1]
            response = custom_react[2]
            user_who_added = self.bot.get_user(custom_react[3])
            delete = custom_react[4]
            anywhere = custom_react[5]
            dm = custom_react[6]
            if delete == 1:
                delete_str = "Deletes the message that calls the reaction"
            else:
                delete_str = ("Does not delete the message that "
                              "calls the reaction")
            if anywhere == 1:
                anywhere_str = ("Activates the custom reaction if "
                                "the prompt is anywhere in a message")
            else:
                anywhere_str = ("Only activates the custom reaction "
                                "if the prompt is the full message")
            if dm == 1:
                dm_str = ("Reacts in the DMs of the user who calls "
                          "the reaction instead of the channel")
            else:
                dm_str = "Reacts directly into the channel"

            if proposals:
                description = (f"{EMOJI['one']} Prompt: {prompt}"
                               f"\n{EMOJI['two']} Response: {response}"
                               f"\n{EMOJI['three']} {delete_str}"
                               f"\n{EMOJI['four']} {anywhere_str}"
                               f"\n{EMOJI['five']} {dm_str}"
                               f"\n{EMOJI['white_check_mark']} "
                               f"Approve this proposal\n"
                               f"{EMOJI['x']} Reject this proposal\n"
                               f"Added by {user_who_added}")
                title = (f"More information on a custom reaction proposal.\n"
                         f"{self.bot.config.moderator_role}s "
                         f"may click on emojis to modify those values or "
                         f"approve/refuse this proposal\n"
                         f"(Will return to the list of current reaction "
                         f"proposals in 40 seconds otherwise)")
            else:
                description = (f"{EMOJI['one']} Prompt: {prompt}\n"
                               f"{EMOJI['two']} Response: {response}"
                               f"\n{EMOJI['three']} {delete_str}"
                               f"\n{EMOJI['four']} {anywhere_str}"
                               f"\n{EMOJI['five']} {dm_str}"
                               f"\n{EMOJI['put_litter_in_its_place']} "
                               f"Delete this custom reaction\n"
                               f"Added by {user_who_added}")
                title = (f"More information on a custom reaction.\n"
                         f"{self.bot.config.moderator_role}s may click "
                         f"on emojis to modify those values "
                         f"or select an option\n(Will return to the list of "
                         f"current reactions in 40 seconds otherwise)")

            current_options.clear()
            await message.clear_reactions()
            if proposals:
                current_options.extend(
                    (*NUMBERS[1:6], EMOJI['white_check_mark'], EMOJI['x'],
                     EMOJI['stop_button']))
            else:
                current_options.extend(
                    (*NUMBERS[1:6], EMOJI['put_litter_in_its_place'],
                     EMOJI['stop_button']))
            if proposals:
                await add_multiple_reactions(
                    message, (*NUMBERS[1:6], EMOJI['white_check_mark'],
                              EMOJI['x'], EMOJI['stop_button']))
            else:
                await add_multiple_reactions(
                    message, (*NUMBERS[1:6], EMOJI['put_litter_in_its_place'],
                              EMOJI['stop_button']))
            await message.edit(
                embed=discord.Embed(title=title, description=description))

            try:
                reaction, user = await self.bot.wait_for(
                    'reaction_add',
                    check=get_reaction_check(moderators=True),
                    timeout=40)
                left = await edit_custom_react(message, reaction, user,
                                               custom_react, proposals)
                if left:
                    return True
            except asyncio.TimeoutError:
                pass
            current_options.clear()
            await message.clear_reactions()

        async def edit_custom_react(message, reaction, user, custom_react,
                                    proposals):
            current_options.clear()
            await message.clear_reactions()
            custom_react_id = custom_react[0]
            delete = custom_react[4]
            anywhere = custom_react[5]
            dm = custom_react[6]
            conn = sqlite3.connect(self.bot.config.db_path)
            c = conn.cursor()

            # Edit the prompt
            if reaction.emoji == EMOJI['one']:
                if proposals:
                    title = "Modify a custom reaction proposal"
                    footer = (f"{user} is currently modifying "
                              f"a custom reaction proposal. \n"
                              f"Write '{STOP_TEXT}' to cancel.")
                else:
                    title = "Modify a custom reaction"
                    footer = (f"{user} is currently "
                              f"modifying a custom reaction. "
                              f"\nWrite '{STOP_TEXT}' to cancel.")
                description = "Please enter the new prompt"
                await message.edit(
                    embed=discord.Embed(title=title, description=description).
                    set_footer(text=footer, icon_url=user.avatar_url))
                try:
                    msg = await self.bot.wait_for(
                        'message',
                        check=get_msg_check(msg_user=user),
                        timeout=60)

                except asyncio.TimeoutError:
                    if proposals:
                        title = ("The modification of the custom reaction "
                                 "proposal timed out. "
                                 "Returning to list of reaction proposals...")
                    else:
                        title = ("The modification of the custom reaction "
                                 "timed out. "
                                 "Returning to list of current reactions...")
                    await message.edit(embed=discord.Embed(title=title))
                    conn.close()
                    await asyncio.sleep(5)
                    return

                prompt = msg.content
                await msg.delete()

                if prompt.lower() == STOP_TEXT:
                    await leave(message)
                    return True

                t = (prompt, custom_react_id)
                c.execute(
                    'UPDATE CustomReactions SET Prompt = ? '
                    'WHERE CustomReactionID = ?', t)
                conn.commit()
                self.rebuild_lists()
                if proposals:
                    title = ("Prompt successfully modified! "
                             "Returning to list of reaction proposals...")
                else:
                    title = ("Prompt successfully modified! "
                             "Returning to list of current reactions...")
                await message.edit(embed=discord.Embed(title=title).set_footer(
                    text=f"Modified by {user}.", icon_url=user.avatar_url))
                conn.close()
                await asyncio.sleep(5)

            # Edit the response
            if reaction.emoji == EMOJI['two']:
                if proposals:
                    title = "Modify a custom reaction proposal"
                    footer = (f"{user} is currently modifying a "
                              f"custom reaction proposal. \n"
                              f"Write '{STOP_TEXT}' to cancel.")
                else:
                    title = "Modify a custom reaction"
                    footer = (f"{user} is currently modifying a "
                              f"custom reaction. "
                              f"\nWrite '{STOP_TEXT}' to cancel.")
                description = "Please enter the new response"
                await message.edit(
                    embed=discord.Embed(title=title, description=description).
                    set_footer(text=footer, icon_url=user.avatar_url))

                try:
                    msg = await self.bot.wait_for(
                        'message',
                        check=get_msg_check(msg_user=user),
                        timeout=60)

                except asyncio.TimeoutError:
                    if proposals:
                        title = ("The modification of the custom reaction "
                                 "proposal timed out. "
                                 "Returning to list of reaction proposals...")
                    else:
                        title = ("The modification of the custom reaction "
                                 "timed out. "
                                 "Returning to list of current reactions...")
                    await message.edit(embed=discord.Embed(title=title))
                    conn.close()
                    await asyncio.sleep(5)
                    return

                response = msg.content
                await msg.delete()

                if response.lower() == STOP_TEXT:
                    await leave(message)
                    return True

                t = (response, custom_react_id)
                c.execute(
                    'UPDATE CustomReactions SET Response = ? '
                    'WHERE CustomReactionID = ?', t)
                conn.commit()
                self.rebuild_lists()
                if proposals:
                    title = ("Response successfully modified! "
                             "Returning to list of reaction proposals...")
                else:
                    title = ("Response successfully modified! "
                             "Returning to list of current reactions...")
                await message.edit(embed=discord.Embed(title=title).set_footer(
                    text=f"Modified by {user}.", icon_url=user.avatar_url))
                conn.close()
                await asyncio.sleep(5)

            # Edit the "delete" option
            if reaction.emoji == EMOJI['three']:
                await message.edit(embed=LOADING_EMBED)
                if proposals:
                    title = ("Modify a custom reaction proposal. "
                             "React with the option you want")
                    footer = (f"{user} is currently modifying a "
                              f"custom reaction proposal. \n")
                else:
                    title = ("Modify a custom reaction. React with the "
                             "option you want")
                    footer = (f"{user} is currently modifying a "
                              f"custom reaction. \n")
                description = (f"Should the message that calls the "
                               f"reaction be deleted?\n"
                               f"{EMOJI['zero']} No\n"
                               f"{EMOJI['one']} Yes")
                current_options.clear()
                await message.clear_reactions()
                current_options.extend((*NUMBERS[0:2], EMOJI['stop_button']))
                await add_yes_or_no_reactions(message)
                await message.edit(
                    embed=discord.Embed(title=title, description=description).
                    set_footer(text=footer, icon_url=user.avatar_url))

                try:
                    reaction, reaction_user = await self.bot.wait_for(
                        'reaction_add',
                        check=get_reaction_check(reaction_user=user),
                        timeout=60)

                except asyncio.TimeoutError:
                    if proposals:
                        title = ("The modification of the custom reaction "
                                 "proposal timed out. "
                                 "Returning to list of reaction proposals...")
                    else:
                        title = ("The modification of the custom reaction "
                                 "timed out. "
                                 "Returning to list of current reactions...")
                    await message.edit(embed=discord.Embed(title=title))
                    conn.close()
                    await asyncio.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()
                # Deactivate the "delete" option
                if reaction.emoji == EMOJI['zero']:
                    if delete == 0:
                        if proposals:
                            title = ("Successfully kept current option! "
                                     "Returning to list of reaction "
                                     "proposals...")
                        else:
                            title = ("Successfully kept current option! "
                                     "Returning to list of current "
                                     "reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)
                    else:
                        t = (0, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET DeletePrompt = ? '
                            'WHERE CustomReactionID = ?', t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reaction proposals...")
                        else:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)

                # Activate the "delete" option
                elif reaction.emoji == EMOJI['one']:
                    if delete == 1:
                        if proposals:
                            title = ("Successfully kept current option! "
                                     "Returning to list of "
                                     "reaction proposals...")
                        else:
                            title = ("Successfully kept current option! "
                                     "Returning to list of "
                                     "current reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)
                    else:
                        t = (1, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET DeletePrompt = ? '
                            'WHERE CustomReactionID = ?', t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reaction proposals...")
                        else:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)
                # Stop
                elif reaction.emoji == EMOJI['stop_button']:
                    await leave(message)
                    return True

            # Edit the "anywhere" option
            if reaction.emoji == EMOJI['four']:
                await message.edit(embed=LOADING_EMBED)
                if proposals:
                    title = ("Modify a custom reaction proposal. "
                             "React with the option you want")
                    footer = (f"{user} is currently modifying a custom "
                              f"reaction proposal. \n")
                else:
                    title = ("Modify a custom reaction. "
                             "React with the option you want")
                    footer = (f"{user} is currently modifying a custom "
                              f"reaction. \n")
                description = (f"Should the custom reaction be activated "
                               f"if the prompt is anywhere in a message?\n"
                               f"{EMOJI['zero']} No\n"
                               f"{EMOJI['one']} Yes")
                current_options.clear()
                await message.clear_reactions()
                current_options.extend((*NUMBERS[0:2], EMOJI['stop_button']))
                await add_yes_or_no_reactions(message)
                await message.edit(
                    embed=discord.Embed(title=title, description=description).
                    set_footer(text=footer, icon_url=user.avatar_url))
                try:
                    reaction, reaction_user = await self.bot.wait_for(
                        'reaction_add',
                        check=get_reaction_check(reaction_user=user),
                        timeout=60)

                except asyncio.TimeoutError:
                    if proposals:
                        title = ("The modification of the custom reaction "
                                 "proposal timed out. "
                                 "Returning to list of reaction proposals...")
                    else:
                        title = ("The modification of the custom reaction "
                                 "timed out. "
                                 "Returning to list of current reactions...")
                    await message.edit(embed=discord.Embed(title=title))
                    conn.close()
                    await asyncio.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()
                # Deactivate "anywhere" option
                if reaction.emoji == EMOJI['zero']:
                    if anywhere == 0:
                        if proposals:
                            title = ("Successfully kept current option! "
                                     "Returning to list of "
                                     "reaction proposals...")
                        else:
                            title = ("Successfully kept current option! "
                                     "Returning to list of "
                                     "current reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)
                    else:
                        t = (0, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET Anywhere = ? '
                            'WHERE CustomReactionID = ?', t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reaction proposals...")
                        else:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)

                # Activate "anywhere" option
                elif reaction.emoji == EMOJI['one']:
                    if anywhere == 1:
                        if proposals:
                            title = ("Successfully kept current option! "
                                     "Returning to list of "
                                     "reaction proposals...")
                        else:
                            title = ("Successfully kept current option! "
                                     "Returning to list of current "
                                     "reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)
                    else:
                        t = (1, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET Anywhere = ? '
                            'WHERE CustomReactionID = ?', t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reaction proposals...")
                        else:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)
                # Stop
                elif reaction.emoji == EMOJI['stop_button']:
                    await leave(message)
                    return True

            # Edit "dm" option
            if reaction.emoji == EMOJI['five']:
                await message.edit(embed=LOADING_EMBED)
                if proposals:
                    title = ("Modify a custom reaction proposal. "
                             "React with the option you want")
                    footer = (f"{user} is currently modifying a custom "
                              f"reaction "
                              f"proposal. \n")
                else:
                    title = ("Modify a custom reaction. React with the "
                             "option you want")
                    footer = (f"{user} is currently modifying a "
                              f"custom reaction. \n")
                description = (f"Should the reaction be sent in the DMs of "
                               f"the user who called the reaction "
                               f"instead of the channel?\n"
                               f"{EMOJI['zero']} No\n"
                               f"{EMOJI['one']} Yes")
                current_options.clear()
                await message.clear_reactions()
                current_options.extend((*NUMBERS[0:2], EMOJI['stop_button']))
                await add_yes_or_no_reactions(message)
                await message.edit(
                    embed=discord.Embed(title=title, description=description).
                    set_footer(text=footer, icon_url=user.avatar_url))
                try:
                    reaction, reaction_user = await self.bot.wait_for(
                        'reaction_add',
                        check=get_reaction_check(reaction_user=user),
                        timeout=60)

                except asyncio.TimeoutError:
                    if proposals:
                        title = ("The modification of the custom reaction "
                                 "proposal timed out. "
                                 "Returning to list of reaction proposals...")
                    else:
                        title = ("The modification of the custom reaction "
                                 "timed out. "
                                 "Returning to list of current reactions...")
                    await message.edit(embed=discord.Embed(title=title))
                    conn.close()
                    await asyncio.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()
                # Deactivate "dm" option
                if reaction.emoji == EMOJI['zero']:
                    if dm == 0:
                        if proposals:
                            title = ("Successfully kept current option! "
                                     "Returning to list of "
                                     "reaction proposals...")
                        else:
                            title = ("Successfully kept current option! "
                                     "Returning to list of "
                                     "current reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)
                    else:
                        t = (0, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET DM = ? '
                            'WHERE CustomReactionID = ?', t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reaction proposals...")
                        else:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)
                # Activate "dm" option
                elif reaction.emoji == EMOJI['one']:
                    if dm == 1:
                        if proposals:
                            title = ("Successfully kept current option! "
                                     "Returning to list of "
                                     "reaction proposals...")
                        else:
                            title = ("Successfully kept current option! "
                                     "Returning to list of current "
                                     "reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)
                    else:
                        t = (1, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET DM = ? '
                            'WHERE CustomReactionID = ?', t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reaction proposals...")
                        else:
                            title = ("Option successfully modified! "
                                     "Returning to list of current "
                                     "reactions...")
                        await message.edit(embed=discord.Embed(
                            title=title).set_footer(
                                text=f"Modified by {user}.",
                                icon_url=user.avatar_url))
                        conn.close()
                        await asyncio.sleep(5)
                # Stop
                elif reaction.emoji == EMOJI['stop_button']:
                    await leave(message)
                    return True

            # Approve a custom reaction proposal
            if reaction.emoji == EMOJI['white_check_mark']:
                t = (0, custom_react_id)
                c.execute(
                    'UPDATE CustomReactions SET Proposal = ? '
                    'WHERE CustomReactionID = ?', t)
                conn.commit()
                self.rebuild_lists()
                title = ("Custom reaction proposal successfully approved! "
                         "Returning to list of current reaction proposals...")
                footer = f"Approved by {user}."
                await message.edit(embed=discord.Embed(title=title).set_footer(
                    text=footer, icon_url=user.avatar_url))
                conn.close()
                await asyncio.sleep(5)

            # Delete a custom reaction or proposal
            if reaction.emoji == EMOJI[
                    "put_litter_in_its_place"] or reaction.emoji == EMOJI['x']:
                t = (custom_react_id, )
                c.execute(
                    'DELETE FROM CustomReactions WHERE CustomReactionID = ?',
                    t)
                conn.commit()
                if proposals:
                    title = ("Custom reaction proposal successfully "
                             "rejected! Returning to list of current "
                             "reaction proposals...")
                    footer = f"Rejected by {user}."
                else:
                    title = ("Custom reaction successfully deleted! "
                             "Returning to list of current reactions...")
                    footer = f"Deleted by {user}."
                await message.edit(embed=discord.Embed(title=title).set_footer(
                    text=footer, icon_url=user.avatar_url))
                conn.close()
                self.rebuild_lists()
                await asyncio.sleep(5)

            # Stop
            if reaction.emoji == EMOJI['stop_button']:
                await leave(message)
                return True

        async def list_placeholders(message):
            title = ("The following placeholders can be used in "
                     "prompts and responses:")
            description = ("-%user%: the user who called "
                           "the prompt (can only be used in a response)\n"
                           "-%channel%: the name of "
                           "the channel where the prompt was called "
                           "(can only be used in a response) \n"
                           "-%1%, %2%, etc. up to %9%: Groups. When a "
                           "prompt uses this, anything will match. For "
                           "example, the prompt \"i %1% apples\" will work "
                           "for any message that starts with \"i\" and ends "
                           "with \"apples\", such as \"i really like "
                           "apples\". Then, the words that match to this "
                           "group can be used in the response. For example, "
                           "keeping the same prompt and using the response "
                           "\"i %1% pears\" will send "
                           "\"i really like pears\"\n"
                           "-%[]%: a comma-separated choice list. There are "
                           "two uses for this. The first is that when it is "
                           "used in a prompt, the prompt will accept either "
                           "of the choices. For example, the prompt "
                           "\"%[hello, hi, hey]% world\" will work if someone "
                           "writes \"hello world\", \"hi world\" or "
                           "\"hey world\". The second use is that when it is "
                           "used in a response, a random choice will be "
                           "chosen from the list. For example, the response "
                           "\"i %[like, hate]% you\" will either send \"i "
                           "like you\" or \"i hate you\". All placeholders "
                           "can be used in choice lists (including choice "
                           "lists themselves). If a choice contains commas, "
                           "it can be surrounded by \"\" to not be split into "
                           "different choices")
            await message.edit(
                embed=discord.Embed(title=title, description=description))

        async def leave(message):
            await message.delete()

        initial_message = await ctx.send(embed=LOADING_EMBED)
        is_mod = (discord.utils.get(main_user.roles,
                                    name=self.bot.config.moderator_role)
                  is not None)
        await create_assistant(initial_message, is_mod)


def setup(bot):
    bot.add_cog(CustomReactions(bot))
