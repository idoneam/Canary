#!/usr/bin/python3

import discord
from discord.ext import commands
import asyncio

import math


class Pages():
    def __init__(self,
                 ctx,
                 currentPage=1,
                 msg=None,
                 itemList=[],
                 title='Paginator',
                 displayOption=(1, 0),
                 editableContent=True):
        """Creates a paginator.

        Parameters
        -----------
        ctx: discord.ext.commands.Context
            The current context (guild, channel, etc for bot to send messages).
        currentPage: int
            Specify which page to display.
        msg: discord.Message
            This is helpful for delete function. Specify which message the bot needs to update if an element in the original message is modified.
        itemList: list or dictionary
            List of items to paginate. Using a dictionary is only useful for embeds option where there is a need for field names and values.
        title: str
            Summary of content of the items.
        displayOption: tuple
            The first record of the tuple may have these values:
                0   : Messages will be in code blocks, the number of entries for each page is
                    defined by user (autosize = False), and itemList will be a list of strings
                    corresponding to the pages.
                1   : Code blocks, autosize = True, itemList is a list of strings.
                2   : Embed, autosize = False, itemList is a dictionary with two keys: names & values
                    the values of which will be a list. (itemList = {'names': [], 'values': []})
                3   : Embed, autosize = False, itemList is a list of strings.
                4   : Embed, autosize = True, itemList is a dictionary.
                5   : Embed, autosize = True, itemList is a list of strings.
            The second record is the user defined size of each page. For autosize = True, this value
            is ignored.
        editableContent: bool
            True if the items can be updated by the users (this is like an MVC).
            False otherwise.
        """
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.user = ctx.author
        self.message = msg
        self.itemList = itemList
        self.title = title
        self.displayOption = displayOption
        self._organize()
        self.actions = [
            ('⏪', self._firstPage),
            ('◀', self._prevPage),
            ('▶', self._nextPage),
            ('⏩', self._lastPage),
            ('⏹', self._halt),
        ]
        if editableContent:
            self.actions.append(('🚮', self._del))
        self.currentPage = currentPage
        self.delete = False

    def _organize(self):
        organize_helper_map = {
            0: self._organize_code_blocks,
            1: self._organize_code_blocks_autosize,
            2: self._organize_embeds_dict,
            3: self._organize_embeds_list,
            4: self._organize_embeds_autosize_dict,
            5: self._organize_embeds_autosize_list,
        }
        pagesToSend = ['empty page']
        self.organize_helper = organize_helper_map[self.displayOption[0]]
        self.pagesToSend, self.lastPage = self.organize_helper(pagesToSend)

    def _organize_code_blocks(self, pagesToSend):
        itemPerPage = self.displayOption[1]
        pageCounter = math.ceil(len(self.itemList) / itemPerPage)
        for i in range(pageCounter):
            indexStart = itemPerPage * i
            indexEnd = itemPerPage * (i + 1)
            content = '\n'.join(self.itemList[indexStart:indexEnd]).replace(
                '```', '')
            pagesToSend.append('```markdown\n' + content +
                               '\n\n~ Page {:02d} of {:02d} ~'.format(
                                   i + 1, pageCounter) + '```')
        return (pagesToSend, pageCounter)

    def _organize_code_blocks_autosize(self, pagesToSend):
        pageCounter = length = cache = 0
        for i in range(len(self.itemList)):
            # truncate quotes that are too long
            if len(self.itemList[i]) > 1200:
                self.itemList[i] = self.itemList[i][:1200] + '...'
            length += len(self.itemList[i])
            if length > 1894:
                pagesToSend.append(
                    '```markdown\n' + self.title + ':\n\n' +
                    '\n'.join(self.itemList[cache:i]).replace('```', ''))
                cache = i
                length = len(self.itemList[i])
                pageCounter += 1
            elif i == len(self.itemList) - 1:    # edge case
                pagesToSend.append(
                    '```markdown\n' + self.title + ':\n\n' +
                    '\n'.join(self.itemList[cache:i + 1]).replace('```', ''))
                pageCounter += 1
        for i in range(len(pagesToSend)):
            pagesToSend[i] += '\n\n~ Page {:02d} of {:02d} ~'.format(
                i, pageCounter) + '```'
        return (pagesToSend, pageCounter)

    def _organize_embeds_dict(self, pagesToSend):
        itemPerPage = self.displayOption[1]
        pageCounter = math.ceil(len(self.itemList['names']) / itemPerPage)
        em = discord.Embed(title=self.title, colour=0xDA291C)
        for i in range(pageCounter):
            em.set_footer(
                text='Page {:02d} of {:02d}'.format(i + 1, pageCounter))
            indexStart = itemPerPage * i
            indexEnd = itemPerPage * (i + 1)
            for name, val in zip(self.itemList['names'][indexStart:indexEnd],
                                 self.itemList['values'][indexStart:indexEnd]):
                em.add_field(name=name, value=val)
            pagesToSend.append(em)
            em = discord.Embed(title=self.title, colour=0xDA291C)
        return (pagesToSend, pageCounter)

    def _organize_embeds_list(self, pagesToSend):
        itemPerPage = self.displayOption[1]
        pageCounter = math.ceil(len(self.itemList) / itemPerPage)
        em = discord.Embed(title=self.title, colour=0xDA291C)
        for i in range(pageCounter):
            em.set_footer(
                text='Page {:02d} of {:02d}'.format(i + 1, pageCounter))
            indexStart = itemPerPage * i
            indexEnd = itemPerPage * (i + 1)
            em.description = ''.join(self.itemList[indexStart:indexEnd])
            if len(em.description) > 1200:
                em.description = em.description[:1200] + '...'
            pagesToSend.append(em)
            em = discord.Embed(title=self.title, colour=0xDA291C)
        return (pagesToSend, pageCounter)

    def _organize_embeds_autosize_dict(self, pagesToSend):
        # TODO: implement real autosize™
        # this method should not be called at the moment
        # itemPerPage = 10
        pass

    def _organize_embeds_autosize_list(self, pagesToSend):
        pass

    async def _showPage(self, page):
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
                if self.displayOption[0] < 2:    # code blocks
                    await self.message.edit(
                        content=self.pagesToSend[self.currentPage])
                else:    # embeds
                    await self.message.edit(
                        embed=self.pagesToSend[self.currentPage])
                return
        else:
            if self.displayOption[0] < 2:
                self.message = await self.channel.send(
                    content=self.pagesToSend[self.currentPage],
                    delete_after=300)
            else:
                self.message = await self.channel.send(
                    embed=self.pagesToSend[self.currentPage], delete_after=300)
            for (emoji, _) in self.actions:
                await self.message.add_reaction(emoji)
            return

    async def _firstPage(self):
        await self._showPage(1)

    async def _prevPage(self):
        await self._showPage(max(1, self.currentPage - 1))

    async def _nextPage(self):
        await self._showPage(min(self.lastPage, self.currentPage + 1))

    async def _lastPage(self):
        await self._showPage(self.lastPage)

    async def _halt(self):
        await self._showPage(0)

    async def _del(self):
        self.delete = True
        await self._showPage(self.currentPage)

    def _reactCheck(self, reaction, user):
        if user == self.bot.user:
            return False
        if reaction.message.id != self.message.id:
            return False
        for (emoji, action) in self.actions:
            if reaction.emoji == emoji:
                self.user = user
                self._turnPage = action
                return True
        return False

    async def paginate(self):
        if self.delete:
            self.delete = False
            self._organize()
        await self._showPage(self.currentPage)
        while not self.delete and self.message:
            try:
                reaction, user = await self.bot.wait_for(
                    'reaction_add', check=self._reactCheck)
            except:
                try:
                    self.message.delete()
                except:
                    pass
                finally:
                    break
            await self._turnPage()
            try:
                await self.message.remove_reaction(reaction, user)
            except:
                pass
