# Copyright (C) idoneam (2016-2020)
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
        self.reaction_list_prompts = []
        self.proposal_list = []
        self.rebuild_lists()

    def rebuild_lists(self):
        self.rebuild_reaction_list()
        self.rebuild_proposal_list()

    def rebuild_reaction_list(self):
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM CustomReactions WHERE Proposal = 0')
        self.reaction_list = c.fetchall()
        # get list of the Prompt column only
        self.reaction_list_prompts = [row[1] for row in self.reaction_list]
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

        if any(s.lower() in message.content.lower()
               for s in self.reaction_list_prompts):
            # get indices of every prompt that contains the message.
            # Done this way to not compute it every time a message is sent
            indices = [
                i for i, x in enumerate(self.reaction_list_prompts)
                if x.lower() in message.content.lower()
            ]
            # only keep the ones that are exactly the message, or that are
            # contained in the message AND have the anywhere option activated
            reactions_at_indices = [self.reaction_list[i] for i in indices]
            reactions = [
                reaction for reaction in reactions_at_indices
                if (reaction[1].lower() == message.content.lower()
                    or reaction[5] == 1)
            ]

            # return if no reactions were kept
            if not reactions:
                return

            # choose a random one of these
            reaction = random.choice(reactions)

            # delete the prompt if DeletePrompt option is activated
            if reaction[4] == 1:
                await message.delete()

            # send the response if DM option selected,
            # send in the DM of the user who wrote the prompt
            if reaction[6] == 1:
                await message.author.send(reaction[2])
            else:
                await message.channel.send(reaction[2])

    @commands.command(
        aliases=['customreaction', 'customreacts', 'customreact'])
    async def customreactions(self, ctx):
        current_options = []
        author = ctx.message.author
        await ctx.message.delete()

        def get_number_of_proposals():
            return len(self.proposal_list)

        def reaction_check(reaction, user):
            return all((reaction.emoji in current_options, user == author,
                        reaction.message.id == initial_message.id))

        def reaction_check_any_user(reaction, user):
            return all((reaction.emoji in current_options,
                        reaction.message.id == initial_message.id))

        def reaction_check_moderators(reaction, user):
            return all(
                (reaction.emoji
                 in current_options, reaction.message.id == initial_message.id,
                 discord.utils.get(user.roles,
                                   name=self.bot.config.moderator_role)))

        def msg_check(msg):
            return msg.author == author

        def number_check(msg):
            return msg.content.isdigit()

        async def wait_for_reaction(message):
            try:
                reaction, user = await self.bot.wait_for('reaction_add',
                                                         check=reaction_check,
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
                msg = await self.bot.wait_for('message',
                                              check=msg_check,
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
                    f"and approve or reject them")
            else:
                description = (
                    f"{EMOJI['new']} Propose a new custom reaction\n"
                    f"{EMOJI['mag']} See the list of current reactions\n"
                    f"{EMOJI['pencil']} See the list of proposed reactions "
                    f"({get_number_of_proposals()})")
            current_options.extend((EMOJI['new'], EMOJI['mag'],
                                    EMOJI['pencil'], EMOJI['stop_button']))
            await add_multiple_reactions(
                message, (EMOJI['new'], EMOJI['mag'], EMOJI['pencil'],
                          EMOJI['stop_button']))
            await message.edit(embed=discord.Embed(
                title="Custom Reactions", description=description).set_footer(
                    text=f"{author}: Click on an emoji to choose an "
                    f"option (If a list is chosen, all users "
                    f"will be able to interact with it)",
                    icon_url=author.avatar_url))
            try:
                reaction, user = await wait_for_reaction(message)
            except TypeError:
                return
            current_options.clear()
            await message.clear_reactions()
            # Add/Propose a new custom reaction
            if reaction.emoji == EMOJI['new']:
                await addcustomreact(message, is_moderator)
                return
            # List custom reactions
            if reaction.emoji == EMOJI['mag']:
                await listcustomreacts(message, proposals=False)
                return
            # List proposals
            if reaction.emoji == EMOJI['pencil']:
                await listcustomreacts(message, proposals=True)
                return
            # Stop
            if reaction.emoji == EMOJI['stop_button']:
                await leave(message)
                return True

        async def addcustomreact(message, is_moderator):
            if is_moderator:
                title = "Add a custom reaction"
                footer = (f"{author} is currently adding a custom reaction. \n"
                          f"Write '{STOP_TEXT}' to cancel.")
            else:
                title = "Propose a custom reaction"
                footer = (f"{author} is currently proposing a custom "
                          f"reaction. \n"
                          f"Write '{STOP_TEXT}' to cancel.")
            description = "Write the prompt the bot will react to"
            await message.edit(
                embed=discord.Embed(title=title, description=description).
                set_footer(text=footer, icon_url=author.avatar_url))
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
                set_footer(text=footer, icon_url=author.avatar_url))
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
            footer = f"{author} is currently proposing a custom reaction."
            current_options.extend((EMOJI['ok'], EMOJI['stop_button']))
            await add_multiple_reactions(
                message, (*NUMBERS[1:4], EMOJI['ok'], EMOJI['stop_button']))
            await message.edit(
                embed=discord.Embed(title=title, description=description).
                set_footer(text=footer, icon_url=author.avatar_url))
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
                    if author in users_who_reacted:
                        delete = delete or reaction.emoji == EMOJI['one']
                        anywhere = anywhere or reaction.emoji == EMOJI['two']
                        dm = dm or reaction.emoji == EMOJI['three']

                current_options.clear()
                await message.clear_reactions()
                conn = sqlite3.connect(self.bot.config.db_path)
                c = conn.cursor()
                t = (prompt_message, response, author.id, delete, anywhere, dm,
                     not is_moderator)
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

                await message.edit(embed=discord.Embed(
                    title=title, description=description).set_footer(
                        text=f"Added by {author}.", icon_url=author.avatar_url)
                                   )

                return

            # Stop
            if reaction.emoji == EMOJI['stop_button']:
                await leave(message)
                return True

        async def listcustomreacts(message, proposals):
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
                "names": [f"[{i+1}]" for i in range(len(current_list))],
                "values": [
                    f'Prompt: {reaction[1]}\nResponse: {reaction[2]}'
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
                    number_sent_by_user_modifying = False
                    manual_timeout = time.time() + 60
                    while not number_sent_by_user_modifying:
                        msg = await self.bot.wait_for('message',
                                                      check=number_check,
                                                      timeout=60)
                        if msg.author == user_modifying:
                            number = int(msg.content)
                            number_sent_by_user_modifying = True
                            await msg.delete()
                        elif time.time() > manual_timeout:
                            raise asyncio.TimeoutError

                except asyncio.TimeoutError:
                    pass

                if number < 1 or number > len(current_list):
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
                            f'Prompt: {reaction[1]}\nResponse: {reaction[2]}'
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
                    check=reaction_check_moderators,
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
                prompt = None
                try:
                    msg_sent_by_user_modifying = False
                    manual_timeout = time.time() + 60
                    while not msg_sent_by_user_modifying:
                        msg = await self.bot.wait_for('message', timeout=60)
                        if msg.author == user:
                            prompt = msg.content
                            msg_sent_by_user_modifying = True
                            await msg.delete()
                        elif time.time() > manual_timeout:
                            raise asyncio.TimeoutError

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
                    time.sleep(5)
                    return

                if prompt is None:
                    return
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
                time.sleep(5)

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
                response = None
                try:
                    msg_sent_by_user_modifying = False
                    manual_timeout = time.time() + 60
                    while not msg_sent_by_user_modifying:
                        msg = await self.bot.wait_for('message', timeout=60)
                        if msg.author == user:
                            response = msg.content
                            msg_sent_by_user_modifying = True
                            await msg.delete()
                        elif time.time() > manual_timeout:
                            raise asyncio.TimeoutError

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
                    time.sleep(5)
                    return

                if response is None:
                    return
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
                time.sleep(5)

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
                reaction = None
                try:
                    react_sent_by_user_modifying = False
                    manual_timeout = time.time() + 60
                    while not react_sent_by_user_modifying:
                        reaction, reaction_user = await self.bot.wait_for(
                            'reaction_add',
                            check=reaction_check_any_user,
                            timeout=60)
                        if reaction_user == user:
                            react_sent_by_user_modifying = True
                        elif time.time() > manual_timeout:
                            raise asyncio.TimeoutError

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
                    time.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()
                if reaction is None:
                    return
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
                        time.sleep(5)
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
                        time.sleep(5)

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
                        time.sleep(5)
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
                        time.sleep(5)
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
                reaction = None
                try:
                    react_sent_by_user_modifying = False
                    manual_timeout = time.time() + 60
                    while not react_sent_by_user_modifying:
                        reaction, reaction_user = await self.bot.wait_for(
                            'reaction_add',
                            check=reaction_check_any_user,
                            timeout=60)
                        if reaction_user == user:
                            react_sent_by_user_modifying = True
                        elif time.time() > manual_timeout:
                            raise asyncio.TimeoutError

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
                    time.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()
                if reaction is None:
                    return
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
                        time.sleep(5)
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
                        time.sleep(5)

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
                        time.sleep(5)
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
                        time.sleep(5)
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
                reaction = None
                try:
                    react_sent_by_user_modifying = False
                    manual_timeout = time.time() + 60
                    while not react_sent_by_user_modifying:
                        reaction, reaction_user = await self.bot.wait_for(
                            'reaction_add',
                            check=reaction_check_any_user,
                            timeout=60)
                        if reaction_user == user:
                            react_sent_by_user_modifying = True
                        else:
                            if time.time() > manual_timeout:
                                raise asyncio.TimeoutError

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
                    time.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()
                if reaction is None:
                    return
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
                        time.sleep(5)
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
                        time.sleep(5)
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
                        time.sleep(5)
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
                        time.sleep(5)
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
                time.sleep(5)

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
                time.sleep(5)

            # Stop
            if reaction.emoji == EMOJI['stop_button']:
                await leave(message)
                return True

        async def leave(message):
            await message.delete()

        initial_message = await ctx.send(embed=LOADING_EMBED)
        is_moderator = (discord.utils.get(ctx.author.roles,
                                          name=self.bot.config.moderator_role)
                        is not None)
        await create_assistant(initial_message, is_moderator)


def setup(bot):
    bot.add_cog(CustomReactions(bot))
