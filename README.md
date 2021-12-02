# Canary

 [![Discord](https://img.shields.io/discord/236668784948019202.svg)](https://discord.gg/HDHvv58)
 [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Canary is a Python3 bot designed for the McGill University Community Discord Server. The bot provides helper functions to users, as well as fun functions, a quote database and custom greeting messages.

## Build Statuses

| **Master**  | [![Prod Dependencies](https://github.com/idoneam/Canary/workflows/Prod%20Dependencies/badge.svg?branch=master)](https://github.com/idoneam/Canary/actions?query=workflow%3A%22Prod+Dependencies%22+branch%3Amaster) |
| ------- | --------------------------------------------------------------------------------------------------------------- |
| **Dev** | [![Dev Dependencies](https://github.com/idoneam/Canary/workflows/Dev%20Dependencies/badge.svg?branch=dev)](https://github.com/idoneam/Canary/actions?query=workflow%3A%22Dev+Dependencies%22+branch%3Adev)  |

## Installation

1. If you wish to use the `update` command to update to the latest version of the bot, configure your github account in
your environment of choice and clone into the repository with:

```bash
git clone https://github.com/idoneam/Canary
```

2. Dependencies are managed with poetry which can be installed via pip with:

```bash
python3 -m pip install poetry
```

3. Dependencies may be installed using poetry with the following command:

```bash
poetry install --no-dev
```

4. Use of the LaTeX equation functionality requires a working LaTeX installation (at the very minimum, `latex` and `dvipng` must be present). The easiest way to do this is to install TeX Live (usually possible through your distro's package manager, or through TeX Live's own facilities for the latest version). See the [TeX Live site](https://tug.org/texlive/) for more information.

5. Development dependencies (YAPF and `pytest`) can be installed alongside all other dependencies with:

```bash
poetry install
```

6. You may enter the virtual environment generated by the pipenv installation with: `$ poetry shell` or simply run the bot with `$ poetry run python3 Main.py`

7. In order to run bots on Discord, you need to [create a bot account](https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token).

8. In the Discord Developer Portal, you must enable the "Presence" and "Server Members" Privileged Gateway Intents (In the Bot tab of your application)

You must set certain values in the `config.ini` file, in particular your Discord bot token (which you get in the previous link) and the values in the `[Server]` section.
<details><summary>Click here to see descriptions for a few of those values</summary><p>

(For values that use Discord IDs, see [this](https://support.discordapp.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-) to know how to find them)

* `[Discord]`
  * `Key`: Your Discord bot token.
* `[Server]`
    * `ServerID`: Your server ID.
    * `CommandPrefix`: What a message should begin with to be considered a command.
    * `BotName`: The name of your bot.
* `[Emoji]`
    * `UpvoteEmoji`: The name of your upvote emoji (for the score function).
    * `DownvoteEmoji`: The name of your downvote emoji.
    * `BannerVoteEmoji`: The name of the emoji that is used to vote on Banner of the Week Contests.
* `[Roles]`
    * `ModeratorRole`: The name of the role that your moderators have (for functions like DMing users).
    * `DeveloperRole`: The name of the role that your developers have (for functions like restarting the bot). This could be the same role than moderator.
    * `McgillianRole`: The name of the role that verified McGillians have.
    * `HonoraryMcGillianRole`: The name of the role that Honorary McGillians (verified Non-McGillians) have.
    * `BannerRemindersRole`: The name of the role that is pinged when a Banner of the Week Contest starts.
    * `BannerWinnerRole`: The name of the role that is given to users that win a Banner of the Week Contest.
    * `TrashTierBannerRole`: The name of the role that is given to users that are banned from submitting in Banner of the Week Contests.
    * `NoFoodSpottingRole`: The name of the role assigned to abusers of the foodspotting command that will prevent them from using it.
* `[Channels]`
    * `ReceptionChannel`: The name of the channel that will receive messages sent to the bot through the `answer` command (and where messages sent by mods to users with the `dm` command will be logged)
    * `BannerOfTheWeekChannel`: The name of the channel where winning submissions for Banner of the Week Contests are sent.
    * `BannerSubmissionsChannel`: The name of the channel where submissions for Banner of the Week Contests are sent. This is where users vote.
    * `BannerConvertedChannel`: The name of the channel where the converted submissions for Banner of the Week Contests are sent. This is where the bot will fetch the winning banner.
    * `FoodSpottingChannel`: The name of the channel where foodspotting posts are sent.
    * `MetroStatusChannel`: The name of the channel where metro status alerts are sent.
    * `BotsChannel`: The name of the channel for bot spamming.
* `[Meta]`
  * `Repository`: The HTTPS remote for this repository, used by the `update` command as the remote when pulling.
* `[Logging]`
    * `LogLevel`: [See this for a list of levels](https://docs.python.org/3/library/logging.html#levels). Logs from exceptions and commands like `mix` and `bac` are at the `info` level. Logging messages from the level selected *and* from more severe levels will be sent to your logging file. For example, setting the level to `info` also sends logs from `warning`, `error` and `critical`, but not  from `debug`.
    * `LogFile`: The file where the logging output will be sent (will be created there by the bot if it doesn't exist). Note that all logs are sent there, including those destined for devs and those destined for mods.
    * `DevLogWebhookID`: Optional. If the ID of a webhook is input (and it's token below), logs destined for devs will also be sent to it. These values are contained in the discord webhook url: [discordapp.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN](discordapp.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN)
    * `DevLogWebhookToken`: Optional. See above.
    * `ModLogWebhookID`: Optional. If the ID of a webhook is input (and it's token below), logs destined for mods will also be sent to it. See the URL above to see how to find those values.
    * `ModLogWebhookToken`: Optional. See above.
* `[DB]`
  * `Schema`: Location of the Schema file that creates tables in the database (This file already exists so you shouldn't have to change this unless you rename it or change its location).
  * `Path`: Your database file path (will be created there by the bot if it doesn't exist).
* `[Helpers]`
  * `CourseTemplate`: McGill course schedule URL. **Changes every school year.**
  * `CourseSearchTemplate`: McGill course search URL. **Changes every school year.**
  * `GCWeatherURL`: Government of Canada weather URL. **Region-specific.**
  * `GCWeatherAlertURL`: Government of Canada weather alerts URL. **Region-specific.**
  * `WttrINTemplate`: [http://wttr.in/](http://wttr.in/) URL template. **Region-specific.**
  * `TepidURL`: [TEPID](https://github.com/ctf/TEPID-Server) screensaver endpoint for printer status.
* `[Subscribers]`
  * `FoodRecallChannel`: Channel where you want CFIA recall notices posted.
  * `FoodRecallLocationFilter`: Regions you want to receive CFIA recall notices for.
  * `FoodSpottingChannel`: Channel where you want foodspotting posts to be sent, ideally in a dedicated channel.
  * `NoFoodSpottingRole`: Name of role assigned to abusers of the foodspotting command that will prevent them from using it.
  * `MetroStatusChannel`: Channel where you want metro status alerts to be sent, ideally in a dedicated channel with opt-in read permissions for users.
* `[Currency]`
  * `Name`: The name of the bot currency.
  * `Symbol`: The currency's symbol (e.g. `$`).
  * `Precision`: How many decimal digits after the decimal point are "official" for the currency.
  * `Initial`: How much currency is given out by the `initial_claim` command.
  * `SalaryBase`: *Currently unused.*
  * `Inflation`: *Currently unused.*
* `[IncomeTax]`: *Currently unused.*
* `[AssetTax]`: *Currently unused.*
* `[OtherTax]`: *Currently unused.*
* `[Betting]`:
  * `RollCases`: Intervals for `bet_roll`. For example, a value of `66, 90, 99, 100` gives the intervals
      `[1, 66]`, `[67, 90]`, `[91, 99]`, and `[100]`.
  * `RollReturns`: The multiplier return for each interval. For example, a value of `0, 2, 4, 10` with the intervals
      described above gives a 0x return for `random <= 66`, a 2x return for `66 < random <= 90`, a 4x return for
      `90 < random <= 99`, and a 10x return for `random == 100`.
* `[Images]`
    * `MaxImageSize`: Maximum image size to allow to be sent without compression, in bytes.
    * `ImageHistoryLimit`: Maximum amount of messages to check in history for an image before giving up.
    * `MaxRadius`: Maximum radius used for various image transformation functions.
    * `MaxIterations`: Maximum iterations allowed for various image transformation functions.
* `[Games]`:
    * `HangmanNormalWin`: Value of normal hangman win.
    * `HangmanCoolWin`: Value of cool hangman win.
    * `HangmanTimeOut`: Time before a hangman game will time out if not interacted with.
* `[AssignableRoles]`:
    * `Pronouns`: Comma separated list of pronoun roles in server.
    * `Fields`: Comma separated list of field of study roles in server.
    * `Faculties`: Comma separated list of faculty roles in server.
    * `Years`: Comma separated list of year roles in server.
    * `Generics`: Comma separated list of generic or meme roles in server.
</p>
</details>

## Testing functions

If you installed all dev dependencies, you can run tests with `poetry run pytest`.

## Running the bot

Run `poetry run python Main.py` in your shell. Ensure that your Discord token is set in the `config.ini` file within the `config` directory.

### Docker Container

A Docker Container is provided for easier development.

#### Building the Image

Freeze requirements to a requirements.txt

```
poetry export -f requirements.txt > requirements.txt
```

From within the root of the repository:

```
docker build -t canary:latest .
```

#### Running the Container

From within the root of the repository:

```
docker run -v $(pwd):/mnt/canary canary:latest
```

Optionally provide the `-d` flag to run the container in detached state.

Note that the current host directory is mounted into the container, any changes to log files, pickles, configuration are reflected
across the host and the container.

## Code Linting

We format our code using PSF's [black](https://github.com/psf/black). Our builds will reject code that do not conform to the standards defined in [`pyproject.toml`](https://black.readthedocs.io/en/stable/pyproject_toml.html) . You may format your code using:

```
poetry run black .
```

and ensure your code conforms to our linting with :

```
poetry run black --diff .
```

## Contributions

Contributions are welcome, feel free to fork our repository and open a pull request or open an issue. Please [review our contribution guidelines](https://github.com/idoneam/Canary/blob/master/.github/contributing.md) before contributing.
