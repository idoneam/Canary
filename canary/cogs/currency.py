# Copyright (C) idoneam (2016-2022)
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

import datetime

import aiosqlite
import discord
import json
import random

from decimal import Decimal, InvalidOperation
from discord.ext import commands
from tabulate import tabulate

from ..bot import Canary
from ..config.config import CurrencyModel
from .base_cog import CanaryCog
from .utils.members import add_member_if_needed
from .utils.paginator import Pages


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
HANGMAN_REWARD = "hangman_reward"

TRANSACTION_ACTIONS = (
    ACTION_INITIAL_CLAIM,
    ACTION_CLAIM,
    ACTION_BET_FLIP,
    ACTION_BET_ROLL,
    ACTION_GIFTER,
    ACTION_GIFTEE,
    HANGMAN_REWARD,
)


class Currency(CanaryCog):
    def __init__(self, bot: Canary):
        super().__init__(bot)
        self.currency: CurrencyModel = self.bot.config.currency

        self.symbol: str = self.currency.symbol
        self.prec: int = self.currency.precision
        self.initial: Decimal = Decimal(self.currency.initial)

    async def fetch_all_balances(self) -> list[tuple[str, str, Decimal]]:
        # after
        return [
            (user_id, name, self.db_to_currency(balance))
            for user_id, name, balance in (
                await self.fetch_list(
                    "SELECT BT.UserID, M.Name, IFNULL(SUM(BT.Amount), 0) "
                    "FROM BankTransactions AS BT, Members as M "
                    "WHERE BT.UserID = M.ID GROUP BY UserID"
                )
            )
        ]

    async def fetch_bank_balance(self, user: discord.Member) -> Decimal:
        balance_t = await self.fetch_one(
            "SELECT IFNULL(SUM(Amount), 0) FROM BankTransactions WHERE UserID = ?", (user.id,)
        )
        return self.db_to_currency(balance_t[0]) if balance_t is not None else Decimal(0)

    async def create_bank_transaction(
        self, db: aiosqlite.Connection, user: discord.Member, amount: Decimal, action: str, metadata: dict
    ) -> None:
        # Don't create another connection in this function in order to properly
        # transaction-ify a series of bank "transactions".

        if action not in TRANSACTION_ACTIONS:
            self.bot.logger.info("Error: Invalid bank transaction '{}'".format(action))
            return

        now = int(datetime.datetime.now().timestamp())

        await db.execute("PRAGMA foreign_keys = ON")
        await add_member_if_needed(self, db, user.id)
        await db.execute(
            "INSERT INTO BankTransactions(UserID, Amount, Action, Metadata, Date) VALUES(?, ?, ?, ?, ?)",
            (user.id, self.currency_to_db(amount), action, json.dumps(metadata), now),
        )

    @staticmethod
    def parse_currency(amount: str, balance: Decimal) -> Decimal | None:
        if amount.lower().strip() in CURRENCY_ALL:
            return balance

        try:
            return Decimal(amount)
        except InvalidOperation:
            # Value error (invalid conversion)
            return None

    def currency_to_db(self, amount: Decimal) -> int:
        return int(amount * Decimal(10 ** self.prec))

    def db_to_currency(self, amount: int) -> Decimal:
        return Decimal(amount) / Decimal(10 ** self.prec)

    def format_currency(self, amount: Decimal) -> str:
        return ("{:." + str(self.prec) + "f}").format(amount)

    def format_symbol_currency(self, amount: Decimal) -> str:
        return self.symbol + self.format_currency(amount)

    @staticmethod
    def check_bet(balance: Decimal, bet: Decimal) -> str | None:
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

    async def get_last_claim_time(self, db: aiosqlite.Connection, author: discord.Member | discord.User) -> int | None:
        claim_time_t = await self.fetch_one(
            "SELECT IFNULL(MAX(Date), 0) FROM BankTransactions WHERE UserID = ? AND Action = ?",
            (author.id, ACTION_INITIAL_CLAIM),
            db=db,
        )
        return claim_time_t[0] if claim_time_t is not None else None

    @commands.command()
    async def initial_claim(self, ctx: commands.Context):
        """
        Claim's the user's start-up grant currency.
        """

        await ctx.trigger_typing()

        author = ctx.message.author
        author_name = author.display_name

        db: aiosqlite.Connection
        async with self.db() as db:
            claim_time = await self.get_last_claim_time(db, author)

            if claim_time is None:
                return

            if claim_time > 0:
                await ctx.send(f"{author_name} has already claimed their initial currency.")
                return

            await self.create_bank_transaction(
                db,
                author,
                self.initial,
                ACTION_INITIAL_CLAIM,
                {"channel": ctx.message.channel.id},
            )
            await db.commit()

        await ctx.send(
            f"{author_name} claimed their initial {self.format_symbol_currency(self.initial)}!"
        )

    @commands.command()
    async def claim(self, ctx: commands.Context):
        """
        Claim's the user's hourly currency.
        """

        # Start bot typing
        await ctx.trigger_typing()

        author = ctx.message.author
        threshold = datetime.datetime.now() - CLAIM_WAIT_TIME

        db: aiosqlite.Connection
        async with self.db() as db:
            claim_time = await self.get_last_claim_time(db, author)

            if claim_time is None:
                return

            last_claimed = datetime.datetime.fromtimestamp(claim_time)

            if last_claimed < threshold:
                metadata = {"channel": ctx.message.channel.id}
                await self.create_bank_transaction(db, author, CLAIM_AMOUNT, ACTION_CLAIM, metadata)
                await db.commit()

                author_name = author.display_name if author else ":b:roken bot"
                await ctx.send(f"{author_name} claimed {self.format_symbol_currency(CLAIM_AMOUNT)}!")
                return

        time_left = last_claimed - threshold
        await ctx.send(f"Please wait {time_left.seconds // 3600}h {time_left.seconds // 60 % 60}m to claim again!")

    @commands.command(aliases=["$", "bal"])
    async def balance(self, ctx: commands.Context, user: discord.Member = None):
        """
        Return the user's account balance.
        """

        # Start bot typing
        await ctx.trigger_typing()

        # TODO: TEST ACCOUNTS NOT IN THE SERVER?

        author = user if user else ctx.message.author
        amount = self.format_symbol_currency(await self.fetch_bank_balance(author))

        await ctx.send(f"{author.display_name} has {amount} in their account.")

    @commands.command(aliases=["bf"])
    async def bet_flip(self, ctx: commands.Context, bet: str | None = None, face: str | None = None):
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

        if (error := self.check_bet(balance, bet_dec)) is not None:
            await ctx.send(error)
            return

        # - Choice-related subcase
        if choice not in COIN_FLIP_CHOICES:
            await ctx.send("Please choose either h or t.")
            return

        # If all cases pass, perform the gamble

        result = random.choice(COIN_FLIP_CHOICES)
        metadata = {"result": result, "channel": ctx.message.channel.id}
        amount = bet_dec if choice == result else -bet_dec

        db: aiosqlite.Connection
        async with self.db() as db:
            await self.create_bank_transaction(db, ctx.message.author, amount, ACTION_BET_FLIP, metadata)
            await db.commit()

        message = "Sorry! {} lost {} (result was **{}**)."
        if choice == result:
            message = "Congratulations! {} won {} on **{}**"

        author_name = ctx.message.author.display_name

        await ctx.send(message.format(author_name, self.format_symbol_currency(bet_dec), result))

    @commands.command(aliases=["br"])
    async def bet_roll(self, ctx: commands.Context, bet: str | None = None):
        """
        Bets an amount of currency on a D100 roll.
        Usage: ?bet_roll 100 or ?br all
        """

        if bet is None:
            return

        # Start bot typing
        await ctx.trigger_typing()

        balance: Decimal = await self.fetch_bank_balance(ctx.message.author)
        bet_dec = self.parse_currency(bet, balance)

        # Handle invalid cases
        if (error := self.check_bet(balance, bet_dec)) != "":
            await ctx.send(error)
            return

        # If all cases pass, perform the gamble

        result = random.randrange(1, 101)
        amount_returned = Decimal(0)

        for case, amount in zip(self.currency.bet_roll_cases, self.currency.bet_roll_returns):
            if result <= case:
                amount_returned = bet_dec * amount
                break

        metadata = {
            "result": result,
            "bet": str(bet_dec),
            "returned": self.format_currency(amount_returned),
            "channel": ctx.message.channel.id,
        }

        db: aiosqlite.Connection
        async with self.db() as db:
            await self.create_bank_transaction(
                db, ctx.message.author, amount_returned - bet_dec, ACTION_BET_ROLL, metadata
            )
            await db.commit()

        if amount_returned == bet_dec:
            message_tpl = "{un} broke even (result was **{re}**)."
        elif amount_returned > bet_dec:
            message_tpl = "Congratulations! {un} won [net] {am} (result was **{re}**)."
        else:
            message_tpl = "Sorry! {un} lost {am} (result was **{re}**)."

        author_name = ctx.message.author.display_name

        amount_msg_multiplier = -1 if amount_returned < bet_dec else 1
        bet_str = self.format_symbol_currency(amount_msg_multiplier * (amount_returned - bet_dec))

        await ctx.send(message_tpl.format(un=author_name, am=bet_str, re=result))

    @commands.command()
    async def give(self, ctx: commands.Context, user: discord.Member | None = None, amount: str | None = None):
        """
        Gives some amount of currency to another user.
        """

        # Start bot typing
        await ctx.trigger_typing()

        if not user or amount is None:
            await ctx.send("Usage: ?give [user] [amount]")
            return

        balance: Decimal = await self.fetch_bank_balance(ctx.message.author)

        if balance <= 0:
            await ctx.send("You're too broke to give anyone anything!")
            return

        amount_dec = self.parse_currency(amount, balance)

        # Handle invalid cases

        if amount_dec is None:
            await ctx.send(f"Invalid quantity: '{amount}'.")
            return

        if amount_dec <= 0:
            await ctx.send(f"You cannot give {self.format_symbol_currency(amount_dec)}!")
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

        gifter_metadata = {"giftee": user.id, "channel": ctx.message.channel.id}
        giftee_metadata = {"gifter": ctx.message.author.id, "channel": ctx.message.channel.id}

        db: aiosqlite.Connection
        async with self.db() as db:
            await self.create_bank_transaction(db, ctx.message.author, -amount_dec, ACTION_GIFTER, gifter_metadata)
            await self.create_bank_transaction(db, user, amount_dec, ACTION_GIFTEE, giftee_metadata)
            await db.commit()

        await ctx.send(f"{grn} gave {self.format_symbol_currency(amount_dec)} to {gen}!")

    @commands.command(aliases=["lb"])
    async def leaderboard(self, ctx):
        """
        Currency rankings
        """

        await ctx.trigger_typing()

        balances = sorted(await self.fetch_all_balances(), reverse=True, key=lambda b: b[2])

        if len(balances) == 0:
            await ctx.send("Leaderboards are not yet available for this server, please collect some currency.")
            return

        table = []
        table_list = []
        counter = 1

        for (_user_id, name, balance) in balances:
            table.append((counter, name, self.format_symbol_currency(balance)))
            if counter % 7 == 0 or counter == len(balances):
                table_list.append(tabulate(table[:counter], headers=["Rank", "Name", "Balance"], tablefmt="fancy_grid"))
                del table[:]
            counter += 1

        p = Pages(ctx, item_list=table_list, title="Currency ranking", display_option=(0, 1), editable_content=False)

        await p.paginate()


def setup(bot):
    bot.add_cog(Currency(bot))
