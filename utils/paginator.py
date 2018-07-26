#!/usr/bin/python3

import discord
from discord.ext import commands
import asyncio

import math

class Pages():
    def __init__(self, ctx, currentPage=1, msg=None, itemList=[], title='Paginator', option='CODE_BLOCKS', autosize=(True,0), editableContent=True):
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
        option: 'CODE_BLOCKS' or 'EMBEDS'
            Specify if the pages sent will be in either format.
        autosize: tuple
            If there should be a certain number of items per page, the first value should be set to False, and the second value of the tuple is the desired number of items.
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
        self.option = option
        self.autosize = autosize
        self.__organize()
        self.actions = [('⏪', self.__firstPage),
                        ('◀', self.__prevPage),
                        ('▶', self.__nextPage),
                        ('⏩', self.__lastPage),
                        ('⏹', self.__halt),
                        ]
        if editableContent:
            self.actions.append(('🚮', self.__del))
        self.currentPage = currentPage
        self.delete = False


    def __organize(self):
        pagesToSend = ['empty page']
        if self.option == "EMBEDS":
            if self.autosize[0] == True:
                result = self.__organize_embeds_autosize(pagesToSend)
            else:
                result = self.__organize_embeds(pagesToSend)
        elif self.option == "CODE_BLOCKS":
            if self.autosize[0] == True:
                result = self.__organize_code_blocks_autosize(pagesToSend)
            else:
                result = self.__organize_code_blocks(pagesToSend)
        self.pagesToSend, self.lastPage = result


    def __organize_embeds(self, pagesToSend):
        itemPerPage = self.autosize[1]
        pageCounter = math.ceil(len(self.itemList['names']) / itemPerPage)
        em = discord.Embed(title=self.title, colour=0xDA291C)
        for i in range(pageCounter):
            em.set_footer(text='Page {:02d} of {:02d}'.format(i+1, pageCounter))
            indexStart = itemPerPage * i
            indexEnd = itemPerPage * (i+1)
            for name, val in zip( self.itemList['names'][indexStart:indexEnd], self.itemList['values'][indexStart:indexEnd]):
                em.add_field(
                    name=name,
                    value=val
                )
            pagesToSend.append(em)
            em = discord.Embed(title=self.title, colour=0xDA291C)
        return (pagesToSend, pageCounter)


    def __organize_embeds_autosize(self, pagesToSend):
        # TODO: implement real autosize™
        # this method should not be called at the moment
        itemPerPage = 10
        pageCounter = math.ceil(len(self.itemList['names']) / itemPerPage)
        em = discord.Embed(title=self.title, colour=0xDA291C)
        for i in range(pageCounter):
            em.set_footer(text='Page {:02d} of {:02d}'.format(i+1, pageCounter))
            indexStart = itemPerPage * i
            indexEnd = itemPerPage * (i+1)
            for name, val in zip( self.itemList['names'][indexStart:indexEnd], self.itemList['values'][indexStart:indexEnd]):
                em.add_field(
                    name=name,
                    value=val
                )
            pagesToSend.append(em)
            em = discord.Embed(title=self.title, colour=0xDA291C)
        return (pagesToSend, pageCounter)


    def __organize_code_blocks(self, pagesToSend):
        itemPerPage = self.autosize[1]
        pageCounter = math.ceil(len(self.itemList) / itemPerPage)
        for i in range(pageCounter):
            indexStart = itemPerPage * i
            indexEnd = itemPerPage * (i+1)
            content = '\n'.join(self.itemList[indexStart:indexEnd]).replace('```', '')
            pagesToSend.append('```markdown\n'
                + content
                + '\n\n~ Page {:02d} of {:02d} ~'.format(i+1, pageCounter)
                + '```'
            )
        return (pagesToSend, pageCounter)


    def __organize_code_blocks_autosize(self, pagesToSend):
        pageCounter = length = cache = 0
        for i in range(len(self.itemList)):
            length += len(self.itemList[i])
            if length > 1894:
                pagesToSend.append('```'
                    + self.title
                    + ':\n\n'
                    + '\n'.join(self.itemList[cache:i]).replace('```', ''))
                cache = i
                length = len(self.itemList[i])
                pageCounter += 1
            elif i == len(self.itemList)-1: # edge case
                pagesToSend.append('```markdown\n'
                    + self.title
                    + ':\n\n'
                    + '\n'.join(self.itemList[cache:i+1]).replace('```', ''))
                pageCounter += 1
        for i in range(len(pagesToSend)):
            pagesToSend[i] += '\n\n~ Page {:02d} of {:02d} ~'.format(i, pageCounter) + '```'
        return (pagesToSend, pageCounter)


    async def __showPage(self, page):
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
                if self.option == 'CODE_BLOCKS':
                    await self.message.edit(content=self.pagesToSend[self.currentPage])
                elif self.option == 'EMBEDS':
                    await self.message.edit(embed=self.pagesToSend[self.currentPage])
                return
        else:
            if self.option == 'CODE_BLOCKS':
                self.message = await self.channel.send(content=self.pagesToSend[self.currentPage], delete_after=300)
            elif self.option == 'EMBEDS':
                self.message = await self.channel.send(embed=self.pagesToSend[self.currentPage], delete_after=300)
            for (emoji, _) in self.actions:
                await self.message.add_reaction(emoji)
            return


    async def __firstPage(self):
        await self.__showPage(1)


    async def __prevPage(self):
        await self.__showPage(max(1, self.currentPage - 1))


    async def __nextPage(self):
        await self.__showPage(min(self.lastPage, self.currentPage + 1))


    async def __lastPage(self):
        await self.__showPage(self.lastPage)


    async def __halt(self):
        await self.__showPage(0)


    async def __del(self):
        self.delete = True
        await self.__showPage(self.currentPage)


    def __reactCheck(self, reaction, user):
        if user == self.bot.user:
            return False
        if reaction.message.id != self.message.id:
            return False
        for (emoji, action) in self.actions:
            if reaction.emoji == emoji:
                self.user = user
                self.__turnPage = action
                return True
        return False


    async def paginate(self):
        if self.delete:
            self.delete = False
            self.__organize()
        await self.__showPage(self.currentPage)
        while not self.delete and self.message:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=self.__reactCheck)
            except:
                try:
                    self.message.delete()
                except:
                    pass
                finally:
                    break
            await self.__turnPage()
            try:
                await self.message.remove_reaction(reaction, user)
            except:
                pass
