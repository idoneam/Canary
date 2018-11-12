#!/usr/bin/python3

# discord.py requirements
import discord
from discord.ext import commands
import asyncio

# For DB functionality
import sqlite3
import datetime

# For betting
import random


class Currency:
    def __init__(self, bot):
        self.bot = bot

    async def create_account_if_not_exists(self, ctx):
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        c.execute("SELECT ID FROM BankAccounts WHERE ID = ?",
                  (ctx.message.author.id, ))

        if len(c.fetchall()) == 0:
            c.execute("INSERT INTO BankAccounts VALUES (?, ?, ?)",
                      (ctx.message.author.id, 0, 0))

            conn.commit()
            conn.close()

    @commands.command()
    async def claim(self, ctx):
        """
        Claim's the user's hourly currency.
        """

        # Start bot typing
        await ctx.trigger_typing()

        # Create the user's bank account if it doesn't exist already
        await self.create_account_if_not_exists(ctx)

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        c.execute("SELECT LastClaimed FROM BankAccounts WHERE ID = ?",
                  (ctx.message.author.id, ))

        last_claimed = datetime.datetime.fromtimestamp(c.fetchone()[0])
        threshold = datetime.datetime.now() - datetime.timedelta(hours=1)

        if last_claimed < threshold:
            author = discord.utils.get(
                ctx.guild.members, id=ctx.message.author.id)
            author_name = author.display_name if author else ":b:roken bot"
            updates = (20, int(datetime.datetime.now().timestamp()))
            c.execute(
                "UPDATE BankAccounts SET Balance = Balance + ?, "
                "LastClaimed = ?", updates)
            await ctx.send("{} claimed ${}!".format(author_name, 20))
        else:
            time_left = last_claimed - threshold
            await ctx.send("Please wait {}h {}m to claim again!".format(
                time_left.seconds // 3600, time_left.seconds // 60 % 60))

        conn.commit()
        conn.close()

    @commands.command()
    async def balance(self, ctx):
        """
        Return the user's account balance.
        """

        # Start bot typing
        await ctx.trigger_typing()

        # Create the user's bank account if it doesn't exist already
        await self.create_account_if_not_exists(ctx)

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT Balance FROM BankAccounts WHERE ID = ?",
                  (ctx.message.author.id, ))

        author = discord.utils.get(ctx.guild.members, id=ctx.message.author.id)
        author_name = author.display_name if author else ":b:roken bot"
        balance = c.fetchone()[0]

        await ctx.send("{} has ${} in their account.".format(
            author_name, balance))

        conn.close()

    @commands.command()
    async def flip(self, ctx, face: str = None, bet: int = None):
        """
        Bets an amount of money on a coin flip.
        Usage: ?flip h 10 or ?flip t 5
        """

        if face is None or bet is None:
            return

        choice = face.strip().lower()

        if bet <= 0 or choice not in ("h", "t"):
            if bet <= 0:
                await ctx.send("Please bet a positive amount.")

            if choice not in ("h", "t"):
                await ctx.send("Please choose either h or t.")

            return

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        c.execute("SELECT Balance FROM BankAccounts WHERE ID = ?",
                  (ctx.message.author.id, ))

        if c.fetchone()[0] < bet:
            await ctx.send("You're too broke to bet that much!")

            conn.commit()
            conn.close()

            return

        author = discord.utils.get(ctx.guild.members, id=ctx.message.author.id)
        author_name = author.display_name if author else ":b:roken bot"

        result = random.choice(("h", "t"))

        if choice == result:
            await ctx.send("Congratulations! {} won {} on **{}**".format(
                author_name, bet, result))
            c.execute(
                "UPDATE BankAccounts SET Balance = Balance + ? "
                "WHERE ID = ?", (bet, ctx.message.author.id))
        else:
            await ctx.send("Sorry! {} lost {} (result was **{}**).".format(
                author_name, bet, result))
            c.execute(
                "UPDATE BankAccounts SET Balance = Balance - ? "
                "WHERE ID = ?", (bet, ctx.message.author.id))

        conn.commit()
        conn.close()


def setup(bot):
    bot.add_cog(Currency(bot))
