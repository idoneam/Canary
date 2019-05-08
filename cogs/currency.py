#!/usr/bin/python3

# discord.py requirements
import discord
from discord.ext import commands
import asyncio

# For type hinting
from typing import Dict, Optional

# For DB functionality
import sqlite3
import datetime

# For general currency shenanigans
from decimal import *

# For betting
import random

# For other stuff
import json

CLAIM_AMOUNT = Decimal(20)
CLAIM_WAIT_TIME = datetime.timedelta(hours=1)

COIN_FLIP_CHOICES = ("h", "t")

CURRENCY_ALL = ["all", "tout"]

ACTION_INITIAL_CLAIM = "init_claim"
ACTION_CLAIM = "claim"
ACTION_BET_FLIP = "bet_flip"
ACTION_BET_ROLL = "bet_roll"
ACTION_GIFTER = "gifter"
ACTION_GIFTEE = "giftee"

TRANSACTION_ACTIONS = (ACTION_INITIAL_CLAIM, ACTION_CLAIM, ACTION_BET_FLIP,
                       ACTION_BET_ROLL, ACTION_GIFTER, ACTION_GIFTEE)


class Currency():
    def __init__(self, bot):
        self.bot = bot
        self.currency = self.bot.config.currency
        self.prec = self.currency["precision"]

    async def fetch_bank_balance(self, user: discord.Member) -> Decimal:
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT IFNULL(SUM(Amount), 0) FROM BankTransactions WHERE "
            "UserID = ?", (user.id, ))

        balance = self.db_to_currency(c.fetchone()[0])
        if balance is None:
            balance = Decimal(0)

        conn.close()

        return balance

    async def create_bank_transaction(self, c, user: discord.Member,
                                      amount: Decimal, action: str,
                                      metadata: Dict):
        # Don't create another connection in this function in order to properly
        # transaction-ify a series of bank "transactions".

        if action not in TRANSACTION_ACTIONS:
            print("Error: Invalid bank transaction '{}'".format(action))
            return

        now = int(datetime.datetime.now().timestamp())
        t = (user.id, self.currency_to_db(amount), action,
             json.dumps(metadata), now)
        c.execute(
            "INSERT INTO BankTransactions(UserID, Amount, Action, "
            "Metadata, Date) VALUES(?, ?, ?, ?, ?)", t)

    def parse_currency(self, amount: str, balance: Decimal):
        if amount.lower().strip() in CURRENCY_ALL:
            return balance
        else:
            try:
                return Decimal(amount)
            except InvalidOperation:
                # Value error (invalid conversion)
                return None

    def currency_to_db(self, amount: Decimal):
        return int(amount * Decimal(10**self.currency["precision"]))

    def db_to_currency(self, amount: int):
        return Decimal(amount) / Decimal(10**self.currency["precision"])

    def format_currency(self, amount: Decimal):
        return ("{:." + str(self.prec) + "f}").format(amount)

    def format_symbol_currency(self, amount: Decimal):
        return self.currency["symbol"] + self.format_currency(amount)

    def check_bet(self, balance: Decimal, bet: Decimal) -> Optional[str]:
        """
        Checks universally invalid betting cases.
        """

        # - Balance-related subcase

        if balance <= 0:
            return "You're too broke to bet!"

        # - Bet-related subcases

        if bet is None:
            # Invalid conversion to decimal.
            return "Invalid betting quantity: '{}'.".format(bet)

        if bet <= 0:
            return "Please bet a positive amount."

        if bet > balance:
            return "You're too broke to bet that much!"

        return ""

    @commands.command()
    async def initial_claim(self, ctx):
        """
        Claim's the user's start-up grant currency.
        """

        # Start bot typing
        await ctx.trigger_typing()

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        c.execute(
            "SELECT IFNULL(MAX(Date), 0) FROM BankTransactions "
            "WHERE UserID = ? AND Action = ?",
            (ctx.message.author.id, ACTION_INITIAL_CLAIM))

        claim_time = c.fetchone()[0]

        author_name = ctx.message.author.display_name

        if claim_time > 0:
            await ctx.send("{} has already claimed their initial "
                           "currency.".format(author_name))
            return

        metadata = {"channel": ctx.message.channel.id}

        await self.create_bank_transaction(c, ctx.message.author,
                                           self.currency["initial_amount"],
                                           ACTION_INITIAL_CLAIM, metadata)

        conn.commit()

        await ctx.send("{} claimed their initial {}!".format(
            author_name,
            self.format_symbol_currency(self.currency["initial_amount"])))

        conn.close()

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
        threshold = datetime.datetime.now() - CLAIM_WAIT_TIME

        if last_claimed < threshold:
            author_name = (ctx.message.author.display_name
                           if ctx.message.author else ":b:roken bot")

            metadata = {"channel": ctx.message.channel.id}

            await self.create_bank_transaction(
                c, ctx.message.author, CLAIM_AMOUNT, ACTION_CLAIM, metadata)

            conn.commit()

            await ctx.send("{} claimed {}!".format(
                author_name, self.format_symbol_currency(CLAIM_AMOUNT)))

        else:
            time_left = last_claimed - threshold
            await ctx.send("Please wait {}h {}m to claim again!".format(
                time_left.seconds // 3600, time_left.seconds // 60 % 60))

        conn.close()

    @commands.command(aliases=["$", "bal"])
    async def balance(self, ctx, user: discord.Member = None):
        """
        Return the user's account balance.
        """

        # Start bot typing
        await ctx.trigger_typing()

        # TODO: TEST ACCOUNTS NOT IN THE SERVER?

        author = user if user else ctx.message.author
        amount = self.format_symbol_currency(await
                                             self.fetch_bank_balance(author))

        await ctx.send("{} has {} in their account.".format(
            author.display_name, amount))

    @commands.command(aliases=["bf"])
    async def bet_flip(self, ctx, bet: str = None, face: str = None):
        """
        Bets an amount of money on a coin flip.
        Usage: ?bet_flip h 10 or ?bet_flip t 5
        """

        if face is None or bet is None:
            return

        # Start bot typing
        await ctx.trigger_typing()

        balance = await self.fetch_bank_balance(ctx.message.author)
        bet_dec = self.parse_currency(bet, balance)
        choice = face.strip().lower()

        # Handle invalid cases

        error = self.check_bet(balance, bet_dec)
        if error != "":
            await ctx.send(error)
            return

        # - Choice-related subcase
        if choice not in COIN_FLIP_CHOICES:
            await ctx.send("Please choose either h or t.")
            return

        # If all cases pass, perform the gamble

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        result = random.choice(COIN_FLIP_CHOICES)

        metadata = {"result": result, "channel": ctx.message.channel.id}

        amount = bet_dec if choice == result else -bet_dec
        await self.create_bank_transaction(c, ctx.message.author, amount,
                                           ACTION_BET_FLIP, metadata)
        conn.commit()

        message = "Sorry! {} lost {} (result was **{}**)."
        if choice == result:
            message = "Congratulations! {} won {} on **{}**"

        author_name = ctx.message.author.display_name

        await ctx.send(
            message.format(author_name, self.format_symbol_currency(bet_dec),
                           result))

        conn.close()

    @commands.command(aliases=["br"])
    async def bet_roll(self, ctx, bet: str = None):
        """
        Bets an amount of currency on a D100 roll.
        Usage: ?bet_roll 100 or ?br all
        """

        if bet is None:
            return

        # Start bot typing
        await ctx.trigger_typing()

        balance = await self.fetch_bank_balance(ctx.message.author)
        bet_dec = self.parse_currency(bet, balance)

        # Handle invalid cases
        error = self.check_bet(balance, bet_dec)
        if error != "":
            await ctx.send(error)
            return

        # If all cases pass, perform the gamble

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        result = random.randrange(1, 101)
        amount_returned = Decimal(0)

        for case, amount in self.currency["bet_roll_cases"]:
            if result <= case:
                amount_returned = bet_dec * amount
                break

        metadata = {
            "result": result,
            "bet": str(bet_dec),
            "returned": self.format_currency(amount_returned),
            "channel": ctx.message.channel.id
        }

        await self.create_bank_transaction(c, ctx.message.author,
                                           amount_returned - bet_dec,
                                           ACTION_BET_ROLL, metadata)

        conn.commit()

        message = "Sorry! {un} lost {am} (result was **{re}**)."
        if amount_returned == bet_dec:
            message = "{un} broke even (result was **{re}**)."
        elif amount_returned > bet_dec:
            message = "Congratulations! {un} won [net] {am} (result was " \
                      "**{re}**)."

        author_name = ctx.message.author.display_name

        amount_msg_multiplier = -1 if amount_returned < bet_dec else 1
        bet_str = self.format_symbol_currency(
            amount_msg_multiplier * (amount_returned - bet_dec))

        await ctx.send(message.format(un=author_name, am=bet_str, re=result))

        conn.close()

    @commands.command()
    async def give(self, ctx, user: discord.Member = None, amount: str = None):
        """
        Gives some amount of currency to another user.
        """

        # Start bot typing
        await ctx.trigger_typing()

        if not user or amount is None:
            await ctx.send("Usage: ?give [user] [amount]")
            return

        balance = await self.fetch_bank_balance(ctx.message.author)

        if balance <= 0:
            await ctx.send("You're too broke to give anyone anything!")
            return

        amount_dec = self.parse_currency(amount, balance)

        # Handle invalid cases

        if amount_dec is None:
            await ctx.send("Invalid quantity: '{}'.".format(amount))
            return

        if amount_dec <= 0:
            await ctx.send("You cannot give {}!".format(
                self.format_symbol_currency(amount_dec)))
            return

        if amount_dec > balance:
            await ctx.send("You do not have that much money!")
            return

        if user.id == ctx.message.author.id:
            await ctx.send(":thinking:")
            return

        # If all cases pass, gift the money

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

        await self.create_bank_transaction(c, ctx.message.author, -amount_dec,
                                           ACTION_GIFTER, gifter_metadata)

        await self.create_bank_transaction(c, user, amount_dec, ACTION_GIFTEE,
                                           giftee_metadata)

        conn.commit()

        await ctx.send("{} gave {} to {}!".format(
            grn, self.format_symbol_currency(amount_dec), gen))

        conn.close()


def setup(bot):
    bot.add_cog(Currency(bot))
