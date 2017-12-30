#!/usr/bin/env python3

# discord-py requirements
import discord
from discord.ext import commands
import asyncio

# Other utilities
import os, sys

# List the extensions (modules) that should be loaded on startup.
startup= ["db", "memes", "helpers"]

bot=commands.Bot(command_prefix='?')


@bot.event
@asyncio.coroutine
def on_ready():
    print('Logged in as {0} ({1})'.format(bot.user.name, bot.user.id))


@bot.command()
@asyncio.coroutine
def load(extension_name: str):
    '''
    Load a specific extension.
    '''
    try:
        bot.load_extension(extension_name)
    except (AttributeError, ImportError) as e:
        yield from bot.say("```{}: {}\n```".format(type(e).__name__,str(e)))

        return
    yield from bot.say("{} loaded.".format(extension_name))
    

@bot.command()
@asyncio.coroutine
def unload(extension_name: str):
    '''
    Unload a specific extension.
    '''
    bot.unload_extension(extension_name)
    yield from bot.say("Unloaded {}.".format(extension_name))
    

@bot.command(pass_context=True)
@asyncio.coroutine
def restart():
    yield from bot.say('https://streamable.com/dli1')
    python = sys.executable
    os.execl(python, python, *sys.argv)


@bot.command(pass_context=True)
@asyncio.coroutine
def update():
    yield from bot.say('https://streamable.com/c7s2o')
    os.system('git pull')
    

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
        

@bot.event
@asyncio.coroutine
def on_message(message):
    if message.author == bot.user:
        return
    if message.content == "dammit marty":
        yield from bot.send_message(message.channel, ":c")
    if message.content == "worm":
        yield from bot.send_message(message.channel, "walk without rhythm, and it won't attract the worm.")
    if message.content == "hey":
        yield from bot.send_message(message.channel, "whats going on?")
    yield from bot.process_commands(message)


# Startup extensions
# If statement will only execute if we are running this file (i.e. won't run if its imported)
if __name__ == "__main__":
    for extension in startup:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print('Failed to load extension {}\n{}: {}'.format(extension, type(e).__name__, e))

    bot.run(os.environ.get("DISCORD_TOKEN"))
