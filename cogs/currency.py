#!/usr/bin/python3

# discord.py requirements
import discord
from discord.ext import commands
import asyncio

# For type hinting
from typing import Dict

# For DB functionality
import sqlite3
import datetime

# For betting
import random

# For other stuff
import json

ACTION_CLAIM = "claim"
ACTION_COIN_FLIP = "coin_flip"
ACTION_GIFTER = "gifter"
ACTION_GIFTEE = "giftee"

TRANSACTION_ACTIONS = (ACTION_CLAIM, ACTION_COIN_FLIP, ACTION_GIFTER,
                       ACTION_GIFTEE)


class Currency:
    def __init__(self, bot):
        self.bot = bot

    async def fetch_bank_balance(self, user: discord.Member):
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT SUM(Amount) FROM BankTransactions WHERE UserID = ?",
                  (user.id, ))

        balance = c.fetchone()[0]
        if balance is None:
            balance = 0

        conn.close()

        return balance

    async def create_bank_transaction(self, c, user: discord.Member,
                                      amount: int, action: str,
                                      metadata: Dict):
        if action not in TRANSACTION_ACTIONS:
            print("Error: Invalid bank transaction '{}'".format(action))
            return

        now = int(datetime.datetime.now().timestamp())
        t = (user.id, amount, action, json.dumps(metadata), now)
        c.execute(
            "INSERT INTO BankTransactions(UserID, Amount, Action, "
            "Metadata, Date) VALUES(?, ?, ?, ?, ?)", t)

    @commands.command()
    async def claim(self, ctx):
        """
        Claim's the user's hourly currency.
        """

        # Start bot typing
        await ctx.trigger_typing()

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        c.execute(
            "SELECT IFNULL(MAX(Date), 0) FROM BankTransactions "
            "WHERE UserID = ? AND Action = ?",
            (ctx.message.author.id, ACTION_CLAIM))

        last_claimed = datetime.datetime.fromtimestamp(c.fetchone()[0])
        threshold = datetime.datetime.now() - datetime.timedelta(hours=1)

        if last_claimed < threshold:
            author_name = (ctx.message.author.display_name
                           if ctx.message.author else ":b:roken bot")

            metadata = {"channel": ctx.message.channel.id}

            await self.create_bank_transaction(c, ctx.message.author, 20,
                                               ACTION_CLAIM, metadata)

            conn.commit()

            await ctx.send("{} claimed ${}!".format(author_name, 20))
        else:
            time_left = last_claimed - threshold
            await ctx.send("Please wait {}h {}m to claim again!".format(
                time_left.seconds // 3600, time_left.seconds // 60 % 60))

        conn.close()

    @commands.command(aliases=["$"])
    async def balance(self, ctx, user: discord.Member = None):
        """
        Return the user's account balance.
        """

        # Start bot typing
        await ctx.trigger_typing()

        author = user if user else ctx.message.author
        author_name = author.display_name if author else ":b:roken bot"
        balance = await self.fetch_bank_balance(author)

        await ctx.send("{} has ${} in their account.".format(
            author_name, balance))

    @commands.command(aliases=["bf"])
    async def flip(self, ctx, bet: str = None, face: str = None):
        """
        Bets an amount of money on a coin flip.
        Usage: ?flip h 10 or ?flip t 5
        """

        if face is None or bet is None:
            return

        balance = await self.fetch_bank_balance(ctx.message.author)

        if balance <= 0:
            await ctx.send("You're too broke to bet!".format(bet))
            return

        if bet.lower().strip() == "all":
            bet_int = balance
        else:
            try:
                bet_int = int(bet)
            except ValueError:
                await ctx.send("Invalid betting quantity: '{}'.".format(bet))
                return

        choice = face.strip().lower()

        if bet_int <= 0 or choice not in ("h", "t"):
            if bet_int <= 0:
                await ctx.send("Please bet a positive amount.")

            if choice not in ("h", "t"):
                await ctx.send("Please choose either h or t.")

            return

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        if balance < bet_int:
            await ctx.send("You're too broke to bet that much!")
            conn.close()
            return

        author_name = (ctx.message.author.display_name
                       if ctx.message.author else ":b:roken bot")

        result = random.choice(("h", "t"))

        metadata = {"result": result, "channel": ctx.message.channel.id}

        amount = bet_int if choice == result else -bet_int
        await self.create_bank_transaction(c, ctx.message.author, amount,
                                           ACTION_COIN_FLIP, metadata)
        conn.commit()

        if choice == result:
            await ctx.send("Congratulations! {} won ${} on **{}**".format(
                author_name, bet_int, result))
        else:
            await ctx.send("Sorry! {} lost ${} (result was **{}**).".format(
                author_name, bet_int, result))

        conn.close()

    @commands.command()
    async def give(self, ctx, user: discord.Member = None, amount: int = None):
        """
        Gives some amount of currency to another user.
        """

        if not user or amount is None:
            await ctx.send("Usage: ?give [user] [amount]")
            return

        if amount <= 0:
            await ctx.send("You cannot give ${}!".format(amount))
            return

        if user.id == ctx.message.author.id:
            await ctx.send(":thinking:")
            return

        grn = ctx.message.author.display_name
        gen = user.display_name

        gifter_metadata = {
            "giftee": user.id,
            "channel": ctx.message.channel.id
        }

        giftee_metadata = {
            "gifter": ctx.message.author.id,
            "channel": ctx.message.channel.id
        }

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        await self.create_bank_transaction(c, ctx.message.author, -amount,
                                           ACTION_GIFTER, gifter_metadata)

        await self.create_bank_transaction(c, user, amount, ACTION_GIFTEE,
                                           giftee_metadata)

        conn.commit()

        await ctx.send("{} gave ${} to {}!".format(grn, amount, gen))

        conn.close()


def setup(bot):
    bot.add_cog(Currency(bot))
