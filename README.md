# Canary
 [![Discord](https://img.shields.io/discord/236668784948019202.svg)](https://discord.gg/HDHvv58)

Canary is a Python3 bot designed for the McGill University Community Discord Server. The bot provides helper functions to users, as well as fun functions, a quote database and custom greeting messages. 

## Build Statuses

| Master |  [![Build Status](https://travis-ci.org/idoneam/Canary.svg?branch=master)](https://travis-ci.org/idoneam/Canary)  |
|--------|---|
| **Dev**    |  [![Build Status](https://travis-ci.org/idoneam/Canary.svg?branch=dev)](https://travis-ci.org/idoneam/Canary) |

## Installation

Install dependencies with `python3 -m pip install --user -r requirements.txt`. If you'd like to learn more about them, dependencies are listed in `requirements.txt` - you can search for them in the [Python Package Index](https://pypi.python.org).

In order to run bots on Discord, you need to [create a bot account](https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token).

Set your Discord bot token in the `config.ini` file within the `config` directory. Also change your Database file path as well as Greeting and Farewell messages, if desired.

## Running the bot
Run `python3 Main.py` in your shell. Ensure that your Discord token is set in the `config.ini` file within the `config` directory.

## Code Linting
We format our code using Google's [YAPF](https://github.com/google/yapf). Our builds will reject code that do not conform to YAPF's standards. You may format your code using :

```
yapf --recursive --in-place .
```
and ensure your code conforms to our linting with :
```
yapf --diff --recursive .
```
## Contributions
Contributions are welcome, feel free to fork our repository and Open a Pull Request or Open an Issue.
