# Copyright (C) idoneam (2016-2022)
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

# TeX rendering
from io import BytesIO
from sympy import preview
import cv2
import numpy as np
import googletrans

# Other utilities
import datetime
import math
import random
import re
import sqlite3
import time
from ..bot import Canary
from .utils.arg_converter import ArgConverter, StrConverter
from .utils.paginator import Pages
from .utils.custom_requests import fetch
from .utils.site_save import site_save
from .utils.checks import is_developer
from discord.ext.commands import MessageConverter

MCGILL_EXAM_URL = "https://www.mcgill.ca/exams/dates"

CFIA_FEED_URL = "http://inspection.gc.ca/eng/1388422350443/1388422374046.xml"

MCGILL_KEY_DATES_URL = "https://www.mcgill.ca/importantdates/key-dates"

WTTR_IN_MOON_URL = "http://wttr.in/moon.png"

URBAN_DICT_TEMPLATE = "http://api.urbandictionary.com/v0/define?term={}"

LMGTFY_TEMPLATE = "https://letmegooglethat.com/?q={}"

MTL_REGEX = re.compile("Montréal.*")
ALERT_REGEX = re.compile("Alerts.*")

LATEX_PREAMBLE = r"""\documentclass[varwidth,12pt]{standalone}
\usepackage{alphabeta}
\usepackage[utf8]{inputenc}
\usepackage[LGR,T1]{fontenc}
\usepackage{amsmath,amsfonts,lmodern}
\begin{document}"""

MAIN_WEBHOOKS_PREFIX = "Main webhook for #"


class Helpers(commands.Cog):
    def __init__(self, bot: Canary):
        self.bot: Canary = bot
        self.guild: discord.Guild | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.bot.config.server_id)

    @commands.command(aliases=["exams"])
    async def exam(self, ctx: commands.Context):
        """Retrieves the exam schedule link from McGill's Exam website."""
        await ctx.trigger_typing()

        r = await fetch(MCGILL_EXAM_URL, "content")

        soup = BeautifulSoup(r, "html.parser")

        if (link_el := soup.find("a", href=re.compile(r"exams/files/exams"))) is None:
            return await ctx.send("Error: could not find exam link on McGill's website")

        link = link_el["href"]
        if isinstance(link, list):  # Attribute access can return str or list[str]
            link = link[0]

        if link[:2] == "//":
            link = "https:" + link

        exam_schedule = discord.Embed(title="Latest Exam Schedule", description="{}".format(link))

        await ctx.send(embed=exam_schedule)

    @staticmethod
    def _calculate_feels_like(temp: float, humidity: float, ws_kph: float) -> str:
        """
        Get "Feels like" temperature using formula from MetService
        (Meteorological Service of New Zealand), which uses the standard
        formula for windchill from Environment Canada for temperatures of 10°C
        and less (or the normal temperature if the wind speed is less than 5
        km/h), the Australian apparent temperature for temperatures of 14°C
        and more (or the normal temperature if it is higher), and a linear
        roll-off of the wind chill between 10°C and 14°C
        (https://blog.metservice.com/FeelsLikeTemp)
        Written by @le-potate

        temp: temperature (in degrees C)
        humidity: relative humidity (percentage points)
        ws_kph: wind speed (in km/h)
        """

        wind_speed_mps = ws_kph * 1000 / 3600
        wind_chill = 13.12 + 0.6215 * temp - 11.37 * ws_kph**0.16 + 0.3965 * temp * ws_kph**0.16
        vapour_pressure = humidity / 100 * 6.105 * math.exp((17.27 * temp) / (237.7 + temp))
        apparent_temperature = temp + 0.33 * vapour_pressure - 0.7 * wind_speed_mps - 4.00
        feels_like = temp
        if temp <= 10:
            if ws_kph >= 5:
                feels_like = wind_chill
        elif temp >= 14:
            if apparent_temperature > temp:
                feels_like = apparent_temperature
        else:
            if ws_kph >= 5:
                feels_like = temp - ((temp - wind_chill) * (14 - temp)) / 4

        return f"{round(feels_like, 1)}°C"

    @commands.command()
    @site_save("http://weather.gc.ca/city/pages/qc-147_metric_e.html")
    async def weather(self, ctx: commands.Context):
        """
        Retrieves current weather conditions.
        Data taken from http://weather.gc.ca/city/pages/qc-147_metric_e.html
        """
        await ctx.trigger_typing()

        r = await fetch(self.bot.config.gc_weather_url, "content")
        soup = BeautifulSoup(r, "html.parser")

        def retrieve_string(label):
            if elem := soup.find("dt", string=label).find_next_sibling():
                return elem.get_text().strip()
            return None

        observed_string = retrieve_string("Date: ")
        temperature_string = retrieve_string("Temperature:")
        condition_string = retrieve_string("Condition:")
        pressure_string = retrieve_string("Pressure:")
        tendency_string = retrieve_string("Tendency:")
        wind_string = retrieve_string("Wind:")
        humidity_string = retrieve_string("Humidity:")

        feels_like_values = {
            "temp": re.search(r"-?\d+\.\d", temperature_string),
            "humidity": re.search(r"\d+", humidity_string),
            "ws_kph": re.search(r"\d+", wind_string),
        }

        feels_like_string = (
            Helpers._calculate_feels_like(**{k: float(v.group()) for k, v in feels_like_values.items()})
            if all((
                humidity_string,
                temperature_string,
                wind_string,
                *feels_like_values.values(),
            ))
            else "n/a"
        )

        weather_now = discord.Embed(
            title="Current Weather",
            description=f"Conditions observed at {observed_string or '[REDACTED]'}",
            colour=0x7EC0EE,
        )
        weather_now.add_field(name="Temperature", value=temperature_string or "n/a", inline=True)
        weather_now.add_field(name="Condition", value=condition_string or "n/a", inline=True)
        weather_now.add_field(name="Pressure", value=pressure_string or "n/a", inline=True)
        weather_now.add_field(name="Tendency", value=tendency_string or "n/a", inline=True)
        weather_now.add_field(name="Wind Speed", value=wind_string or "n/a", inline=True)
        weather_now.add_field(name="Feels like", value=feels_like_string, inline=True)

        # Send weather first, then figure out alerts
        await ctx.send(embed=weather_now)

        # Weather alerts

        def no_alerts_embed(title: str | None = None):
            return discord.Embed(title=title, description="No alerts in effect.", colour=0xFF0000)

        r_alert = await fetch(self.bot.config.gc_weather_alert_url, "content")
        alert_soup = BeautifulSoup(r_alert, "html.parser")

        alert_title = alert_soup.find("h1", string=ALERT_REGEX)

        if not alert_title:
            return await ctx.send(embed=no_alerts_embed())

        alert_title_text = alert_title.get_text().strip()
        no_alerts = no_alerts_embed(alert_title_text)

        # Only gets first <p> of warning. Subsequent paragraphs are ignored.

        if (alert_category := alert_title.find_next("h2")) is None:
            return await ctx.send(embed=no_alerts)
        if (alert_date := alert_category.find_next("span")) is None:
            return await ctx.send(embed=no_alerts)
        if (alert_heading := alert_date.find_next("strong")) is None:
            return await ctx.send(embed=no_alerts)
        # This is a string for some reason.
        if (alert_location := alert_heading.find_next(string=MTL_REGEX)) is None:
            return await ctx.send(embed=no_alerts)

        # Only gets first <p> of warning. Subsequent paragraphs are ignored
        if (alert_paragraph := alert_location.find_next("p")) is None:
            return await ctx.send(embed=no_alerts)

        alert_content = ". ".join(alert_paragraph.get_text().strip().split(".")).rstrip()

        weather_alert = discord.Embed(
            title=alert_title_text,
            description=f"**{alert_category.get_text().strip()}** at {alert_date.get_text().strip()}",
            colour=0xFF0000,
        )
        weather_alert.add_field(
            name=alert_heading.get_text().strip(),
            value=f"**{alert_location.strip()}**\n{alert_content}",
            inline=True,
        )

        # Sending final message
        await ctx.send(embed=weather_alert)

    @commands.command()
    async def wttr(self, ctx: commands.Context):
        """Retrieves Montreal's weather forecast from wttr.in"""
        await ctx.send(self.bot.config.wttr_in_tpl.format(round(time.time())))

    @commands.command(aliases=["wttrmoon"])
    async def wttr_moon(self, ctx: commands.Context):
        """Retrieves the current moon phase from wttr.in/moon"""
        await ctx.send(WTTR_IN_MOON_URL)

    @commands.command()
    async def course(self, ctx: commands.Context, *, query: str):
        """Prints a summary of the queried course, taken from the course
        calendar. i.e. ?course comp 206
        Note: Bullet points without colons (':') are not parsed because I have
        yet to see one that actually has useful information.
        """
        await ctx.trigger_typing()

        # Course codes are in the format AAAA 000, or AAA1 000 in some rare
        # cases. Courses across multiple semesters have a suffix like D1/D2.
        result = re.compile(r"([A-Za-z]{3}[A-Za-z0-9])\s*(\d{3}\s*(\w\d)?)", re.IGNORECASE | re.DOTALL).search(query)
        if not result:
            await ctx.send(":warning: Incorrect format. The correct format is `?course " "<course name>`.")
            return

        search_term = re.sub(r"\s+", "", f"{result.group(1)}-{result.group(2)}")
        url = self.bot.config.course_tpl.format(search_term)
        r = await fetch(url, "content")
        soup = BeautifulSoup(r, "html.parser")

        # TODO: brute-force parsing at the moment
        title = soup.find_all("h1", {"id": "page-title"})[0].get_text().strip()
        if title == "Page not found":
            await ctx.send("No course found for {}.".format(query))
            return

        content = soup.find("div", id="block-system-main").find_all("div", {"class": "content"})[1]
        overview = content.p.get_text().strip()
        terms = soup.find_all("p", {"class": "catalog-terms"})[0].get_text().split(":")[1].strip()
        instructors = soup.find_all("p", {"class": "catalog-instructors"})[0].get_text().split(":")[1].strip()
        lists = content.find_all("li")
        tidbits = []
        for i in lists:
            # TODO: include tidbits without colon as well?
            if ":" not in i.get_text():
                continue
            (a, b) = i.get_text().split(":", 1)
            tidbits.append((a.strip(), b.strip()))

        em = discord.Embed(title=title, description=url, colour=0xDA291C)
        em.add_field(name="Overview", value=overview, inline=False)
        em.add_field(name="Terms", value=terms, inline=False)
        em.add_field(name="Instructor(s)", value=instructors, inline=False)
        for (a, b) in tidbits:
            em.add_field(name=a, value=b, inline=False)
        await ctx.send(embed=em)

    @commands.command()
    async def keydates(self, ctx: commands.Context):
        """Retrieves the important dates for the current term (Winter from
        January-April, Fall from May-December)."""

        await ctx.trigger_typing()

        soup = BeautifulSoup(await fetch(MCGILL_KEY_DATES_URL, "content"), "html.parser")

        now = datetime.datetime.now()
        current_year, current_month = now.year, now.month
        is_fall: bool = current_month > 4
        text = soup.find("div", {"class": "field-item even"})

        # The layout is trash and the divs don't follow a pattern so
        # disintegrate all div tags.
        for div in text.find_all("div"):
            if (div_cls := div.get("class")) and "note" in div_cls:
                div.decompose()
            else:
                div.replaceWithChildren()

        headers = []
        sections = []

        node = text.find_all("h2")[not is_fall].next_sibling

        # Iterate through the tags and find unordered lists.
        # The content of each list will become the body of each section
        # while the contents of the <p> above it will become the headers.
        while node:
            if hasattr(node, "name"):
                if node.name == "h2" and is_fall:
                    break
                if node.name == "ul":
                    sections.append(node.get_text())
                    previous = node.previous_sibling.previous_sibling
                    if previous.name == "p":
                        headers.append(previous.get_text())
                    else:
                        # just in case the layout changes again, at least the whole thing won't break
                        headers.append("...")

            node = node.next_sibling

        em = discord.Embed(
            title=f"McGill Important Dates {'Fall' if is_fall else 'Winter'} {current_year}",
            description=MCGILL_KEY_DATES_URL,
            colour=0xDA291C,
        )

        for i in range(len(headers)):
            em.add_field(
                name=f"{headers[i][:255]}\u2026" if len(headers[i]) > 256 else headers[i],
                value=sections[i],
                inline=False,
            )

        await ctx.send(embed=em)

    @commands.command()
    async def urban(self, ctx: commands.Context, *, query: str):
        """Fetches the top definitions from Urban Dictionary"""

        await ctx.trigger_typing()

        url = URBAN_DICT_TEMPLATE.format(query.replace(" ", "+"))
        definitions = await fetch(url, "json")
        definitions = definitions["list"][:5]

        if not definitions:
            await ctx.send(f"No definition found for **{query}**.")
            return

        markdown_url = f"[{definitions[0]['word']}]({url})"
        definitions_list_text = [
            "**\n{}**\n\n{}\n\n*{}*".format(
                markdown_url,
                bytes(entry["definition"], "utf-8").decode("unicode_escape"),
                bytes(entry["example"], "utf-8").decode("unicode_escape"),
            )
            for entry in definitions
        ]

        p = Pages(
            ctx,
            item_list=definitions_list_text,
            title=f"Definitions for '{query}' from Urban Dictionary:",
            display_option=(3, 1),
            editable_content=False,
        )

        await p.paginate()

    @commands.command()
    async def lmgtfy(self, ctx: commands.Context, *, query: str):
        """Generates a Let Me Google that For You link."""
        url = LMGTFY_TEMPLATE.format(query.replace("+", "%2B").replace(" ", "+"))
        await ctx.send(url)

    @commands.command()
    async def tex(self, ctx: commands.Context, *, query: str):
        """Parses and prints LaTeX equations."""
        await ctx.trigger_typing()

        tex = ""
        sp = ""
        if "$$" in ctx.message.content:
            sp = ctx.message.content.split("$$")
        elif "$" in ctx.message.content:
            sp = ctx.message.content.split("$")

        if len(sp) < 3:
            await ctx.send("PLEASE USE '$' AROUND YOUR LATEX EQUATIONS. CHEEP.")
            return

        up = int(len(sp) / 2)
        for i in range(up):
            tex += "\\[" + sp[2 * i + 1] + "\\]"

        buf = BytesIO()
        preview(
            tex,
            preamble=LATEX_PREAMBLE,
            viewer="BytesIO",
            outputbuffer=buf,
            euler=False,
            dvioptions=["-T", "tight", "-z", "9", "--truecolor", "-D", "600"],
        )
        buf.seek(0)
        img_bytes = np.asarray(bytearray(buf.read()), dtype=np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_UNCHANGED)
        img2 = cv2.copyMakeBorder(img, 115, 115, 115, 115, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        fn = "latexed.png"
        retval, buf = cv2.imencode(".png", img2)
        img_bytes = BytesIO(buf)

        await ctx.send(file=discord.File(fp=img_bytes, filename=fn))

    @commands.command()
    async def search(self, ctx: commands.Context, *, query: str):
        """Shows results for the queried keyword(s) in McGill courses"""

        keyword = query.replace(" ", "+")
        pagelimit = 5
        pagenum = 0
        courses: list = []

        await ctx.trigger_typing()

        while pagenum < pagelimit:
            r = await fetch(self.bot.config.course_search_tpl.format(keyword, pagenum), "content")
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

        course_list: dict[str, list[str]] = {"names": [], "values": []}
        for course in courses:
            # split results into titles + information
            title = course.find_all("h4")[0].get_text().split(" ")
            course_list["names"].append(" ".join(title[:2]))
            course_list["values"].append(" ".join(title[2:]))

        p = Pages(
            ctx,
            item_list=course_list,
            title="Courses found for {}".format(query),
            display_option=(2, 10),
            editable_content=False,
        )
        await p.paginate()

    @commands.command()
    async def mose(self, ctx: commands.Context, dollar: float):
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
    async def tepid(self, ctx: commands.Context):
        """Retrieves the CTF printers' statuses from tepid.science.mcgill.ca"""
        data = await fetch(self.bot.config.tepid_url, "json")
        for key, value in data.items():
            await ctx.send(f"At least one printer in {key} is up!" if value else f"Both printers in {key} are down.")

    @commands.command()
    async def modpow(self, ctx: commands.Context, a, b, m):
        """Calculates a^b mod m, where a, b, c are big integers"""
        try:
            a, b, m = map(int, (a, b, m))
            await ctx.send(pow(a, b, m))
        except ValueError:
            await ctx.send("Input must be integers")

    @commands.command(aliases=["foodspot", "fs", "food", "foodspotting", "food_spotting"])
    async def food_spot(self, ctx: commands.Context, *args):
        # Written by @le-potate
        """Posts a food sale in #foodspotting.
        Use: `?foodspot Samosas in leacock`
        You can also attach one picture to your message (Write the command in
        the uploaded image caption)"""
        if utils.get(ctx.author.roles, name=self.bot.config.no_food_spotting_role):
            return

        # If no value is provided, use a zero-width space
        channel = utils.get(
            self.bot.get_guild(self.bot.config.server_id).text_channels, name=self.bot.config.food_spotting_channel
        )
        embed = discord.Embed(title="Food spotted", description=" ".join(args) if args else "\u200b")
        embed.set_footer(
            text=("Added by {0} • Use '{1}foodspot' or '{1}fs' if you spot " "food (See '{1}help foodspot')").format(
                ctx.message.author, self.bot.config.command_prefix[0]
            ),
            icon_url=ctx.message.author.avatar_url,
        )

        try:
            embed.set_image(url=ctx.message.attachments[0].url)
        except IndexError:  # No attachment
            pass

        await channel.send(embed=embed)

    @commands.command()
    async def choose(self, ctx: commands.Context, *, input_opts: str):
        """
        Randomly chooses one of the given options delimited by semicola or
        commas.
        Usage: ?choose opt1;opt2
        """
        opts = input_opts.split(";" if ";" in input_opts else ",")
        msg = f"🤔\n{opts[random.randint(0, (len(opts) - 1))]}"
        embed = discord.Embed(colour=0xDA291C, description=msg)
        await ctx.send(embed=embed)

    @commands.command(aliases=["color"])
    async def colour(self, ctx: commands.Context, *, arg: str):
        """Shows a small image filled with the given hex colour.
        Usage: `?colour hex`
        """
        allowed = re.compile("^#?(?:0x)?([0-9a-fA-F]{6})$")
        match = allowed.match(arg)
        if not match:
            await ctx.send("Please use a valid 6-digit hex number.")
            return

        await ctx.trigger_typing()

        c = int(match.group(1), 16)
        r = (c & 0xFF0000) >> 16
        g = (c & 0xFF00) >> 8
        b = c & 0xFF
        size = 64
        img = np.zeros((size, size, 3), np.uint8)
        img[:, :] = (b, g, r)
        ext = "png"
        _r, buffer = cv2.imencode(f".{ext}", img)
        buffer = BytesIO(buffer)
        fn = f"{match.group(1)}.{ext}"
        await ctx.send(file=discord.File(fp=buffer, filename=fn))

    @commands.command(aliases=["ui", "av", "avi", "userinfo"])
    async def user_info(self, ctx: commands.Context, user: discord.Member | None = None):
        """
        Show user info and avatar.
        Displays the information of the user
        that called the command, or another member's
        if one is passed as an optional argument."""
        if user is None:
            user = ctx.author
        ui_embed = discord.Embed(colour=(user.id - sum(ord(char) for char in user.name)) % 0xFFFFFF)
        ui_embed.add_field(name="username", value=str(user))
        ui_embed.add_field(name="display name", value=user.display_name)
        ui_embed.add_field(name="id", value=user.id)
        ui_embed.add_field(name="joined server", value=user.joined_at.strftime("%m/%d/%Y, %H:%M:%S"))
        ui_embed.add_field(name="joined discord", value=user.created_at.strftime("%m/%d/%Y, %H:%M:%S"))
        ui_embed.add_field(
            name="top role, colour",
            value=f"`{user.top_role}`, "
            + (str(user.colour).upper() if user.colour != discord.Colour.default() else "default colour"),
        )
        ui_embed.add_field(name="avatar url", value=user.avatar_url, inline=False)
        ui_embed.set_image(url=user.avatar_url)

        await ctx.send(embed=ui_embed)

    @commands.command(aliases=["trans"])
    async def translate(self, ctx: commands.Context, command: str, *, inp_str: str | None = None):
        """
        Command used to translate some text from one language to another
        Takes two arguments: the source/target languages and the text to translate
        The first argument must be under the following format `src>dst`.
        `src` indicates the language of the source text.
        `dst` indicates which language you want the text to be translated into.
        `src` must be either an empty string (to indicate that you want
        to autodetect the source language) or a language code/name.
        `dst` must be a language code/name different from `src` (it cannot be empty).
        To get a list of all valid language codes and names, call `?translate codes`
        Second argument is the text that you want to translate. This text is either
        taken from the message to which the invoking message was replying to, or if the
        invoking message is not a reply, then to the rest of the message after the first argument.
        """
        if command == "help":
            await ctx.send(
                "Command used to translate text.\n"
                "Example usage: `?translate en>ru Rush B`\n"
                "It takes two arguments.\n"
                "The first argument must be of the format `source>destination`.\n"
                "`source` and `destination` must be language codes; "
                "alternatively, `source` may be left empty to auto-detect the "
                "source language.\n"
                "For a list of language codes, see `?translate codes`.\n"
                "The second argument is the text to translate. "
                "You may reply to a message using this command to translate it, "
                "or supply your own text as the second argument."
            )
            return

        if command == "codes":
            await ctx.send(
                "Here is a list of all language "
                "codes and names:\n" + ", ".join(f"`{code}`: {lang}" for code, lang in googletrans.LANGUAGES.items())
            )
            return

        # If the command was invoked by a reply, use the original message as input text.
        if ctx.message.reference and ctx.message.reference.resolved:
            inp_str = ctx.message.reference.resolved.content
        if not inp_str:
            await ctx.send("Sorry, no string to translate has been detected.")
            return

        # Validation of language codes
        codes = command.replace("_", "-").split(">")
        if len(codes) != 2:
            await ctx.send(f"Argument `{command}` is not properly formatted. " f"See `?translate help` to learn more.")
            return
        source = codes[0].lower().strip()
        translator = googletrans.Translator()
        if source == "":
            detection = translator.detect(inp_str)
            source = detection.lang
        elif source not in googletrans.LANGUAGES:
            await ctx.send(f"`{source}` is not a valid language code. " f"See `?translate codes` for language codes.")
            return
        destination = codes[1].lower().strip()
        if destination not in googletrans.LANGUAGES:
            await ctx.send(
                f"`{destination}` is not a valid language code. " f"See `?translate codes` for language codes."
            )
            return

        await ctx.send(
            embed=discord.Embed(colour=random.randint(0, 0xFFFFFF)).add_field(
                name=f"translated text from {googletrans.LANGUAGES[source]} to {googletrans.LANGUAGES[destination]}",
                value=translator.translate(inp_str, src=source, dest=destination).text,
            )
        )

    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    @commands.command()
    @is_developer()
    async def create_main_webhooks(self, ctx: commands.Context):
        """
        Create the general-use webhooks for each channel. The command ignores channels that already have webhooks.
        """
        if not self.guild:
            return

        ignored = 0
        for channel in self.guild.text_channels:
            try:
                webhook = discord.utils.find(
                    lambda w: w.user == self.bot.user and w.name[: len(MAIN_WEBHOOKS_PREFIX)] == MAIN_WEBHOOKS_PREFIX,
                    await channel.webhooks(),
                )
                if webhook:
                    await ctx.send(f"Webhook for {channel.mention} already exists")
                    continue
                # max length for webhook name is 80
                await channel.create_webhook(
                    name=f"{MAIN_WEBHOOKS_PREFIX}{channel.name[:(80 - len(MAIN_WEBHOOKS_PREFIX))]}"
                )
                await ctx.send(f"Created webhook for {channel.mention}")
            except discord.errors.Forbidden:
                ignored += 1

        await ctx.send(f"Ignored {ignored} channel{'s' if ignored == 1 else ''} without bot permissions")
        await ctx.send("Job completed.")

    async def spoilerize_utility(self, ctx: commands.Context, message, reason: str = None, moderator: bool = False):
        if not moderator and ctx.author != message.author:
            return
        # get the webhook for this channel
        webhook = discord.utils.find(
            lambda w: w.user == self.bot.user and w.name[: len(MAIN_WEBHOOKS_PREFIX)] == MAIN_WEBHOOKS_PREFIX,
            await ctx.channel.webhooks(),
        )
        if not webhook:
            await ctx.send(f"Could not find main webhook for channel {ctx.channel.mention}")
            return

        # get author, content, attachments and embeds
        author = message.author
        content = message.content
        attachments = message.attachments

        # spoilerize content
        if content:
            content = f"||{content.strip()}||"

        # convert attachments to spoilerized files:
        files = []
        for attachment in attachments:
            file = await attachment.to_file(spoiler=True)
            files.append(file)

        # if there is nothing to send at this point, silently return
        if not content and not files:
            return

        user_str = "A moderator" if moderator else ctx.author
        if content and not files:
            footer_txt = f"{user_str} spoilerized this message"
        elif files and not content:
            footer_txt = f"{user_str} spoilerized the attachment{'s' if len(files) > 1 else ''} below"
        else:
            footer_txt = f"{user_str} spoilerized this message and the attachment{'s' if len(files) > 1 else ''} below"

        if reason:
            footer_txt = f"{footer_txt} • Reason: {reason}"

        footer_txt = f"{footer_txt} • Delete with 🚮"

        embed = discord.Embed(description=content).set_footer(text=footer_txt)
        spoilerized_messages = [
            await webhook.send(embed=embed, username=author.display_name, avatar_url=author.avatar_url, wait=True)
        ]
        if files:
            spoilerized_messages.append(
                await webhook.send(files=files, username=author.display_name, avatar_url=author.avatar_url, wait=True)
            )

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        for spoilerized_message in spoilerized_messages:
            c.execute("REPLACE INTO SpoilerizedMessages VALUES (?, ?)", (spoilerized_message.id, author.id))
        conn.commit()
        conn.close()

        # delete original message
        await message.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.guild_id != self.guild.id or str(payload.emoji) != "🚮":
            return
        # if the put_litter_in_its_place react was used check if it was
        # on a spoilerized message by its original author, and if so delete it
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT * From SpoilerizedMessages WHERE MessageID=? AND UserID=?",
            (int(payload.message_id), int(payload.member.id)),
        )
        found = c.fetchone()
        if found:
            channel = utils.get(self.guild.text_channels, id=payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await message.delete()
        conn.close()

    @commands.command(alias=["spoiler"])
    async def spoilerize(self, ctx: commands.Context, *args):
        """
        Spoilerize a message or a range of messages (max 30 messages)

        To spoilerize a message, this can either be used as a reply to it, or the message ID can be specified.
        To spoilerize a range of messages, two message IDs must be given.
        The reason for the spoilerization can also be provided. The order of the arguments doesn't matter.

        Moderators can spoilerize any messages, while users can only spoilerize their own messages (if a range is used,
        other users' messages are not spoilerized but count towards the limit of 30).

        The original author of a spoilerized message can delete it by using the 🚮 react.

        Basic examples:
        -As a reply: ?spoilerize
        -As a reply, with a reason: ?spoilerize spoiler for movie
        -Specify message_id, with a reason: ?spoilerize message_id CW: violent content
        -Specify range:, without a reason ?spoilerize oldest_messaage_id newest_message_id
        """
        moderator = discord.utils.get(ctx.author.roles, name=self.bot.config.moderator_role)

        converters_dict = {
            "id_1": (MessageConverter(), None),
            "id_2": (MessageConverter(), None),
        }

        # todo: arg_converter should probably be made in a way that
        # makes taking multi-words strings possible without this workaround
        for i in range(len(args)):
            converters_dict[f"reason_{i}"] = (StrConverter(), None)

        arg_converter = ArgConverter(converters_dict)
        try:
            args_dict = await arg_converter.convert(ctx, args)
        except commands.BadArgument as err:
            raise commands.BadArgument(str(err))
        msg_1 = args_dict["id_1"]
        msg_2 = args_dict["id_2"]
        reason = " ".join([args_dict[f"reason_{i}"] for i in range(len(args)) if args_dict[f"reason_{i}"]])

        if msg_1 and ctx.message.reference and ctx.message.reference.resolved:
            await ctx.send("Cannot specify a message ID to spoilerize and use the command as a reply at the same time")
            return

        if msg_1 and not msg_2:
            await self.spoilerize_utility(ctx, msg_1, reason, moderator)
        elif msg_1 and msg_2:
            # check that the messages are in this channel
            if msg_1.channel != ctx.channel or msg_2.channel != ctx.channel:
                await ctx.send("The specified messages must be in the same channel as where the command is used")
                return
            # check that the 2nd message is more recent than the first:
            if msg_2.id <= msg_1.id:
                msg_1, msg_2 = msg_2, msg_1

            limit = 30
            # to avoid problems, we are using a limit of 30 messages.
            # since this doesn't fetch msg_1 and msg_2, we only need to fetch 28 messages.
            # however, 29 is specified here so that we can know if there were too many messages
            messages = [message async for message in ctx.channel.history(after=msg_1, before=msg_2, limit=limit - 1)]
            limit_reached = len(messages) == limit - 1

            messages.insert(0, msg_1)
            if not limit_reached:
                messages.append(msg_2)

            for message in messages:
                if message == ctx.message:
                    continue
                await self.spoilerize_utility(ctx, message, reason, moderator)

            if limit_reached:
                await ctx.send(
                    "Could not spoilerize all messages: Max 30 at the same time (this message will be deleted in 15 seconds).",
                    delete_after=15,
                )
            else:
                if moderator:
                    await ctx.send(
                        f"Completed spoilerization of {len(messages)} messages (this message will be deleted in 15 seconds).",
                        delete_after=15,
                    )
                else:
                    # if non-moderator, we don't specify the number of messages
                    # because we don't track how many were ignored (messages from other users).
                    await ctx.send(
                        f"Completed spoilerization (this message will be deleted in 15 seconds).", delete_after=15
                    )
        elif not msg_1 and ctx.message.reference and ctx.message.reference.resolved:
            await self.spoilerize_utility(ctx, ctx.message.reference.resolved, reason, moderator)
        else:
            await ctx.send(
                "You must either use this command as a reply or specify the ID of the message to spoilerize "
                "(the message must be in the same channel as the command)."
            )

        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Helpers(bot))
