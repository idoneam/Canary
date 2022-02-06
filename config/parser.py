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

import codecs
import configparser

import logging
import decimal  # Currency

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "notset": logging.NOTSET,
}


class Parser:
    def __init__(self):
        self.configfile = "./config/config.ini"

        config = configparser.ConfigParser()
        config.read_file(codecs.open(self.configfile, "r", "utf-8-sig"))

        # Discord token
        self.discord_key = config["Discord"]["Key"]

        # Server configs
        self.server_id = int(config["Server"]["ServerID"])
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
        self.crabbo_role = config["Roles"]["CrabboRole"]

        # Channels
        self.reception_channel = config["Channels"]["ReceptionChannel"]
        self.banner_of_the_week_channel = config["Channels"]["BannerOfTheWeekChannel"]
        self.banner_submissions_channel = config["Channels"]["BannerSubmissionsChannel"]
        self.banner_converted_channel = config["Channels"]["BannerConvertedChannel"]
        self.food_spotting_channel = config["Channels"]["FoodSpottingChannel"]
        self.metro_status_channel = config["Channels"]["MetroStatusChannel"]
        self.bots_channel = config["Channels"]["BotsChannel"]

        # Meta
        self.repository = config["Meta"]["Repository"]

        # Logging
        self.log_file = config["Logging"]["LogFile"]
        loglevel = config["Logging"]["LogLevel"].lower()
        self.log_level = LOG_LEVELS.get(loglevel, logging.WARNING)
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
        self.db_schema_path = config["DB"]["Schema"]

        # Helpers configuration
        self.course_tpl = config["Helpers"]["CourseTemplate"]
        self.course_search_tpl = config["Helpers"]["CourseSearchTemplate"]
        self.gc_weather_url = config["Helpers"]["GCWeatherURL"]
        self.gc_weather_alert_url = config["Helpers"]["GCWeatherAlertURL"]
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
