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
from discord.ext import commands
from discord import utils
import asyncio

# URL access and parsing
from bs4 import BeautifulSoup

# Other utilities
import os
import re
import pickle
import feedparser
import requests

CFIA_FEED_URL = "http://inspection.gc.ca/eng/1388422350443/1388422374046.xml"
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

# Default values by line number for status
metro_status = {
    METRO_GREEN_LINE: METRO_NORMAL_SERVICE_MESSAGE,
    METRO_ORANGE_LINE: METRO_NORMAL_SERVICE_MESSAGE,
    METRO_YELLOW_LINE: METRO_NORMAL_SERVICE_MESSAGE,
    METRO_BLUE_LINE: METRO_NORMAL_SERVICE_MESSAGE,
}

os.makedirs('./pickles', exist_ok=True)


class Subscribers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cfia_rss(self):
        # Written by @jidicula
        """
        Co-routine that periodically checks the CFIA Health Hazard Alerts RSS
         feed for updates.
        """
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            recall_channel = utils.get(self.bot.get_guild(
                self.bot.config.server_id).text_channels,
                                       name=self.bot.config.recall_channel)
            newest_recalls = feedparser.parse(CFIA_FEED_URL)['entries']
            try:
                id_unpickle = open("pickles/recall_tag.obj", 'rb')
                recalls = pickle.load(id_unpickle)
                id_unpickle.close()
            except Exception:
                recalls = {}
            new_recalls = False
            for recall in newest_recalls:
                recall_id = recall['id']
                if recall_id not in recalls:
                    new_recalls = True
                    recalls[recall_id] = ""
                    recall_warning = discord.Embed(title=recall['title'],
                                                   description=recall['link'])
                    soup = BeautifulSoup(recall['summary'], "html.parser")
                    try:
                        img_url = soup.img['src']
                        summary = soup.p.find_parent().text.strip()
                    except Exception:
                        img_url = ""
                        summary = recall['summary']
                    if re.search(self.bot.config.recall_filter, summary,
                                 re.IGNORECASE):
                        recall_warning.set_image(url=img_url)
                        recall_warning.add_field(name="Summary", value=summary)
                        await recall_channel.send(embed=recall_warning)
            if new_recalls:
                # Pickle newly added IDs
                id_pickle = open("pickles/recall_tag.obj", 'wb')
                pickle.dump(recalls, id_pickle)
                id_pickle.close()
            await asyncio.sleep(12 * 3600)    # run every 12 hours

    async def metro_status(self):
        # Written by @jidicula
        """
        Co-routine that periodically checks the STM Metro status API for
        outages.
        """
        await self.bot.wait_until_ready()

        def check_status(line_number, response):
            # Helper function to return line name and status.
            # - `line_number` must be a string containing the number of the
            # metro line
            # - `response` must be a JSON response object from a GET request to
            # the metro status API.
            line_name = response.json()["metro"][line_number]["name"]
            status = response.json()["metro"][line_number]["data"]["text"]
            return (line_name, status)

        while not self.bot.is_closed():
            metro_status_channel = utils.get(
                self.bot.get_guild(self.bot.config.server_id).text_channels,
                name=self.bot.config.metro_status_channel)
            response = requests.get(METRO_STATUS_API)
            for line_status in metro_status.items():
                line_number = line_status[0]
                cached_status = line_status[1]
                line_name, current_status = check_status(line_number, response)
                if (current_status != cached_status
                        and current_status != METRO_INTERIM_STATUS):
                    metro_status[line_number] = current_status
                    metro_status_update = discord.Embed(
                        title=line_name,
                        description=current_status,
                        colour=METRO_COLOURS[line_number])
                    await metro_status_channel.send(embed=metro_status_update)
            await asyncio.sleep(60)    # Run every 60 seconds


def setup(bot):
    bot.add_cog(Subscribers(bot))
    bot.loop.create_task(Subscribers(bot).cfia_rss())
    bot.loop.create_task(Subscribers(bot).metro_status())
