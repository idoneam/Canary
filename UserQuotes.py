#!/usr/bin/env python3

import discord,asyncio,sqlite3,random,os
from discord.ext import commands
from datetime import datetime


# Set path to your .db file here
QUOTES_DB_PATH = 'QUOTES_DB_PATH'

bot = commands.Bot(command_prefix='?')

@bot.event
@asyncio.coroutine
def on_ready():
    print('Logged in as {0} ({1})'.format(bot.user.name, bot.user.id))

@bot.command(pass_context=True)
@asyncio.coroutine
def addq(ctx, member: discord.Member, *, quote: str):
	conn = sqlite3.connect(QUOTES_DB_PATH)
	c = conn.cursor()
	t = (member.id, member.name, quote, ctx.message.timestamp.strftime("%c"))
	c.execute('INSERT INTO quotes VALUES (?,?,?,?)', t)
	yield from bot.say('`Quote added.`')
	conn.commit()
	conn.close()

@bot.command()
@asyncio.coroutine
def q(member: discord.Member):
	conn = sqlite3.connect(QUOTES_DB_PATH)
	c = conn.cursor()
	t = (member.id,)
	quoteslist = c.execute('SELECT quote FROM quotes WHERE id=?',t).fetchall()
	if not quoteslist:
		yield from bot.say('No quotes found.')
		conn.close()
		return
	else:
		quote = random.choice(quoteslist)[0]
		yield from bot.say(":mega: %s" % quote)
		conn.close()

# This WILL throw a HTTPError if the quote list is too long
# TODO: Find a solution to fix that
@bot.command(pass_context=True)
@asyncio.coroutine
def delq(ctx):
	conn = sqlite3.connect(QUOTES_DB_PATH)
	c = conn.cursor()
	t = (ctx.message.author.id,)
	quoteslist = c.execute('SELECT quote FROM quotes WHERE id=?',t).fetchall()
	if not quoteslist:
		yield from bot.say('No quotes found.')
		conn.close()
		return
	else:
		msg = "Please choose a quote you would like to delete.\n\n```"
		for i in range(len(quoteslist)):
			msg += '[%d] %s\n' % (i+1, quoteslist[i][0])
		msg += '\n[0] Exit without deleting quotes```'
	yield from bot.say(msg)

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
		c.execute('DELETE FROM quotes WHERE quote=? AND id=?', t)
		yield from bot.say("Quote successfully deleted.")
		conn.commit()
		conn.close()

bot.run(os.environ.get("DISCORD_TOKEN"))
