#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) idoneam (2016-2019)
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

# discord-py requirements
import discord

# Other utilities
import os
import sys
import subprocess
from datetime import datetime
from pytz import timezone
from bot import bot

from cogs.utils.checks import is_developer, is_moderator

# List the extensions (modules) that should be loaded on startup.
startup = [
    "cogs.currency",
    "cogs.games",
    "cogs.helpers",
    "cogs.images",
    "cogs.info",
    "cogs.memes",
    "cogs.mod",
    "cogs.quotes",
    "cogs.reminder",
    "cogs.roles",
    "cogs.score",
    "cogs.subscribers",
]

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
    sys.stdout.write(
        'Bot is ready, program output will be written to a log file.\n')
    sys.stdout.flush()
    bot.logger.info('Logged in as {} ({})'.format(bot.user.name, bot.user.id))


@bot.command()
@is_moderator()
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
@is_moderator()
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
@is_developer()
async def restart(ctx):
    """
    Restart the bot
    """
    bot.logger.info('Bot restart')
    await ctx.send('https://streamable.com/dli1')
    python = sys.executable
    os.execl(python, python, *sys.argv)


@bot.command()
@is_moderator()
async def sleep(ctx):
    """
    Shut down the bot
    """
    bot.logger.info('Received sleep command. Shutting down bot')
    await ctx.send('Bye')
    await bot.logout()


@bot.command()
@is_developer()
async def update(ctx):
    """
    Update the bot by pulling changes from the git repository
    """
    bot.logger.info('Update Git repository')
    shell_output = subprocess.check_output("git pull {}".format(
        bot.config.repository),
                                           shell=True)
    status_message = shell_output.decode("unicode_escape")
    await ctx.send('`{}`'.format(status_message))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    key = message.content.lower()
    if key in MARTY_RESPONSES:
        await message.channel.send(MARTY_RESPONSES[key])
        return

    await bot.process_commands(message)


@bot.command()
@is_moderator()
async def backup(ctx):
    """
    Send the current database file to the owner
    """
    current_time = datetime.now(
        tz=timezone('America/New_York')).strftime('%Y%m%d-%H:%M')
    backup_filename = 'Martlet{}.db'.format(current_time)
    await ctx.send(content='Here you go',
                   file=discord.File(fp=bot.config.db_path,
                                     filename=backup_filename))
    bot.logger.info('Database backup')


if __name__ == "__main__":
    for extension in startup:
        try:
            bot.load_extension(extension)
        except Exception as e:
            bot.logger.warning('Failed to load extension {}\n{}: {}'.format(
                extension,
                type(e).__name__, e))
    bot.run(bot.config.discord_key)
