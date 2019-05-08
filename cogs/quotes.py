#!/usr/bin/python3

# discord.py requirements
import discord
from discord.ext import commands
import asyncio

# For DB functionality
import sqlite3
import datetime

# For Markov Chain
import numpy as np
import re

# Other utils
import random
from .utils.paginator import Pages

GEN_SPACE_SYMBOLS = re.compile(r"[,“”\".?!]")
GEN_BLANK_SYMBOLS = re.compile(r"['()`]")


class Quotes():
    def __init__(self, bot):
        self.bot = bot
        self.mc_table = {}
        self.rebuild_mc()

    def rebuild_mc(self):
        """
        Rebuilds the Markov Chain lookup table for use with the ?generate command.
        Blame David for this code.
        """
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT Quote FROM Quotes")

        lookup = {}

        for q in c.fetchall():
            # Skip URL quotes
            if 'http://' in q[0] or 'https://' in q[0]:
                continue

            # Preprocess the quote to improve chances of getting a nice
            # dictionary going
            cq = re.sub(GEN_SPACE_SYMBOLS, ' ',
                        re.sub(GEN_BLANK_SYMBOLS, '', q[0].lower())).strip()

            # Split cleaned quote into words by any whitespace.
            words = re.split(r'\s+', cq)

            # Count up word occurrences in the lookup table in order to
            # eventually build the probability distribution for the key.
            for i in range(len(words)):
                key = words[i]
                if i == len(words) - 1:
                    # Last word of a quote, so give the word a chance of
                    # terminating the generated 'quote'.
                    if key in lookup:
                        lookup[key]['TOTAL'] += 1
                        lookup[key]['TERM'] = lookup[key].get('TERM', 0) + 1.0
                    else:
                        lookup[key] = {'TERM': 1.0, 'TOTAL': 1}
                else:
                    nxt = words[i + 1]
                    if key in lookup:
                        lookup[key]['TOTAL'] += 1
                        lookup[key][nxt] = lookup[key].get(nxt, 0) + 1.0
                    else:
                        lookup[key] = {nxt: 1.0, 'TOTAL': 1}

        for word in lookup:
            total = lookup[word]['TOTAL']
            del lookup[word]['TOTAL']
            for option in lookup[word]:
                lookup[word][option] = lookup[word][option] / total

        self.mc_table = lookup
        conn.close()

    @commands.command(aliases=['addq'])
    async def add_quotes(self, ctx, member: discord.Member, *, quote: str):
        """
        Add a quote to a user's quote database.
        """

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        t = (member.id, member.name, quote, str(ctx.message.created_at))
        c.execute('INSERT INTO Quotes VALUES (?,?,?,?)', t)
        await ctx.send('`Quote added.`')

        conn.commit()
        conn.close()

        # Rebuild the Markov Chain lookup table to include new quote data.
        self.rebuild_mc()

    @commands.command(aliases=['q'])
    async def quotes(self, ctx, str1: str = None, *, str2: str = None):
        """
        Retrieve a quote with a specified keyword / mention.
        """

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        mentions = ctx.message.mentions

        if str1 is None:    # No argument passed
            quotes = c.execute('SELECT ID, Name, Quote FROM Quotes').fetchall()

        elif mentions and mentions[0].mention == str1:    # Has args
            u_id = mentions[0].id
            # Query for either user and quote or user only (None)
            c.execute(
                'SELECT ID, Name, Quote FROM Quotes WHERE ID = ? AND Quote '
                'LIKE ?',
                (u_id, "%{}%".format(str2 if str2 is not None else "")))
            quotes = c.fetchall()

        else:    # query for quote only
            query = str1 if str2 is None else str1 + ' ' + str2
            c.execute('SELECT ID, Name, Quote FROM Quotes WHERE Quote LIKE ?',
                      ('%{}%'.format(query), ))
            quotes = c.fetchall()

        if not quotes:
            conn.close()
            await ctx.send('Quote not found.')
            return

        conn.close()
        quote_tuple = random.choice(quotes)
        author_id = int(quote_tuple[0])
        name = quote_tuple[1]
        quote = quote_tuple[2]
        author = discord.utils.get(ctx.guild.members, id=author_id)

        # get author name, if the user is still on the server, their
        # current nick will be displayed, otherwise use the name stored
        # in db

        author_name_unesc = author.display_name if author else name
        author_name = " ".join(author_name_unesc)
        await ctx.send('{} 📣 {}'.format(author_name, quote))

    @commands.command(aliases=['lq'])
    async def list_quotes(self, ctx, author: discord.Member = None):
        """
        List quotes
        """

        await ctx.trigger_typing()

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        quote_author = author if author else ctx.message.author
        author_id = quote_author.id
        c.execute('SELECT * FROM Quotes WHERE ID = ?', (author_id, ))
        quote_list = c.fetchall()

        if not quote_list:
            await ctx.send('No quote found.', delete_after=60)
            return

        quote_list_text = [
            '[{}] {}'.format(i + 1, quote[2])
            for i, quote in zip(range(len(quote_list)), quote_list)
        ]

        p = Pages(ctx,
                  item_list=quote_list_text,
                  title='Quotes from {}'.format(quote_author.display_name))

        await p.paginate()

        def msg_check(msg):
            try:
                return (0 <= int(msg.content) <= len(quote_list)
                        and msg.author.id == author_id
                        and msg.channel == ctx.message.channel)
            except ValueError:
                return False

        while p.delete:
            await ctx.send(
                'Delete option selected. Enter a number to specify which '
                'quote you want to delete, or enter 0 to return.',
                delete_after=60)

            try:
                message = await self.bot.wait_for('message',
                                                  check=msg_check,
                                                  timeout=60)

            except asyncio.TimeoutError:
                await ctx.send(
                    'Command timeout. You may want to run the command again.',
                    delete_after=60)
                break

            else:
                index = int(message.content) - 1
                if index == -1:
                    await ctx.send('Exit delq.', delete_after=60)
                else:
                    t = (quote_list[index][0], quote_list[index][2])
                    del quote_list[index]
                    c.execute('DELETE FROM Quotes WHERE ID = ? AND Quote = ?',
                              t)
                    conn.commit()

                    await ctx.send('Quote deleted', delete_after=60)
                    await message.delete()

                    p.itemList = [
                        '[{}] {}'.format(i + 1, quote[2])
                        for i, quote in zip(range(len(quote_list)), quote_list)
                    ]

                await p.paginate()

        conn.commit()
        conn.close()

    @commands.command(aliases=['allq', 'aq'])
    async def all_quotes(self, ctx, *, query):
        """
        List all quotes that contain the query string.
        Usage: ?all_quotes [-p pagenum] query

        Optional arguments:
        -p pagenum      Choose a page to display
        """

        if not query:
            ctx.send('You must provide a query')
            return

        query_splitted = query.split()
        pagenum = 1

        if '-p' in query_splitted:
            idx = query_splitted.index('-p')
            query_splitted.pop(idx)

            try:
                pagenum = int(query_splitted[idx])
                query_splitted.pop(idx)
            except Exception:
                pass

        query = " ".join(query_splitted)
        await ctx.trigger_typing()

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        t = ('%{}%'.format(query), )
        c.execute('SELECT * FROM Quotes WHERE Quote LIKE ?', t)
        quote_list = c.fetchall()

        if not quote_list:
            await ctx.send('No quote found.', delete_after=60)
            return

        quote_list_text = [
            '[{}] {}'.format(i + 1, quote[2])
            for i, quote in zip(range(len(quote_list)), quote_list)
        ]

        p = Pages(ctx,
                  item_list=quote_list_text,
                  title='Quotes that contain "{}"'.format(query),
                  editable_content=False,
                  current_page=pagenum)

        await p.paginate()

    @commands.command(aliases=['gen'])
    async def generate(self, ctx, seed: str = None, min_length: int = 1):
        """
        Generates a random 'quote' using a Markov Chain. Optionally takes in a
        word to seed the Markov Chain with and (also optionally) a desired
        minimum length which is NOT guaranteed to be met.
        """

        await ctx.trigger_typing()

        # Preprocess seed so that we can use it as a lookup
        if seed is not None:
            seed = re.sub(GEN_SPACE_SYMBOLS, ' ',
                          re.sub(GEN_SPACE_SYMBOLS, '', seed.lower())).strip()
        else:
            try:
                seed = np.random.choice(list(self.mc_table.keys()))
            except ValueError:
                # Value errors are encountered when the keys list is empty.
                seed = None

        if seed is None:
            await ctx.send('Markov chain table is empty.', delete_after=60)
        elif seed not in self.mc_table.keys():
            await ctx.send('Could not generate anything with that seed.',
                           delete_after=60)
        else:
            longest_sentence = []
            retries = 0

            while len(longest_sentence) < min_length and retries < 200:
                current_word = seed
                sentence = [current_word]

                # Add words to the sentence until a termination condition is
                # encountered.
                while True:
                    choices = [(w, self.mc_table[current_word][w])
                               for w in self.mc_table[current_word]]
                    c_words, p_dist = zip(*choices)

                    # Choose a random word and add it to the sentence using the
                    # probability distribution stored in the word entry.
                    old_word = current_word
                    current_word = np.random.choice(c_words, p=p_dist)

                    # Don't allow termination until the minimum length is met or we
                    # don't have any other option.
                    while current_word == 'TERM' and len(sentence) < min_length \
                            and len(self.mc_table[old_word].keys()) > 1:
                        current_word = np.random.choice(c_words, p=p_dist)

                    # Don't allow repeat words too much
                    while len(sentence) >= 3 and \
                            (current_word == sentence[-1]
                             == sentence[-2] == sentence[-3]):
                        current_word = np.random.choice(c_words, p=p_dist)

                    # Cap sentence at 1000 words, just in case, and terminate if
                    # termination symbol is seen.
                    if current_word == 'TERM' or len(sentence) >= 1000:
                        break
                    sentence.append(current_word)

                if len(longest_sentence) < len(sentence) \
                        and len(' '.join(sentence)) <= 2000:
                    longest_sentence = sentence[:]

                retries += 1

            await ctx.send(' '.join(longest_sentence))


def setup(bot):
    bot.add_cog(Quotes(bot))
