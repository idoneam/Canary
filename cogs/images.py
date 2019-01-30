#!/usr/bin/python3

# imports for Discord
import discord
from discord.ext import commands
import asyncio

# misc imports
import os, sys, random
import numpy as np
import cv2
import math
from functools import wraps
from io import BytesIO
import traceback


def filterImage(func):
    @wraps(func)
    async def wrapper(self, ctx, *args):
        att = await Images.getAttachment(ctx)
        if att is None:
            await ctx.send('Image not found :c', delete_after=15)
        else:
            buffer = BytesIO()
            await att.save(fp=buffer)
            original_name, ext = att.filename.rsplit('.', 1)
            fn = f'{original_name}-{func.__name__}.{ext}'
        try:
            await ctx.trigger_typing()
            img_bytes = np.asarray(bytearray(buffer.read()), dtype=np.uint8)
            result = cv2.imdecode(img_bytes, cv2.IMREAD_UNCHANGED)
            if len(args) == 2:
                args = (args[0], result)
            else:
                args = (result, )
            result = await func(self, ctx, *args)
            retval, buffer = cv2.imencode(f'.{ext}', result,
                                            [cv2.IMWRITE_JPEG_QUALITY, 100])
            await ctx.message.delete()

            buffer = BytesIO(buffer)
            await ctx.send(file=discord.File(fp=buffer, filename=fn))
        except Exception:
            # traceback.print_exc()
            await ctx.send('Error occurred.', delete_after=60)
            
    return wrapper


class Images():
    def __init__(self, bot):
        self.bot = bot

    async def on_ready(self):
        if not os.path.exists('./tmp/'):
            os.mkdir('./tmp/', mode=0o755)

    @staticmethod
    async def getAttachment(ctx: discord.ext.commands.Context):
        messages = await ctx.channel.history(limit=100).flatten()
        for msg in messages:
            if msg.attachments:
                return msg.attachments[0]
        return None

    def _polar(self, image):
        height, width = image.shape[:2]
        centerX = width / 2
        centerY = height / 2
        radius = math.sqrt(width**2 + height**2) / 2

        result = cv2.linearPolar(image, (centerX, centerY), radius,
                                 cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS)
        return result

    def _cart(self, image):
        height, width = image.shape[:2]
        centerX = width / 2
        centerY = height / 2
        radius = math.sqrt(width**2 + height**2) / 2

        result = cv2.linearPolar(
            image, (centerX, centerY), radius,
            cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS + cv2.WARP_INVERSE_MAP)
        return result

    @commands.command()
    @filterImage
    async def polar(self, ctx, image=None):
        '''
        Transform Cartesian to polar coordinates
        '''
        image = self._polar(image)
        return np.rot90(image, -1)

    @commands.command()
    @filterImage
    async def cart(self, ctx, image=None):
        '''
        Transform from polar to Cartesian coordinates
        '''
        image = self._cart(np.rot90(image))
        return image

    @commands.command()
    @filterImage
    async def blur(self, ctx, iterations='1', image=None):
        '''
        Blur the image
        '''
        iterations = max(0, min(int(iterations), 100))
        for i in range(iterations):
            image = cv2.GaussianBlur(image, (5, 5), 0)
        return image

    @commands.command(aliases=['left', 'right'])
    @filterImage
    async def hblur(self, ctx, radius='10', image=None):
        '''
        Blur the image horizontally
        '''
        radius = max(1, min(int(radius), 500))
        image = cv2.blur(image, (radius, 1))
        return image

    @commands.command(aliases=['up', 'down'])
    @filterImage
    async def vblur(self, ctx, radius='10', image=None):
        '''
        Blur the image vertically
        '''
        radius = max(1, min(int(radius), 500))
        image = cv2.blur(image, (1, radius))
        return image

    @commands.command(aliases=['zoom', 'radial'])
    @filterImage
    async def rblur(self, ctx, radius='10', image=None):
        '''
        Radial blur
        '''
        radius = max(1, min(int(radius), 500))
        image = self._polar(image)
        image = cv2.blur(image, (radius, 1))
        image = self._cart(image)
        return image

    @commands.command(aliases=['circle', 'circular', 'spin'])
    @filterImage
    async def cblur(self, ctx, radius='10', image=None):
        '''
        Circular blur
        '''
        radius = max(1, min(int(radius), 500))
        halfRadius = radius // 2
        # determine values for padding
        height, width = image.shape[:2]
        r = math.sqrt(width**2 + height**2) // 2
        verticalPad = int(r - height / 2)
        horizontalPad = int(r - width / 2)
        # pad border to avoid black regions when transforming image back to normal
        image = cv2.copyMakeBorder(image, verticalPad, verticalPad,
                                   horizontalPad, horizontalPad,
                                   cv2.BORDER_REPLICATE)
        image = self._polar(image)
        # wrap border to avoid the sharp horizontal line when transforming image back to normal
        image = cv2.copyMakeBorder(image, halfRadius, halfRadius, halfRadius,
                                   halfRadius, cv2.BORDER_WRAP)
        image = cv2.blur(image, (1, radius))
        image = image[halfRadius:-halfRadius, halfRadius:-halfRadius]
        image = self._cart(image)
        image = image[verticalPad:-verticalPad, horizontalPad:-horizontalPad]
        return image

    @commands.command(aliases=['df', 'dfry', 'fry'])
    @filterImage
    async def deepfry(self, ctx, iterations='1', image=None):
        '''
        Deep fry an image, mhmm
        '''
        iterations = max(0, min(int(iterations), 20))
        kernel = np.array([[0,0,0], [0,1,0], [0,0,0]]) \
                + np.array([[0,-1,0], [-1,4,-1], [0,-1,0]]) * 0.3
        for i in range(iterations):
            std = int(np.std(image))
            # Contrast
            image = cv2.addWeighted(image, 0.9, image, 0, std * 0.3)
            # Sharpness
            image = cv2.filter2D(image, 0, kernel)
            # Saturation
            image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            image[:, :, 1:] = cv2.add(image[:, :, 1:], image[:, :, 1:])
            image = cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
        return image

    @commands.command()
    @filterImage
    async def noise(self, ctx, iterations='1', image=None):
        '''
        Add some noise to tha image!!
        '''
        iterations = max(0, min(int(iterations), 20))

        for i in range(iterations):
            noise = np.std(image) * np.random.random(image.shape)
            image = cv2.add(image, noise.astype('uint8'))
            image = cv2.addWeighted(image, 1, image, 0, -np.std(image) * 0.49)
        return image


def setup(bot):
    bot.add_cog(Images(bot))
