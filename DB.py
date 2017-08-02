#!/usr/bin/env python3

import discord
from discord.ext import commands
import asyncio
import sqlite3
from datetime import datetime
import random, os
from tabulate import tabulate

# Set path to your .db file here
DB_PATH = 'PATH_TO_DB'

bot = commands.Bot(command_prefix='%')

@bot.event
@asyncio.coroutine
def on_ready():
    print('Logged in as {0} ({1})'.format(bot.user.name, bot.user.id))

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
def q(member: discord.Member, *, query: str=None):
	conn = sqlite3.connect(DB_PATH)
	c = conn.cursor()
	t = (member.id,)
	if query is None:
		quoteslist = c.execute('SELECT Quote FROM Quotes WHERE ID=?',t).fetchall()
	else:
		t = (member.id, '%'+query+'%')
		quoteslist = c.execute('SELECT Quote FROM Quotes WHERE ID=? AND Quote LIKE ?',t).fetchall()
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
	conn = sqlite3.connect(DB_PATH)
	c = conn.cursor()
	t = (ctx.message.author.id,)
	quoteslist = c.execute('SELECT Quote FROM Quotes WHERE ID=?',t).fetchall()
	if not quoteslist:
		yield from bot.say('No quotes found.')
		conn.close()
		return
	else:
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
			yield from bot.say(msg)
		else:
			msg += '```'
			yield from bot.say(msg)
			msg = '```\n[0] Exit without deleting quotes```'
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
def restart():
    yield from bot.say('https://streamable.com/dli1')
    python = sys.executable
    os.execl(python, python, *sys.argv)

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
	yield from bot.send_message(ctx.message.channel, '```Java\n'+tabulate(table, headers=["NAME","#"], tablefmt="fancy_grid")+'```')

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
