#! /usr/bin/env python3
#
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

import discord
import os
import sqlite3
import sys

from datetime import datetime
from discord.ext.commands import Context
from pytz import timezone

from canary.bot import bot
from canary.cogs.utils.checks import is_developer, is_moderator

startup = [
    f"cogs.{c}"
    for c in (
        "banner",
        "currency",
        "customreactions",
        "games",
        "helpers",
        "images",
        "info",
        "memes",
        "mod",
        "music",
        "quotes",
        "reminder",
        "roles",
        "score",
        "subscribers",  # Do not remove this terminating comma.
    )
]


@bot.event
async def on_ready():
    if bot.config.dev_log_webhook_id and bot.config.dev_log_webhook_token:
        webhook_string = " and to the log webhook"
    else:
        webhook_string = ""
    sys.stdout.write(f"Bot is ready, program output will be written to a " f"log file{webhook_string}.\n")
    sys.stdout.flush()
    bot.dev_logger.info(f"Logged in as {bot.user.name} ({bot.user.id})")


@bot.command()
@is_moderator()
async def load(ctx, extension_name: str):
    """
    Load a specific extension. Specify as cogs.<name>
    """
    try:
        bot.load_extension(extension_name)
    except (AttributeError, ImportError) as e:
        await ctx.send(f"```{type(e).__name__}: {str(e)}\n```")

        return
    await ctx.send(f"{extension_name} loaded.")


@bot.command()
@is_moderator()
async def unload(ctx: Context, extension_name: str):
    """
    Unload a specific extension. Specify as cogs.<name>
    """
    try:
        bot.unload_extension(extension_name)
    except Exception as e:
        await ctx.send(f"```{type(e).__name__}: {str(e)}\n```")
        return

    await ctx.send(f"{extension_name} unloaded.")


@bot.command()
@is_developer()
async def restart(ctx: Context):
    """
    Restart the bot
    """
    bot.dev_logger.info("Bot restart")
    await ctx.send("https://streamable.com/dli1")
    python = sys.executable
    os.execl(python, python, *sys.argv)


@bot.command()
@is_moderator()
async def sleep(ctx: Context):
    """
    Shut down the bot
    """
    bot.dev_logger.info("Received sleep command. Shutting down bot")
    await ctx.send("Bye")
    await bot.logout()


@bot.command()
@is_moderator()
async def backup(ctx: Context):
    """
    Send the current database file to the owner
    """
    current_time = datetime.now(tz=timezone("America/New_York")).strftime("%Y%m%d-%H:%M")
    backup_filename = "Martlet{}.db".format(current_time)
    await ctx.send(content="Here you go", file=discord.File(fp=bot.config.db_path, filename=backup_filename))
    bot.dev_logger.info("Database backup")


@bot.listen()
async def on_member_join(member):
    member_id = member.id
    name = str(member)
    conn = sqlite3.connect(bot.config.db_path)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO Members VALUES (?,?)", (member_id, name))
    conn.commit()
    conn.close()


@bot.listen()
async def on_user_update(before, after):
    if str(before) == str(after):
        return

    user_id = after.id
    new_name = str(after)
    conn = sqlite3.connect(bot.config.db_path)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO Members VALUES (?,?)", (user_id, new_name))
    conn.commit()
    conn.close()


def main():
    if os.name == "posix":
        import uvloop
        uvloop.install()

    for extension in startup:
        try:
            bot.load_extension(extension)
        except Exception as e:
            bot.dev_logger.warning(f"Failed to load extension {extension}\n" f"{type(e).__name__}: {e}")

    bot.run(bot.config.discord_key)


if __name__ == "__main__":
    main()
