# Copyright (C) idoneam (2016-2023)
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

import codecs
import configparser
import decimal
import os

from pathlib import Path
from pydantic import BaseModel, BaseSettings

from typing import Literal

__all__ = [
    "CurrencyModel",
    "MusicModel",
    "Config",
]


class CurrencyModel(BaseModel):
    name: str = "cheeps"
    symbol: str = "ʧ"
    precision: int = 2
    initial: int = 1000

    bet_roll_cases: tuple[int, ...] = (66, 90, 99, 100)  # d100 roll threshold
    bet_roll_returns: tuple[int, ...] = (0, 2, 4, 10)  # multiplication factorys

    # TODO: Finish


class MusicModel(BaseModel):
    ban_role: str = "tone deaf"
    start_vol: float = 100.0


class ImagesModel(BaseModel):
    max_image_size: int = 8000000
    image_history_limit: int = 50
    max_radius: int = 500
    max_iterations: int = 20


class GamesModel(BaseModel):
    hm_norm_win: int = 10
    hm_cool_win: int = 20
    hm_timeout: int = 600


class RolesModel(BaseModel):
    pronouns: tuple[str, ...] = ("She/Her", "He/Him", "They/Them")
    fields: tuple[str, ...] = (
        "Accounting",
        "Agriculture",
        "Anatomy and Cell Biology",
        "Anthropology",
        "Architecture",
        "Biochemistry",
        "Bioengineering",
        "Biology",
        "Bioresource Engineering",
        "Chemical Engineering",
        "Chemistry",
        "Civil Engineering",
        "Classics",
        "cogito",
        "Commerce",
        "Computer Engineering",
        "Computer Science",
        "Computer Science/Biology",
        "Cultural Studies",
        "Desautels",
        "Economics",
        "Electrical Engineering",
        "English",
        "Experimental Medicine",
        "Finance",
        "Geography",
        "History",
        "Human Genetics",
        "Indigenous Studies",
        "International Development Studies",
        "Jewish Studies",
        "linguini",
        "mac kid",
        "Materials Engineering",
        "Math",
        "MBA",
        "Mechanical Engineering",
        "Medicine",
        "Microbiology and Immunology",
        "Neuroscience",
        "Nursing",
        "Pharmacology",
        "Philosophy",
        "Physical Therapy",
        "Physics",
        "Physiology",
        "Political Science",
        "Psychiatry",
        "Psychology",
        "Public Health",
        "Social Work",
        "Sociology",
        "Software Engineering",
        "Statistics",
        "Theology",
        "Urban Systems",
    )
    faculties: tuple[str, ...] = (
        "Science",
        "Engineering",
        "Management",
        "art you glad you're not in arts",
        "ArtSci",
        "Agriculture and Environment",
        "Continuing Studies",
        "Law",
        "Education",
        "Dentistry",
        "Music",
    )
    years: tuple[str, ...] = ("U0", "U1", "U2", "U3", "U4", "grad student", "workhere", "wenthere")
    generics: tuple[str, ...] = (
        "weeb",
        "weeb stomper",
        "crosswords",
        "stm_alertee",
        "Stardew",
        "R6",
        "CS:GO Popflash",
        "CS:GO Comp",
        "Minecraft",
        "Among Us",
        "Pokemon Go",
        "Secret Crabbo",
        "Warzone",
        "Monster Hunter",
        "undersad",
    )


class Config(BaseSettings):
    # Logging
    log_level: Literal["critical", "error", "warning", "info", "debug", "notset"] = "info"
    log_file: Path = Path.cwd() / "canary.log"

    dev_log_webhook_id: int | None = None
    dev_log_webhook_token: str | None = None
    mod_log_webhook_id: int | None = None
    mod_log_webhook_token: str | None = None

    # Discord token
    discord_key: str

    # Server configs
    server_id: int
    command_prefix: str = "?"
    bot_name: str = "Marty"

    # Emoji
    upvote_emoji: str = "upmartlet"
    downvote_emoji: str = "downmartlet"
    banner_vote_emoji: str = "redchiken"

    # Roles
    moderator_role: str = "Discord Moderator"
    developer_role: str = "idoneam"
    mcgillian_role: str = "McGillian"
    honorary_mcgillian_role: str = "Honorary McGillian"
    banner_reminders_role: str = "Banner Submissions"
    banner_winner_role: str = "Banner of the Week Winner"
    trash_tier_banner_role: str = "Trash Tier Banner Submissions"
    no_food_spotting_role: str = "Trash Tier Foodspotting"
    muted_role: str = "Muted"
    crabbo_role: str = "Secret Crabbo"

    # Channels
    reception_channel: str = "martys_dm"
    banner_of_the_week_channel: str = "banner_of_the_week"
    banner_submissions_channel: str = "banner_submissions"
    banner_converted_channel: str = "converted_banner_submissions"
    food_spotting_channel: str = "foodspotting"
    metro_status_channel: str = "stm_alerts"
    bots_channel: str = "bots"
    verification_channel: str = "verification_log"
    appeals_log_channel: str = "appeals_log"
    appeals_category: str = "appeals"

    # Meta
    repository: str = "https://github.com/idoneam/Canary.git"

    # Welcome + Farewell messages
    # NOT PORTED FROM OLD CONFIG SETUP.

    # DB configuration
    db_path: str = "./data/runtime/Martlet.db"

    # Helpers configuration
    course_year_range: str = "2023-2024"
    course_tpl: str = "http://www.mcgill.ca/study/{course_year_range}/courses/{}"
    course_search_tpl: str = (
        "http://www.mcgill.ca/study/{course_year_range}/courses/search?search_api_views_fulltext={}"
        "&sort_by=field_subject_code"
        "&page={}"
    )
    gc_weather_url: str = "http://weather.gc.ca/city/pages/qc-147_metric_e.html"
    gc_weather_alert_url: str = "https://weather.gc.ca/warnings/report_e.html?qc67"
    wttr_in_tpl: str = "http://wttr.in/Montreal_2mpq_lang=en.png?_m"
    tepid_url: str = "https://tepid.science.mcgill.ca:8443/tepid/screensaver/queues/status"

    # Subscription configuration
    recall_channel: str = "food"
    recall_filter: str = "Quebec|National"

    # Currency configuration
    currency: CurrencyModel = CurrencyModel()

    # Music configuration
    music: MusicModel = MusicModel()

    # Images configuration
    images: ImagesModel = ImagesModel()

    # Games configuration
    games: GamesModel = GamesModel()

    # Assignable Roles
    roles: RolesModel = RolesModel()

    class Config:  # Pydantic config for our own Config class
        env_file = ".env"
        env_prefix = "CANARY_"
        env_nested_delimiter = "__"


class ConfigOld:
    CONFIG_PATH = Path(__file__).parent / "config.ini"

    def __init__(self):
        config = configparser.ConfigParser()
        config.read_file(codecs.open(str(ConfigOld.CONFIG_PATH), "r", "utf-8-sig"))

        # Discord token
        # Try to get from environment; if not found, then
        self.discord_key = os.environ.get("CANARY_DISCORD_KEY", config["Discord"].get("Key"))

        if self.discord_key is None:
            raise Exception("Missing discord key; please specify with CANARY_DISCORD_KEY environment variable.")

        # Server configs
        self.server_id = int(os.environ.get("CANARY_SERVER_ID", config["Server"].get("ServerID")))
        self.command_prefix = [s for s in config["Server"]["CommandPrefix"].strip().split(",")]
        self.bot_name = config["Server"]["BotName"]

        # Emoji
        self.upvote_emoji = config["Emoji"]["UpvoteEmoji"]
        self.downvote_emoji = config["Emoji"]["DownvoteEmoji"]
        self.banner_vote_emoji = config["Emoji"]["BannerVoteEmoji"]

        # Roles
        self.moderator_role = config["Roles"]["ModeratorRole"]
        self.developer_role = config["Roles"]["DeveloperRole"]
        self.mcgillian_role = config["Roles"]["McGillianRole"]
        self.honorary_mcgillian_role = config["Roles"]["HonoraryMcGillianRole"]
        self.banner_reminders_role = config["Roles"]["BannerRemindersRole"]
        self.banner_winner_role = config["Roles"]["BannerWinnerRole"]
        self.trash_tier_banner_role = config["Roles"]["TrashTierBannerRole"]
        self.no_food_spotting_role = config["Roles"]["NoFoodSpottingRole"]
        self.muted_role = config["Roles"]["MutedRole"]
        self.crabbo_role = config["Roles"]["CrabboRole"]

        # Channels
        self.reception_channel = config["Channels"]["ReceptionChannel"]
        self.banner_of_the_week_channel = config["Channels"]["BannerOfTheWeekChannel"]
        self.banner_submissions_channel = config["Channels"]["BannerSubmissionsChannel"]
        self.banner_converted_channel = config["Channels"]["BannerConvertedChannel"]
        self.food_spotting_channel = config["Channels"]["FoodSpottingChannel"]
        self.metro_status_channel = config["Channels"]["MetroStatusChannel"]
        self.bots_channel = config["Channels"]["BotsChannel"]
        self.verification_channel = config["Channels"]["VerificationChannel"]
        self.appeals_log_channel = config["Channels"]["AppealsLogChannel"]
        self.appeals_category = config["Channels"]["AppealsCategory"]

        # Meta
        self.repository = config["Meta"]["Repository"]

        # Logging
        self.log_file = config["Logging"]["LogFile"]
        # loglevel = config["Logging"]["LogLevel"].lower()
        # self.log_level = LOG_LEVELS.get(loglevel, logging.WARNING)
        if config["Logging"]["DevLogWebhookID"] and config["Logging"]["DevLogWebhookToken"]:
            self.dev_log_webhook_id = int(config["Logging"]["DevLogWebhookID"])
            self.dev_log_webhook_token = config["Logging"]["DevLogWebhookToken"]
        else:
            self.dev_log_webhook_id = None
            self.dev_log_webhook_token = None
        if config["Logging"]["ModLogWebhookID"] and config["Logging"]["ModLogWebhookToken"]:
            self.mod_log_webhook_id = int(config["Logging"]["ModLogWebhookID"])
            self.mod_log_webhook_token = config["Logging"]["ModLogWebhookToken"]
        else:
            self.mod_log_webhook_id = None
            self.mod_log_webhook_token = None

        # Welcome + Farewell messages
        self.welcome = config["Greetings"]["Welcome"].split("\n")
        self.goodbye = config["Greetings"]["Goodbye"].split("\n")

        # DB configuration
        self.db_path = config["DB"]["Path"]

        # Helpers configuration
        self.course_tpl = config["Helpers"]["CourseTemplate"]
        self.course_search_tpl = config["Helpers"]["CourseSearchTemplate"]
        self.gc_weather_url = config["Helpers"]["GCWeatherURL"]
        self.gc_weather_alert_url = config["Helpers"]["GCWeatherAlertURL"]
        self.wttr_in_tpl = config["Helpers"]["WttrINTemplate"]
        self.tepid_url = config["Helpers"]["TepidURL"]

        # Subscription configuration
        self.recall_channel = config["Subscribers"]["FoodRecallChannel"]
        self.recall_filter = config["Subscribers"]["FoodRecallLocationFilter"]

        # Below lies currency configuration
        currency_precision = int(config["Currency"]["Precision"])

        income_tb = zip(
            [x.strip() for x in config["IncomeTax"]["Brackets"].split(",")],
            [x.strip() for x in config["IncomeTax"]["Amounts"].split(",")],
        )

        asset_tb = zip(
            [x.strip() for x in config["AssetTax"]["Brackets"].split(",")],
            [x.strip() for x in config["AssetTax"]["Amounts"].split(",")],
        )

        br_cases = zip(
            [x.strip() for x in config["Betting"]["RollCases"].split(",")],
            [x.strip() for x in config["Betting"]["RollReturns"].split(",")],
        )

        self.currency = {
            "name": config["Currency"]["Name"],
            "symbol": config["Currency"]["Symbol"],
            "precision": currency_precision,
            "initial_amount": decimal.Decimal(config["Currency"]["Initial"]),
            "salary_base": decimal.Decimal(config["Currency"]["SalaryBase"]),
            "inflation": decimal.Decimal(config["Currency"]["Inflation"]),
            "income_tax": {decimal.Decimal(b): float(a) for b, a in income_tb},
            "asset_tax": {decimal.Decimal(b): float(a) for b, a in asset_tb},
            "transaction_tax": float(config["OtherTax"]["TransactionTax"]),
            "bet_roll_cases": sorted([(int(c), decimal.Decimal(a)) for c, a in br_cases], key=lambda c: c[0]),
        }

        self.images = {
            "max_image_size": int(config["Images"]["MaxImageSize"]),
            "image_history_limit": int(config["Images"]["ImageHistoryLimit"]),
            "max_radius": int(config["Images"]["MaxRadius"]),
            "max_iterations": int(config["Images"]["MaxIterations"]),
        }

        self.games = {
            "hm_norm_win": int(config["Games"]["HangmanNormalWin"]),
            "hm_cool_win": int(config["Games"]["HangmanCoolWin"]),
            "hm_timeout": int(config["Games"]["HangmanTimeOut"]),
        }

        # Assignable Roles
        roles = {
            "pronouns": config["AssignableRoles"]["Pronouns"],
            "fields": config["AssignableRoles"]["Fields"],
            "faculties": config["AssignableRoles"]["Faculties"],
            "years": config["AssignableRoles"]["Years"],
            "generics": config["AssignableRoles"]["Generics"],
        }

        self.music = {"ban_role": config["Music"]["BanRole"], "start_vol": float(config["Music"]["StartVol"])}

        for rc in roles:
            roles[rc] = [r.strip() for r in roles[rc].split(",")]

        self.roles = roles
