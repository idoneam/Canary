import discord
from discord.ext import commands
import asyncio
import requests
import urllib.request
import urllib.error
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

@bot.command(pass_context=True)
@asyncio.coroutine
def urban(ctx, *, query: str):
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

#prints latex equations
@bot.command(pass_context=True)
@asyncio.coroutine
def tex(ctx, *, query: str):
    if "$" in ctx.message.content:
        tex=""
        sp=ctx.message.content.split('$')
        if(len(sp)<3):
             yield from bot.send_message(ctx.message.channel, 'PLEASE USE \'$\' AROUND YOUR LATEX EQUATIONS. CHIRP.')
             return
        #yield from bot.send_message(ctx.message.channel, 'LATEX FOUND. CHIRP.')
        up = int(len(sp)/2)
        for i in range(up):
            tex+="\["+sp[2*i+1]+"\]"
        fn ='tmp.png'
        preview(tex, viewer='file', filename=fn)
        yield from bot.send_file(ctx.message.channel, fn)
    else:
        yield from bot.send_message(ctx.message.channel, 'PLEASE USE \'$\' AROUND YOUR LATEX EQUATIONS. CHIRP.')

#searches for keyword in mcgill courses and prints results
@bot.command(pass_context=True)
@asyncio.coroutine
def search(ctx, *, query: str):
    keyword=query.replace (" ", "+")
    pagelimit = 5
    pagenum=0
    courses=[]
    while(True and pagenum < pagelimit ):
        url = "http://www.mcgill.ca/study/2016-2017/courses/search\
        ?search_api_views_fulltext=%s&sort_by=field_subject_code&page=%d" % (keyword, pagenum)
        r = requests.get(url)
        soup = BeautifulSoup(r.content , "html.parser")
        found = soup.find_all("div", {"class": "views-row"})
        if(len(found)<1):
            break
        else:
            courses = courses+found
            pagenum+=1
    if(len(courses)<1):
        print("No course found error")
        yield from bot.say("No course found for: %s." % query)
        return
                
    em = discord.Embed(title="Courses Found 1 / %d" % len(courses)/24, colour=0xDA291C)
    c = 1
    #create a new message every 24 results 
    for course in courses:
        #split results into titles + information
        title = course.find_all("h4")[0].get_text().split(" ")
        if(len(title)>2):
            em.add_field(name=' '.join(title[:2]), value=' '.join(title[2:]))
            c+=1
            if(c%24==0):
                yield from bot.send_message(ctx.message.channel, embed=em)
                em = discord.Embed(title="Courses Found %d / %d" % (c/24,len(courses)/24), colour=0xDA291C) 
    yield from bot.send_message(ctx.message.channel, embed=em)
    return
    
bot.run('token')
