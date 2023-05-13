# Copyright (C) idoneam (2016-2023)
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

import discord

import math


class Pages:
    def __init__(
        self,
        ctx,
        current_page=1,
        msg=None,
        item_list=[],
        title="Paginator",
        display_option=(1, 0),
        editable_content=True,
        editable_content_emoji="🚮",
        return_user_on_edit=False,
        timeout=300,
    ):
        """Creates a paginator.

        Parameters
        -----------
        ctx: Union[discord.ext.commands.Context, MockContext]
            The current context (guild, channel, etc for the bot to send messages).
        current_page: int
            Specify which page to display.
        msg: discord.Message
            This is helpful for edit function. Specify which message the bot
            needs to update if an element in the original message is modified.
        item_list: list or dictionary
            List of items to paginate. Using a dictionary is only useful for
            embeds option where there is a need for field names and values.
        title: str
            Summary of content of the items.
        display_option: tuple
            The first record of the tuple may have these values:
                0   : Messages will be in code blocks, the number of entries
                    for each page is defined by user (autosize = False), and
                    item_list will be a list of strings corresponding to
                    the pages.
                1   : Code blocks, autosize = True, item_list is a list
                    of strings.
                2   : Embed, autosize = False, item_list is a dictionary
                    with two keys: names & values, the values of which will
                    be a list. (item_list = {'names': [], 'values': []})
                3   : Embed, autosize = False, item_list is a list of strings.
                4   : Embed, autosize = True, item_list is a dictionary.
                5   : Embed, autosize = True, item_list is a list of strings.
                6   : Embed, autosize = True, item_list is a list of embeds
                      that will be used as pages
            The second record is the user defined size of each page.
            For autosize = True, this value is ignored.
        editable_content: bool
            True if the items can be updated by the users
            If this is True, then the editable_content_emoji will be added on
            the message. When a user clicks it, paginator.edit_mode
            will be set to True, and the function will return.
            (If return_user_on_edit is set to True, the user will be returned)
            A recommended use is then to create a while paginator.edit_mode
            loop after the await paginator.paginate() call, edit the content
            there (for example, ask the user which item to delete and delete
            it), then call paginator.paginate() again in the loop.
            False otherwise.
        editable_content_emoji: string or discord.Emoji
            If editable_content is True, this is the emoji that will be
            added on the message and be used to edit content.
        return_user_on_edit: bool
            True if the user that clicked the editable_content_emoji react
            should be returned when editing.
            False otherwise.
        timeout: int
            The time in seconds before the message gets deleted.
            The timeout is reset when a user turns pages.
            It is not recommended to use a value much bigger than the default
            one.
        """
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.user = ctx.author
        self.message = msg
        self.itemList = item_list
        self.title = title
        self.displayOption = display_option
        self._organize()
        self.actions = [
            ("⏪", self._first_page),
            ("◀", self._prev_page),
            ("▶", self._next_page),
            ("⏩", self._last_page),
            ("⏹", self._halt),
        ]
        if editable_content:
            self.actions.append((editable_content_emoji, self._edit))
        self.currentPage = current_page
        self.edit_mode = False
        self.return_user_on_edit = return_user_on_edit
        self.timeout = timeout

    def _organize(self):
        organize_helper_map = {
            0: self._organize_code_blocks,
            1: self._organize_code_blocks_autosize,
            2: self._organize_embeds_dict,
            3: self._organize_embeds_list,
            4: self._organize_embeds_autosize_dict,
            5: self._organize_embeds_autosize_list,
            6: self._organize_embeds_list_embeds,
        }
        pages_to_send = ["empty page"]
        self.organize_helper = organize_helper_map[self.displayOption[0]]
        self.pagesToSend, self.lastPage = self.organize_helper(pages_to_send)

    def _organize_code_blocks(self, pages_to_send):
        item_per_page = self.displayOption[1]
        page_counter = math.ceil(len(self.itemList) / item_per_page)
        for i in range(page_counter):
            index_start = item_per_page * i
            index_end = item_per_page * (i + 1)
            content = "\n".join(self.itemList[index_start:index_end]).replace("```", "")
            pages_to_send.append(
                "```markdown\n" + content + "\n\n~ Page {:02d} of {:02d} ~".format(i + 1, page_counter) + "```"
            )
        return pages_to_send, page_counter

    def _organize_code_blocks_autosize(self, pages_to_send):
        page_counter = length = cache = 0
        for i in range(len(self.itemList)):
            # truncate quotes that are too long
            if len(self.itemList[i]) > 1200:
                self.itemList[i] = self.itemList[i][:1200] + "..."
            length += len(self.itemList[i])
            if length > 1894:
                pages_to_send.append(
                    "```markdown\n" + self.title + ":\n\n" + "\n".join(self.itemList[cache:i]).replace("```", "")
                )
                cache = i
                length = len(self.itemList[i])
                page_counter += 1
            elif i == len(self.itemList) - 1:  # edge case
                pages_to_send.append(
                    "```markdown\n" + self.title + ":\n\n" + "\n".join(self.itemList[cache : i + 1]).replace("```", "")
                )
                page_counter += 1
        for i in range(len(pages_to_send)):
            pages_to_send[i] += "\n\n~ Page {:02d} of {:02d} ~".format(i, page_counter) + "```"
        return pages_to_send, page_counter

    def _organize_embeds_dict(self, pages_to_send):
        item_per_page = self.displayOption[1]
        page_counter = math.ceil(len(self.itemList["names"]) / item_per_page)
        em = discord.Embed(title=self.title, colour=0xDA291C)
        for i in range(page_counter):
            em.set_footer(text="Page {:02d} of {:02d}".format(i + 1, page_counter))
            index_start = item_per_page * i
            index_end = item_per_page * (i + 1)
            for name, val in zip(
                self.itemList["names"][index_start:index_end], self.itemList["values"][index_start:index_end]
            ):
                em.add_field(name=name, value=val)
            pages_to_send.append(em)
            em = discord.Embed(title=self.title, colour=0xDA291C)
        return pages_to_send, page_counter

    def _organize_embeds_list(self, pages_to_send):
        item_per_page = self.displayOption[1]
        page_counter = math.ceil(len(self.itemList) / item_per_page)
        em = discord.Embed(title=self.title, colour=0xDA291C)
        for i in range(page_counter):
            em.set_footer(text="Page {:02d} of {:02d}".format(i + 1, page_counter))
            index_start = item_per_page * i
            index_end = item_per_page * (i + 1)
            em.description = "".join(self.itemList[index_start:index_end])
            if len(em.description) > 1200:
                em.description = em.description[:1200] + "..."
            pages_to_send.append(em)
            em = discord.Embed(title=self.title, colour=0xDA291C)
        return pages_to_send, page_counter

    def _organize_embeds_autosize_dict(self, pages_to_send):
        # TODO: implement real autosize™
        # this method should not be called at the moment
        # itemPerPage = 10
        pass

    def _organize_embeds_autosize_list(self, pages_to_send):
        pass

    def _organize_embeds_list_embeds(self, pages_to_send):
        page_counter = len(self.itemList)
        pages_to_send.extend(self.itemList)
        return pages_to_send, page_counter

    async def _show_page(self, page):
        self.currentPage = max(0, min(page, self.lastPage))
        if self.message:
            if self.currentPage == 0:
                try:
                    await self.message.delete()
                    self.message = None
                    return
                except:
                    pass
            else:
                if self.displayOption[0] < 2:  # code blocks
                    await self.message.edit(content=self.pagesToSend[self.currentPage], delete_after=self.timeout)
                else:  # embeds
                    await self.message.edit(embed=self.pagesToSend[self.currentPage], delete_after=self.timeout)
                return
        else:
            if self.displayOption[0] < 2:
                self.message = await self.channel.send(
                    content=self.pagesToSend[self.currentPage], delete_after=self.timeout
                )
            else:
                self.message = await self.channel.send(
                    embed=self.pagesToSend[self.currentPage], delete_after=self.timeout
                )
            for emoji, _ in self.actions:
                await self.message.add_reaction(emoji)
            return

    async def _first_page(self):
        await self._show_page(1)

    async def _prev_page(self):
        await self._show_page(max(1, self.currentPage - 1))

    async def _next_page(self):
        await self._show_page(min(self.lastPage, self.currentPage + 1))

    async def _last_page(self):
        await self._show_page(self.lastPage)

    async def _halt(self):
        await self._show_page(0)

    async def _edit(self):
        self.edit_mode = True
        await self._show_page(self.currentPage)

    def _react_check(self, reaction, user):
        if user == self.bot.user:
            return False
        if reaction.message.id != self.message.id:
            return False
        for emoji, action in self.actions:
            if reaction.emoji != emoji:
                continue
            self.user = user
            self._turn_page = action
            return True
        return False

    async def paginate(self):
        if self.edit_mode:
            self.edit_mode = False
            self._organize()
        await self._show_page(self.currentPage)
        while not self.edit_mode and self.message:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=self._react_check)
            except:
                try:
                    await self.message.delete()
                except:
                    pass
                finally:
                    break
            await self._turn_page()
            try:
                await self.message.remove_reaction(reaction, user)
            except:
                pass
            if self.edit_mode and self.return_user_on_edit:
                return user
