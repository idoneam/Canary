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
import random
from .utils.paginator import Pages
from .utils.requests import fetch
import sqlite3

MCGILL_EXAM_URL = "https://www.mcgill.ca/exams/dates"

CFIA_FEED_URL = "http://inspection.gc.ca/eng/1388422350443/1388422374046.xml"

MCGILL_KEY_DATES_URL = "https://www.mcgill.ca/importantdates/key-dates"

WTTR_IN_MOON_URL = "http://wttr.in/moon.png"

URBAN_DICT_TEMPLATE = "http://api.urbandictionary.com/v0/define?term={}"

LMGTFY_TEMPLATE = "https://lmgtfy.com/?q={}"

try:
    os.mkdir('./pickles')
except Exception:
    pass


class Helpers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        def retrieve_string(label):
            return soup.find(
                "dt", string=label).find_next_sibling().get_text().strip()

        await ctx.trigger_typing()

        r = await fetch(self.bot.config.gc_weather_url, "content")

        soup = BeautifulSoup(r, "html.parser")
        # Get date
        observed_string = retrieve_string("Date: ")
        # Get temperature
        temperature_string = retrieve_string("Temperature:")
        # Get condition
        condition_string = retrieve_string("Condition:")
        # Get pressure
        pressure_string = retrieve_string("Pressure:")
        # Get tendency
        tendency_string = retrieve_string("Tendency:")
        # Get wind
        wind_string = retrieve_string("Wind:")
        # Get relative humidity
        humidity_string = retrieve_string("Humidity:")
        # Get "Feels like" temperature using formula from MetService
        # (Meteorological Service of New Zealand), which uses the standard
        # formula for windchill from Environment Canada for temperatures of 10°C
        # and less (or the normal temperature if the wind speed is less than 5
        # km/h), the Australian apparent temperature for temperatures of 14°C
        # and more (or the normal temperature if it is higher), and a linear
        # roll-off of the wind chill between 10°C and 14°C
        # (https://blog.metservice.com/FeelsLikeTemp)
        # Written by @le-potate
        temperature = float(
            re.search(r"-?\d+\.\d", temperature_string).group())
        wind_speed_kph = float(re.search(r"\d+", wind_string).group())
        wind_speed_mps = wind_speed_kph * 1000 / 3600
        humidity = float(re.search(r"\d+", humidity_string).group())
        wind_chill = (13.12 + 0.6215 * temperature -
                      11.37 * wind_speed_kph**0.16 +
                      0.3965 * temperature * wind_speed_kph**0.16)
        vapour_pressure = humidity / 100 * 6.105 * math.exp(
            (17.27 * temperature) / (237.7 + temperature))
        apparent_temperature = (temperature + 0.33 * vapour_pressure -
                                0.7 * wind_speed_mps - 4.00)
        feels_like = temperature
        if temperature <= 10:
            if wind_speed_kph >= 5:
                feels_like = wind_chill
        elif temperature >= 14:
            if apparent_temperature > temperature:
                feels_like = apparent_temperature
        else:
            if wind_speed_kph >= 5:
                feels_like = temperature - ((temperature - wind_chill) *
                                            (14 - temperature)) / 4

        feels_like = round(feels_like, 1)
        feels_like_string = "{}°C".format(feels_like)

        weather_now = discord.Embed(title='Current Weather',
                                    description='Conditions observed at %s' %
                                    observed_string,
                                    colour=0x7EC0EE)
        weather_now.add_field(name="Temperature",
                              value=temperature_string,
                              inline=True)
        weather_now.add_field(name="Condition",
                              value=condition_string,
                              inline=True)
        weather_now.add_field(name="Pressure",
                              value=pressure_string,
                              inline=True)
        weather_now.add_field(name="Tendency",
                              value=tendency_string,
                              inline=True)
        weather_now.add_field(name="Wind Speed",
                              value=wind_string,
                              inline=True)
        weather_now.add_field(name="Feels like",
                              value=feels_like_string,
                              inline=True)

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

        if term == 'Fall':
            node = text[0].find_all('h2')[0].next_sibling
        else:
            node = text[0].find_all('h2')[1].next_sibling

        # Iterate through the tags and find unordered lists.
        # The content of each list will become the body of each section
        # while the contents of the <p> above it will become the headers.
        while node:
            if hasattr(node, 'name'):
                if node.name == 'h2' and term == 'Fall':
                    break
                elif node.name == 'ul':
                    sections.append(node.get_text())
                    previous = node.previous_sibling.previous_sibling
                    if previous.name == 'p':
                        headers.append(previous.get_text())
                    else:
                        # just in case the layout changes again, at least the whole thing won't break
                        headers.append("...")

            node = node.next_sibling

        em = discord.Embed(title='McGill Important Dates {0} {1}'.format(
            term, str(current_year)),
                           description=MCGILL_KEY_DATES_URL,
                           colour=0xDA291C)

        for i in range(len(headers)):
            em.add_field(name=f"{headers[i][:255]}\u2026"
                         if len(headers[i]) > 256 else headers[i],
                         value=sections[i],
                         inline=False)

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
    async def lmgtfy(self, ctx, *, query):
        """Generates a Let Me Google that For You link."""
        url = LMGTFY_TEMPLATE.format(
            query.replace("+", "%2B").replace(" ", "+"))
        await ctx.send(url)

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
        LATEX_PREAMBLE = ("\\documentclass[varwidth,12pt]{standalone}"
                          "\\usepackage{alphabeta}"
                          "\\usepackage[utf8]{inputenc}"
                          "\\usepackage[LGR,T1]{fontenc}"
                          "\\usepackage{amsmath,amsfonts,lmodern}"
                          "\\begin{document}")
        preview(
            tex,
            preamble=LATEX_PREAMBLE,
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
        # Written by @le-potate
        """Posts a food sale in #foodspotting.
        Use: `?foodspot Samosas in leacock`
        You can also attach one picture to your message (Write the command in
        the uploaded image caption)"""
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

    @commands.command(aliases=["color"])
    async def colour(self, ctx, *, arg: str):
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
        SIZE = 64
        img = np.zeros((SIZE, SIZE, 3), np.uint8)
        img[:, :] = (b, g, r)
        ext = "jpg"
        retval, buffer = cv2.imencode('.{}'.format(ext), img,
                                      [cv2.IMWRITE_JPEG_QUALITY, 0])
        buffer = BytesIO(buffer)
        fn = "{}.{}".format(match.group(1), ext)
        await ctx.send(file=discord.File(fp=buffer, filename=fn))

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        roles_id = [
            role.id for role in member.roles if role.name != "@everyone"
        ]
        if roles_id:
            conn = sqlite3.connect(self.bot.config.db_path)
            c = conn.cursor()
            # store roles as a string of IDs separated by spaces
            t = (member.id, ' '.join(str(e) for e in roles_id))
            c.execute('REPLACE INTO PreviousRoles VALUES (?, ?)', t)
            conn.commit()
            conn.close()

    @commands.command(aliases=['previousroles', 'giverolesback', 'rolesback'])
    async def previous_roles(self, ctx, user: discord.Member):
        """Show the list of roles that a user had before leaving, if possible.
        A moderator can click the OK react on the message to give these roles back
        """
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        fetched_roles = c.execute(
            'SELECT Roles FROM PreviousRoles WHERE ID = ?',
            (user.id, )).fetchone()
        # the above returns a tuple with a string of IDs separated by spaces
        if fetched_roles is not None:
            roles_id = fetched_roles[0].split(" ")
            valid_roles = []
            for role_id in roles_id:
                role = self.bot.get_guild(self.bot.config.server_id).get_role(
                    int(role_id))
                if role:
                    valid_roles.append(role)

            roles_name = [
                "[{}] {}\n".format(i, role.name)
                for i, role in enumerate(valid_roles, 1)
            ]

            embed = discord.Embed(title="Loading...")
            message = await ctx.send(embed=embed)

            if len(valid_roles) > 20:
                await message.add_reaction("◀")
                await message.add_reaction("▶")
            await message.add_reaction("🆗")

            p = Pages(
                ctx,
                item_list=roles_name,
                title="{} had the following roles before leaving.\n"
                "A {} can add these roles back by reacting with 🆗".format(
                    user.display_name, self.bot.config.moderator_role),
                msg=message,
                display_option=(3, 20),
                editable_content=True,
                editable_content_emoji="🆗",
                return_user_on_edit=True)
            ok_user = await p.paginate()

            while p.edit_mode:
                if discord.utils.get(ok_user.roles,
                                     name=self.bot.config.moderator_role):
                    await user.add_roles(
                        *valid_roles,
                        reason="{} used the previous_roles command".format(
                            ok_user.name))
                    embed = discord.Embed(
                        title="{}'s previous roles were successfully "
                        "added back by {}".format(user.display_name,
                                                  ok_user.display_name))
                    await message.edit(embed=embed)
                    await message.clear_reaction("◀")
                    await message.clear_reaction("▶")
                    await message.clear_reaction("🆗")
                    return
                else:
                    ok_user = await p.paginate()

        else:
            embed = discord.Embed(
                title="Could not find any roles for this user")
            await ctx.send(embed=embed)

        conn.close()

    @commands.command(aliases=["ui", "av", "avi", "userinfo"])
    async def user_info(self, ctx, user: discord.Member = None):
        """
        Show user info and avi
        Defaults to displaying the information of the user
        that called the command, whoever another member's username
        can be passed as an optional argument to display their info"""
        if user is None:
            user = ctx.author
        ui_embed = discord.Embed(colour=user.id % 16777215)
        ui_embed.add_field(name="username",
                           value=f"{user.name}#{user.discriminator}",
                           inline=True)
        ui_embed.add_field(name="display name",
                           value=user.display_name,
                           inline=True)
        ui_embed.add_field(name="id", value=user.id, inline=True)
        ui_embed.add_field(name="joined server",
                           value=user.joined_at.strftime("%m/%d/%Y, %H:%M:%S"),
                           inline=True)
        ui_embed.add_field(
            name="joined discord",
            value=user.created_at.strftime("%m/%d/%Y, %H:%M:%S"),
            inline=True)
        ui_embed.add_field(name=f"top role",
                           value=str(user.top_role),
                           inline=True)
        ui_embed.add_field(name="avatar url",
                           value=user.avatar_url,
                           inline=False)
        ui_embed.set_image(url=user.avatar_url)

        await ctx.send(embed=ui_embed)


def setup(bot):
    bot.add_cog(Helpers(bot))
