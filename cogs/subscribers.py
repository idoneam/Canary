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
import datetime
import pickle
import feedparser
from .utils.paginator import Pages
from .utils.requests import fetch

CFIA_FEED_URL = "http://inspection.gc.ca/eng/1388422350443/1388422374046.xml"

try:
    os.mkdir('./pickles')
except Exception:
    pass


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


def setup(bot):
    bot.add_cog(Subscribers(bot))
    bot.loop.create_task(Subscribers(bot).cfia_rss())
