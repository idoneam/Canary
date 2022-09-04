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

from discord.ext import commands

from ..bot import Canary
from .base_cog import CanaryCog
from .utils.paginator import Pages
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

NUMBERS = (EMOJI["zero"], EMOJI["one"], EMOJI["two"], EMOJI["three"], EMOJI["four"], EMOJI["five"])

CUSTOM_REACTION_TIMEOUT = "Custom Reaction timed out. You may want to run the command again."
STOP_TEXT = "stop"
LOADING_EMBED = discord.Embed(title="Loading...")


class CustomReactions(CanaryCog):
    # Written by @le-potate
    def __init__(self, bot: Canary):
        super().__init__(bot)

        self.reaction_list: list[tuple] = []
        self.proposal_list: list[tuple] = []
        self.p_strings: PStringEncodings | None = None

    @CanaryCog.listener()
    async def on_ready(self):
        await super().on_ready()
        await self.rebuild_lists()

    async def rebuild_lists(self):
        await self.rebuild_reaction_list()
        await self.rebuild_proposal_list()

    async def rebuild_reaction_list(self):
        self.reaction_list = await self.fetch_list("SELECT * FROM CustomReactions WHERE Proposal = 0")

        prompts = [row[1].lower() for row in self.reaction_list]
        responses = [row[2] for row in self.reaction_list]
        anywhere_values = [row[5] for row in self.reaction_list]
        additional_info_list = [(row[4], row[6]) for row in self.reaction_list]
        self.p_strings = PStringEncodings(
            prompts, responses, anywhere_values, additional_info_list=additional_info_list
        )

    async def rebuild_proposal_list(self):
        self.proposal_list = await self.fetch_list("SELECT * FROM CustomReactions WHERE Proposal = 1")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if self.p_strings is None:
            return

        response = self.p_strings.parser(
            message.content.lower(), user=message.author.mention, channel=str(message.channel)
        )
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
    @commands.command(aliases=["customreaction", "customreacts", "customreact"])
    async def customreactions(self, ctx: commands.Context):
        current_options = []
        main_user = ctx.message.author
        await ctx.message.delete()

        def get_number_of_proposals():
            return len(self.proposal_list)

        def get_reaction_check(moderators=False, reaction_user=None):
            def reaction_check(reaction, user):
                return all(
                    (
                        reaction.emoji in current_options,
                        reaction.message.id == initial_message.id,
                        not moderators or discord.utils.get(user.roles, name=self.bot.config.moderator_role),
                        not reaction_user or user == reaction_user,
                    )
                )

            return reaction_check

        def get_msg_check(msg_user=None):
            def msg_check(msg):
                if all((not msg_user or msg.author == msg_user, msg.channel == ctx.channel)):
                    if msg.attachments:
                        # in python 3.7, rewrite as
                        # asyncio.create_task(ctx.send([...]))
                        # (the get_event_loop() part isn't necessary)
                        loop = asyncio.get_event_loop()
                        loop.create_task(ctx.send("Attachments cannot be used, but you may use URLs"))
                    else:
                        return True

            return msg_check

        def get_number_check(msg_user=None, number_range=None):
            def number_check(msg):
                if msg.content.isdigit():
                    return all(
                        (
                            not msg_user or msg.author == msg_user,
                            not number_range or int(msg.content) in number_range,
                            msg.channel == ctx.channel,
                        )
                    )

            return number_check

        async def wait_for_reaction(message: discord.Message):
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=get_reaction_check(reaction_user=main_user), timeout=60
                )
            except asyncio.TimeoutError:
                await message.clear_reactions()
                await message.edit(embed=discord.Embed(title=CUSTOM_REACTION_TIMEOUT), delete_after=60)
                return
            return reaction, user

        async def wait_for_message(message: discord.Message):
            try:
                msg = await self.bot.wait_for("message", check=get_msg_check(msg_user=main_user), timeout=60)
            except asyncio.TimeoutError:
                await message.clear_reactions()
                await message.edit(embed=discord.Embed(title=CUSTOM_REACTION_TIMEOUT), delete_after=60)
                return
            content = msg.content
            await msg.delete()
            return content

        async def clear_options(message: discord.Message):
            current_options.clear()
            await message.clear_reactions()

        async def add_multiple_reactions(message: discord.Message, reactions):
            for reaction in reactions:
                await message.add_reaction(reaction)

        async def add_yes_or_no_reactions(message: discord.Message):
            await add_multiple_reactions(message, (EMOJI["zero"], EMOJI["one"], EMOJI["stop_button"]))

        async def add_control_reactions(message: discord.Message):
            await add_multiple_reactions(
                message,
                (
                    EMOJI["rewind"],
                    EMOJI["arrow_backward"],
                    EMOJI["arrow_forward"],
                    EMOJI["fast_forward"],
                    EMOJI["stop_button"],
                    EMOJI["ok"],
                ),
            )

        async def create_assistant(message: discord.Message, is_moderator: bool) -> bool | None:
            actions = {
                # Add/Propose a new custom reaction
                EMOJI["new"]: {
                    "fn": add_custom_react,
                    "desc": f"{'Add' if is_moderator else 'Propose'} a new custom reaction",
                    "kwargs": dict(proposals=not is_moderator),
                },
                # List custom reactions
                EMOJI["mag"]: {
                    "fn": list_custom_reacts,
                    "desc": "See the list of current reactions" + (" and modify them" if is_moderator else ""),
                    "kwargs": dict(proposals=False),
                },
                # List proposals
                EMOJI["pencil"]: {
                    "fn": list_custom_reacts,
                    "desc": f"See the list of proposed reactions ({get_number_of_proposals()})" + (
                        " and approve or reject them" if is_moderator else ""),
                    "kwargs": dict(proposals=True),
                },
                # List placeholders
                EMOJI["grey_question"]: {
                    "fn": list_placeholders,
                    "desc": "List of placeholders",
                    "kwargs": dict(),
                },
                # Stop
                EMOJI["stop_button"]: {
                    "fn": leave,
                    "desc": "",
                    "kwargs": dict(),
                    "hidden": True,
                },
            }

            description = "\n".join(f"{k} {v['desc']}" for k, v in actions.items() if not v.get("hidden"))

            action_keys = tuple(actions.keys())

            current_options.extend(action_keys)
            await add_multiple_reactions(message, action_keys)

            await message.edit(
                embed=discord.Embed(title="Custom Reactions", description=description).set_footer(
                    text=f"{main_user}: Click on an emoji to choose an "
                    f"option (If a list is chosen, all users "
                    f"will be able to interact with it)",
                    icon_url=main_user.avatar_url,
                )
            )

            try:
                reaction, user = await wait_for_reaction(message)
            except TypeError:
                return

            await clear_options(message)

            if (action := actions.get(reaction.emoji)) is not None:
                return await action["fn"](message, **action["kwargs"])

        async def add_custom_react(message: discord.Message, proposals: bool):
            status_msg = f"{main_user} is currently {'proposing' if proposals else 'adding'} a custom reaction."

            title = f"{'Propose' if proposals else 'Add'} a custom reaction"
            footer = f"{status_msg}\nWrite '{STOP_TEXT}' to cancel."
            description = "Write the prompt the bot will react to"

            async def _refresh_msg():
                await message.edit(
                    embed=discord.Embed(title=title, description=description).set_footer(
                        text=footer, icon_url=main_user.avatar_url
                    )
                )

            await _refresh_msg()

            prompt_message = await wait_for_message(message)

            if prompt_message is None:
                return

            if prompt_message.lower() == STOP_TEXT:
                await leave(message)
                return True

            description = f"Prompt: {prompt_message}\nWrite the response the bot will send"
            await _refresh_msg()

            response = await wait_for_message(message)

            if response is None:
                return

            if response.lower() == STOP_TEXT:
                await leave(message)
                return True

            await message.edit(embed=LOADING_EMBED)

            description = (
                f"Prompt: {prompt_message}\nResponse: {response}\n"
                f"React with the options you want and click {EMOJI['ok']} when you are ready\n"
                f"{EMOJI['one']} Delete the message that calls the reaction\n"
                f"{EMOJI['two']} Activate the custom reaction if the prompt is anywhere in a message \n"
                f"{EMOJI['three']} React in the DMs of the user who calls the reaction instead of the channel\n"
            )

            footer = f"{main_user} is currently {'proposing' if proposals else 'adding'} a custom reaction."

            current_options.extend((EMOJI["ok"], EMOJI["stop_button"]))
            await add_multiple_reactions(message, (*NUMBERS[1:4], EMOJI["ok"], EMOJI["stop_button"]))
            await _refresh_msg()

            try:
                reaction, user = await wait_for_reaction(message)
            except TypeError:
                return

            # If the user clicked OK, check if delete/anywhere/dm are checked
            if reaction.emoji == EMOJI["ok"]:
                delete = False
                anywhere = False
                dm = False
                cache_msg = await message.channel.fetch_message(message.id)
                for reaction in cache_msg.reactions:
                    users_who_reacted = await reaction.users().flatten()
                    if main_user in users_who_reacted:
                        delete = delete or reaction.emoji == EMOJI["one"]
                        anywhere = anywhere or reaction.emoji == EMOJI["two"]
                        dm = dm or reaction.emoji == EMOJI["three"]

                current_options.clear()
                await message.clear_reactions()

                db: aiosqlite.Connection
                async with self.db() as db:
                    await db.execute(
                        "INSERT INTO CustomReactions(Prompt, Response, UserID, DeletePrompt, Anywhere, DM, Proposal) "
                        "VALUES(?, ?, ?, ?, ?, ?, ?)",
                        (prompt_message, response, main_user.id, delete, anywhere, dm, proposals),
                    )
                    await db.commit()

                await self.rebuild_lists()

                if proposals:
                    title = "Custom reaction proposal successfully submitted!"
                else:
                    title = "Custom reaction successfully added!"
                description = f"-Prompt: {prompt_message}\n-Response: {response}"
                if delete:
                    description = f"{description}\n-Will delete the message that calls the reaction"
                if anywhere:
                    description = (
                        f"{description}\n-Will activate the custom reaction if the prompt is anywhere in a message"
                    )
                if dm:
                    description = (
                        f"{description}\n"
                        f"-Will react in the DMs of the user who calls the reaction instead of the channel"
                    )

                await _refresh_msg()

                return

            # Stop
            if reaction.emoji == EMOJI["stop_button"]:
                return await leave(message)

        async def list_custom_reacts(message: discord.Message, proposals: bool) -> bool | None:
            current_list = self.proposal_list if proposals else self.reaction_list

            no_items_msg = f"There are currently no custom reaction{' proposal' if proposals else ''}s in this server"

            if not current_list:
                title = no_items_msg
                await message.edit(embed=discord.Embed(title=title), delete_after=60)
                return

            reaction_dict = {
                "names": [f"[{i + 1}]" for i in range(len(current_list))],
                "values": [
                    f"Prompt: {reaction[1][:min(len(reaction[1]), 287)]}"
                    f'{"..." if len(reaction[1]) > 287 else ""}\n'
                    f"Response: {reaction[2][:min(len(reaction[2]), 287)]}"
                    f'{"..." if len(reaction[2]) > 287 else ""}'
                    for reaction in current_list
                ],
            }

            await message.edit(embed=LOADING_EMBED)

            await add_control_reactions(message)

            if proposals:
                title = (
                    f"Current custom reaction proposals\n"
                    f"Click on {EMOJI['ok']} to approve, reject, edit, or see more information on one of them"
                )
            else:
                title = (
                    f"Current custom reactions\n"
                    f"Click on {EMOJI['ok']} to edit or see more information on one of them"
                )

            p = Pages(
                ctx,
                msg=message,
                item_list=reaction_dict,
                title=title,
                display_option=(2, 10),
                editable_content_emoji=EMOJI["ok"],
                return_user_on_edit=True,
            )

            user_modifying = await p.paginate()
            while p.edit_mode:
                await message.clear_reactions()
                if proposals:
                    title = (
                        f"Current custom reaction proposals\n"
                        f"{user_modifying}: Write the number of the custom reaction proposal you want to "
                        f"approve, reject, edit, or see more information on"
                    )
                else:
                    title = (
                        f"Current custom reactions\n"
                        f"{user_modifying}: Write the number of the custom reaction you want to edit or see more "
                        f"information on"
                    )
                message.embeds[0].title = title
                await message.edit(embed=message.embeds[0])
                number = 0
                try:
                    msg = await self.bot.wait_for(
                        "message",
                        check=get_number_check(msg_user=user_modifying, number_range=range(1, len(current_list) + 1)),
                        timeout=60,
                    )
                    number = int(msg.content)
                    await msg.delete()
                except asyncio.TimeoutError:
                    pass

                if number == 0:
                    if proposals:
                        title = (
                            f"Current custom reaction proposals\n"
                            f"Click on {EMOJI['ok']} to approve, reject, edit, or see more information on one of them "
                            f"(Previous attempt received invalid input or timed out)"
                        )
                    else:
                        title = (
                            f"Current custom reactions\n"
                            f"Click on {EMOJI['ok']} to edit or see more information on one of "
                            f"them (Previous attempt received invalid input or timed out)"
                        )
                    p = Pages(
                        ctx,
                        msg=message,
                        item_list=reaction_dict,
                        title=title,
                        display_option=(2, 10),
                        editable_content_emoji=EMOJI["ok"],
                        return_user_on_edit=True,
                    )

                else:
                    if left := await information_on_react(message, current_list, number, proposals):
                        return left

                    if proposals:
                        title = (
                            f"Current custom reaction proposals\n"
                            f"Click on {EMOJI['ok']} to approve, reject, edit, or see more information on one of them"
                        )
                    else:
                        title = (
                            f"Current custom reactions\n"
                            f"Click on {EMOJI['ok']} to edit or see more information on one of them"
                        )

                    # update dictionary since a custom reaction might have been
                    # modified
                    current_list = self.proposal_list if proposals else self.reaction_list

                    if not current_list:
                        title = no_items_msg
                        await message.edit(embed=discord.Embed(title=title), delete_after=60)
                        return

                    reaction_dict = {
                        "names": [f"[{i + 1}]" for i in range(len(current_list))],
                        "values": [
                            f"Prompt: {reaction[1][:min(len(reaction[1]), 287)]}"
                            f'{"..." if len(reaction[1]) > 287 else ""}'
                            f"\nResponse: {reaction[2][:min(len(reaction[2]), 287)]}"
                            f'{"..." if len(reaction[2]) > 287 else ""}'
                            for reaction in current_list
                        ],
                    }

                    p = Pages(
                        ctx,
                        msg=message,
                        item_list=reaction_dict,
                        title=title,
                        display_option=(2, 10),
                        editable_content_emoji=EMOJI["ok"],
                        return_user_on_edit=True,
                    )

                await message.edit(embed=LOADING_EMBED)
                await add_control_reactions(message)
                user_modifying = await p.paginate()

        async def information_on_react(message: discord.Message, current_list, number, proposals) -> bool | None:
            await message.edit(embed=LOADING_EMBED)

            custom_react = current_list[number - 1]
            prompt = custom_react[1]
            response = custom_react[2]
            user_who_added = self.bot.get_user(custom_react[3])
            delete = custom_react[4]
            anywhere = custom_react[5]
            dm = custom_react[6]

            delete_str = f"{'Deletes' if delete == 1 else 'Does not delete'} the message that calls the reaction"

            if anywhere == 1:
                anywhere_str = "Activates the custom reaction if the prompt is anywhere in a message"
            else:
                anywhere_str = "Only activates the custom reaction if the prompt is the full message"

            if dm == 1:
                dm_str = "Reacts in the DMs of the user who calls the reaction instead of the channel"
            else:
                dm_str = "Reacts directly into the channel"

            base_desc = (
                f"{EMOJI['one']} Prompt: {prompt}\n"
                f"{EMOJI['two']} Response: {response}\n"
                f"{EMOJI['three']} {delete_str}\n"
                f"{EMOJI['four']} {anywhere_str}\n"
                f"{EMOJI['five']} {dm_str}\n"
            )

            if proposals:
                description = (
                    f"{base_desc}\n"
                    f"{EMOJI['white_check_mark']} Approve this proposal\n"
                    f"{EMOJI['x']} Reject this proposal\n"
                    f"Added by {user_who_added}"
                )
                title = (
                    f"More information on a custom reaction proposal.\n"
                    f"{self.bot.config.moderator_role}s "
                    f"may click on emojis to modify those values or "
                    f"approve/refuse this proposal\n"
                    f"(Will return to the list of current reaction "
                    f"proposals in 40 seconds otherwise)"
                )
            else:
                description = (
                    f"{base_desc}\n"
                    f"{EMOJI['put_litter_in_its_place']} Delete this custom reaction\n"
                    f"Added by {user_who_added}"
                )
                title = (
                    f"More information on a custom reaction.\n"
                    f"{self.bot.config.moderator_role}s may click "
                    f"on emojis to modify those values "
                    f"or select an option\n(Will return to the list of "
                    f"current reactions in 40 seconds otherwise)"
                )

            await clear_options(message)
            if proposals:
                current_options.extend((*NUMBERS[1:6], EMOJI["white_check_mark"], EMOJI["x"], EMOJI["stop_button"]))
            else:
                current_options.extend((*NUMBERS[1:6], EMOJI["put_litter_in_its_place"], EMOJI["stop_button"]))
            if proposals:
                await add_multiple_reactions(
                    message, (*NUMBERS[1:6], EMOJI["white_check_mark"], EMOJI["x"], EMOJI["stop_button"])
                )
            else:
                await add_multiple_reactions(
                    message, (*NUMBERS[1:6], EMOJI["put_litter_in_its_place"], EMOJI["stop_button"])
                )
            await message.edit(embed=discord.Embed(title=title, description=description))

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=get_reaction_check(moderators=True), timeout=40
                )
                if left := await edit_custom_react(message, reaction, user, custom_react, proposals):
                    return left
            except asyncio.TimeoutError:
                pass

            await clear_options(message)

        async def edit_custom_react(
            message: discord.Message,
            reaction: discord.Reaction,
            user,
            custom_react,
            proposals,
        ) -> bool | None:
            db: aiosqlite.Connection

            await clear_options(message)

            custom_react_id = custom_react[0]
            delete = custom_react[4]
            anywhere = custom_react[5]
            dm = custom_react[6]

            noun = f"reaction{' proposal' if proposals else ''}"
            noun_custom = f"custom {noun}"

            message_kept = f"Successfully kept current option! Returning to list of {noun}s..."
            message_modified = f"Option successfully modified! Returning to list of {noun}s..."
            message_time_out = f"The modification of the {noun_custom} timed out. Returning to list of {noun}s..."

            footer_modifying_stop = f"{user} is currently modifying a {noun_custom}. \nWrite '{STOP_TEXT}' to cancel."
            footer_modified = f"Modified by {user}."

            async def _edit_reaction_and_rebuild(react_id, key, value):
                db_: aiosqlite.Connection
                async with self.db() as db_:
                    await db_.execute(
                        f"UPDATE CustomReactions SET {key} = ? WHERE CustomReactionID = ?", (value, react_id)
                    )
                    await db_.commit()
                await self.rebuild_lists()

            # Edit the prompt
            if reaction.emoji == EMOJI["one"]:
                await message.edit(
                    embed=(
                        discord.Embed(
                            title=f"Modify a {noun_custom}", description="Please enter the new prompt"
                        ).set_footer(text=footer_modifying_stop, icon_url=user.avatar_url)
                    )
                )

                try:
                    msg = await self.bot.wait_for("message", check=get_msg_check(msg_user=user), timeout=60)
                except asyncio.TimeoutError:
                    await message.edit(embed=discord.Embed(title=message_time_out))
                    await asyncio.sleep(5)
                    return

                prompt = msg.content
                await msg.delete()

                if prompt.lower() == STOP_TEXT:
                    return await leave(message)

                await _edit_reaction_and_rebuild(custom_react_id, "Prompt", prompt)

                await message.edit(
                    embed=discord.Embed(
                        title=f"Prompt successfully modified! Returning to list of {noun}s..."
                    ).set_footer(text=footer_modified, icon_url=user.avatar_url)
                )
                await asyncio.sleep(5)

            # Edit the response
            if reaction.emoji == EMOJI["two"]:
                await message.edit(
                    embed=discord.Embed(
                        title=f"Modify a {noun_custom}", description="Please enter the new response"
                    ).set_footer(text=footer_modifying_stop, icon_url=user.avatar_url)
                )

                try:
                    msg = await self.bot.wait_for("message", check=get_msg_check(msg_user=user), timeout=60)
                except asyncio.TimeoutError:
                    await message.edit(embed=discord.Embed(title=message_time_out))
                    await asyncio.sleep(5)
                    return

                response = msg.content
                await msg.delete()

                if response.lower() == STOP_TEXT:
                    return await leave(message)

                await _edit_reaction_and_rebuild(custom_react_id, "Response", response)

                title = f"Response successfully modified! Returning to list of {noun}s..."
                await message.edit(
                    embed=discord.Embed(title=title).set_footer(text=footer_modified, icon_url=user.avatar_url)
                )
                await asyncio.sleep(5)

            # Edit the "delete" option
            if reaction.emoji == EMOJI["three"]:
                await message.edit(embed=LOADING_EMBED)
                description = (
                    f"Should the message that calls the reaction be deleted?\n"
                    f"{EMOJI['zero']} No\n"
                    f"{EMOJI['one']} Yes"
                )
                current_options.clear()
                await message.clear_reactions()
                current_options.extend((*NUMBERS[0:2], EMOJI["stop_button"]))
                await add_yes_or_no_reactions(message)
                await message.edit(
                    embed=(
                        discord.Embed(
                            title=f"Modify a {noun_custom}. React with the option you want",
                            description=description,
                        ).set_footer(
                            text=f"{user} is currently modifying a {noun_custom}. \n",
                            icon_url=user.avatar_url,
                        )
                    )
                )

                try:
                    reaction, reaction_user = await self.bot.wait_for(
                        "reaction_add", check=get_reaction_check(reaction_user=user), timeout=60
                    )
                except asyncio.TimeoutError:
                    await message.edit(embed=discord.Embed(title=message_time_out))
                    await asyncio.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()

                if reaction.emoji == EMOJI["stop_button"]:
                    return await leave(message)

                if reaction.emoji in (EMOJI["zero"], EMOJI["one"]):
                    # 0: Deactivate the "delete" option
                    # 1: Activate the "delete" option
                    new_value = int(reaction.emoji == EMOJI["one"])  # 1 if one, 0 if zero; simple as that

                    if delete == new_value:
                        title = message_kept
                    else:
                        title = message_modified
                        await _edit_reaction_and_rebuild(custom_react_id, "DeletePrompt", new_value)

                    await message.edit(
                        embed=discord.Embed(title=title).set_footer(text=footer_modified, icon_url=user.avatar_url)
                    )

                    await asyncio.sleep(5)

            # Edit the "anywhere" option
            if reaction.emoji == EMOJI["four"]:
                await message.edit(embed=LOADING_EMBED)
                title = f"Modify a {noun_custom}. React with the option you want"
                footer = f"{user} is currently modifying a {noun_custom}. \n"
                description = (
                    f"Should the custom reaction be activated if the prompt is anywhere in a message?\n"
                    f"{EMOJI['zero']} No\n"
                    f"{EMOJI['one']} Yes"
                )
                current_options.clear()
                await message.clear_reactions()
                current_options.extend((*NUMBERS[0:2], EMOJI["stop_button"]))
                await add_yes_or_no_reactions(message)
                await message.edit(
                    embed=discord.Embed(title=title, description=description).set_footer(
                        text=footer, icon_url=user.avatar_url
                    )
                )
                try:
                    reaction, reaction_user = await self.bot.wait_for(
                        "reaction_add", check=get_reaction_check(reaction_user=user), timeout=60
                    )

                except asyncio.TimeoutError:
                    title = f"The modification of the {noun_custom} timed out. Returning to list of {noun}s..."
                    await message.edit(embed=discord.Embed(title=title))
                    await asyncio.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()

                if reaction.emoji == EMOJI["stop_button"]:
                    return await leave(message)

                if reaction.emoji in (EMOJI["zero"], EMOJI["one"]):
                    # 0: Deactivate the "anywhere" option
                    # 1: Activate the "anywhere" option
                    new_value = int(reaction.emoji == EMOJI["one"])  # 1 if one, 0 if zero; simple as that

                    if anywhere == new_value:
                        title = message_kept
                    else:
                        title = message_modified
                        await _edit_reaction_and_rebuild(custom_react_id, "Anywhere", new_value)

                    await message.edit(
                        embed=discord.Embed(title=title).set_footer(text=footer_modified, icon_url=user.avatar_url)
                    )

                    await asyncio.sleep(5)

            # Edit "dm" option
            if reaction.emoji == EMOJI["five"]:
                await message.edit(embed=LOADING_EMBED)
                title = f"Modify a {noun_custom}. React with the option you want"
                footer = f"{user} is currently modifying a {noun_custom}. \n"
                description = (
                    f"Should the reaction be sent in the DMs of the user who called the reaction "
                    f"instead of the channel?\n"
                    f"{EMOJI['zero']} No\n"
                    f"{EMOJI['one']} Yes"
                )
                current_options.clear()
                await message.clear_reactions()
                current_options.extend((*NUMBERS[0:2], EMOJI["stop_button"]))
                await add_yes_or_no_reactions(message)
                await message.edit(
                    embed=(
                        discord.Embed(title=title, description=description).set_footer(
                            text=footer, icon_url=user.avatar_url
                        )
                    )
                )
                try:
                    reaction, reaction_user = await self.bot.wait_for(
                        "reaction_add", check=get_reaction_check(reaction_user=user), timeout=60
                    )

                except asyncio.TimeoutError:
                    title = f"The modification of the {noun_custom} timed out. Returning to list of {noun}s..."
                    await message.edit(embed=discord.Embed(title=title))
                    await asyncio.sleep(5)
                    current_options.clear()
                    await message.clear_reactions()
                    return

                current_options.clear()
                await message.clear_reactions()

                if reaction.emoji == EMOJI["stop_button"]:
                    return await leave(message)

                if reaction.emoji in (EMOJI["zero"], EMOJI["one"]):
                    # 0: Deactivate the "dm" option
                    # 1: Activate the "dm" option
                    new_value = int(reaction.emoji == EMOJI["one"])  # 1 if one, 0 if zero; simple as that

                    if dm == new_value:
                        title = message_kept
                    else:
                        title = message_modified
                        await _edit_reaction_and_rebuild(custom_react_id, "DM", new_value)

                    await message.edit(
                        embed=discord.Embed(title=title).set_footer(text=footer_modified, icon_url=user.avatar_url)
                    )

                    await asyncio.sleep(5)

            # Approve a custom reaction proposal
            if reaction.emoji == EMOJI["white_check_mark"]:
                await _edit_reaction_and_rebuild(custom_react_id, "Proposal", 0)

                await message.edit(
                    embed=discord.Embed(
                        title=(
                            "Custom reaction proposal successfully approved! "
                            "Returning to list of current reaction proposals..."
                        )
                    ).set_footer(text=f"Approved by {user}.", icon_url=user.avatar_url)
                )

                await asyncio.sleep(5)

            # Delete a custom reaction or proposal
            if reaction.emoji == EMOJI["put_litter_in_its_place"] or reaction.emoji == EMOJI["x"]:
                async with self.db() as db:
                    await db.execute("DELETE FROM CustomReactions WHERE CustomReactionID = ?", (custom_react_id,))
                    await db.commit()
                title = f"Custom {noun} successfully rejected! Returning to list of {noun}s..."
                footer = f"{'Rejected' if proposals else 'Deleted'} by {user}."
                await message.edit(embed=discord.Embed(title=title).set_footer(text=footer, icon_url=user.avatar_url))
                await self.rebuild_lists()
                await asyncio.sleep(5)

            # Stop
            if reaction.emoji == EMOJI["stop_button"]:
                return await leave(message)

        async def list_placeholders(message, **_kwargs):
            title = "The following placeholders can be used in prompts and responses:"
            description = (
                "-%user%: the user who called the prompt (can only be used in a response)\n"
                "-%channel%: the name of the channel where the prompt was called (can only be used in a response) \n"
                "-%1%, %2%, etc. up to %9%: Groups. When a prompt uses this, anything will match. For "
                'example, the prompt "i %1% apples" will work for any message that starts with "i" and ends '
                'with "apples", such as "i really like apples". Then, the words that match to this '
                "group can be used in the response. For example, keeping the same prompt and using the response "
                '"i %1% pears" will send "i really like pears"\n'
                "-%[]%: a comma-separated choice list. There are two uses for this. The first is that when it is "
                "used in a prompt, the prompt will accept either of the choices. For example, the prompt "
                '"%[hello, hi, hey]% world" will work if someone writes "hello world", "hi world" or '
                '"hey world". The second use is that when it is '
                "used in a response, a random choice will be chosen from the list. For example, the response "
                '"i %[like, hate]% you" will either send "i like you" or "i hate you". All placeholders '
                "can be used in choice lists (including choice lists themselves). If a choice contains commas, "
                'it can be surrounded by "" to not be split into different choices'
            )
            await message.edit(embed=discord.Embed(title=title, description=description))

        async def leave(message, **_kwargs) -> True:
            await message.delete()
            return True

        initial_message = await ctx.send(embed=LOADING_EMBED)
        is_mod = discord.utils.get(main_user.roles, name=self.bot.config.moderator_role) is not None

        return await create_assistant(initial_message, is_mod)


def setup(bot):
    bot.add_cog(CustomReactions(bot))
