import discord
from discord.ext import commands
import asyncio
import requests
import urllib.request
import urllib.error
import os
from bs4 import BeautifulSoup
from sympy import preview

bot = commands.Bot(command_prefix='?')

@bot.event
@asyncio.coroutine
def on_ready():
    print('Logged in as {0} ({1})'.format(bot.user.name, bot.user.id))

@bot.command()
@asyncio.coroutine
def chirp():
    """:^)"""
    yield from bot.say('CHIRP CHIRP')

@bot.command()
@asyncio.coroutine
def weather():
    """Retrieves current conditions from http://weather.gc.ca/city/pages/qc-147_metric_e.html"""
    # Replace link with any city weather link from http://weather.gc.ca/
    url = "http://weather.gc.ca/city/pages/qc-147_metric_e.html"
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")
    r.close()
    # Get date
    observed_label = soup.find("dt",string="Date: ")
    observed = observed_label.find_next_sibling().get_text().rstrip()
    # Get temperature
    temperature_label = soup.find("dt",string="Temperature:")
    temperature = temperature_label.find_next_sibling().get_text().strip()
    # Get condition
    condition_label = soup.find("dt",string="Condition:")
    condition = condition_label.find_next_sibling().get_text().strip()
    # Get pressure
    pressure_label = soup.find("dt",string="Pressure:")
    pressure = pressure_label.find_next_sibling().get_text().strip()
    # Get tendency
    tendency_label = soup.find("dt",string="Tendency:")
    tendency = tendency_label.find_next_sibling().get_text().strip()
    # Get wind
    wind_label = soup.find("dt",string="Wind:")
    wind = wind_label.find_next_sibling().get_text().strip()
    windchill = u"N/A"
    try:
        # Get windchill, only if it can be found.
        windchill_label = soup.find("a",string="Wind Chill")
        windchill = windchill_label.find_next().get_text().strip() + u"\xb0C"
    except:
        pass

    weather_now = u"Conditions observed at: **%s**.\nTemperature: **%s**\nCondition: **%s**\nPressure: **%s**\nTendency: **%s**\nWind speed: **%s**\nWind chill: **%s**" % (observed,temperature,condition,pressure,tendency,wind,windchill)

    yield from bot.say(weather_now)

@bot.command(pass_context=True)
@asyncio.coroutine
def course(ctx, *, query: str):
    """Prints a summary of the queried course, taken from the course calendar.
    For now, you must include a space between the course code and number.
    ie. '?course comp 206' works, but '?course comp206' does not.

    Note: Bullet points without colons (':') are not parsed because I have yet to see one that actually has useful information."""
    link = "http://www.mcgill.ca/study/2016-2017/courses/%s" % query.replace(' ', '-')
    try:
        r = urllib.request.urlopen(link)
    except urllib.error.HTTPError:
        print("Error")
        yield from bot.say("No course found for: %s." % query)
        return
    soup = BeautifulSoup(r, "html.parser")
    r.close()

    # XXX: brute-force parsing at the moment
    title = soup.find_all("h1", {"id": "page-title"})[0].get_text().strip()
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

    em = discord.Embed(title=title, description=link, colour=0xDA291C)
    em.add_field(name="Overview", value=overview, inline=False)
    em.add_field(name="Terms", value=terms, inline=False)
    em.add_field(name="Instructor(s)", value=instructors, inline=False)
    for (a, b) in tidbits:
        em.add_field(name=a, value=b, inline=False)
    yield from bot.send_message(ctx.message.channel, embed=em)

@bot.command(pass_context=True)
@asyncio.coroutine
def urban(ctx, *, query: str):
    """Fetches the top definition from Urban Dictionary."""
    link = "http://www.urbandictionary.com/define.php?term=%s" % query.replace(' ', '+')
    try:
        r = urllib.request.urlopen(link)
    except urllib.error.HTTPError:
        print("Error")
        yield from bot.say("SOMETHING'S WRONG. CHIRP.")
        return
    soup = BeautifulSoup(r, 'html.parser')
    word = soup.find('div', {'class': 'def-header'}).a
    if not word:
        yield from bot.say("No definition found for **%s**." % query)
        return
    word = word.get_text()
    definition = soup.find('div', {'class': 'meaning'}).get_text()
    examples = soup.find('div', {'class': 'example'}).get_text().strip()
    em = discord.Embed(title=word, description=definition, colour=0x1D2439).set_footer(text="Fetched from the top definition on UrbanDictionary.", icon_url='http://d2gatte9o95jao.cloudfront.net/assets/apple-touch-icon-2f29e978facd8324960a335075aa9aa3.png')
    # em.add_field(name="Examples", value=examples)
    yield from bot.send_message(ctx.message.channel, embed=em)

@bot.command(pass_context=True)
@asyncio.coroutine
def tex(ctx, *, query: str):
    """Parses and prints LaTeX equations."""
    if "$" in ctx.message.content:
        tex = ""
        sp = ctx.message.content.split('$')
        if(len(sp) < 3):
            yield from bot.send_message(ctx.message.channel, 'PLEASE USE \'$\' AROUND YOUR LATEX EQUATIONS. CHIRP.')
            return
        # yield from bot.send_message(ctx.message.channel, 'LATEX FOUND. CHIRP.')
        up = int(len(sp) / 2)
        for i in range(up):
            tex += "\["+sp[2*i+1]+"\]"
        fn = 'tmp.png'
        preview(tex, viewer='file', filename=fn)
        yield from bot.send_file(ctx.message.channel, fn)
    else:
        yield from bot.send_message(ctx.message.channel, 'PLEASE USE \'$\' AROUND YOUR LATEX EQUATIONS. CHIRP.')

@bot.command(pass_context=True)
@asyncio.coroutine
def search(ctx, *, query: str):
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
        yield from bot.say("No course found for: %s." % query)
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
                yield from bot.send_message(ctx.message.channel, embed=em)
                em = discord.Embed(title="Courses Found %d / %d" % (c/24+1,len(courses)/24+1), colour=0xDA291C)
    yield from bot.send_message(ctx.message.channel, embed=em)
    return

bot.run(os.environ.get("DISCORD_TOKEN"))
