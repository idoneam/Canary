#!/usr/bin/python3

# discord.py requirements
import discord
from discord.ext import commands
import asyncio

# For DB functionality
import sqlite3
import datetime

# Other utils
import random
from .utils.paginator import Pages

class Quotes():
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def addq(self, ctx, member: discord.Member, *, quote: str):
        """
        Add a quote to a user's quote database.
        """
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        t = (member.id, member.name, quote,
             str(ctx.message.created_at))
        c.execute('INSERT INTO Quotes VALUES (?,?,?,?)', t)
        await ctx.send('`Quote added.`')
        conn.commit()
        conn.close()


    @commands.command()
    async def q(self, ctx, str1: str = None, *, str2: str = None):
        """
        Retrieve a quote with a specified keyword / mention.
        """
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        t = None
        mentions = ctx.message.mentions
        if str1 is None:        # No argument passed
            quotes = c.execute('SELECT ID, Name, Quote FROM Quotes').fetchall()
        elif mentions and mentions[0].mention == str1:  # Has args
            id = mentions[0].id
            if str2 is None:    # query for user only
                t = (id, '%%',)
            else:               # query for user and quote
                t = (id, '%{}%'.format(str2))
            c.execute('SELECT ID, Name, Quote FROM Quotes WHERE ID = ? AND Quote LIKE ?', t)
            quotes = c.fetchall()
        else:                   # query for quote only
            query = str1 if str2 is None else str1 + ' ' + str2
            t = ('%{}%'.format(query),)
            c.execute('SELECT ID, Name, Quote FROM Quotes WHERE Quote LIKE ?', t)
            quotes = c.fetchall()
        if not quotes:
            conn.close()
            await ctx.send('Quote not found.')
        else:
            conn.close()
            quote_tuple = random.choice(quotes)
            author_id = int(quote_tuple[0])
            name = quote_tuple[1]
            quote = quote_tuple[2]
            author = discord.utils.get(ctx.guild.members, id = author_id)
            # get author name, if the user is still on the server, their current nick will be displayed, otherwise use the name stored in db
            author_name = author.display_name if author else name
            await ctx.send('{} 📣 {}'.format(author_name, quote))


    @commands.command(aliases=['lq'])
    async def list_quotes(self, ctx, author: discord.Member=None):
        """
        List quotes
        """
        await ctx.trigger_typing()
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        quoteAuthor = author if author else ctx.message.author
        author_id = quoteAuthor.id
        t = (author_id,)
        c.execute('SELECT * FROM Quotes WHERE ID = ?', t)
        quoteList = c.fetchall()
        if quoteList:
            quoteListText = ['[{}] {}'.format(i+1, quote[2]) for i,quote in zip(range(len(quoteList)),quoteList)]
            p = Pages(ctx,
                itemList=quoteListText,
                title='Quotes from {}'.format(quoteAuthor.display_name)
            )
            await p.paginate()
            index = 0
            def msgCheck(message):
                try:
                    if (0 <= int(message.content) <= len(quoteList)) and message.author.id == author_id and message.channel == ctx.message.channel:
                        return True
                    return False
                except ValueError:
                    return False
            while p.delete:
                await ctx.send('Delete option selected. Enter a number to specify which quote you want to delete, or enter 0 to return.', delete_after=60)
                try:
                    message = await self.bot.wait_for('message', check=msgCheck, timeout=60)
                except asyncio.TimeoutError:
                    await ctx.send('Command timeout. You may want to run the command again.', delete_after=60)
                    break
                else:
                    index = int(message.content)-1
                    if index == -1:
                        await ctx.send('Exit delq.', delete_after=60)
                    else:
                        t = (quoteList[index][0], quoteList[index][2],)
                        del quoteList[index]
                        c.execute('DELETE FROM Quotes WHERE ID = ? AND Quote = ?', t)
                        conn.commit()
                        await ctx.send('Quote deleted', delete_after=60)
                        await message.delete()
                        p.itemList = ['[{}] {}'.format(i+1, quote[2]) for i,quote in zip(range(len(quoteList)),quoteList)]
                    await p.paginate()
            await ctx.message.delete()
            conn.commit()
            conn.close()
        else:
            await ctx.send('No quote found.', delete_after=60)


def setup(bot):
    bot.add_cog(Quotes(bot))
