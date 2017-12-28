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

# Pillow for image manipulation
import PIL
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
import textwrap

class Memes():
    def __init__(self, bot):
        self.bot = bot


    @commands.command(pass_context=True)
    @asyncio.coroutine
    def lenny(self, ctx):
        """
        Lenny face
        """
        yield from self.bot.send_message(ctx.message.channel, "( ͡° ͜ʖ ͡°) ")
        yield from self.bot.delete_message(ctx.message)  


    @commands.command(pass_context=True)
    @asyncio.coroutine    
    def gohere(self, ctx):
        """
        for future mcgillians
        """
        yield from self.bot.send_message(ctx.message.channel, "http://gph.is/1cN9wO1")
        yield from self.bot.delete_message(ctx.message)
  
    @commands.command(pass_context=True)
    @asyncio.coroutine    
    def tunak(self, ctx):
        """
        bitch pls
        """
        yield from self.bot.send_message(ctx.message.channel, "http://i.imgur.com/rNNLyjK.gif")
        yield from self.bot.delete_message(ctx.message)

   
    @commands.command(pass_context=True)
    @asyncio.coroutine    
    def bb8(self, ctx):
        """
        nice job bb8
        """
        yield from self.bot.send_message(ctx.message.channel, "http://i.imgur.com/SUvaUM2.gif")
        yield from self.bot.delete_message(ctx.message)

    
    @commands.command(pass_context=True)
    @asyncio.coroutine    
    def longtime(self, ctx):
        """
        That's a name I've not heard in a long time
        """
        yield from self.bot.send_message(ctx.message.channel, "http://i.imgur.com/e1T1xcq.mp4")
        yield from self.bot.delete_message(ctx.message)

 
    @commands.command(pass_context=True)
    @asyncio.coroutine    
    def thonk(self, ctx):
        """
        when thonking consumes you
        """
        yield from self.bot.send_message(ctx.message.channel, "https://i.imgur.com/VADGUwj.gifv")
        yield from self.bot.delete_message(ctx.message)

   
    @commands.command(pass_context=True)
    @asyncio.coroutine    
    def dealwithit(self, ctx):
        """
        deal with it trump
        """
        yield from self.bot.send_message(ctx.message.channel, "http://i.imgur.com/5jzN8zV.mp4")
        yield from self.bot.delete_message(ctx.message)

        
    @commands.command(pass_context=True)
    @asyncio.coroutine    
    def lmao(self, ctx):
        """
        that's hilarious
        """
        yield from self.bot.send_message(ctx.message.channel, "http://i.imgur.com/o5Cc3i2.mp4")
        yield from self.bot.delete_message(ctx.message)    

       
    @commands.command()
    @asyncio.coroutine
    def chirp(self):
        """:^)"""
        yield from self.bot.say('CHIRP CHIRP')


    @commands.command(pass_context=True)
    @asyncio.coroutine
    def trivia(self, ctx, questions: int=10):
        """Starts a trivia game.
        Optional number of questions as argument; defaults to 10 questions."""
        if questions <= 2:
            # At least 3 questions
            yield from self.bot.say(":warning: Too little questions!")
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
            yield from self.bot.say("**Category: **%s\n**Question: **%s" % (category, question))

            def check(msg):
                if msg.content.lower() == answer.lower():
                    return True
                return False

            response = yield from self.bot.wait_for_message(timeout=4.0, check=check)
            if response != None:
                yield from self.bot.say("%s is correct!" % response.author.mention)
                continue

            clue = ''.join('?' if random.randint(0,3) and i!=' ' else i for i in answer)
            yield from self.bot.say("`Clue: %s`" % clue)

            response = yield from self.bot.wait_for_message(timeout=20.0, check=check)
            if response != None:
                yield from self.bot.say("%s is correct!" % response.author.mention)
            else:
                yield from self.bot.say("Time's up!\n**Answer: **%s" % answer)

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def mix(self, ctx, *, inputStr: str=None):
        if inputStr is None:
            yield from self.bot.say()
        words = inputStr.split()
        msg = "".join([(c.upper() if random.randint(0, 1) else c.lower()) for c in inputStr])
        yield from self.bot.say(msg)
        yield from self.bot.delete_message(ctx.message)

    
def setup(bot):
    bot.add_cog(Memes(bot))
