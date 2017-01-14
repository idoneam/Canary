# Martlet
Discord bot for McGill

## Dependencies

* [discord.py](https://github.com/Rapptz/discord.py)
* [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/)
* [sympy](https://github.com/sympy/sympy)
* [requests](https://pypi.python.org/pypi/requests/)
* [cleverbot](https://github.com/folz/cleverbot.py)
* [wolframalpha](https://github.com/jaraco/wolframalpha)
* [dvipng](https://sourceforge.net/projects/dvipng/) (Bundled with [MiKTeX](https://miktex.org/) on Windows)

Dependencies are available via `python3 -m pip install --user requirements.txt` except for dvipng; see their respective links for detailed installation instructions.

## Installation
In order to run bots on Discord, you need to [create a bot account](https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token).

In your terminal, export your Discord token as an environment variable.
```
$ export DISCORD_TOKEN='your-token-here'
```
You will have to do this each time you restart your shell.
