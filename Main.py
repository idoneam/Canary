import discord
from discord.ext import commands
import asyncio
import urllib.request
import urllib.error
from bs4 import BeautifulSoup

bot = commands.Bot(command_prefix='?')

@bot.event
@asyncio.coroutine
def on_ready():
    print('Logged in as {0} ({1})'.format(bot.user.name, bot.user.id))

@bot.command()
@asyncio.coroutine
def chirp():
    yield from bot.say('CHIRP CHIRP')

@bot.command()
@asyncio.coroutine
def exam():
    yield from bot.say('https://www.mcgill.ca/students/exams/files/students.exams/december_2016_final_exam_schedule_with_room_locationsd8.pdf')

@bot.command(pass_context=True)
@asyncio.coroutine
def course(ctx, *, query: str):
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

bot.run('TOKEN')
