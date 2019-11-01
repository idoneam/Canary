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

# TeX rendering
from io import BytesIO
from sympy import preview
import cv2
import numpy as np

# Other utilities
import os
import re
import math
import time
import datetime
import pickle
import feedparser
import random
from .utils.paginator import Pages
from .utils.requests import fetch

MCGILL_EXAM_URL = "https://www.mcgill.ca/exams/dates"

CFIA_FEED_URL = "http://inspection.gc.ca/eng/1388422350443/1388422374046.xml"

MCGILL_KEY_DATES_URL = "https://www.mcgill.ca/importantdates/key-dates"

WTTR_IN_MOON_URL = "http://wttr.in/moon.png"

URBAN_DICT_TEMPLATE = "http://api.urbandictionary.com/v0/define?term={}"

try:
    os.mkdir('./pickles')
except Exception:
    pass


class Helpers(commands.Cog):
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

    @commands.command(aliases=['exams'])
    async def exam(self, ctx):
        """Retrieves the exam schedule link from McGill's Exam website."""
        await ctx.trigger_typing()

        r = await fetch(MCGILL_EXAM_URL, "content")

        soup = BeautifulSoup(r, "html.parser")
        link = soup.find("a", href=re.compile("exams/files/exams"))["href"]

        if link[:2] == "//":
            link = "https:" + link

        exam_schedule = discord.Embed(title="Latest Exam Schedule",
                                      description="{}".format(link))

        await ctx.send(embed=exam_schedule)

    @commands.command()
    async def weather(self, ctx):
        """Retrieves current weather conditions.
        Data taken from http://weather.gc.ca/city/pages/qc-147_metric_e.html"""
        await ctx.trigger_typing()

        r = await fetch(self.bot.config.gc_weather_url, "content")

        soup = BeautifulSoup(r, "html.parser")
        # Get date
        observed_label = soup.find("dt", string="Date: ")
        # Get temperature
        temperature_label = soup.find("dt", string="Temperature:")
        # Get condition
        condition_label = soup.find("dt", string="Condition:")
        # Get pressure
        pressure_label = soup.find("dt", string="Pressure:")
        # Get tendency
        tendency_label = soup.find("dt", string="Tendency:")
        # Get wind
        wind_label = soup.find("dt", string="Wind:")
        # Get windchill using standard formula from Environment Canada
        temperature = float(
            re.search("-*\d+\.\d",
                      temperature_label.find_next_sibling().get_text().strip()
                      ).group())
        wind_speed = float(
            re.search(
                "\d+",
                wind_label.find_next_sibling().get_text().strip()).group())
        windchill = "{}°C".format(
            round(
                13.12 + 0.6215 * temperature - 11.37 * wind_speed**0.16 +
                0.3965 * temperature * wind_speed**0.16, 1))

        weather_now = discord.Embed(
            title='Current Weather',
            description='Conditions observed at %s' %
            observed_label.find_next_sibling().get_text().rstrip(),
            colour=0x7EC0EE)
        weather_now.add_field(
            name="Temperature",
            value=temperature_label.find_next_sibling().get_text().strip(),
            inline=True)
        weather_now.add_field(
            name="Condition",
            value=condition_label.find_next_sibling().get_text().strip(),
            inline=True)
        weather_now.add_field(
            name="Pressure",
            value=pressure_label.find_next_sibling().get_text().strip(),
            inline=True)
        weather_now.add_field(
            name="Tendency",
            value=tendency_label.find_next_sibling().get_text().strip(),
            inline=True)
        weather_now.add_field(
            name="Wind Speed",
            value=wind_label.find_next_sibling().get_text().strip(),
            inline=True)
        weather_now.add_field(name="Wind Chill", value=windchill, inline=True)

        # Weather alerts

        r_alert = await fetch(self.bot.config.gc_weather_alert_url, "content")
        alert_soup = BeautifulSoup(r_alert, "html.parser")
        # Exists
        alert_title = alert_soup.find("h1", string=re.compile("Alerts.*"))
        # Only gets first <p> of warning. Subsequent paragraphs are ignored.
        try:
            alert_category = alert_title.find_next("h2")
            alert_date = alert_category.find_next("span")
            alert_heading = alert_date.find_next("strong")
            # This is a string for some reason.
            alert_location = alert_heading.find_next(
                string=re.compile("Montréal.*"))
            # Only gets first <p> of warning. Subsequent paragraphs are ignored
            alert_content = alert_location.find_next("p").get_text().strip()
            alert_content = ". ".join(alert_content.split(".")).strip()

            weather_alert = discord.Embed(
                title=alert_title.get_text().strip(),
                description="**{}** at {}".format(
                    alert_category.get_text().strip(),
                    alert_date.get_text().strip()),
                colour=0xFF0000)
            weather_alert.add_field(name=alert_heading.get_text().strip(),
                                    value="**{}**\n{}".format(
                                        alert_location.strip(), alert_content),
                                    inline=True)

        except Exception:
            weather_alert = discord.Embed(title=alert_title.get_text().strip(),
                                          description="No alerts in effect.",
                                          colour=0xFF0000)

        # TODO Finish final message. Test on no-alert condition.

        # Sending final message
        await ctx.send(embed=weather_now)
        await ctx.send(embed=weather_alert)

    @commands.command()
    async def wttr(self, ctx):
        """Retrieves Montreal's weather forecast from wttr.in"""
        await ctx.send(self.bot.config.wttr_in_tpl.format(round(time.time())))

    @commands.command(aliases=["wttrmoon"])
    async def wttr_moon(self, ctx):
        """Retrieves the current moon phase from wttr.in/moon"""
        await ctx.send(WTTR_IN_MOON_URL)

    @commands.command()
    async def course(self, ctx, *, query: str):
        """Prints a summary of the queried course, taken from the course
        calendar. ie. ?course comp 206
        Note: Bullet points without colons (':') are not parsed because I have
        yet to see one that actually has useful information.
        """
        fac = r'([A-Za-z]{4})'
        num = r'(\d{3}\s*(\w\d)?)'
        await ctx.trigger_typing()
        result = re.compile(fac + r'\s*' + num,
                            re.IGNORECASE | re.DOTALL).search(query)
        if not result:
            await ctx.send(
                ':warning: Incorrect format. The correct format is `?course '
                '<course name>`.')
            return

        search_term = "{}-{}".format(result.group(1), result.group(2))
        search_term = re.sub(r'\s+', r'', search_term)
        url = self.bot.config.course_tpl.format(search_term)
        r = await fetch(url, "content")
        soup = BeautifulSoup(r, "html.parser")

        # TODO: brute-force parsing at the moment
        title = soup.find_all("h1", {"id": "page-title"})[0].get_text().strip()
        if title == 'Page not found':
            await ctx.send("No course found for {}.".format(query))
            return

        content = soup.find("div", id="block-system-main").find_all(
            "div", {"class": "content"})[1]
        overview = content.p.get_text().strip()
        terms = soup.find_all(
            "p",
            {"class": "catalog-terms"})[0].get_text().split(':')[1].strip()
        instructors = soup.find_all("p",
                                    {"class": "catalog-instructors"
                                     })[0].get_text().split(':')[1].strip()
        lists = content.find_all('li')
        tidbits = []
        for i in lists:
            # TODO: include tidbits without colon as well?
            if ':' not in i.get_text():
                continue
            (a, b) = i.get_text().split(':', 1)
            tidbits.append((a.strip(), b.strip()))

        em = discord.Embed(title=title, description=url, colour=0xDA291C)
        em.add_field(name="Overview", value=overview, inline=False)
        em.add_field(name="Terms", value=terms, inline=False)
        em.add_field(name="Instructor(s)", value=instructors, inline=False)
        for (a, b) in tidbits:
            em.add_field(name=a, value=b, inline=False)
        await ctx.send(embed=em)

    @commands.command()
    async def keydates(self, ctx):
        """Retrieves the important dates for the current term (Winter from
        January-April, Fall from May-December)."""

        await ctx.trigger_typing()

        r = await fetch(MCGILL_KEY_DATES_URL, "content")
        soup = BeautifulSoup(r, 'html.parser')

        now = datetime.datetime.now()
        current_year = now.year
        current_month = now.month
        if current_month > 4:
            term = 'Fall'
        else:
            term = 'Winter'

        text = soup.find_all('div', {'class': 'field-item even'})

        # The layout is trash and the divs don't follow a pattern so
        # disintegrate all div tags.
        for div in text[0].find_all('div'):
            div.replaceWithChildren()

        headers = []
        sections = []
        subsection = []

        if term == 'Fall':
            node = text[0].find_all('h2')[0].next_sibling
        else:
            node = text[0].find_all('h2')[1].next_sibling

        # Iterate through the tags and gather h3 headings in one list and the
        # text between them in another.
        while node:
            if hasattr(node, 'name'):
                if node.name == 'h2' and term == 'Fall':
                    break
                elif node.name == 'h3':
                    headers.append(node.get_text())
                    if subsection:
                        sections.append(subsection)
                    subsection = []
                else:
                    nodestr = str(node)
                    if nodestr[0] != '\n' and nodestr and nodestr != ' ':
                        subsection.append(node.get_text().replace('\xa0', ' '))

            node = node.next_sibling

        if subsection:
            sections.append(subsection)

        em = discord.Embed(title='McGill Important Dates {0} {1}'.format(
            term, str(current_year)),
                           description=MCGILL_KEY_DATES_URL,
                           colour=0xDA291C)

        for i in range(len(headers)):
            if i == 2:
                continue

            if i == 1:
                value = ' '.join(sections[i][1:-1])
            elif i == 3:
                value = ' '.join(sections[i][1:-2])
            else:
                value = ' '.join(sections[i][1:])

            em.add_field(name=headers[i], value=value, inline=False)

        await ctx.send(embed=em)

    @commands.command()
    async def urban(self, ctx, *, query):
        """Fetches the top definitions from Urban Dictionary"""

        await ctx.trigger_typing()

        url = URBAN_DICT_TEMPLATE.format(query.replace(" ", "+"))
        definitions = await fetch(url, "json")
        definitions = definitions["list"][:5]

        if not definitions:
            await ctx.send("No definition found for **%s**." % query)
            return

        markdown_url = "[{}]({})".format(definitions[0]["word"], url)
        definitions_list_text = [
            "**\n{}**\n\n{}\n\n*{}*".format(
                markdown_url,
                bytes(entry["definition"], "utf-8").decode("unicode_escape"),
                bytes(entry["example"], "utf-8").decode("unicode_escape"))
            for entry in definitions
        ]

        p = Pages(
            ctx,
            item_list=definitions_list_text,
            title="Definitions for '{}' from Urban Dictionary:".format(query),
            display_option=(3, 1),
            editable_content=False)

        await p.paginate()

    @commands.command()
    async def tex(self, ctx, *, query: str):
        """Parses and prints LaTeX equations."""
        await ctx.trigger_typing()

        tex = ""
        sp = ""
        if "$$" in ctx.message.content:
            sp = ctx.message.content.split("$$")
        elif "$" in ctx.message.content:
            sp = ctx.message.content.split("$")

        if len(sp) < 3:
            await ctx.send("PLEASE USE '$' AROUND YOUR LATEX EQUATIONS. CHEEP."
                           )
            return

        up = int(len(sp) / 2)
        for i in range(up):
            tex += "\\[" + sp[2 * i + 1] + "\\]"

        buf = BytesIO()
        preview(
            tex,
            viewer="BytesIO",
            outputbuffer=buf,
            euler=False,
            dvioptions=["-T", "tight", "-z", "9", "--truecolor", "-D", "600"])
        buf.seek(0)
        img_bytes = np.asarray(bytearray(buf.read()), dtype=np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_UNCHANGED)
        img2 = cv2.copyMakeBorder(img,
                                  115,
                                  115,
                                  115,
                                  115,
                                  cv2.BORDER_CONSTANT,
                                  value=(255, 255, 255))
        fn = "latexed.png"
        retval, buf = cv2.imencode(".png", img2)
        img_bytes = BytesIO(buf)

        await ctx.send(file=discord.File(fp=img_bytes, filename=fn))

    @commands.command()
    async def search(self, ctx, *, query: str):
        """Shows results for the queried keyword(s) in McGill courses"""

        keyword = query.replace(" ", "+")
        pagelimit = 5
        pagenum = 0
        courses = []

        await ctx.trigger_typing()

        while pagenum < pagelimit:
            r = await fetch(
                self.bot.config.course_search_tpl.format(keyword, pagenum),
                "content")
            soup = BeautifulSoup(r, "html.parser")
            found = soup.find_all("div", {"class": "views-row"})

            if len(found) < 1:
                break
            else:
                courses = courses + found
                pagenum += 1

        if len(courses) < 1:
            await ctx.send("No course found for: {}.".format(query))
            return

        course_list = {"names": [], "values": []}
        for course in courses:
            # split results into titles + information
            title = course.find_all("h4")[0].get_text().split(" ")
            course_list["names"].append(" ".join(title[:2]))
            course_list["values"].append(" ".join(title[2:]))

        p = Pages(ctx,
                  item_list=course_list,
                  title="Courses found for {}".format(query),
                  display_option=(2, 10),
                  editable_content=False)
        await p.paginate()

    @commands.command()
    async def mose(self, ctx, dollar: float):
        """Currency conversion. Converts $$$ to the equivalent number of
        samosas, based on holy prices.
        Usage: `?mose <AMOUNT>`
        i.e. ?mose 200
        """
        if dollar < 0:
            await ctx.send("Trying to owe samosas now, are we? :wink:")
            return
        total = dollar // 2 * 3 + (math.floor(dollar) % 2)
        await ctx.send("${:.2f} is worth {} samosas.".format(dollar, total))

    @commands.command()
    async def tepid(self, ctx):
        """Retrieves the CTF printers' statuses from tepid.science.mcgill.ca"""
        data = await fetch(self.bot.config.tepid_url, "json")
        for key, value in data.items():
            await ctx.send("At least one printer in {} is {}!".format(
                key, "up" if value else "down"))

    @commands.command()
    async def modpow(self, ctx, a, b, m):
        """Calculates a^b mod m, where a, b, c are big integers"""
        try:
            a, b, m = map(int, (a, b, m))
            await ctx.send(pow(a, b, m))
        except ValueError:
            ctx.send("Input must be integers")

    @commands.command(
        aliases=['foodspot', 'fs', 'food', 'foodspotting', 'food_spotting'])
    async def food_spot(self, ctx, *args):
        """Posts a food sale in #foodspotting.
        Use: `?foodspot Samosas in leacock`
        You can also attach one picture to your message (Write the command in the uploaded image caption)"""
        if utils.get(ctx.author.roles,
                     name=self.bot.config.no_food_spotting_role):
            return
        if not args:
            message = "\u200b"
        else:
            message = "**{}**".format(" ".join(args))
        channel = utils.get(self.bot.get_guild(
            self.bot.config.server_id).text_channels,
                            name=self.bot.config.food_spotting_channel)
        username = ctx.message.author
        pfp = ctx.message.author.avatar_url
        embed = discord.Embed()
        try:
            embed.set_image(url=ctx.message.attachments[0].url)
        except Exception:
            pass
        embed.set_footer(
            text=("Added by {0} • Use '{1}foodspot' or '{1}fs' if you spot "
                  "food (See '{1}help foodspot')").format(
                      username, self.bot.config.command_prefix[0]),
            icon_url=pfp)
        embed.add_field(name="`Food spotted`", value=message)
        await channel.send(embed=embed)

    @commands.command()
    async def choose(self, ctx, *, inputOpts: str):
        """Randomly chooses one of the given options delimited by semicola.
        Usage: ?choose opt1;opt2 
        """
        opts = inputOpts.split(';')
        sel = random.randint(0, (len(opts) - 1))
        msg = "🤔\n" + opts[sel]
        embed = discord.Embed(colour=0xDA291C, description=msg)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Helpers(bot))
    bot.loop.create_task(Helpers(bot).cfia_rss())
