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
import re, os, sys, random, math, time
from html import unescape


class Helpers():
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @asyncio.coroutine
    def exam(self):
        yield from self.bot.say('https://www.mcgill.ca/students/exams/files/students.exams/december_2017_final_schedule_with_room_locations_12.pdf')


    @commands.command(pass_context=True)
    @asyncio.coroutine
    def weather(self, ctx):
        """Retrieves current weather conditions.
        Data taken from http://weather.gc.ca/city/pages/qc-147_metric_e.html"""
        # Replace link with any city weather link from http://weather.gc.ca/
        url = "http://weather.gc.ca/city/pages/qc-147_metric_e.html"
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        r.close()
        # Get date
        observed_label = soup.find("dt",string="Date: ")
        # Get temperature
        temperature_label = soup.find("dt",string="Temperature:")
        # Get condition
        condition_label = soup.find("dt",string="Condition:")
        # Get pressure
        pressure_label = soup.find("dt",string="Pressure:")
        # Get tendency
        tendency_label = soup.find("dt",string="Tendency:")
        # Get wind
        wind_label = soup.find("dt",string="Wind:")
        # Get windchill, only if it can be found.
        try:
            windchill_label = soup.find("a",string="Wind Chill")
            windchill = windchill_label.find_next().get_text().strip() + u"\xb0C"
        except:
            windchill = u"N/A"

        weather_now = discord.Embed(title='Current Weather', description='Conditions observed at %s' % observed_label.find_next_sibling().get_text().rstrip(), colour=0x7EC0EE)
        weather_now.add_field(name="Temperature", value=temperature_label.find_next_sibling().get_text().strip(), inline=True)
        weather_now.add_field(name="Condition", value=condition_label.find_next_sibling().get_text().strip(), inline=True)
        weather_now.add_field(name="Pressure", value=pressure_label.find_next_sibling().get_text().strip(), inline=True)
        weather_now.add_field(name="Tendency", value=tendency_label.find_next_sibling().get_text().strip(), inline=True)
        weather_now.add_field(name="Wind Speed", value=wind_label.find_next_sibling().get_text().strip(), inline=True)
        weather_now.add_field(name="Wind Chill", value=windchill, inline=True)

        # Weather alerts

        alert_url = "https://weather.gc.ca/warnings/report_e.html?qc67"
        r_alert = requests.get(alert_url)
        alert_soup = BeautifulSoup(r_alert.content, "html.parser")
        # Exists
        alert_title = alert_soup.find("h1",string=re.compile("Alerts.*"))
        # Only gets first <p> of warning. Subsequent paragraphs are ignored.
        try:
            alert_category = alert_title.find_next("h2")
            alert_date = alert_category.find_next("span")
            alert_heading = alert_date.find_next("strong")
            # This is a string for some reason.
            alert_location = alert_heading.find_next(string=re.compile("Montréal.*"))
            # Only gets first <p> of warning. Subsequent paragraphs are ignored
            alert_content = alert_location.find_next("p").get_text().strip()
            alert_content = ". ".join(alert_content.split(".")).strip()

            weather_alert = discord.Embed(title=alert_title.get_text().strip(), description="**%s** at %s" % (alert_category.get_text().strip(),alert_date.get_text().strip()), colour=0xFF0000)
            weather_alert.add_field(name=alert_heading.get_text().strip(), value="**%s**\n%s" %(alert_location.strip(),alert_content), inline=True)
            
        except:
            weather_alert = discord.Embed(title=alert_title.get_text().strip(), description="No alerts in effect.", colour=0xFF0000)

        # TODO Finish final message. Test on no-alert condition.
        
        # Sending final message
        yield from self.bot.send_message(ctx.message.channel, embed=weather_now)
        yield from self.bot.send_message(ctx.message.channel, embed=weather_alert)


    @commands.command(pass_context=True)
    @asyncio.coroutine
    def wttr(self, ctx):
        em = discord.Embed(title="Weather in Montreal").set_image(url='http://wttr.in/Montreal_2mpq_lang=en.png?_=%d' % round(time.time()))
        yield from self.bot.send_message(ctx.message.channel, embed=em)


    @commands.command(pass_context=True)
    @asyncio.coroutine
    def course(self, ctx, *, query: str):
        """Prints a summary of the queried course, taken from the course calendar.
        ie. ?course comp 206
        Note: Bullet points without colons (':') are not parsed because I have yet to see one that actually has useful information."""
        fac = r'([a-zA-Z]{4})'
        num = r'(\d{3})'
        result = re.compile(fac+r'\s?'+num, re.IGNORECASE|re.DOTALL).search(query)
        if not result:
            yield from self.bot.say(':warning: Incorrect format. The correct format is `?course <course name>`.')
        search_term = result.group(1) + '-' + result.group(2)
        url = "http://www.mcgill.ca/study/2017-2018/courses/%s" % search_term
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        r.close()

        # XXX: brute-force parsing at the moment
        title = soup.find_all("h1", {"id": "page-title"})[0].get_text().strip()
        if title == 'Page not found':
            yield from self.bot.send_message(ctx.message.channel, "No course found for %s." % query)
            return
        content = soup.find_all("div", {"class": "content"})[3]
        overview = content.p.get_text().strip()
        terms = soup.find_all("p", {"class": "catalog-terms"})[0].get_text().split(':')[1].strip()
        instructors = soup.find_all("p", {"class": "catalog-instructors"})[0].get_text().split(':')[1].strip()
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
        yield from self.bot.send_message(ctx.message.channel, embed=em)


    @commands.command(pass_context=True)
    @asyncio.coroutine
    def urban(self, ctx, *, query: str):
        """Fetches the top definition from Urban Dictionary."""
        url = "http://www.urbandictionary.com/define.php?term=%s" % query.replace(' ', '+')
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        r.close()
        word = soup.find('div', {'class': 'def-header'}).a
        if not word:
            yield from self.bot.say("No definition found for **%s**." % query)
            return
        word = word.get_text()
        definition = soup.find('div', {'class': 'meaning'}).get_text()
        examples = soup.find('div', {'class': 'example'}).get_text().strip()
        em = discord.Embed(title=word, description=definition, colour=0x1D2439).set_footer(text="Fetched from the top definition on UrbanDictionary.", icon_url='http://d2gatte9o95jao.cloudfront.net/assets/apple-touch-icon-2f29e978facd8324960a335075aa9aa3.png')
        # em.add_field(name="Examples", value=examples)
        yield from self.bot.send_message(ctx.message.channel, embed=em)


    @commands.command(pass_context=True)
    @asyncio.coroutine
    def tex(self, ctx, *, query: str):
        """Parses and prints LaTeX equations."""
        if "$" in ctx.message.content:
            tex = ""
            sp = ctx.message.content.split('$')
            if(len(sp) < 3):
                yield from self.bot.send_message(ctx.message.channel, 'PLEASE USE \'$\' AROUND YOUR LATEX EQUATIONS. CHIRP.')
                return
            # yield from bot.send_message(ctx.message.channel, 'LATEX FOUND. CHIRP.')
            up = int(len(sp) / 2)
            for i in range(up):
                tex += "\["+sp[2*i+1]+"\]"
            fn = 'tmp.png'
            preview(tex, viewer='file', filename=fn, euler=False)
            yield from self.bot.send_file(ctx.message.channel, fn)
            fn.close()
        else:
            yield from self.bot.send_message(ctx.message.channel, 'PLEASE USE \'$\' AROUND YOUR LATEX EQUATIONS. CHIRP.')


    @commands.command(pass_context=True)
    @asyncio.coroutine
    def search(self, ctx, *, query: str):
        """Shows results for the queried keyword(s) in McGill courses"""
        keyword = query.replace(" ", "+")
        pagelimit = 5
        pagenum = 0
        courses = []
        while(True and pagenum < pagelimit):
            url = "http://www.mcgill.ca/study/2016-2017/courses/search\
            ?search_api_views_fulltext=%s&sort_by=field_subject_code&page=%d" % (keyword, pagenum)
            r = requests.get(url)
            soup = BeautifulSoup(r.content, "html.parser")
            found = soup.find_all("div", {"class": "views-row"})
            if(len(found) < 1):
                break
            else:
                courses = courses + found
                pagenum += 1
        if(len(courses) < 1):
            print("No course found error")
            yield from self.bot.say("No course found for: %s." % query)
            return

        em = discord.Embed(title="Courses Found 1 / %d" % (len(courses)/24+1), colour=0xDA291C)
        c = 1
        # create a new message every 24 results
        for course in courses:
            # split results into titles + information
            title = course.find_all("h4")[0].get_text().split(" ")
            if(len(title) > 2):
                em.add_field(name=' '.join(title[:2]), value=' '.join(title[2:]))
                c += 1
                if(c%24 == 0):
                    yield from self.bot.send_message(ctx.message.channel, embed=em)
                    em = discord.Embed(title="Courses Found %d / %d" % (c/24+1,len(courses)/24+1), colour=0xDA291C)
        yield from self.bot.send_message(ctx.message.channel, embed=em)
        return


    @commands.command(pass_context=True)
    @asyncio.coroutine
    def xe(self, ctx, *, query: str):
        """Currency conversion.
        Uses real-time exchange rates taken from http://www.xe.com.
        Usage: ?xe <AMOUNT> <CURRENCY> to <CURRENCY>
        ie. ?xe 60.00 CAD to EUR
        The currencies supported for conversion (and their abbreviations) can be found at http://www.xe.com/currency/.
        """
        if '.' in query.split(' ')[0]:  # Distinguish regex between floats and ints
            re1 = '([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'
        else:
            re1 = '(\\d+)'
        re2 = '((?:[a-z][a-z]+))' # Currency FROM
        re3 = '(to)'
        re4 = '((?:[a-z][a-z]+))' # Currency TO
        ws = '(\\s+)' # Whitespace
        rg = re.compile(re1+ws+re2+ws+re3+ws+re4,re.IGNORECASE|re.DOTALL)
        m = rg.search(query)
        if m:
            url = 'http://www.xe.com/currencyconverter/convert/?Amount=%s&From=%s&To=%s' % (m.group(1),m.group(3),m.group(7))
            r = requests.get(url)
            soup = BeautifulSoup(r.content, "html.parser")
            r.close()
            convertedCOST = soup.find('span', {'class':'uccResultAmount'}).get_text()
            #FIXME: there has to be a more elegant way to print this
            yield from self.bot.say("%s %s = %s %s" % (m.group(1),m.group(3).upper(),convertedCOST,m.group(7).upper()))
        else:
            yield from self.bot.say(""":warning: Wrong format.
            The correct format is `?xe <AMOUNT> <CURRENCY> to <CURRENCY>`.
            ie. `?xe 60.00 CAD to EUR`""")

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def mose(self, ctx, dollar: float):
        """Currency conversion. Converts $$$ to the equivalent number of samosas, based on holy prices.
        Usage: `?mose <AMOUNT>`
        i.e. ?mose 200
        """
        if dollar<0:
            yield from self.bot.say("Trying to owe samosas now, are we? :wink:")
            return
        total = dollar//2*3
        if(math.floor(dollar)%2==1):
            total += 1
        yield from self.bot.say("$%.2f is worth %d samosas." % (dollar,total))

def setup(bot):
    bot.add_cog(Helpers(bot))
