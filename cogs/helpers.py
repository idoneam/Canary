#!/usr/bin/env python3

# discord-py requirements
import discord
from discord.ext import commands
import asyncio

# URL access and parsing
import requests
from bs4 import BeautifulSoup

# Other utilities
from sympy import preview
import re
import math
import time
import os
from .utils.paginator import Pages


class Helpers():
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def exam(self, ctx):
        await ctx.send(
            'https://mcgill.ca/students/exams/files/students.exams/april_2018_final_exam_schedule_with_room_locations.pdf'
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
        em = discord.Embed(title="Weather in Montreal").set_image(
            url='http://wttr.in/Montreal_2mpq_lang=en.png?_=%d' %
            round(time.time()))
        await ctx.send(embed=em)

    @commands.command()
    async def wttrMoon(self, ctx):
        em = discord.Embed(title="Current moon phase").set_image(
            url='http://wttr.in/moon.png')
        await ctx.send(embed=em)

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
    async def urban(self, ctx, *, query: str):
        """Fetches the top definition from Urban Dictionary."""
        await ctx.trigger_typing()
        url = "http://www.urbandictionary.com/define.php?term=%s" % query.replace(
            ' ', '+')
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        r.close()
        word = soup.find('div', {'class': 'def-header'})
        if not word:
            await ctx.send("No definition found for **%s**." % query)
            return
        word = word.get_text()
        definition = soup.find('div', {'class': 'meaning'}).get_text()
        examples = soup.find('div', {'class': 'example'}).get_text().strip()
        em = discord.Embed(
            title=word, description=definition, colour=0x1D2439
        ).set_footer(
            text="Fetched from the top definition on UrbanDictionary.",
            icon_url=
            'http://d2gatte9o95jao.cloudfront.net/assets/apple-touch-icon-2f29e978facd8324960a335075aa9aa3.png'
        )
        # em.add_field(name="Examples", value=examples)
        await ctx.send(embed=em)

    @commands.command()
    async def tex(self, ctx, *, query: str):
        """Parses and prints LaTeX equations."""
        await ctx.trigger_typing()
        if "$" in ctx.message.content:
            tex = ""
            sp = ctx.message.content.split('$')
            if (len(sp) < 3):
                await ctx.send(
                    'PLEASE USE \'$\' AROUND YOUR LATEX EQUATIONS. CHIRP.')
                return
            # await bot.send_message(ctx.message.channel, 'LATEX FOUND. CHIRP.')
            up = int(len(sp) / 2)
            for i in range(up):
                tex += "\[" + sp[2 * i + 1] + "\]"
            fn = 'tmp.png'
            preview(tex, viewer='file', filename=fn, euler=False)
            await ctx.send(file=discord.File(fp=fn))
            os.remove(fn)
        else:
            await ctx.send(
                'PLEASE USE \'$\' AROUND YOUR LATEX EQUATIONS. CHIRP.')

    @commands.command()
    @commands.cooldown(rate=1, per=120)
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
            option='EMBEDS',
            autosize=(False, 10),
            editableContent=False)
        await p.paginate()

    @search.error
    async def search_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.CommandOnCooldown):
            await ctx.send("Command is on cooldown. Cooldown time: 2 minutes")

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


def setup(bot):
    bot.add_cog(Helpers(bot))
