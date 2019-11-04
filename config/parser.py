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
import decimal    # Currency

LOG_LEVELS = {
    'critical': logging.CRITICAL,
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'notset': logging.NOTSET
}


class Parser:
    def __init__(self):
        self.configfile = './config/config.ini'

        config = configparser.ConfigParser()
        config.read_file(codecs.open(self.configfile, "r", "utf-8-sig"))

        # Discord token
        self.discord_key = config['Discord']['Key']

        # Server configs
        self.server_id = int(config['Server']['ServerID'])
        self.command_prefix = [
            s for s in config['Server']['CommandPrefix'].strip().split(',')
        ]
        self.bot_name = config['Server']['BotName']
        self.upvote_emoji = config['Server']['UpvoteEmoji']
        self.downvote_emoji = config['Server']['DownvoteEmoji']
        self.moderator_role = config['Server']['ModeratorRole']
        self.developer_role = config['Server']['DeveloperRole']
        self.reception_channel = config['Server']['ReceptionChannel']

        # Logging
        self.log_file = config['Logging']['LogFile']
        loglevel = config['Logging']['LogLevel'].lower()
        self.log_level = LOG_LEVELS.get(loglevel, logging.WARNING)

        # Welcome + Farewell messages
        self.welcome = config['Greetings']['Welcome'].split('\n')
        self.goodbye = config['Greetings']['Goodbye'].split('\n')

        # DB configuration
        self.db_path = config['DB']['Path']
        self.db_schema_path = config['DB']['Schema']

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
        self.food_spotting_channel = config["Subscribers"][
            "FoodSpottingChannel"]
        self.no_food_spotting_role = config["Subscribers"][
            "NoFoodSpottingRole"]
        self.metro_status_channel = config["Subscribers"]["MetroStatusChannel"]

        # Below lies currency configuration
        currency_precision = int(config["Currency"]["Precision"])

        income_tb = zip(
            [x.strip() for x in config["IncomeTax"]["Brackets"].split(",")],
            [x.strip() for x in config["IncomeTax"]["Amounts"].split(",")])

        asset_tb = zip(
            [x.strip() for x in config["AssetTax"]["Brackets"].split(",")],
            [x.strip() for x in config["AssetTax"]["Amounts"].split(",")])

        br_cases = zip(
            [x.strip() for x in config["Betting"]["RollCases"].split(",")],
            [x.strip() for x in config["Betting"]["RollReturns"].split(",")])

        self.currency = {
            "name":
            config["Currency"]["Name"],
            "symbol":
            config["Currency"]["Symbol"],
            "precision":
            currency_precision,
            "initial_amount":
            decimal.Decimal(config["Currency"]["Initial"]),
            "salary_base":
            decimal.Decimal(config["Currency"]["SalaryBase"]),
            "inflation":
            decimal.Decimal(config["Currency"]["Inflation"]),
            "income_tax": {decimal.Decimal(b): float(a)
                           for b, a in income_tb},
            "asset_tax": {decimal.Decimal(b): float(a)
                          for b, a in asset_tb},
            "transaction_tax":
            float(config["OtherTax"]["TransactionTax"]),
            "bet_roll_cases":
            sorted([(int(c), decimal.Decimal(a)) for c, a in br_cases],
                   key=lambda c: c[0])
        }
