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

import asyncio
import discord
import json

from collections import OrderedDict, defaultdict
from typing import Optional, Tuple, Union

from cogs.utils.paginator import Pages
from cogs.utils.emojis import EMOJI

PagesDisplayOptionT = Union[Tuple[int], Tuple[int, int]]


def _const_true(_x):
    return True


def _const_true_2(_x, _y):
    return True


def _id(x):
    return x


class AssistantHelperUninitialized(Exception):
    pass


# TODO: Require initialized decorator


class AssistantHelper:
    """
    Class to help commands make wizards for doing stuff in the bot.
    Written by @davidlougheed, but owes its life to @le-potate
    """

    LOADING_EMBED = discord.Embed(title="Loading...")

    EMOJI_NO = EMOJI["zero"]
    EMOJI_YES = EMOJI["one"]
    EMOJI_STOP = EMOJI["stop_button"]
    EMOJI_OK = EMOJI["ok"]

    STOP_TEXT = "stop"

    def __init__(self, ctx, title=None, description=None, footer=None,
                 options=(), author=None,
                 page_display: PagesDisplayOptionT = (2, 10),
                 page_editable_content_emoji: str = EMOJI["ok"],
                 page_return_user_on_edit: bool = True):
        self._ctx = ctx
        self._message = None

        # Original author of the message that triggered the assistant
        self._author = author

        self._title: Optional[str] = title or None
        self._description: Optional[str] = description or None
        self._footer: dict = footer or None
        self._options: Tuple[str] = options or ()

        self._old_title = None
        self._old_description = None
        self._old_footer = None
        self._old_options = ()

        self._old_pages = None
        self._pages: Optional[dict] = None

        self._pagination_obj: Optional[Pages] = None

        # Pagination object settings
        self._page_display = page_display
        self._page_editable_content_emoji = page_editable_content_emoji
        self._page_return_user_on_edit = page_return_user_on_edit

        self._is_loading: bool = False

    async def initialize(self):
        self._message = await self._ctx.send(
            embed=AssistantHelper.LOADING_EMBED)
        # TODO: Handle and possibly exit if errors occur, return standard exit

    def _check_init(self):
        if not self._message:
            raise AssistantHelperUninitialized()

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, title):
        self._old_title = self._title
        self._title = title or None
        # TODO: Batch updates

    def set_title(self, title):
        self.title = title  # Use setter
        return self  # Allow chaining

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        self.clear_pages_if_set()
        self._old_description = self._description
        self._description = description or None
        # TODO: Batch updates

    @property
    def footer(self):
        return self._footer

    @footer.setter
    def footer(self, footer):
        self.clear_pages_if_set()
        self._old_footer = self._footer
        self._footer = footer or None
        # TODO: Batch updates

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, options: Optional[Tuple[str]]):
        self.clear_pages_if_set()
        self._old_options = self._options
        self._options = options or ()

    def clear_options(self):
        self.options = ()
        return self

    def add_yes_no_stop_options(self):
        self.options = (
            *self._options,
            AssistantHelper.EMOJI_NO,
            AssistantHelper.EMOJI_YES,
            AssistantHelper.EMOJI_STOP,
        )
        return self

    @property
    def pages(self):
        return self._pages

    @pages.setter
    def pages(self, pages: Optional[Pages]):
        self._old_pages = self._pages
        self._pages = pages

    def set(self, **kwargs):
        """
        Overrides properties specified in kwargs, without clearing anything
        """
        # TODO: Check this

        setter_props = {a for a, v in vars(AssistantHelper).items()
                        if isinstance(v, property) and v.fset is not None}

        for k, v in kwargs.items():
            if k in setter_props:
                setattr(self, k, v)

        return self

    def clear_pages_if_set(self):
        if self.pages:
            self.pages = None

    def _reaction_extension(self):
        i = 0
        for a, b in zip(self._old_options, self._options):
            if a != b:
                break
            i += 1

        return i if i == len(self._old_options) else 0

    async def _update_reactions_if_needed(self):
        # Do nothing if the options haven't changed
        if self._old_options == self._options:
            return

        r_ext = self._reaction_extension()
        if not r_ext:
            # If we're not simply tacking on extra options, clear them all
            await self._message.clear_reactions()

        # Add new reactions
        for reaction in self._options[r_ext:]:
            await self._message.add_reaction(reaction)

    def _should_update_pages(self):
        return self._pages and (
                json.dumps(self._old_pages, sort_keys=True) !=
                json.dumps(self._pages, sort_keys=True))

    def _should_update_embed(self):
        return not self._pages and any((
            self._old_title != self._title,
            self._old_description != self._description,
            (json.dumps(self._old_footer, sort_keys=True)
             != json.dumps(self._footer, sort_keys=True))
        ))

    async def start_loading(self):
        if not self._is_loading:
            self._is_loading = True
            await self._message.edit(embed=AssistantHelper.LOADING_EMBED)

    async def update(self, delete_after: Optional[int] = None,
                     loading_screen: bool = False,
                     force_pagination_update: bool = False,
                     sleep_after: int = 0) -> bool:
        embed_update = self._should_update_embed()

        if loading_screen and embed_update:
            await self.start_loading()

            # If we're doing a loading screen, handle react updates first
            await self._update_reactions_if_needed()

        if embed_update or delete_after:
            embed_content = {}
            footer_content = None

            if self._title:
                embed_content["title"] = self._title
            if self._description:
                embed_content["description"] = self._description

            if self._footer and isinstance(self._footer, dict):
                footer_content = self._footer

            embed = discord.Embed(**embed_content)
            if footer_content is not None:
                embed.set_footer(**footer_content)

            await self._message.edit(embed=embed)

        # ---

        if self._should_update_pages() or \
                (self.pages and force_pagination_update):
            self._pagination_obj = Pages(
                ctx=self._ctx,
                msg=self._message,
                item_list=self.pages,
                title=self.title,
                editable_content_emoji=self._page_editable_content_emoji,
                return_user_on_edit=self._page_return_user_on_edit,
            )

        elif self.pages and self._old_title != self._title:
            # Pagination embed title changed
            # TODO: This should be in pagination API probably
            self._message.embeds[0].title = self._title
            await self._message.edit(embed=self._message.embeds[0])

        # ---

        if delete_after:
            self._pagination_obj = None
            await self._message.edit(delete_after=delete_after)

        if not loading_screen:
            # If not doing a loading screen, add reactions at the end
            await self._update_reactions_if_needed()

        self._is_loading = False

        if sleep_after:
            await asyncio.sleep(sleep_after)

        return bool(delete_after)

    def clear_title(self):
        self.title = None
        return self

    def clear_description(self):
        self.description = None
        return self

    def clear_footer(self):
        self.footer = None
        return self

    def clear_pages(self):
        self.pages = None
        return self

    def clear_everything(self):
        return self.clear_title()\
            .clear_description()\
            .clear_footer()\
            .clear_pages()\
            .clear_options()

    async def _update_message(self):
        try:
            self._message = await self._message.channel.fetch_message(self._message.id)
        except (discord.NotFound, discord.HTTPException):
            pass

    def get_reactions_from_user(self, user):
        # Gets all reactions on the assistant message from a specific user
        # Need to re-fetch the message from the server, since the reactions may
        # have updated
        await self._update_message()
        return [
            r for r in self._message.reactions
            if user in (await r.users().flatten())
        ]

    async def _timeout_update(self, timeout_message: str,
                              timeout_error_delete: Optional[int],
                              timeout_error_sleep: Optional[int] = None):
        self.clear_everything()
        self.title = timeout_message

        await self.update(**({"delete_after": timeout_error_delete}
                             if timeout_error_delete else {}))

        if timeout_error_sleep:
            await asyncio.sleep(timeout_error_sleep)

    def _reaction_check(self, only_user=None, additional_check=None):
        if not additional_check:
            additional_check = _const_true_2

        def _inner_check(reaction, user):
            return all((
                reaction.emoji in self._options,
                (only_user is None or user == only_user),
                reaction.message.id == self._message.id,
                additional_check(reaction, user)
            ))

        return _inner_check

    async def wait_for_option(self,
                              user=None,
                              timeout_message: str = "",
                              timeout_error: bool = True,
                              timeout_error_delete: Optional[int] = 60,
                              timeout_error_sleep: Optional[int] = None,
                              timeout: int = 60,
                              additional_check=None):
        if user is None:
            user = self._author

        try:
            reaction, reaction_user = await self._ctx.bot.wait_for(
                'reaction_add',
                check=self._reaction_check(only_user=user,
                                           additional_check=additional_check),
                timeout=timeout)

        except asyncio.TimeoutError:
            if timeout_error:
                await self._timeout_update(timeout_message,
                                           timeout_error_delete,
                                           timeout_error_sleep)
            return None, None

        return reaction, reaction_user

    async def yes_no_stop_prompt(self, title, prompt, footer, **kwargs):
        await self.start_loading()

        # Update without clearing loading screen
        await self.clear_options().update()

        self.title = title
        self.description = f"{prompt}\n{AssistantHelper.EMOJI_NO} No\n" \
                           f"{AssistantHelper.EMOJI_YES} Yes"
        self.footer = footer

        await self.add_yes_no_stop_options()\
            .update(loading_screen=True)

        r, u = await self.wait_for_option(**kwargs)

        await self.clear_options().update()

        if r is None:
            return r, u, False

        stop = r.emoji == AssistantHelper.STOP_TEXT

        if stop:
            await self.clean_up()

        return r.emoji, u, stop

    async def wait_for_message(self,
                               timeout_message: str = "",
                               timeout_error: bool = True,
                               timeout_error_delete: Optional[int] = 60,
                               timeout_error_sleep: Optional[int] = None,
                               timeout: int = 60,
                               post_process=None,
                               user=None,
                               additional_check=None):
        if user is None:
            user = self._author

        if additional_check is None:
            additional_check = _const_true

        def check(message):
            return message.author == user and additional_check(message)

        if post_process is None:
            post_process = _id

        try:
            msg = await self._ctx.bot.wait_for(
                'message',
                check=check,
                timeout=timeout)
        except asyncio.TimeoutError:
            if timeout_error:
                await self._timeout_update(timeout_message,
                                           timeout_error_delete,
                                           timeout_error_sleep)
            return None

        content = post_process(msg.content)
        await msg.delete()

        return content

    async def wait_for_pos_int_message(self, **kwargs):
        return await self.wait_for_message(
            additional_check=lambda x: x.content.isdigit(),
            post_process=int,
            **kwargs)

    async def text_prompt(self, title: Optional[str] = None,
                          prompt: Optional[str] = None,
                          footer: Optional[dict] = None, **kwargs):
        self.clear_options()
        if title is not None:
            self.title = title
        if prompt is not None:
            self.description = prompt
        if footer is not None:
            self.footer = footer

        await self.update()

        res = await self.wait_for_message(**kwargs)

        if res is None:
            return None, False

        stop = res.lower().strip() == AssistantHelper.STOP_TEXT

        # Get outta here
        await self.clean_up()

        return res, stop

    @staticmethod
    def _join_options(options: 'OrderedDict[str, Union[str, dict]]'):
        return (
            "\n".join(f"{c} {mo if isinstance(mo, str) else mo['text']}\n"
                      for c, mo in options.items()
                      if (isinstance(mo, str) and mo) or mo.get("text"))
            + "\n")

    async def menu(self, title, menu_options: OrderedDict,
                   user, preface: str = "", footer: Optional[dict] = None,
                   loading_screen: bool = True, **kwargs):
        await self.set(
            title=title,
            description=(
                (preface.rstrip() + "\n") if preface else "" +
                AssistantHelper._join_options(menu_options)),
            footer=footer,
            options=(*menu_options.keys(), AssistantHelper.EMOJI_STOP)
        ).update(loading_screen=loading_screen)

        reaction, user_ = await self.wait_for_option(user=user, **kwargs)

        if not reaction:
            return None, None, False

        await self.clear_options().update()

        stop = reaction.emoji == AssistantHelper.EMOJI_STOP

        if stop:
            await self.clean_up()
            return None, user_, True

        return ((await menu_options[reaction.emoji]["callback"](self, user_)),
                user_, False)

    def selector(self, title, footer, select_options: OrderedDict, user,
                 preface: str = "", multi: bool = True, **kwargs):
        preface = ((preface.rstrip() + "\n") if preface else "") + \
            f"React with the options you want and click " \
            f"{AssistantHelper.EMOJI_OK} when you are ready\n"

        await self.set(
            title=title,
            description=(
                preface + AssistantHelper._join_options(select_options)),
            footer=footer,
            options=(*select_options.keys(),
                     AssistantHelper.EMOJI_OK,
                     AssistantHelper.EMOJI_STOP)
        ).update(loading_screen=True)

        results = defaultdict(list)
        stop = False

        # TODO: Manual timeout of 60 seconds? Timeout arg probably?

        while True:
            # Loop until OK is pressed or a timeout occurs
            reaction, user_ = await self.wait_for_option(user=user, **kwargs)

            if not reaction:
                return None, False

            if reaction.emoji == AssistantHelper.EMOJI_OK:
                break

            if reaction.emoji == AssistantHelper.EMOJI_STOP:
                stop = True
                break

            # TODO: Different functionality when multi is False

            results[reaction.emoji].append(user_)

        # TODO: Should we use get_reactions instead?

        # Before return, clear reacts
        await self.clear_options().update()

        if stop:
            self.clean_up()
            return None, True  # TODO: Decorator for cleaning up every time

        return {**results}, False

    async def paginate(self):
        if self.pages and self._pagination_obj:
            return await self._pagination_obj.paginate()

    @property
    def pagination_edit_mode(self):
        return all((self.pages,
                    self._pagination_obj,
                    self._pagination_obj.edit_mode))

    async def clean_up(self):
        self._pagination_obj = None
        await self._message.delete()
