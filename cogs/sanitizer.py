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

import discord
from discord import utils
from discord.ext import commands
import re
import requests

TIKTOK_SHORTLINK = re.compile(r"https?:\/\/vm\.tiktok\.com\/[A-Za-z0-9]+")
TIKTOK_MOBILE = re.compile(
    r"(https?:\/\/m\.tiktok\.com\/v\/[0-9]+)\.html\?[A-Za-z0-9_&=%\.\?-]+")
TIKTOK_DESKTOP = re.compile(
    r"(https?:\/\/www\.tiktok\.com\/@[A-Za-z0-9_\.]+\/video\/[0-9]+)\?[A-Za-z0-9_&=%\.\?-]+"
)


def unroll_tiktok(link):
    return requests.head(link,
                         headers={
                             "User-Agent": "Mozilla/5.0 (X11)"
                         },
                         allow_redirects=True).url


class Sanitizer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def tiktok_link_sanitizer(self, msg):
        replace: bool = False
        msg_txt: str = str(msg.content)
        for short in TIKTOK_SHORTLINK.finditer(msg_txt):
            short_match = short.group()
            msg_txt = msg_txt.replace(short_match, unroll_tiktok(short_match))
            replace = True
        for mobile in TIKTOK_MOBILE.finditer(msg_txt):
            full, clean = mobile.group(0, 1)
            msg_txt = msg_txt.replace(full, unroll_tiktok(clean))
            replace = True
        for desktop in TIKTOK_DESKTOP.finditer(msg_txt):
            full, clean = desktop.group(0, 1)
            msg_txt = msg_txt.replace(full, clean)
            replace = True
        if replace:
            await msg.delete()
            await msg.channel.send(f"> from: `{msg.author}`\n{msg_txt}")
            dm_channel = msg.author.dm_channel or await msg.author.create_dm()
            await dm_channel.send(
                f"⚠️***WARNING*** ⚠️:\na message you sent contained "
                "a tiktok link that could potentially reveal sensitive information."
                "\nas such, it has been deleted and a sanitized "
                "version of the message was resent by this discord bot.")


def setup(bot):
    bot.add_cog(Sanitizer(bot))
