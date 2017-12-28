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
    def chosenOne(self, ctx, arg2 : str):
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

        yield from self.bot.send_file(ctx.message.channel, path)
        yield from self.bot.delete_message(ctx.message) 


    @commands.command(pass_context=True)
    @asyncio.coroutine
    def isMayo(self, ctx, arg1 : str):
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

        yield from self.bot.send_file(ctx.message.channel, path)
        yield from self.bot.delete_message(ctx.message) 
        

    @commands.command(pass_context=True)
    @asyncio.coroutine
    def notsure(self, ctx, arg1 : str, arg2 : str):
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

        yield from self.bot.send_file(ctx.message.channel, path)
        yield from self.bot.delete_message(ctx.message)


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
    def awyiss(self, ctx):
        """
        aw yiss mother fucking breadcrumbs
        """
        yield from self.bot.send_message(ctx.message.channel, "http://gph.is/294XA0F")
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
    def todo(self, ctx):
        """
        when its the weekend
        """
        yield from self.bot.send_message(ctx.message.channel, "http://gph.is/2dnMUJ6")
        yield from self.bot.delete_message(ctx.message)    

 
    @commands.command(pass_context=True)
    @asyncio.coroutine    
    def love(self, ctx):
        """
        back off yo
        """
        yield from self.bot.send_message(ctx.message.channel, "http://gph.is/2eePP6k")
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
    def overhead(self, ctx):
        """
        Not actually what this gif does...
        """
        yield from self.bot.send_message(ctx.message.channel, "http://i.imgur.com/xCS121c.gif")
        yield from self.bot.delete_message(ctx.message)   

 
    @commands.command(pass_context=True)
    @asyncio.coroutine    
    def sideglance(self, ctx):
        """
        when even bernie sanders hates you
        """
        yield from self.bot.send_message(ctx.message.channel, "http://i.imgur.com/xc6gMIo.gif")
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
    def ye(self, ctx):
        """
        Better Call Saul is awesome
        """
        yield from self.bot.send_message(ctx.message.channel, "http://i.imgur.com/iSMh7zO.gif")
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
