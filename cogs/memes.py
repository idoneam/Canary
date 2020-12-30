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
from discord.ext import commands
import discord

# Other utilities
import random
import requests
import re
from bs4 import BeautifulSoup
from .utils.auto_incorrect import auto_incorrect


class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def bac(self, ctx, *, input_str: str = None):
        """
        Purposefully auto-incorrects inputted sentences
        """
        if input_str is None:
            await ctx.send()
        msg = auto_incorrect(input_str)
        self.bot.mod_logger.info(
            '?bac invoked: Author: {}, Message: {}'.format(
                ctx.message.author, ctx.message.content))
        await ctx.send(msg)
        await ctx.message.delete()

    @commands.command()
    async def lenny(self, ctx):
        """
        Lenny face
        """
        await ctx.send("( ͡° ͜ʖ ͡°) ")
        await ctx.message.delete()

    @commands.command()
    async def license(self, ctx):
        """
        License
        """
        await ctx.send("This bot is free software: you can redistribute"
                       " it and/or modify it under the terms of the GNU"
                       " General Public License as published by the "
                       "Free Software Foundation, either version 3 of "
                       "the License, or (at your option) any later "
                       "version. **This bot is distributed in the hope "
                       "that it will be useful**, but WITHOUT ANY "
                       "WARRANTY; without even the implied warranty of "
                       "MERCHANTABILITY or **FITNESS FOR A PARTICULAR "
                       "PURPOSE**.  See the GNU General Public License "
                       "for more details. This bot is developed "
                       "primarily by student volunteers with better "
                       "things to do. A copy of the GNU General Public "
                       "License is provided in the LICENSE.txt file "
                       "along with this bot. The GNU General Public "
                       "License can also be found at "
                       "<http://www.gnu.org/licenses/>.")
        await ctx.message.delete()

    @commands.command()
    async def gohere(self, ctx):
        """
        for future mcgillians
        """
        await ctx.send("http://gph.is/1cN9wO1")
        await ctx.message.delete()

    @commands.command()
    async def tunak(self, ctx):
        """
        bitch pls
        """
        await ctx.send("http://i.imgur.com/rNNLyjK.gif")
        await ctx.message.delete()

    @commands.command()
    async def bb8(self, ctx):
        """
        nice job bb8
        """
        await ctx.send("http://i.imgur.com/SUvaUM2.gif")
        await ctx.message.delete()

    @commands.command()
    async def longtime(self, ctx):
        """
        That's a name I've not heard in a long time
        """
        await ctx.send("http://i.imgur.com/e1T1xcq.mp4")
        await ctx.message.delete()

    @commands.command()
    async def thonk(self, ctx):
        """
        when thonking consumes you
        """
        await ctx.send("https://i.imgur.com/VADGUwj.gifv")
        await ctx.message.delete()

    @commands.command()
    async def dealwithit(self, ctx):
        """
        deal with it trump
        """
        await ctx.send("http://i.imgur.com/5jzN8zV.mp4")
        await ctx.message.delete()

    @commands.command()
    async def lmao(self, ctx):
        """
        that's hilarious
        """
        await ctx.send("http://i.imgur.com/o5Cc3i2.mp4")
        await ctx.message.delete()

    @commands.command()
    async def cheep(self, ctx):
        """:^)"""
        await ctx.send('CHEEP CHEEP')

    @commands.command()
    async def mix(self, ctx, *, input_str: str = None):
        """Alternates upper/lower case for input string. Input message
        disappears after."""
        if input_str is None:
            await ctx.send()
        msg = "".join([(c.upper() if random.randint(0, 1) else c.lower())
                       for c in input_str])
        self.bot.mod_logger.info(
            '?mix invoked: Author: {}, Message: {}'.format(
                ctx.message.author, ctx.message.content))
        await ctx.send(msg)
        await ctx.message.delete()

    @commands.command(aliases=['boot'])
    async def pyramid(self, ctx, num: int = 2, emoji: str = "👢"):
        """Draws a pyramid of boots, default is 2 unless user specifies an integer number of levels of boots between -8 and 8. Also accepts any other emoji, word or multiword (in quotes) string."""
        def pyramidy(n, m):
            return "{spaces}{emojis}".format(spaces=" " * ((m - n) * 3),
                                             emojis=(emoji + " ") * n)

        if (num > 0):
            num = max(min(num, 8), 1)    # Above 8, herre gets angry
            msg = "\n".join(pyramidy(ln, num) for ln in range(1, num + 1))
        else:
            num = min(max(num, -8), -1)    # Below -8, herre gets angry
            msg = "\n".join(
                pyramidy(ln, abs(num))
                for ln in reversed(range(1,
                                         abs(num) + 1)))

        await ctx.send("**\n{}**".format(msg))

    @commands.command()
    async def xkcd(self, ctx, xkcd_command: str = None):
        """
        Enjoy a nice xkcd comic with some strangers on the internet!
        If no issue number is passed, returns a random xkcd.
        Valid options are: nothing, 'latest' or a positive integer greater than one and at most equal to the latest issue number.
        """
        await ctx.trigger_typing()
        xkcd_num = None
        if xkcd_command is None:
            xkcd_req = requests.get("https://c.xkcd.com/comic/random")
        elif xkcd_command == "latest":
            xkcd_req = requests.get("https://xkcd.com/")
        else:
            try:
                xkcd_num = int(xkcd_command)
            except ValueError:
                await ctx.send(
                    f"invalid input: `{xkcd_command}` does not parse to an integer"
                )
                return
            xkcd_req = requests.get(f"https://xkcd.com/{xkcd_num}")
            if xkcd_num < 1:
                await ctx.send(
                    f"the number `{xkcd_num}` is less than one, such an xkcd issue cannot exist"
                )
                return
        if xkcd_req.status_code == 404:
            xkcd_num = None
            xkcd_req = requests.get("https://xkcd.com/")
        if xkcd_req.status_code != 200:
            await ctx.send(
                f"xkcd number `{xkcd_command}` could not be found (request returned `{xkcd_req.status_code}`)"
            )
            return
        xkcd_soup = BeautifulSoup(xkcd_req.content, "html.parser")
        if xkcd_num is None:
            xkcd_title_num = re.findall(
                r'^https://xkcd.com/([1-9][0-9]*)/$',
                xkcd_soup.find('meta', property='og:url')['content'])[0]
        else:
            xkcd_title_num = str(xkcd_num)
        xkcd_img_soup = xkcd_soup.find("div", attrs={
            "id": "comic"
        }).find("img")
        xkcd_embed = discord.Embed(
            title=f"{xkcd_img_soup['alt']} (#{xkcd_title_num})",
            url=xkcd_req.url)
        xkcd_embed.set_image(url=f"https:{xkcd_img_soup['src']}")
        xkcd_embed.set_footer(text=str(xkcd_img_soup['title']))
        await ctx.send(embed=xkcd_embed)


def setup(bot):
    bot.add_cog(Memes(bot))
