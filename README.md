# Canary
Python3 Discord bot.

## Installation

Install dependencies with `python3 -m pip install --user -r requirements.txt`. If you'd like to learn more about them, dependencies are listed in `requirements.txt` - you can search for them in the [Python Package Index](https://pypi.python.org).

In order to run bots on Discord, you need to [create a bot account](https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token).

In your terminal, export your Discord token as an environment variable.
```
$ export DISCORD_TOKEN='your-token-here'
```
You will have to do this each time you restart your shell. We recommend setting up a Bash script for bot startup.

## Running the bot
Run `python3 Main.py` in your shell. Make sure `DB_PATH` in db.py is set correctly and that the `.db` file exists.
