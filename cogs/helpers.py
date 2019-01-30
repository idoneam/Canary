#!/usr/bin/env python3

# discord-py requirements
import discord
from discord.ext import commands
import asyncio

# URL access and parsing
import requests
from bs4 import BeautifulSoup

# TeX rendering
from io import BytesIO
from sympy import preview
import cv2
import numpy as np

# Other utilities
import re
import math
import time
import os
import datetime
from .utils.paginator import Pages


class Helpers():
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['exams'])
    async def exam(self, ctx):
        """Retrieves the exam schedule link from McGill's Exam website."""
        await ctx.send(
            'https://www.mcgill.ca/exams/files/exams/final_alpha_dec_2018_12.pdf'
        )

    @commands.command()
    async def weather(self, ctx):
        """Retrieves current weather conditions.
        Data taken from http://weather.gc.ca/city/pages/qc-147_metric_e.html"""
        await ctx.trigger_typing()
        # Replace link with any city weather link from http://weather.gc.ca/
        url = "http://weather.gc.ca/city/pages/qc-147_metric_e.html"
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        r.close()
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
        # Get windchill, only if it can be found.
        try:
            windchill_label = soup.find("a", string="Wind Chill")
            windchill = windchill_label.find_next().get_text().strip(
            ) + u"\xb0C"
        except:
            windchill = u"N/A"

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

        alert_url = "https://weather.gc.ca/warnings/report_e.html?qc67"
        r_alert = requests.get(alert_url)
        alert_soup = BeautifulSoup(r_alert.content, "html.parser")
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
                description="**%s** at %s" %
                (alert_category.get_text().strip(),
                 alert_date.get_text().strip()),
                colour=0xFF0000)
            weather_alert.add_field(
                name=alert_heading.get_text().strip(),
                value="**%s**\n%s" % (alert_location.strip(), alert_content),
                inline=True)

        except:
            weather_alert = discord.Embed(
                title=alert_title.get_text().strip(),
                description="No alerts in effect.",
                colour=0xFF0000)

        # TODO Finish final message. Test on no-alert condition.

        # Sending final message
        await ctx.send(embed=weather_now)
        await ctx.send(embed=weather_alert)

    @commands.command()
    async def wttr(self, ctx):
        """Retrieves Montreal's weather forecast from wttr.in"""
        await ctx.send('http://wttr.in/Montreal_2mpq_lang=en.png?_=%d' % round(
            time.time()))

    @commands.command()
    async def wttrmoon(self, ctx):
        """Retrieves the current moon phase from wttr.in/moon"""
        await ctx.send('http://wttr.in/moon.png')

    @commands.command()
    async def course(self, ctx, *, query: str):
        """Prints a summary of the queried course, taken from the course calendar.
        ie. ?course comp 206
        Note: Bullet points without colons (':') are not parsed because I have yet to see one that actually has useful information."""
        fac = r'([A-Za-z]{4})'
        num = r'(\d{3}\s*(\w\d)?)'
        await ctx.trigger_typing()
        result = re.compile(fac + r'\s*' + num,
                            re.IGNORECASE | re.DOTALL).search(query)
        if not result:
            await ctx.send(
                ':warning: Incorrect format. The correct format is `?course <course name>`.'
            )
            return
        search_term = result.group(1) + '-' + result.group(2)
        search_term = re.sub(r'\s+', r'', search_term)
        url = "http://www.mcgill.ca/study/2018-2019/courses/%s" % search_term
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        r.close()

        # XXX: brute-force parsing at the moment
        title = soup.find_all("h1", {"id": "page-title"})[0].get_text().strip()
        if title == 'Page not found':
            await ctx.send("No course found for %s." % query)
            return
        content = soup.find_all("div", {"class": "content"})[3]
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
        """Retrieves the important dates for the current term (Winter from January-April, Fall from May-December)."""
        await ctx.trigger_typing()
        url = 'https://www.mcgill.ca/importantdates/key-dates'
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        r.close()

        now = datetime.datetime.now()
        current_year = now.year
        current_month = now.month
        if current_month > 4:
            term = 'Fall'
        else:
            term = 'Winter'

        text = soup.find_all('div', {'class': 'field-item even'})

        # The layout is trash and the divs don't follow a pattern so disintegrate all div tags
        for div in text[0].find_all('div'):
            div.replaceWithChildren()

        headers = []
        sections = []
        subsection = []

        if term == 'Fall':
            node = text[0].find_all('h2')[0].next_sibling
        else:
            node = text[0].find_all('h2')[1].next_sibling

        # Iterate through the tags and gather h3 headings in one list and the text between them in another
        while node:
            if hasattr(node, 'name'):
                if node.name == 'h2' and term == 'Fall':
                    break
                elif node.name == 'h3':
                    nodestr = str(node)
                    headers.append(node.get_text())
                    if subsection: sections.append(subsection)
                    subsection = []
                else:
                    nodestr = str(node)
                    if nodestr[0] != '\n' and nodestr and nodestr != ' ':
                        subsection.append(node.get_text().replace('\xa0', ' '))
            node = node.next_sibling
        if subsection: sections.append(subsection)

        em = discord.Embed(
            title='McGill Important Dates {0} {1}'.format(
                term, str(current_year)),
            description=url,
            colour=0xDA291C)
        for i in range(len(headers)):
            if i == 2: continue
            elif i == 1:
                em.add_field(
                    name=headers[i],
                    value=' '.join(sections[i][1:-1]),
                    inline=False)
            elif i == 3:
                em.add_field(
                    name=headers[i],
                    value=' '.join(sections[i][1:-2]),
                    inline=False)
            else:
                em.add_field(
                    name=headers[i],
                    value=' '.join(sections[i][1:]),
                    inline=False)
        await ctx.send(embed=em)

    @commands.command()
    async def urban(self, ctx, *, query):
        """Fetches the top definitions from Urban Dictionary"""
        await ctx.trigger_typing()
        url = "http://api.urbandictionary.com/v0/define?term=%s" % query.replace(
            ' ', '+')
        r = requests.get(url)
        definitions = r.json()["list"][:5]
        r.close()
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
            itemList=definitions_list_text,
            title="Definitions for '%s' from Urban Dictionary:" % query,
            displayOption=(3, 1),
            editableContent=False)
        await p.paginate()

    @commands.command()
    async def tex(self, ctx, *, query: str):
        """Parses and prints LaTeX equations."""
        await ctx.trigger_typing()

        tex = ""
        sp = ""
        if "$$" in ctx.message.content:
            sp = ctx.message.content.split('$$')
        elif "$" in ctx.message.content:
            sp = ctx.message.content.split('$')

        if len(sp) < 3:
            await ctx.send(
                'PLEASE USE \'$\' AROUND YOUR LATEX EQUATIONS. CHIRP.')
            return

        up = int(len(sp) / 2)
        for i in range(up):
            tex += "\\[" + sp[2 * i + 1] + "\\]"

        buf = BytesIO()
        preview(tex, viewer='BytesIO', outputbuffer=buf, euler=False)
        buf.seek(0)
        img_bytes = np.asarray(bytearray(buf.read()), dtype=np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_UNCHANGED)
        img2 = cv2.copyMakeBorder(
            img, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        fn = 'latexed.png'
        retval, buf = cv2.imencode('.png', img2)
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
        while (True and pagenum < pagelimit):
            url = "http://www.mcgill.ca/study/2018-2019/courses/search\
            ?search_api_views_fulltext=%s&sort_by=field_subject_code&page=%d" % (
                keyword, pagenum)
            r = requests.get(url)
            soup = BeautifulSoup(r.content, "html.parser")
            found = soup.find_all("div", {"class": "views-row"})
            if (len(found) < 1):
                break
            else:
                courses = courses + found
                pagenum += 1
        if (len(courses) < 1):
            await ctx.send("No course found for: %s." % query)
            return

        courseList = {'names': [], 'values': []}
        for course in courses:
            # split results into titles + information
            title = course.find_all("h4")[0].get_text().split(" ")
            courseList['names'].append(' '.join(title[:2]))
            courseList['values'].append(' '.join(title[2:]))
        p = Pages(
            ctx,
            itemList=courseList,
            title='Courses found for {}'.format(query),
            displayOption=(2, 10),
            editableContent=False)
        await p.paginate()

    @commands.command()
    async def xe(self, ctx, *, query: str):
        """Currency conversion.
        Uses real-time exchange rates taken from http://www.xe.com.
        Usage: ?xe <AMOUNT> <CURRENCY> to <CURRENCY>
        ie. ?xe 60.00 CAD to EUR
        The currencies supported for conversion (and their abbreviations) can be found at http://www.xe.com/currency/.
        """
        await ctx.trigger_typing()
        if '.' in query.split(' ')[
                0]:    # Distinguish regex between floats and ints
            re1 = '([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'
        else:
            re1 = '(\\d+)'
        re2 = '((?:[a-z][a-z]+))'    # Currency FROM
        re3 = '(to)'
        re4 = '((?:[a-z][a-z]+))'    # Currency TO
        ws = '(\\s+)'    # Whitespace
        rg = re.compile(re1 + ws + re2 + ws + re3 + ws + re4,
                        re.IGNORECASE | re.DOTALL)
        m = rg.search(query)
        if m:
            url = 'http://www.xe.com/currencyconverter/convert/?Amount=%s&From=%s&To=%s' % (
                m.group(1), m.group(3), m.group(7))
            r = requests.get(url)
            soup = BeautifulSoup(r.content, "html.parser")
            r.close()
            convertedCOST = soup.find('span', {
                'class': 'uccResultAmount'
            }).get_text()
            #FIXME: there has to be a more elegant way to print this
            await ctx.send(
                "%s %s = %s %s" % (m.group(1), m.group(3).upper(),
                                   convertedCOST, m.group(7).upper()))
        else:
            await ctx.send(""":warning: Wrong format.
            The correct format is `?xe <AMOUNT> <CURRENCY> to <CURRENCY>`.
            ie. `?xe 60.00 CAD to EUR`""")

    @commands.command()
    async def mose(self, ctx, dollar: float):
        """Currency conversion. Converts $$$ to the equivalent number of samosas, based on holy prices.
        Usage: `?mose <AMOUNT>`
        i.e. ?mose 200
        """
        if dollar < 0:
            await ctx.send("Trying to owe samosas now, are we? :wink:")
            return
        total = dollar // 2 * 3
        if (math.floor(dollar) % 2 == 1):
            total += 1
        await ctx.send("$%.2f is worth %d samosas." % (dollar, total))

    @commands.command()
    async def tepid(self, ctx):
        """Retrieves the CTF printers' statuses from tepid.science.mcgill.ca"""
        url = "https://tepid.science.mcgill.ca:8443/tepid/screensaver/queues/status"
        r = requests.get(url)
        data = r.json()
        for key, value in data.items():
            if value == True:
                await ctx.send("A printer in " + key + " room is up!")
            else:
                await ctx.send("A printer in " + key + " is down!")


def setup(bot):
    bot.add_cog(Helpers(bot))
