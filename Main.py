#!/usr/bin/env python3

# discord-py requirements
import asyncio
import discord
from discord.ext import commands
import asyncio

# for database
import sqlite3

# logger
import logging

# Other utilities
import os
import sys
import subprocess
from config import parser
import random
from datetime import datetime
from pytz import timezone

# List the extensions (modules) that should be loaded on startup.
startup = [
    "cogs.reminder", "cogs.memes", "cogs.helpers", "cogs.mod", "cogs.score",
    "cogs.quotes", "cogs.images", "cogs.currency"
]

bot = commands.Bot(command_prefix='?', case_insensitive=True)

# Logging configuration
logger = logging.getLogger('discord')
logger.setLevel(logging.ERROR)
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(
    logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# TODO: SHOULD BE DB
MARTY_RESPONSES = {
    "dammit marty":
    ":c",
    "worm":
    "walk without rhythm, and it won't attract the worm.",
    "hey":
    "whats going on?",
    "this is so sad, marty play despacito":
    "`Now playing:` https://www.youtube.com/watch?v=kJQP7kiw5Fk"
}


@bot.event
async def on_ready():
    print('Logged in as {0} ({1})'.format(bot.user.name, bot.user.id))


@bot.command()
@commands.has_role("Discord Moderator")
async def load(ctx, extension_name: str):
    """
    Load a specific extension. Specify as cogs.<name>
    """
    try:
        bot.load_extension(extension_name)
    except (AttributeError, ImportError) as e:
        await ctx.send("```{}: {}\n```".format(type(e).__name__, str(e)))

        return
    await ctx.send("{} loaded.".format(extension_name))


@bot.command()
@commands.has_role("Discord Moderator")
async def unload(ctx, extension_name: str):
    """
    Unload a specific extension. Specify as cogs.<name>
    """
    try:
        bot.unload_extension(extension_name)
    except Exception as e:
        await ctx.send("```{}: {}\n```".format(type(e).__name__, str(e)))
        return

    await ctx.send("{} unloaded.".format(extension_name))


@bot.command()
@commands.has_role("Discord Moderator")
async def restart(ctx):
    """
    Restart the bot
    """
    await ctx.send('https://streamable.com/dli1')
    python = sys.executable
    os.execl(python, python, *sys.argv)


@bot.command()
@commands.has_role("Discord Moderator")
async def sleep(ctx):
    """
    Shut down the bot
    """
    await ctx.send('Bye')
    await bot.logout()
    print('Bot shut down')


@bot.command()
@commands.has_role("idoneam")
async def update(ctx):
    """
    Update the bot by pulling changes from the git repository
    """
    shell_output = subprocess.check_output("git pull", shell=True)
    status_message = shell_output.decode("unicode_escape")
    await ctx.send('`%s`' % status_message)


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.lower() in MARTY_RESPONSES:
        await message.channel.send(MARTY_RESPONSES[message.content.lower()])
        return

    await bot.process_commands(message)


@bot.command()
@commands.has_role("Discord Moderator")
async def backup(ctx):
    """
    Send the current database file to the owner
    """
    current_time = datetime.now(
        tz=timezone('America/New_York')).strftime('%Y%m%d-%H:%M')
    backup_filename = 'Martlet%s.db' % current_time
    await ctx.send(
        content='Here you go',
        file=discord.File(fp=bot.config.db_path, filename=backup_filename))


# Startup extensions
# If statement will only execute if we are running this file (i.e. won't run
# if it's imported)
if __name__ == "__main__":
    bot.config = parser.Parser()
    conn = sqlite3.connect(bot.config.db_path)
    c = conn.cursor()
    with open('./Martlet.schema') as fp:
        c.executescript(fp.read())
        conn.commit()
        conn.close()
    for extension in startup:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print('Failed to load extension {}\n{}: {}'.format(
                extension,
                type(e).__name__, e))
    bot.run(bot.config.discord_key)
