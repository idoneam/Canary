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
from collections import OrderedDict

import discord
from discord.ext import commands

# Other utilities
import random
import sqlite3

from .utils.assistant_helper import AssistantHelper
from .utils.emojis import EMOJI, NUMBERS

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
        conn = self.get_conn()
        try:
            c = conn.cursor()
            c.execute('SELECT * FROM CustomReactions WHERE Proposal = 0')
            self.reaction_list = c.fetchall()
            # get list of the Prompt column only
            self.reaction_list_prompts = [row[1] for row in self.reaction_list]
        finally:
            conn.close()

    def get_conn(self):
        return sqlite3.connect(self.bot.config.db_path)

    def rebuild_proposal_list(self):
        conn = self.get_conn()
        try:
            c = conn.cursor()
            c.execute('SELECT * FROM CustomReactions WHERE Proposal = 1')
            self.proposal_list = c.fetchall()
        finally:
            conn.close()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if any(s.lower() in message.content.lower()
               for s in self.reaction_list_prompts):
            # get indices of every prompt that contains the message.
            # Done this way to not compute it every time a message is sent
            indices = (
                i for i, x in enumerate(self.reaction_list_prompts)
                if x.lower() in message.content.lower()
            )
            # only keep the ones that are exactly the message, or that are
            # contained in the message AND have the anywhere option activated
            reactions_at_indices = (self.reaction_list[i] for i in indices)
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
            ch = message.author if reaction[6] == 1 else message.channel
            await ch.send(reaction[2])

    @commands.command(aliases=[
        "customreactions",
        "customreaction",
        "customreacts",
        "customreact"
    ])
    async def custom_reactions(self, ctx):
        author = ctx.message.author
        await ctx.message.delete()

        def get_number_of_proposals():
            return len(self.proposal_list)

        async def create_assistant(is_mod):
            assistant = await AssistantHelper(
                ctx,
                page_display=(2, 10),
                page_editable_content_emoji=EMOJI["ok"],
                page_return_user_on_edit=True,
            ).initialize()

            return await assistant.menu(
                title="Custom Reactions",
                footer={
                    "text": (
                        f"{author}: Click on an emoji to choose an "
                        f"option (If a list is chosen, all users "
                        f"will be able to interact with it)"
                    ),
                    "icon_url": author.avatar_url
                },
                menu_options=OrderedDict((
                    (EMOJI["new"], {
                        "text": f"{'Add' if is_mod else 'Propose'} a new "
                                f"custom reaction",
                        "callback": lambda a, _u: add_custom_react(a, is_mod)
                    }),
                    (EMOJI["mag"], {
                        "text": f"See the list of current reactions"
                                f"{' and modify them' if is_mod else ''}",
                        "callback": lambda a, _u: list_custom_reacts(
                            a, proposals=False)
                    }),
                    (EMOJI["pencil"], {
                        "text": (
                            f"See the list of proposed reactions "
                            f"({get_number_of_proposals()})" +
                            (" and approve or reject them" if is_mod else "")),
                        "callback": lambda a, _u: list_custom_reacts(
                            a, proposals=True)
                    }),
                )),

                # TODO: Check if we need more wait_for_option settings here
                timeout_message=CUSTOM_REACTION_TIMEOUT,
                user=author
            )

        # TODO: Callback decorator
        async def add_custom_react(assistant: AssistantHelper, is_mod):
            footer_base = {"icon_url": author.avatar_url}

            prompt_message, stop = await assistant.text_prompt(
                # Prompt embed
                title=f"{'Add' if is_mod else 'Propose'} a custom reaction",
                prompt="Write the prompt the bot will react to",
                footer={
                    **footer_base,
                    "text": (f"{author} is currently "
                             f"{'adding' if is_mod else 'proposing'} a custom "
                             f"reaction. \nWrite '{STOP_TEXT}' to cancel."),
                },

                # Response processing
                timeout_message=CUSTOM_REACTION_TIMEOUT)

            if prompt_message is None or stop:
                return stop

            response, stop = await assistant.text_prompt(
                description=(f"Prompt: {prompt_message}\nWrite the response "
                             f"the bot will send"),
                timeout_message=CUSTOM_REACTION_TIMEOUT)

            if response is None or stop:
                return stop

            res, stop = await assistant.selector(
                title=None,  # TODO: What is title,
                preface=f"Prompt: {prompt_message}\nResponse: {response}",
                footer={
                    **footer_base,
                    "text": f"{author} is currently proposing a custom "
                            f"reaction."
                },
                select_options=OrderedDict((
                    (NUMBERS[1], "Delete the message that calls the reaction"),
                    (NUMBERS[2], "Activate the custom reaction if the prompt "
                                 "is anywhere in a message"),
                    (NUMBERS[3], "React in the DMs of the user who calls the "
                                 "reaction instead of the channel"),
                )),
                multi=True,
                timeout_message=CUSTOM_REACTION_TIMEOUT,
                user=author
            )

            if res is None or stop:
                return stop

            delete = author in res.get(EMOJI["one"], [])
            anywhere = author in res.get(EMOJI["two"], [])
            dm = author in res.get(EMOJI["three"], [])

            add_custom_reaction(
                prompt=prompt_message,
                response=response,
                delete=delete,
                anywhere=anywhere,
                dm=dm,
                is_moderator_=is_mod
            )

            return await assistant.set(
                title=(
                    "Custom reaction successfully added!" if is_mod
                    else "Custom reaction proposal successfully submitted!"),
                description=
                f"-Prompt: {prompt_message}\n-Response: {response}" +
                ("\n-Will delete the message that calls the reaction"
                 if delete else "") +
                ("\n-Will activate the custom reaction if the prompt is "
                 "anywhere in a message" if anywhere else "") +
                ("\n-Will react in the DMs of the user who calls the "
                 "reaction instead of the channel" if dm else ""),
                footer={**footer_base, "text": f"Added by {author}."}
            ).update()

        def _get_current_list(proposals):
            return self.proposal_list if proposals else self.reaction_list

        def _get_reaction_items(proposals):
            current_list = _get_current_list(proposals)
            return {
                "names": [f"[{i+1}]" for i in range(len(current_list))],
                "values": [
                    f'Prompt: {reaction[1]}\nResponse: {reaction[2]}'
                    for reaction in current_list
                ]
            }

        async def list_custom_reacts(assistant: AssistantHelper, proposals):
            async def _no_reactions(stop_loading: bool = False):
                return await assistant.clear_everything().set_title(
                    f"There are currently no custom reaction"
                    f"{' proposal' if proposals else ''}s "
                    "in this server"
                ).update(delete_after=60, loading_screen=stop_loading)

            def _get_reaction_list_view_mode_title(proposals_, timeout=False):
                return ((
                    f"Current custom reaction proposals\n"
                    f"Click on {EMOJI['ok']} "
                    f"to approve, reject, edit, or see more "
                    f"information on one of them"
                ) if proposals_ else (
                    f"Current custom reactions\nClick on {EMOJI['ok']} "
                    f"to edit or see more information on one of them"
                )) + timeout_message if timeout else ""

            def _get_reaction_list_edit_mode_title(proposals_, user_modifying_, timeout=False):
                return ((
                    f"Current custom reaction proposals\n"
                    f"{user_modifying_}: Write the number of the "
                    f"custom reaction "
                    f"proposal you want to approve, reject, edit, or "
                    f"see more information on"
                ) if proposals_ else (
                    f"Current custom reaction proposals\n"
                    f"{user_modifying_}: Write the number of the "
                    f"custom reaction "
                    f"proposal you want to approve, reject, edit, or "
                    f"see more information on"
                )) + timeout_message if timeout else ""

            timeout_message = " (Previous attempt received invalid input or timed out)"

            await assistant.start_loading()

            current_list = _get_current_list(proposals)
            if not current_list:
                return await _no_reactions(stop_loading=True)

            # TODO: Loading + control reactions formerly added here,
            #  with assistant we can't add pagination control reacts early yet

            reaction_dict = _get_reaction_items(proposals)

            await assistant.clear_everything().set(
                title=_get_reaction_list_view_mode_title(proposals),
                pages=reaction_dict
            ).update(loading_screen=True, force_pagination_update=True)

            user_modifying = await assistant.paginate()

            while assistant.pagination_edit_mode:
                # TODO: Remove pagination side effect stuff with option
                #  clearing - not very elegant
                await assistant.clear_options().set_title(
                    _get_reaction_list_edit_mode_title(
                        proposals, user_modifying, timeout=False)
                ).update()

                number = (await assistant.wait_for_pos_int_message(timeout_error=False)) or 0

                if number < 1 or number > len(current_list):
                    assistant.title = _get_reaction_list_view_mode_title(
                        proposals, timeout=True)
                else:
                    stop = await information_on_react(
                        assistant, current_list, number, proposals)
                    if stop:
                        return True

                    # update dictionary since a custom reaction might have been
                    # modified
                    current_list = _get_current_list(proposals)
                    if not current_list:
                        return await _no_reactions()

                    assistant.title = _get_reaction_list_view_mode_title(
                        proposals)
                    assistant.pages = _get_reaction_items(proposals)

                await assistant.update(loading_screen=True,
                                       force_pagination_update=True)

                user_modifying = await assistant.paginate()
                # TODO await add_control_reactions(message)

        async def information_on_react(assistant: AssistantHelper,
                                       current_list, number,
                                       proposals):

            await assistant.start_loading()

            custom_react = current_list[number - 1]
            custom_react_id = custom_react[0]
            prompt = custom_react[1]
            response = custom_react[2]
            user_who_added = self.bot.get_user(custom_react[3])
            delete = bool(custom_react[4])
            anywhere = bool(custom_react[5])
            dm = bool(custom_react[6])

            # ---------––------------------------------------------------------

            obj_term = f"reaction{' proposal' if proposals else ''}"
            modify_title = f"Modify a custom {obj_term}"

            def usr_footer(user_, text=None):
                return {"icon_url": user_.avatar_url,
                        **({"text": text} if text else {})}

            async def set_text_value(assistant_, user, reaction_id, question_prompt,
                                     flag, flag_txt=None):
                flag_txt = flag_txt or flag

                footer = usr_footer(user, (
                    f"{user} is currently modifying "
                    f"a custom {obj_term}."
                    f"Write '{AssistantHelper.STOP_TEXT}' to cancel."))

                res, stop_ = await assistant_.text_prompt(
                    # Prompt embed
                    title=modify_title,
                    prompt=question_prompt,
                    footer=footer,

                    # Message processing
                    user=user,
                    timeout_message=(f"The modification of the custom {obj_term} "
                                     f"timed out. Returning to list of current "
                                     f"reactions..."),
                    timeout_error_delete=None,
                    timeout_error_sleep=5,
                )

                if res is None or stop_:
                    return stop_

                set_reaction_key(reaction_id, flag, res)

                return await assistant_.clear_everything().set(
                    title=(
                        f"{flag_txt} successfully modified! Returning to "
                        f"list of " +
                        ("reaction proposals" if proposals
                         else "current reactions") + "..."),
                    footer=usr_footer(user, f"Modified by {user}.")
                ).update(sleep_after=5)

            async def toggle_flag(assistant_, user, reaction_id, question_prompt, flag,
                                  old_val) -> bool:
                footer = usr_footer(
                    user, f"{user} is currently modifying a custom {obj_term}.")

                res, __user, stop_ = await assistant_.yes_no_stop_prompt(
                    # Prompt embed
                    title=f"{modify_title}. React with the option you want",
                    prompt=question_prompt,
                    footer=footer,

                    # Reaction processing
                    user=user,
                    timeout_message=(f"The modification of the custom {obj_term} "
                                     f"timed out. Returning to list of custom "
                                     f"{obj_term}s..."),
                    timeout_error_delete=None,
                    timeout_error_sleep=5,
                )

                if res is None:
                    return stop_

                # Other current valid options are 0 or 1, the new delete values

                will_update = old_val == res

                if will_update:
                    set_reaction_key(reaction_id, flag, res)

                return await assistant_.clear_description().set(
                    title=(
                        (f"Successfully kept current option! "
                         f"Returning to list of custom {obj_term}...")
                        if will_update else (
                            "Option successfully modified! "
                            "Returning to list of current "
                            f"{obj_term}...")
                    ),
                    footer=usr_footer(user, f"Modified by {user}.")
                ).update(sleep_after=5)

            async def cb_approve_proposal_cb(assistant_, user, reaction_id):
                set_reaction_key(reaction_id, "Proposal", False)
                return await assistant_.clear_description().set(
                    title=(
                        "Custom reaction proposal successfully approved! "
                        "Returning to list of current reaction proposals..."),
                    footer=usr_footer(user, f"Approved by {user}.")
                ).update(sleep_after=5)

            async def cb_delete_custom_reaction(assistant_, user, reaction_id):
                delete_custom_reaction(reaction_id)
                verb = "rejected" if proposals else "deleted"
                return await assistant_.clear_description().set(
                    title=(
                        f"Custom {obj_term} successfully "
                        f"{verb}! Returning to list of current "
                        f"{obj_term}..."
                    ),
                    footer=usr_footer(user, f"{verb.title()} by {user}.")
                ).update(sleep_after=5)

            # ---------––------------------------------------------------------

            if delete:
                delete_str = "Deletes the message that calls the reaction"
            else:
                delete_str = ("Does not delete the message that "
                              "calls the reaction")
            if anywhere:
                anywhere_str = ("Activates the custom reaction if "
                                "the prompt is anywhere in a message")
            else:
                anywhere_str = ("Only activates the custom reaction "
                                "if the prompt is the full message")
            if dm:
                dm_str = ("Reacts in the DMs of the user who calls "
                          "the reaction instead of the channel")
            else:
                dm_str = "Reacts directly into the channel"

            edit_menu_items = OrderedDict((
                (EMOJI["one"], {  # Edit the prompt
                    "text": f"Prompt: {prompt}",
                    "callback": lambda a, u: set_text_value(
                        a, u, custom_react_id,
                        question_prompt="Please enter the new prompt",
                        flag="Prompt")
                }),
                (EMOJI["two"], {  # Edit the response
                    "text": f"Response: {response},",
                    "callback": lambda a, u: set_text_value(
                        a, u, custom_react_id,
                        question_prompt="Please enter the new response",
                        flag="Response")
                }),
                (EMOJI["three"], {  # Toggle prompt deletion
                    "text": delete_str,
                    "callback": lambda a, u: toggle_flag(
                        a, u, custom_react_id,
                        question_prompt=(
                            f"Should the message that calls the "
                            f"reaction be deleted?"),
                        flag="DeletePrompt",
                        old_val=delete)
                }),
                (EMOJI["four"], {  # Toggle 'anywhere' flag
                    "text": anywhere_str,
                    "callback": lambda a, u: toggle_flag(
                        a, u, custom_react_id,
                        question_prompt=(
                            f"Should the custom reaction be activated "
                            f"if the prompt is anywhere in a message?"),
                        flag="Anywhere",
                        old_val=anywhere)
                }),
                (EMOJI["five"], {  # Toggle the DM-response flag
                    "text": dm_str,
                    "callback": lambda a, u: toggle_flag(
                        a, u, custom_react_id,
                        question_prompt=(
                            f"Should the reaction be sent in the DMs of "
                            f"the user who called the reaction "
                            f"instead of the channel?"),
                        flag="DM",
                        old_val=dm)
                }),

                *((
                      (EMOJI["white_check_mark"], {
                          "text": "Approve this proposal",
                          "callback": lambda a, u: cb_approve_proposal_cb(
                              a, u, custom_react_id)
                      }),
                      (EMOJI["put_litter_in_its_place"], {
                          "text": "Reject this proposal",
                          "callback": lambda a, u: cb_delete_custom_reaction(
                              a, u, custom_react_id)
                      }),
                  ) if proposals else (
                    (EMOJI["x"], {
                        "text": "Delete this custom reaction",
                        "callback": lambda a, u: cb_delete_custom_reaction(
                            a, u, custom_react_id)
                    }),
                ))
            ))

            _reaction, _user, stop = await assistant.menu(
                title=((f"More information on a custom reaction proposal.\n"
                        f"{self.bot.config.moderator_role}s "
                        f"may click on emojis to modify those values or "
                        f"approve/refuse this proposal\n"
                        f"(Will return to the list of current reaction "
                        f"proposals in 40 seconds otherwise)") if proposals else (
                    f"More information on a custom reaction.\n"
                    f"{self.bot.config.moderator_role}s may click "
                    f"on emojis to modify those values "
                    f"or select an option\n(Will return to the list of "
                    f"current reactions in 40 seconds otherwise)"
                )),
                menu_options=edit_menu_items,
                user=None  # TODO: Any moderator for this one? Need additional_check
                # TODO: after_txt: Added by {user_who_added}
            )

            return stop

        def set_reaction_key(reaction_id, key, value):
            strs = ("Prompt", "Reaction")
            flags = ("DeletePrompt", "Anywhere", "DM", "Proposal")

            assert key in strs or key in flags

            if key in strs:
                value = str(value).rstrip()

            if key in flags:
                value = int(value)

            conn = self.get_conn()
            try:
                conn.cursor().execute((
                    f"UPDATE CustomReactions SET {key} = ?"
                    f"WHERE CustomReactionID = ?"
                ), (reaction_id, value))
                conn.commit()
                self.rebuild_lists()
            finally:
                conn.close()

        def add_custom_reaction(prompt, response, delete, anywhere, dm, is_moderator_):
            conn = self.get_conn()
            try:
                t = (prompt, response, author.id, delete, anywhere, dm,
                     not is_moderator_)
                conn.cursor().execute(
                    'INSERT INTO CustomReactions(Prompt, Response, UserID, '
                    'DeletePrompt, Anywhere, DM, Proposal) '
                    'VALUES(?,?,?,?,?,?,?)', t)
                conn.commit()
                self.rebuild_lists()
            finally:
                conn.close()

        def delete_custom_reaction(reaction_id):
            conn = self.get_conn()
            try:
                c = conn.cursor()
                c.execute(
                    'DELETE FROM CustomReactions WHERE CustomReactionID = ?',
                    (reaction_id,))
                conn.commit()
                self.rebuild_lists()
            finally:
                conn.close()

        is_moderator = (discord.utils.get(ctx.author.roles,
                                          name=self.bot.config.moderator_role)
                        is not None)
        await create_assistant(is_moderator)


def setup(bot):
    bot.add_cog(CustomReactions(bot))
