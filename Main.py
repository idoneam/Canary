#!/usr/bin/env python3

# discord.py requirements
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

# Pillow for image manipulation
import PIL
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
import textwrap

# For DB Functionality
import sqlite3
from datetime import datetime
from tabulate import tabulate

# Set path to your .db file here
DB_PATH = './Martlet.db'

bot = commands.Bot(command_prefix='?')

@bot.event
@asyncio.coroutine
def on_ready():
    print('Logged in as {0} ({1})'.format(bot.user.name, bot.user.id))

@bot.command(pass_context=True)
@asyncio.coroutine
def chosenOne(ctx, arg2 : str):
    '''
    ObiWan feeling the pain, ?chosenOne "botString"
    '''
    
    arg1 = "You were the chosen one!"
    para = textwrap.wrap(arg1, width=27)
    lara = textwrap.wrap(arg2, width=27)

    im = Image.open("images/chosenOne.png")
    MAX_W, MAX_H = im.size
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype("fonts/impact/impact.ttf", 40) #Need a outline font still

    current_h, pad = 40, 1 #Determines the starting line, and the spacing between lines
    for line in para:
        w, h = draw.textsize(line, font=font)
        draw.text(((MAX_W - w) / 2, current_h), line, font=font)
        current_h += h + pad
    newlineh, pad = 200, 1
    for line in lara:
        w, h = draw.textsize(line, font=font)
        draw.text(((MAX_W - w) / 2, newlineh), line, font=font)
        newlineh += h + pad    

    im.save('newchosenOne.png')
    path = "newchosenOne.png"

    yield from bot.send_file(ctx.message.channel, path)
    yield from bot.delete_message(ctx.message) 
    
@bot.command(pass_context=True)
@asyncio.coroutine
def isMayo(ctx, arg1 : str):
    '''
    Patrick's question, ?isMayo "text here"
    '''
    para = textwrap.wrap(arg1, width=27)

    im = Image.open("images/isMayo.png")
    MAX_W, MAX_H = im.size
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype("fonts/impact/impact.ttf", 40) #Need a outline font still

    current_h, pad = 40, 1 #Determines the starting line, and the spacing between lines
    for line in para:
        w, h = draw.textsize(line, font=font)
        draw.text(((MAX_W - w) / 2, current_h), line, font=font)
        current_h += h + pad  

    im.save('newisMayo.png')
    path = "newisMayo.png"

    yield from bot.send_file(ctx.message.channel, path)
    yield from bot.delete_message(ctx.message) 
    
    
@bot.command(pass_context=True)
@asyncio.coroutine
def notsure(ctx, arg1 : str, arg2 : str):
    '''
    not sure meme, ?notsure "topString" "botString"
    '''
    para = textwrap.wrap(arg1, width=27)
    lara = textwrap.wrap(arg2, width=27)

    im = Image.open("images/notsure.png")
    MAX_W, MAX_H = im.size
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype("fonts/impact/impact.ttf", 40) #Need a outline font still

    current_h, pad = 40, 1 #Determines the starting line, and the spacing between lines
    for line in para:
        w, h = draw.textsize(line, font=font)
        draw.text(((MAX_W - w) / 2, current_h), line, font=font)
        current_h += h + pad
    newlineh, pad = 275, 1
    for line in lara:
        w, h = draw.textsize(line, font=font)
        draw.text(((MAX_W - w) / 2, newlineh), line, font=font)
        newlineh += h + pad    

    im.save('newnotsure.png')
    path = "newnotsure.png"

    yield from bot.send_file(ctx.message.channel, path)
    yield from bot.delete_message(ctx.message) 



"""For sending gifs 
@bot.command
@asyncio.coroutine
def gifs(ctx):

    #path = "images\\yes.gif"
    #yield from bot.send_file(ctx.message.channel, path) #From stored on server
    #yield from bot.send_message(ctx.message.channel, "http://i.imgur.com/GgNi3Xr.gif") #From internet
    #yield from bot.delete_message(ctx.message)
"""        

@bot.command(pass_context=True)
@asyncio.coroutine
def lenny(ctx):
    """
    Lenny face
    """
    yield from bot.send_message(ctx.message.channel, "( ͡° ͜ʖ ͡°) ")
    yield from bot.delete_message(ctx.message)  

    
@bot.command(pass_context=True)
@asyncio.coroutine
def awyiss(ctx):
    """
    aw yiss mother fucking breadcrumbs
    """
    yield from bot.send_message(ctx.message.channel, "http://gph.is/294XA0F")
    yield from bot.delete_message(ctx.message)       

@bot.command(pass_context=True)
@asyncio.coroutine    
def gohere(ctx):
    """
    for future mcgillians
    """
    yield from bot.send_message(ctx.message.channel, "http://gph.is/1cN9wO1")
    yield from bot.delete_message(ctx.message)     

@bot.command(pass_context=True)
@asyncio.coroutine    
def todo(ctx):
    """
    when its the weekend
    """
    yield from bot.send_message(ctx.message.channel, "http://gph.is/2dnMUJ6")
    yield from bot.delete_message(ctx.message)    

@bot.command(pass_context=True)
@asyncio.coroutine    
def love(ctx):
    """
    back off yo
    """
    yield from bot.send_message(ctx.message.channel, "http://gph.is/2eePP6k")
    yield from bot.delete_message(ctx.message)     

@bot.command(pass_context=True)
@asyncio.coroutine    
def tunak(ctx):
    """
    bitch pls
    """
    yield from bot.send_message(ctx.message.channel, "http://i.imgur.com/rNNLyjK.gif")
    yield from bot.delete_message(ctx.message)

@bot.command(pass_context=True)
@asyncio.coroutine    
def bb8(ctx):
    """
    nice job bb8
    """
    yield from bot.send_message(ctx.message.channel, "http://i.imgur.com/SUvaUM2.gif")
    yield from bot.delete_message(ctx.message)

@bot.command(pass_context=True)
@asyncio.coroutine    
def longtime(ctx):
    """
    That's a name I've not heard in a long time
    """
    yield from bot.send_message(ctx.message.channel, "http://i.imgur.com/e1T1xcq.mp4")
    yield from bot.delete_message(ctx.message)

@bot.command(pass_context=True)
@asyncio.coroutine    
def overhead(ctx):
    """
    Not actually what this gif does...
    """
    yield from bot.send_message(ctx.message.channel, "http://i.imgur.com/xCS121c.gif")
    yield from bot.delete_message(ctx.message)   

@bot.command(pass_context=True)
@asyncio.coroutine    
def sideglance(ctx):
    """
    when even bernie sanders hates you
    """
    yield from bot.send_message(ctx.message.channel, "http://i.imgur.com/xc6gMIo.gif")
    yield from bot.delete_message(ctx.message)

@bot.command(pass_context=True)
@asyncio.coroutine    
def ye(ctx):
    """
    Better Call Saul is awesome
    """
    yield from bot.send_message(ctx.message.channel, "http://i.imgur.com/iSMh7zO.gif")
    yield from bot.delete_message(ctx.message)    

@bot.command(pass_context=True)
@asyncio.coroutine    
def dealwithit(ctx):
    """
    deal with it trump
    """
    yield from bot.send_message(ctx.message.channel, "http://i.imgur.com/5jzN8zV.mp4")
    yield from bot.delete_message(ctx.message)
    
@bot.command(pass_context=True)
@asyncio.coroutine    
def lmao(ctx):
    """
    that's hilarious
    """
    yield from bot.send_message(ctx.message.channel, "http://i.imgur.com/o5Cc3i2.mp4")
    yield from bot.delete_message(ctx.message)    
    
@bot.command()
@asyncio.coroutine
def chirp():
    """:^)"""
    yield from bot.say('CHIRP CHIRP')

@bot.command(pass_context=True)
@asyncio.coroutine
def weather(ctx):
    """Retrieves current weather conditions.
    Data taken from http://weather.gc.ca/city/pages/qc-147_metric_e.html"""
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

    # weather_now = u"Conditions observed at: **%s**.\nTemperature: **%s**\nCondition: **%s**\nPressure: **%s**\nTendency: **%s**\nWind speed: **%s**\nWind chill: **%s**" % (observed,temperature,condition,pressure,tendency,wind,windchill)
    weather_now = discord.Embed(title='Current Weather', description='Conditions observed at %s' % observed, colour=0x7EC0EE)
    weather_now.add_field(name="Temperature", value=temperature, inline=True)
    weather_now.add_field(name="Condition", value=condition, inline=True)
    weather_now.add_field(name="Pressure", value=pressure, inline=True)
    weather_now.add_field(name="Tendency", value=tendency, inline=True)
    weather_now.add_field(name="Wind Speed", value=wind, inline=True)
    weather_now.add_field(name="Wind Chill", value=windchill, inline=True)
    yield from bot.send_message(ctx.message.channel, embed=weather_now)

@bot.command(pass_context=True)
@asyncio.coroutine
def wttr(ctx):
    em = discord.Embed(title="Weather in Montreal").set_image(url='http://wttr.in/Montreal_2mpq_lang=en.png?_=%d' % round(time.time()))
    yield from bot.send_message(ctx.message.channel, embed=em)

@bot.command(pass_context=True)
@asyncio.coroutine
def course(ctx, *, query: str):
    """Prints a summary of the queried course, taken from the course calendar.
    ie. ?course comp 206
    Note: Bullet points without colons (':') are not parsed because I have yet to see one that actually has useful information."""
    fac = r'([a-zA-Z]{4})'
    num = r'(\d{3})'
    result = re.compile(fac+r'\s?'+num, re.IGNORECASE|re.DOTALL).search(query)
    if not result:
        yield from bot.say(':warning: Incorrect format. The correct format is `?course <course name>`.')
    search_term = result.group(1) + '-' + result.group(2)
    url = "http://www.mcgill.ca/study/2017-2018/courses/%s" % search_term
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")
    r.close()

    # XXX: brute-force parsing at the moment
    title = soup.find_all("h1", {"id": "page-title"})[0].get_text().strip()
    if title == 'Page not found':
        yield from bot.send_message(ctx.message.channel, "No course found for %s." % query)
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
    yield from bot.send_message(ctx.message.channel, embed=em)

@bot.command(pass_context=True)
@asyncio.coroutine
def urban(ctx, *, query: str):
    """Fetches the top definition from Urban Dictionary."""
    url = "http://www.urbandictionary.com/define.php?term=%s" % query.replace(' ', '+')
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    r.close()
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
        preview(tex, viewer='file', filename=fn, euler=False)
        yield from bot.send_file(ctx.message.channel, fn)
        fn.close()
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

@bot.command(pass_context=True)
@asyncio.coroutine
def xe(ctx, *, query: str):
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
        yield from bot.say("%s %s = %s %s" % (m.group(1),m.group(3).upper(),convertedCOST,m.group(7).upper()))
    else:
        yield from bot.say(""":warning: Wrong format.
        The correct format is `?xe <AMOUNT> <CURRENCY> to <CURRENCY>`.
        ie. `?xe 60.00 CAD to EUR`""")

@bot.command(pass_context=True)
@asyncio.coroutine
def restart():
    yield from bot.say('https://streamable.com/dli1')
    python = sys.executable
    os.execl(python, python, *sys.argv)

@bot.command(pass_context=True)
@asyncio.coroutine
def trivia(ctx, questions: int=10):
    """Starts a trivia game.
    Optional number of questions as argument; defaults to 10 questions."""
    if questions <= 2:
        # At least 3 questions
        yield from bot.say(":warning: Too little questions!")
        return
    # TODO: implement a scoreboard to keep track of the winner
    scoreboard = {}
    for i in range(questions):
        r = requests.get('https://opentdb.com/api.php?amount=1&type=multiple')
        q = r.json()
        q = q['results'][0]
        r.close()
        question, category, answer = (unescape(q['question']), unescape(q['category']), unescape(q['correct_answer']))
        print(question, answer)
        yield from bot.say("**Category: **%s\n**Question: **%s" % (category, question))

        def check(msg):
            if msg.content.lower() == answer.lower():
                return True
            return False

        response = yield from bot.wait_for_message(timeout=4.0, check=check)
        if response != None:
            yield from bot.say("%s is correct!" % response.author.mention)
            continue

        clue = ''.join('?' if random.randint(0,3) and i!=' ' else i for i in answer)
        yield from bot.say("`Clue: %s`" % clue)

        response = yield from bot.wait_for_message(timeout=20.0, check=check)
        if response != None:
            yield from bot.say("%s is correct!" % response.author.mention)
        else:
            yield from bot.say("Time's up!\n**Answer: **%s" % answer)

@bot.command(pass_context=True)
@asyncio.coroutine
def mose(ctx, dollar: float):
    """Currency conversion. Converts $$$ to the equivalent number of samosas, based on holy prices.
    Usage: `?mose <AMOUNT>`
    i.e. ?mose 200
    """
    if dollar<0:
        yield from bot.say("Trying to owe samosas now, are we? :wink:")
        return
    total = dollar//2*3
    if(math.floor(dollar)%2==1):
        total += 1
    yield from bot.say("$%.2f is worth %d samosas." % (dollar,total))

@bot.event
@asyncio.coroutine
def on_message(message):
    if message.author == bot.user:
        return
    if message.content == "dammit marty":
        yield from bot.send_message(message.channel, ":c")
    if message.content == "worm":
        yield from bot.send_message(message.channel, "walk without rhythm, and it won't attract the worm.")
    yield from bot.process_commands(message)

# Quote Database Commands
@bot.command(pass_context=True)
@asyncio.coroutine
def addq(ctx, member: discord.Member, *, quote: str):
	conn = sqlite3.connect(DB_PATH)
	c = conn.cursor()
	t = (member.id, member.name, quote, ctx.message.timestamp.strftime("%c"))
	c.execute('INSERT INTO Quotes VALUES (?,?,?,?)', t)
	yield from bot.say('`Quote added.`')
	conn.commit()
	conn.close()

@bot.command()
@asyncio.coroutine
def q(str1: str=None, *, str2: str=None):   #member: discord.Member=None, *, query: str=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if str1 is None:    # no argument
        quotes = c.execute('SELECT Quote FROM Quotes').fetchall()
        quote = random.choice(quotes)
        Name = c.execute('SELECT Name FROM Quotes WHERE Quote LIKE ?', quote).fetchall()[0][0]
        yield from bot.say("%(ID)s :mega: %(quote)s" % {"ID": Name, "quote": quote[0]})
        conn.close()
        return
    elif str2 is None:  # 1 argument
        numArgs = 1
        args = str1
    else:   # 2 arguments
        numArgs = 2
        argl = [str1, str2]
        args = ' '.join(argl)
    if (args[1] == '@'):    # member argument supplied
        args = args.split() 
        qId = ''
        for i in range(len(args[0])):
            if (args[0][i] in '0123456789'):
                qId = qId + args[0][i]
        if numArgs == 2:    # query
            t = (qId, '%'+(' '.join(args[1:]))+'%')
            quoteslist = c.execute('SELECT Quote FROM Quotes WHERE ID=? AND Quote LIKE ?',t).fetchall()
        else:   # no query
            t = (qId,)
            quoteslist = c.execute('SELECT Quote FROM Quotes WHERE ID=?',t).fetchall()
        if not quoteslist:  # no result
            yield from bot.say('No quotes found.')
            conn.close()
            return
        else:   # result
            quote = random.choice(quoteslist)
            yield from bot.say(":mega: %s" % quote)
            conn.close()
            return
    else:   # no member argument - only query
        t = ('%'+args[0:]+'%',)
        quoteslist = c.execute('SELECT Quote FROM Quotes WHERE Quote LIKE ?', t).fetchall()
        if not quoteslist:
            yield from bot.say('No quotes found.')
            conn.close()
            return
        else:
            quote = random.choice(quoteslist)
            Name = c.execute('SELECT Name FROM Quotes WHERE Quote LIKE ?', quote).fetchall()[0][0]
            yield from bot.say("%(ID)s :mega: %(quote)s" % {"ID": Name, "quote": quote[0]})
            conn.close()
            return

@bot.command()
@asyncio.coroutine
def lq(member: discord.Member):
	conn = sqlite3.connect(DB_PATH)	
	c = conn.cursor()
	t = (member.id,)
	quoteslist = c.execute('SELECT Quote FROM Quotes WHERE ID=?',t).fetchall()
	msg = "```Quotes: \n"
	for i in range(len(quoteslist)):
		if ((len(msg) + len('[%d] %s\n' % (i+1, quoteslist[i][0]))) > 1996):
			msg += '```'
			yield from bot.say(msg)
			msg = '```[%d] %s\n' % (i+1, quoteslist[i][0])
		else:  
			msg += '[%d] %s\n' % (i+1, quoteslist[i][0])
	if ((len(msg) + len('\n ~ End of Quotes ~```')) < 1996):
		msg += '\n ~ End of Quotes ~```'
		yield from bot.say(msg, delete_after=30)
	else:
		msg += '```'
		yield from bot.say(msg, delete_after=30)
		msg = '```\n ~ End of Quotes ~```'
		yield from bot.say(msg, delete_after=30)

@bot.command(pass_context=True)
@asyncio.coroutine
def delq(ctx):
	conn = sqlite3.connect(DB_PATH)
	c = conn.cursor()
	t = (ctx.message.author.id,)
	quoteslist = c.execute('SELECT Quote FROM Quotes WHERE ID=?',t).fetchall()
	if not quoteslist:
		yield from bot.say('No quotes found.')
		conn.close()
		return
	else:
		# print the quotes of the user in pages
		msg = "Please choose a quote you would like to delete.\n\n```"
		for i in range(len(quoteslist)):
			if ((len(msg) + len('[%d] %s\n' % (i+1, quoteslist[i][0]))) > 1996):
				msg += '```'
				yield from bot.say(msg)
				msg = '```[%d] %s\n' % (i+1, quoteslist[i][0])
			else:  
				msg += '[%d] %s\n' % (i+1, quoteslist[i][0])
		if ((len(msg) + len('\n[0] Exit without deleting quotes```')) < 1996):
			msg += '\n[0] Exit without deleting quotes```'
			yield from bot.say(msg, delete_after=30)
		else:
			msg += '```'
			yield from bot.say(msg, delete_after=30)
			msg = '```\n[0] Exit without deleting quotes```'
			yield from bot.say(msg, delete_after=30)

	def check(choice):
		if 0<=int(choice.content)<=(1+len(quoteslist)):
			return True
		else:
			yield from bot.say("Invalid input.")
			return False

	response = yield from bot.wait_for_message(author=ctx.message.author, check=check)
	choice = int(response.content)
	if choice==0:
		yield from bot.say("Exited quote deletion menu.")
		conn.close()
		return
	else:
		t = (quoteslist[choice-1][0], ctx.message.author.id)
		c.execute('DELETE FROM Quotes WHERE Quote=? AND ID=?', t)
		yield from bot.say("Quote successfully deleted.")
		conn.commit()
		conn.close()

@bot.event
@asyncio.coroutine
def on_reaction_add(reaction,user):
	# Check for Martlet emoji + upmartletting yourself
    if reaction.emoji.id != "240730706303516672" or reaction.message.author == user:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    t = (int(reaction.message.author.id),)
    if not c.execute('SELECT * FROM Members WHERE ID=?', t).fetchall():
        t = (reaction.message.author.id, reaction.message.author.name, 1)
        c.execute('INSERT INTO Members VALUES (?,?,?)', t)
    else:
        c.execute('UPDATE Members SET Upmartlet=Upmartlet+1 WHERE ID=?',t)
    conn.commit()
    conn.close()

@bot.command(pass_context=True)
@asyncio.coroutine
def ranking(ctx):
	conn = sqlite3.connect(DB_PATH)
	c = conn.cursor()
	c.execute("SELECT * FROM Members ORDER BY Upmartlet DESC;")
	members = c.fetchall()[:7]
	table = []
	for (ID, DisplayName, Upmartlet) in members:
		table.append((DisplayName, Upmartlet))
	yield from bot.say(ctx.message.channel, '```Java\n'+tabulate(table, headers=["NAME","#"], tablefmt="fancy_grid")+'```', delete_after=30)

@bot.event
@asyncio.coroutine
def on_reaction_remove(reaction,user):
    if reaction.emoji.id != "240730706303516672" or reaction.message.author == user:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    t = (int(reaction.message.author.id),)
    c.execute('UPDATE Members SET Upmartlet=Upmartlet-1 WHERE ID=?',t)
    conn.commit()
    conn.close()

bot.run(os.environ.get("DISCORD_TOKEN"))
