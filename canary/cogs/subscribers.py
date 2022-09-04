# Copyright (C) idoneam (2016-2021)
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
from discord.ext import commands
from discord import utils

# URL access and parsing
from bs4 import BeautifulSoup

# Other utilities
import json.decoder
import os
import re
import pickle
import feedparser

# Type hinting
from ..bot import Canary
from .base_cog import CanaryCog

# Subscriber decorator
from .utils.custom_requests import fetch
from .utils.subscribers import canary_subscriber

CFIA_FEED_URL = "http://inspection.gc.ca/eng/1388422350443/1388422374046.xml"
CFIA_RECALL_TAG_PATH = "data/runtime/recall_tag.obj"

METRO_STATUS_API = "https://www.stm.info/en/ajax/etats-du-service"

METRO_GREEN_LINE = "1"
METRO_ORANGE_LINE = "2"
METRO_YELLOW_LINE = "4"
METRO_BLUE_LINE = "5"

METRO_COLOURS = {
    METRO_GREEN_LINE: 0x008E4F,
    METRO_ORANGE_LINE: 0xF08123,
    METRO_YELLOW_LINE: 0xFFE400,
    METRO_BLUE_LINE: 0x0083CA,
}

METRO_INTERIM_STATUS = "No information"

METRO_NORMAL_SERVICE_MESSAGE = "Normal métro service"

os.makedirs("./data/runtime", exist_ok=True)


class Subscribers(CanaryCog):
    def __init__(self, bot: Canary):
        super().__init__(bot)

        # Compiled recall regular expression for filtering
        self._recall_filter = re.compile(self.bot.config.recall_filter, re.IGNORECASE)

        # Default values by line number for status
        self._metro_statuses = {
            METRO_GREEN_LINE: METRO_NORMAL_SERVICE_MESSAGE,
            METRO_ORANGE_LINE: METRO_NORMAL_SERVICE_MESSAGE,
            METRO_YELLOW_LINE: METRO_NORMAL_SERVICE_MESSAGE,
            METRO_BLUE_LINE: METRO_NORMAL_SERVICE_MESSAGE,
        }

        self._recall_channel: discord.TextChannel | None = None
        self._metro_status_channel: discord.TextChannel | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        await super().on_ready()

        if not self.guild:
            return

        self._recall_channel = utils.get(self.guild.text_channels, name=self.bot.config.recall_channel)
        self._metro_status_channel = utils.get(self.guild.text_channels, name=self.bot.config.metro_status_channel)

        # Register all subscribers
        self.bot.loop.create_task(self.cfia_rss())
        self.bot.loop.create_task(self.metro_status())

    @canary_subscriber(12 * 3600)  # run every 12 hours
    async def cfia_rss(self):
        # Written by @jidicula
        """
        Co-routine that periodically checks the CFIA Health Hazard Alerts RSS
         feed for updates.
        """

        if not self._recall_channel:
            return

        newest_recalls = feedparser.parse(CFIA_FEED_URL)["entries"]

        try:
            with open(CFIA_RECALL_TAG_PATH, "rb") as id_unpickle:
                recalls = pickle.load(id_unpickle)
        except Exception:  # TODO: Specify exception
            recalls = {}

        new_recalls = False

        for recall in newest_recalls:
            recall_id = recall["id"]
            if recall_id in recalls:
                # Don't send already-sent recalls
                continue

            new_recalls = True
            recalls[recall_id] = ""
            recall_warning = discord.Embed(title=recall["title"], description=recall["link"])
            soup = BeautifulSoup(recall["summary"], "lxml")

            try:
                img_url = soup.img["src"]
                summary = soup.p.find_parent().text.strip()
            except Exception:  # TODO: Specify exception
                img_url = ""
                summary = recall["summary"]

            if self._recall_filter.search(summary):
                recall_warning.set_image(url=img_url)
                recall_warning.add_field(name="Summary", value=summary)
                await self._recall_channel.send(embed=recall_warning)

        if new_recalls:
            # Pickle newly added IDs
            with open(CFIA_RECALL_TAG_PATH, "wb") as id_pickle:
                pickle.dump(recalls, id_pickle)

    @staticmethod
    def _check_metro_status(line_number, response_data):
        # Helper function to return line name and status.
        # - `line_number` must be a string containing the number of the
        # metro line
        # - `response` must be a JSON response object from a GET request to
        # the metro status API.
        line_name = response_data["metro"][line_number]["name"]
        status = response_data["metro"][line_number]["data"]["text"]
        return line_name, status

    @canary_subscriber(60)  # Run every 60 seconds
    async def metro_status(self):
        # Written by @jidicula
        """
        Co-routine that periodically checks the STM Metro status API for
        outages.
        """

        if not self._metro_status_channel:
            return

        try:
            response_data = await fetch(METRO_STATUS_API, "json")
        except json.decoder.JSONDecodeError:
            # STM API sometimes returns non-JSON responses
            return

        for line_number, cached_status in self._metro_statuses.items():
            line_name, current_status = Subscribers._check_metro_status(line_number, response_data)
            if current_status in (cached_status, METRO_INTERIM_STATUS):
                # Don't send message if the status hasn't changed or the status
                # is currently in the middle of changing on the API side.
                continue

            self._metro_statuses[line_number] = current_status
            metro_status_update = discord.Embed(
                title=line_name, description=current_status, colour=METRO_COLOURS[line_number]
            )

            await self._metro_status_channel.send(embed=metro_status_update)


def setup(bot):
    bot.add_cog(Subscribers(bot))
