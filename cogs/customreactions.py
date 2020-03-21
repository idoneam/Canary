# -*- coding: utf-8 -*-
#
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


class Customreactions(commands.Cog):
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
            return

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
                (reaction.emoji in current_options,
                 reaction.message.id == initial_message.id,
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
                embed = discord.Embed(
                    title=
                    'Custom Reaction timed out. You may want to run the command again.'
                )
                await message.clear_reactions()
                await message.edit(embed=embed, delete_after=60)
                return
            return reaction, user

        async def wait_for_message(message):
            try:
                msg = await self.bot.wait_for('message',
                                              check=msg_check,
                                              timeout=60)
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title=
                    'Custom Reaction timed out. You may want to run the command again.'
                )
                await message.clear_reactions()
                await message.edit(embed=embed, delete_after=60)
                return
            content = msg.content
            await msg.delete()
            return content

        async def create_assistant(message, is_moderator):
            if is_moderator:
                description = "🆕 Add a new custom reaction\n" \
                              "🔍 See the list of current reactions and modify them\n" \
                              "📝 See the list of proposed reactions ({}) and approve or reject them"\
                              .format(get_number_of_proposals())
            else:
                description = "🆕 Propose a new custom reaction\n" \
                              "🔍 See the list of current reactions\n" \
                              "📝 See the list of proposed reactions ({})"\
                              .format(get_number_of_proposals())
            embed = discord.Embed(title="Custom Reactions",
                                  description=description)
            embed.set_footer(
                text="{}: Click on an emoji to choose an option "
                "(If a list is chosen, all users will be able to interact with it)"
                .format(author),
                icon_url=author.avatar_url)
            current_options.extend(["🆕", "🔍", "📝", "⏹"])
            for option in current_options:
                await message.add_reaction(option)
            await message.edit(embed=embed)
            try:
                reaction, user = await wait_for_reaction(message)
            except TypeError:
                return
            current_options.clear()
            await message.clear_reactions()
            # Add/Propose a new custom reaction
            if reaction.emoji == "🆕":
                await addcustomreact(message, is_moderator)
                return
            if reaction.emoji == "🔍":
                await listcustomreacts(message, proposals=False)
                return
            if reaction.emoji == "📝":
                await listcustomreacts(message, proposals=True)
                return
            if reaction.emoji == "⏹":
                await leave(message)
                return

        async def addcustomreact(message, is_moderator):
            if is_moderator:
                title = "Add a custom reaction"
                footer = "{} is currently adding a custom reaction. \n" \
                         "Write 'stop' to cancel.".format(author)
            else:
                title = "Propose a custom reaction"
                footer = "{} is currently proposing a custom reaction. \n" \
                         "Write 'stop' to cancel.".format(author)
            description = "Write the prompt the bot will react to"
            embed = discord.Embed(title=title, description=description)
            embed.set_footer(text=footer, icon_url=author.avatar_url)
            await message.edit(embed=embed)
            prompt_message = await wait_for_message(message)
            if prompt_message is None:
                return
            elif prompt_message.lower() == "stop":
                await leave(message)
                return
            description = "Prompt: {}\nWrite the response the bot will send".format(
                prompt_message)
            embed = discord.Embed(title=title, description=description)
            embed.set_footer(text=footer, icon_url=author.avatar_url)
            await message.edit(embed=embed)
            response = await wait_for_message(message)
            if response is None:
                return
            elif response.lower() == "stop":
                await leave(message)
                return
            embed = discord.Embed(title="Loading...")
            await message.edit(embed=embed)
            description = "Prompt: {}\nResponse: {}\nReact with the options you want and click 🆗 when you are ready\n"\
                          "1️⃣ Delete the message that calls the reaction\n" \
                          "2️⃣ Activate the custom reaction if the prompt is anywhere in a message \n" \
                          "3️⃣ React in the DMs of the user who calls the reaction instead of the channel\n"\
                .format(prompt_message, response)
            embed = discord.Embed(title=title, description=description)
            embed.set_footer(text=footer, icon_url=author.avatar_url)
            current_options.extend(["🆗", "⏹"])
            await message.add_reaction("1️⃣")
            await message.add_reaction("2️⃣")
            await message.add_reaction("3️⃣")
            await message.add_reaction("🆗")
            await message.add_reaction("⏹")
            await message.edit(embed=embed)
            try:
                reaction, user = await wait_for_reaction(message)
            except TypeError:
                return

            if reaction.emoji == "🆗":
                delete = False
                anywhere = False
                dm = False
                cache_msg = await message.channel.fetch_message(message.id)
                for reaction in cache_msg.reactions:
                    users_who_reacted = await reaction.users().flatten()
                    if author in users_who_reacted:
                        if reaction.emoji == "1️⃣":
                            delete = True
                        if reaction.emoji == "2️⃣":
                            anywhere = True
                        if reaction.emoji == "3️⃣":
                            dm = True

                current_options.clear()
                await message.clear_reactions()
                conn = sqlite3.connect(self.bot.config.db_path)
                c = conn.cursor()
                t = (prompt_message, response, author.id, delete, anywhere, dm,
                     not is_moderator)
                c.execute(
                    'INSERT INTO CustomReactions(Prompt, Response, UserID, DeletePrompt, Anywhere, DM, '
                    'Proposal) VALUES(?,?,?,?,?,?,?)', t)
                conn.commit()
                conn.close()
                self.rebuild_lists()

                if is_moderator:
                    title = "Custom reaction successfully added!"
                else:
                    title = "Custom reaction proposal successfully submitted!"
                description = "-Prompt: {}\n-Response: {}".format(
                    prompt_message, response)
                if delete:
                    description = "{}\n-Will delete the message that calls the reaction".format(
                        description)
                if anywhere:
                    description = "{}\n-Will activate the custom reaction if the prompt is anywhere in a message"\
                        .format(description)
                if dm:
                    description = "{}\n-Will react in the DMs of the user who calls the reaction instead of the "\
                                  "channel".format(description)

                embed = discord.Embed(title=title, description=description)
                embed.set_footer(text="Added by {}.".format(author),
                                 icon_url=author.avatar_url)
                await message.edit(embed=embed)

                return

            if reaction_emoji == "⏹":
                await leave(message)
                return

        async def listcustomreacts(message, proposals):
            if proposals:
                current_list = self.proposal_list
            else:
                current_list = self.reaction_list

            if not current_list:
                if proposals:
                    title = 'There are currently no custom reaction proposals in this server'
                else:
                    title = 'There are currently no custom reactions in this server'
                embed = discord.Embed(title=title, delete_after=60)
                await message.edit(embed=embed)
                return

            index_list = [
                '[{}]'.format(i + 1) for i in range(len(current_list))
            ]

            prompts_and_responses = [
                'Prompt: {}\nResponse: {}'.format(reaction[1], reaction[2])
                for reaction in current_list
            ]

            reaction_dict = {
                "names": index_list,
                "values": prompts_and_responses
            }

            embed = discord.Embed(title="Loading...")
            await message.edit(embed=embed)

            await message.add_reaction("⏪")
            await message.add_reaction("◀")
            await message.add_reaction("▶")
            await message.add_reaction("⏩")
            await message.add_reaction("⏹")
            await message.add_reaction("🆗")

            if proposals:
                title = "Current custom reaction proposals\n" \
                        "Click on 🆗 to approve, reject, edit, or see more information on one of them"
            else:
                title = "Current custom reactions\nClick on 🆗 to edit or see more information on one of them"

            p = Pages(ctx,
                      msg=message,
                      item_list=reaction_dict,
                      title=title,
                      display_option=(2, 10),
                      editable_content_emoji="🆗",
                      return_user_on_edit=True)

            user_modifying = await p.paginate()
            while p.edit_mode:
                await message.clear_reactions()
                if proposals:
                    title = "Current custom reaction proposals\n" \
                            "{}: Write the number of the custom reaction proposal you want to " \
                            "approve, reject, edit, or see more information on".format(user_modifying)
                else:
                    title = "Current custom reactions\n" \
                            "{}: Write the number of the custom reaction you want to edit or see more " \
                            "information on".format(user_modifying)
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
                        else:
                            if time.time() > manual_timeout:
                                raise asyncio.TimeoutError

                except asyncio.TimeoutError:
                    pass

                if number < 1 or number > len(current_list):
                    if proposals:
                        title = "Current custom reaction proposals\nClick on 🆗 to approve, reject, edit, or see " \
                                "more information on one of them (Previous attempt received invalid input or timed out)"
                    else:
                        title = "Current custom reactions\nClick on 🆗 to edit or see more information on one of " \
                                "them (Previous attempt received invalid input or timed out)"
                    p = Pages(ctx,
                              msg=message,
                              item_list=reaction_dict,
                              title=title,
                              display_option=(2, 10),
                              editable_content_emoji="🆗",
                              return_user_on_edit=True)
                else:
                    await information_on_react(message, current_list, number,
                                               proposals)
                    if proposals:
                        title = "Current custom reaction proposals\nClick on 🆗 to approve, reject, edit, or see " \
                                "more information on one of them"
                    else:
                        title = "Current custom reactions\nClick on 🆗 to edit or see more information on one of them"

                    # update dictionary since a custom reaction might have been modified
                    if proposals:
                        current_list = self.proposal_list
                    else:
                        current_list = self.reaction_list

                    if not current_list:
                        if proposals:
                            title = 'There are currently no custom reaction proposals in this server'
                        else:
                            title = 'There are currently no custom reactions in this server'
                        embed = discord.Embed(title=title, delete_after=60)
                        await message.edit(embed=embed)
                        return

                    index_list = [
                        '[{}]'.format(i + 1) for i in range(len(current_list))
                    ]

                    prompts_and_responses = [
                        'Prompt: {}\nResponse: {}'.format(
                            reaction[1], reaction[2])
                        for reaction in current_list
                    ]

                    reaction_dict = {
                        "names": index_list,
                        "values": prompts_and_responses
                    }

                    p = Pages(ctx,
                              msg=message,
                              item_list=reaction_dict,
                              title=title,
                              display_option=(2, 10),
                              editable_content_emoji="🆗",
                              return_user_on_edit=True)
                embed = discord.Embed(title="Loading...")
                await message.edit(embed=embed)

                await message.add_reaction("⏪")
                await message.add_reaction("◀")
                await message.add_reaction("▶")
                await message.add_reaction("⏩")
                await message.add_reaction("⏹")
                await message.add_reaction("🆗")

                user_modifying = await p.paginate()

        async def information_on_react(message, current_list, number,
                                       proposals):
            embed = discord.Embed(title="Loading...")
            await message.edit(embed=embed)

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
                delete_str = "Does not delete the message that calls the reaction"
            if anywhere == 1:
                anywhere_str = "Activates the custom reaction if the prompt is anywhere in a message"
            else:
                anywhere_str = "Only activates the custom reaction if the prompt is the full message"
            if dm == 1:
                dm_str = "Reacts in the DMs of the user who calls the reaction instead of the channel"
            else:
                dm_str = "Reacts directly into the channel"

            if proposals:
                description = "1️⃣ Prompt: {}\n2️⃣ Response: {}\n3️⃣ {}\n4️⃣ {}\n5️⃣ {}" \
                              "\n✅ Approve this proposal\n❌ Reject this proposal\nAdded by {}"\
                              .format(prompt, response, delete_str, anywhere_str, dm_str, user_who_added)
                title = "More information on a custom reaction proposal.\n" \
                        "{}s may click on emojis to modify those values or approve/refuse this proposal\n" \
                        "(Will return to the list of current reaction proposals in 40 seconds otherwise)"\
                        .format(self.bot.config.moderator_role)
            else:
                description = "1️⃣ Prompt: {}\n2️⃣ Response: {}\n3️⃣ {}\n4️⃣ {}\n5️⃣ {}" \
                              "\n🚮 Delete this custom reaction\nAdded by {}".format(prompt, response, delete_str,
                                                                                    anywhere_str, dm_str,
                                                                                    user_who_added)
                title = "More information on a custom reaction.\n" \
                        "{}s may click on emojis to modify those values or select an option\n" \
                        "(Will return to the list of current reactions in 40 seconds otherwise)"\
                        .format(self.bot.config.moderator_role)

            embed = discord.Embed(title=title, description=description)
            current_options.clear()
            await message.clear_reactions()
            if proposals:
                current_options.extend(
                    ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "✅", "❌", "⏹"])
            else:
                current_options.extend(
                    ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "🚮", "⏹"])
            await message.add_reaction("1️⃣")
            await message.add_reaction("2️⃣")
            await message.add_reaction("3️⃣")
            await message.add_reaction("4️⃣")
            await message.add_reaction("5️⃣")
            if proposals:
                await message.add_reaction("✅")
                await message.add_reaction("❌")
            else:
                await message.add_reaction("🚮")
            await message.add_reaction("⏹")
            await message.edit(embed=embed)

            try:
                reaction, user = await self.bot.wait_for(
                    'reaction_add',
                    check=reaction_check_moderators,
                    timeout=40)
                await edit_custom_react(message, reaction, user, custom_react,
                                        proposals)
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

            if reaction.emoji == "1️⃣":
                if proposals:
                    title = "Modify a custom reaction proposal"
                    footer = "{} is currently modifying a custom reaction proposal. \n" \
                             "Write 'stop' to cancel.".format(user)
                else:
                    title = "Modify a custom reaction"
                    footer = "{} is currently modifying a custom reaction. \n" \
                             "Write 'stop' to cancel.".format(user)
                description = "Please enter the new prompt"
                embed = discord.Embed(title=title, description=description)
                embed.set_footer(text=footer, icon_url=user.avatar_url)
                await message.edit(embed=embed)
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
                        else:
                            if time.time() > manual_timeout:
                                raise asyncio.TimeoutError

                except asyncio.TimeoutError:
                    if proposals:
                        title = 'The modification of the custom reaction proposal timed out. ' \
                                'Returning to list of reaction proposals...'
                    else:
                        title = 'The modification of the custom reaction timed out. ' \
                                'Returning to list of current reactions...'
                    embed = discord.Embed(title=title)
                    await message.edit(embed=embed)
                    conn.close()
                    time.sleep(5)
                    return

                if prompt is None:
                    return
                elif prompt.lower() == "stop":
                    await leave(message)
                    return

                t = (prompt, custom_react_id)
                c.execute(
                    'UPDATE CustomReactions SET Prompt = ? WHERE CustomReactionID = ?',
                    t)
                conn.commit()
                self.rebuild_lists()
                if proposals:
                    title = "Prompt successfully modified! Returning to list of reaction proposals..."
                else:
                    title = "Prompt successfully modified! Returning to list of current reactions..."
                embed = discord.Embed(title=title)
                embed.set_footer(text="Modified by {}.".format(user),
                                 icon_url=user.avatar_url)
                await message.edit(embed=embed)
                conn.close()
                time.sleep(5)

            if reaction.emoji == "2️⃣":
                if proposals:
                    title = "Modify a custom reaction proposal"
                    footer = "{} is currently modifying a custom reaction proposal. \n" \
                             "Write 'stop' to cancel.".format(user)
                else:
                    title = "Modify a custom reaction"
                    footer = "{} is currently modifying a custom reaction. \n" \
                             "Write 'stop' to cancel.".format(user)
                description = "Please enter the new response"
                embed = discord.Embed(title=title, description=description)
                embed.set_footer(text=footer, icon_url=user.avatar_url)
                await message.edit(embed=embed)
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
                        else:
                            if time.time() > manual_timeout:
                                raise asyncio.TimeoutError

                except asyncio.TimeoutError:
                    if proposals:
                        title = 'The modification of the custom reaction proposal timed out. ' \
                                'Returning to list of reaction proposals...'
                    else:
                        title = 'The modification of the custom reaction timed out. ' \
                                'Returning to list of current reactions...'
                    embed = discord.Embed(title=title)
                    await message.edit(embed=embed)
                    conn.close()
                    time.sleep(5)
                    return

                if response is None:
                    return
                elif response.lower() == "stop":
                    await leave(message)
                    return

                t = (response, custom_react_id)
                c.execute(
                    'UPDATE CustomReactions SET Response = ? WHERE CustomReactionID = ?',
                    t)
                conn.commit()
                self.rebuild_lists()
                if proposals:
                    title = "Response successfully modified! Returning to list of reaction proposals..."
                else:
                    title = "Response successfully modified! Returning to list of current reactions..."
                embed = discord.Embed(title=title)
                embed.set_footer(text="Modified by {}.".format(user),
                                 icon_url=user.avatar_url)
                await message.edit(embed=embed)
                conn.close()
                time.sleep(5)

            if reaction.emoji == "3️⃣":
                embed = discord.Embed(title="Loading...")
                await message.edit(embed=embed)
                if proposals:
                    title = "Modify a custom reaction proposal. React with the option you want"
                    footer = "{} is currently modifying a custom reaction proposal. \n".format(
                        user)
                else:
                    title = "Modify a custom reaction. React with the option you want"
                    footer = "{} is currently modifying a custom reaction. \n".format(
                        user)
                description = "Should the message that calls the reaction be deleted?\n" \
                              "0️⃣ No\n" \
                              "1️⃣ Yes"
                embed = discord.Embed(title=title, description=description)
                embed.set_footer(text=footer, icon_url=user.avatar_url)
                current_options.clear()
                await message.clear_reactions()
                current_options.extend(["0️⃣", "1️⃣", "⏹"])
                await message.add_reaction("0️⃣")
                await message.add_reaction("1️⃣")
                await message.add_reaction("⏹")
                await message.edit(embed=embed)
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
                        title = 'The modification of the custom reaction proposal timed out. ' \
                                'Returning to list of reaction proposals...'
                    else:
                        title = 'The modification of the custom reaction timed out. ' \
                                'Returning to list of current reactions...'
                    embed = discord.Embed(title=title)
                    await message.edit(embed=embed)
                    conn.close()
                    time.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()
                if reaction is None:
                    return
                elif reaction.emoji == "0️⃣":
                    if delete == 0:
                        if proposals:
                            title = "Successfully kept current option! Returning to list of reaction proposals..."
                        else:
                            title = "Successfully kept current option! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)
                    else:
                        t = (0, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET DeletePrompt = ? WHERE CustomReactionID = ?',
                            t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = "Option successfully modified! Returning to list of current reaction proposals..."
                        else:
                            title = "Option successfully modified! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)

                elif reaction.emoji == "1️⃣":
                    if delete == 1:
                        if proposals:
                            title = "Successfully kept current option! Returning to list of reaction proposals..."
                        else:
                            title = "Successfully kept current option! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)
                    else:
                        t = (1, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET DeletePrompt = ? WHERE CustomReactionID = ?',
                            t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = "Option successfully modified! Returning to list of current reaction proposals..."
                        else:
                            title = "Option successfully modified! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)
                elif reaction.emoji == "⏹":
                    await leave(message)
                    return

            if reaction.emoji == "4️⃣":
                embed = discord.Embed(title="Loading...")
                await message.edit(embed=embed)
                if proposals:
                    title = "Modify a custom reaction proposal. React with the option you want"
                    footer = "{} is currently modifying a custom reaction proposal. \n".format(
                        user)
                else:
                    title = "Modify a custom reaction. React with the option you want"
                    footer = "{} is currently modifying a custom reaction. \n".format(
                        user)
                description = "Should the custom reaction be activated if the prompt is anywhere in a message?\n" \
                              "0️⃣ No\n" \
                              "1️⃣ Yes"
                embed = discord.Embed(title=title, description=description)
                embed.set_footer(text=footer, icon_url=user.avatar_url)
                current_options.clear()
                await message.clear_reactions()
                current_options.extend(["0️⃣", "1️⃣", "⏹"])
                await message.add_reaction("0️⃣")
                await message.add_reaction("1️⃣")
                await message.add_reaction("⏹")
                await message.edit(embed=embed)
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
                        title = 'The modification of the custom reaction proposal timed out. ' \
                                'Returning to list of reaction proposals...'
                    else:
                        title = 'The modification of the custom reaction timed out. ' \
                                'Returning to list of current reactions...'
                    embed = discord.Embed(title=title)
                    await message.edit(embed=embed)
                    conn.close()
                    time.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()
                if reaction is None:
                    return
                elif reaction.emoji == "0️⃣":
                    if anywhere == 0:
                        if proposals:
                            title = "Successfully kept current option! Returning to list of reaction proposals..."
                        else:
                            title = "Successfully kept current option! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)
                    else:
                        t = (0, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET Anywhere = ? WHERE CustomReactionID = ?',
                            t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = "Option successfully modified! Returning to list of current reaction proposals..."
                        else:
                            title = "Option successfully modified! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)

                elif reaction.emoji == "1️⃣":
                    if anywhere == 1:
                        if proposals:
                            title = "Successfully kept current option! Returning to list of reaction proposals..."
                        else:
                            title = "Successfully kept current option! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)
                    else:
                        t = (1, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET Anywhere = ? WHERE CustomReactionID = ?',
                            t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = "Option successfully modified! Returning to list of current reaction proposals..."
                        else:
                            title = "Option successfully modified! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)
                elif reaction.emoji == "⏹":
                    await leave(message)
                    return

            if reaction.emoji == "5️⃣":
                embed = discord.Embed(title="Loading...")
                await message.edit(embed=embed)
                if proposals:
                    title = "Modify a custom reaction proposal. React with the option you want"
                    footer = "{} is currently modifying a custom reaction proposal. \n".format(
                        user)
                else:
                    title = "Modify a custom reaction. React with the option you want"
                    footer = "{} is currently modifying a custom reaction. \n".format(
                        user)
                description = "Should the reaction be sent in the DMs of the user who called the reaction " \
                              "instead of the channel?\n" \
                              "0️⃣ No\n" \
                              "1️⃣ Yes"
                embed = discord.Embed(title=title, description=description)
                embed.set_footer(text=footer, icon_url=user.avatar_url)
                current_options.clear()
                await message.clear_reactions()
                current_options.extend(["0️⃣", "1️⃣", "⏹"])
                await message.add_reaction("0️⃣")
                await message.add_reaction("1️⃣")
                await message.add_reaction("⏹")
                await message.edit(embed=embed)
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
                        title = 'The modification of the custom reaction proposal timed out. ' \
                                'Returning to list of reaction proposals...'
                    else:
                        title = 'The modification of the custom reaction timed out. ' \
                                'Returning to list of current reactions...'
                    embed = discord.Embed(title=title)
                    await message.edit(embed=embed)
                    conn.close()
                    time.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()
                if reaction is None:
                    return
                elif reaction.emoji == "0️⃣":
                    if dm == 0:
                        if proposals:
                            title = "Successfully kept current option! Returning to list of reaction proposals..."
                        else:
                            title = "Successfully kept current option! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)
                    else:
                        t = (0, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET DM = ? WHERE CustomReactionID = ?',
                            t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = "Option successfully modified! Returning to list of current reaction proposals..."
                        else:
                            title = "Option successfully modified! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)

                elif reaction.emoji == "1️⃣":
                    if dm == 1:
                        if proposals:
                            title = "Successfully kept current option! Returning to list of reaction proposals..."
                        else:
                            title = "Successfully kept current option! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)
                    else:
                        t = (1, custom_react_id)
                        c.execute(
                            'UPDATE CustomReactions SET DM = ? WHERE CustomReactionID = ?',
                            t)
                        conn.commit()
                        self.rebuild_lists()
                        if proposals:
                            title = "Option successfully modified! Returning to list of current reaction proposals..."
                        else:
                            title = "Option successfully modified! Returning to list of current reactions..."
                        embed = discord.Embed(title=title)
                        embed.set_footer(text="Modified by {}.".format(user),
                                         icon_url=user.avatar_url)
                        await message.edit(embed=embed)
                        conn.close()
                        time.sleep(5)
                elif reaction.emoji == "⏹":
                    await leave(message)
                    return

            if reaction.emoji == "✅":
                t = (0, custom_react_id)
                c.execute(
                    'UPDATE CustomReactions SET Proposal = ? WHERE CustomReactionID = ?',
                    t)
                conn.commit()
                self.rebuild_lists()
                title = "Custom reaction proposal successfully approved! " \
                        "Returning to list of current reaction proposals..."
                footer = "Aproved by {}.".format(user)
                embed = discord.Embed(title=title)
                embed.set_footer(text=footer, icon_url=user.avatar_url)
                await message.edit(embed=embed)
                conn.close()
                time.sleep(5)

            if reaction.emoji == "🚮" or reaction.emoji == "❌":
                t = (custom_react_id, )
                c.execute(
                    'DELETE FROM CustomReactions WHERE CustomReactionID = ?',
                    t)
                conn.commit()
                if proposals:
                    title = "Custom reaction proposal successfully rejected! " \
                            "Returning to list of current reaction proposals..."
                    footer = "Rejected by {}.".format(user)
                else:
                    title = "Custom reaction successfully deleted! Returning to list of current reactions..."
                    footer = "Deleted by {}.".format(user)
                embed = discord.Embed(title=title)
                embed.set_footer(text=footer, icon_url=user.avatar_url)
                await message.edit(embed=embed)
                conn.close()
                self.rebuild_lists()
                time.sleep(5)

            if reaction.emoji == "⏹":
                await leave(message)
                return

        async def leave(message):
            await message.delete()

        initial_message = await ctx.send(embed=discord.Embed(
            title="Loading..."))
        is_moderator = (discord.utils.get(
            ctx.author.roles, name=self.bot.config.moderator_role) is not None)
        await create_assistant(initial_message, is_moderator)


def setup(bot):
    bot.add_cog(Customreactions(bot))
