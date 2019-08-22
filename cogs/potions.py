import discord
from discord.ext import commands

import sqlite3
import random

from decimal import Decimal

from .utils.auto_incorrect import auto_incorrect
from .utils.mix import generate_mix


ANNOYING_CHILD_CHANCE = 0.4
DRUNK_MESSAGE_TEMPLATE = "{user} 📣 {message}"

DISAPPOINTMENT_REACTS = (
    (":rolling_eyes:", ),
    (":grimacing:", ),
    (":regional_indicator_x:", ),
    (":regional_indicator_n:", ":regional_indicator_o:"),
)

PRAISE_REACTS = (
    (":100:", ),
    (":point_up:", ),
    (
        ":regional_indicator_t:",
        ":regional_indicator_r:",
        ":regional_indicator_u:",
        ":regional_indicator_e:",
    ),
    (
        ":regional_indicator_y:",
        ":regional_indicator_e:",
        ":regional_indicator_s:",
    ),
    (":heart:", ),
)


async def annoying_child(message: discord.Message):
    if random.random() < ANNOYING_CHILD_CHANCE:
        message.channel.send(generate_mix(message.content))


async def drunk(message: discord.Message):
    await message.channel.send(DRUNK_MESSAGE_TEMPLATE.format(
        user=message.author.display_name,
        message=auto_incorrect(message.content)))
    await message.channel.delete()


async def disappointment(message: discord.Message):
    reacts = random.choice(DISAPPOINTMENT_REACTS)
    for r in reacts:
        await message.add_reaction(r)


async def praise(message: discord.Message):
    reacts = random.choice(PRAISE_REACTS)
    for r in reacts:
        await message.add_reaction(r)


POTIONS = {
    "annoying_child": {
        "name": "Cursed Potion of Being Followed by an Annoying "
                "{bot_name}-Child",
        "description": "{bot_name} will follow the afflicted person around "
                       "and repeat some things they say in an annoying tone.",
        "function":  annoying_child
    },
    "drunk": {
        "name": "Cursed Potion of Inebriation",
        "description": "Everything the afflicted person says will be slurred, "
                       "almost beyond comprehension.",
        "function": drunk
    },
    "disappointment": {
        "name": "Cursed Potion for the Disappointing",
        "description": "{bot_name} will follow the afflicted person around "
                       "and undermine their confidence.",
        "function": disappointment
    },
    "praise": {
        "name": "Blessed Potion for the Praise-Worthy",
        "description": "{bot_name} will respond to a user's messages with "
                       "positive reinforcement.",
        "function": praise
    }
}


class Potions:
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.user == self.bot.user:
            return

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        c.execute("SELECT * FROM ActivePotions WHERE AffectedUserID = ?",
                  message.user.id)

        potions_on_user = c.fetchall()

        for p in potions_on_user:
            if p[4] in POTIONS:
                await POTIONS[p[4]]["function"](message)
