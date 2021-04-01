# Copyright (C) idoneam (2016-2021)
#
# This file is part of Canary
#
# Canary is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Canary is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Canary. If not, see <https://www.gnu.org/licenses/>.

# imports for Discord
import discord
from discord.ext import commands

# misc imports
import concurrent.futures
import os
import numpy as np
import cv2
import math
from functools import wraps, partial
from io import BytesIO

MAX_IMAGE_SIZE = 8 * (10**6)


def filter_image(func):
    @wraps(func)
    async def wrapper(self, ctx, *args):
        att = await Images.get_attachment(ctx)
        if att is None:
            await ctx.send("no image could be found (only attached image files"
                           " can be detected) or message could not be found")
            return

        await ctx.trigger_typing()
        buffer = BytesIO()
        await att.save(fp=buffer)

        original_name, ext = att.filename.rsplit('.', 1)
        ext = ext.lower()
        if ext in ("jpeg", "jpg"):
            is_png = False
        elif ext in ("png"):
            is_png = True
        else:
            await ctx.send("image format not supported.")
            return

        fn = f"{original_name}-{func.__name__}.{ext}"
        ratio = (MAX_IMAGE_SIZE /
                 att.size) * 100 if att.size > MAX_IMAGE_SIZE else 100

        try:

            with concurrent.futures.ProcessPoolExecutor() as pool:
                img_bytes = await self.bot.loop.run_in_executor(
                    pool,
                    partial(np.asarray, bytearray(buffer.read()), np.uint8))
                result = await self.bot.loop.run_in_executor(
                    pool, partial(cv2.imdecode, img_bytes,
                                  cv2.IMREAD_UNCHANGED))

                if att.size > MAX_IMAGE_SIZE:
                    _, buffer = await self.bot.loop.run_in_executor(
                        pool,
                        partial(cv2.imencode, f".{ext}", result,
                                (cv2.IMWRITE_JPEG_QUALITY if is_png else
                                 cv2.IMWRITE_JPEG_QUALITY, ratio)))
                    result = await self.bot.loop.run_in_executor(
                        pool,
                        partial(cv2.imdecode, buffer, cv2.IMREAD_UNCHANGED))

                args = (*args[:-1], result)
                result = await func(self, ctx, *args)
                _, buffer = await self.bot.loop.run_in_executor(
                    pool,
                    partial(cv2.imencode, f".{ext}", result,
                            (cv2.IMWRITE_JPEG_QUALITY
                             if is_png else cv2.IMWRITE_JPEG_QUALITY, 100)))

        except Exception as exc:    # TODO: Narrow the exception
            await ctx.send('an error has occurred.')
            raise exc

        else:
            await ctx.message.delete()
            await ctx.send(file=discord.File(fp=BytesIO(buffer), filename=fn))

    return wrapper


class Images(commands.Cog):
    IMAGE_HISTORY_LIMIT = 50

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not os.path.exists("./tmp/"):
            os.mkdir("./tmp/", mode=0o755)

    @staticmethod
    async def get_attachment(ctx: discord.ext.commands.Context):
        """
        Returns either the attachment of the message to which
        the invoking message is replying to, or, if that fails
        the attachment of the most recent of the last 100 messages.
        If no such message exists, returns None.
        """
        if (ctx.message.reference and ctx.message.reference.resolved
                and ctx.message.reference.resolved.attachments):
            return ctx.message.reference.resolved.attachments[0]
        async for msg in ctx.channel.history(limit=Images.IMAGE_HISTORY_LIMIT):
            if msg.attachments:
                return msg.attachments[0]
        return None

    @staticmethod
    def _cv_linear_polar(image, flags):
        h, w = image.shape[:2]
        r = math.sqrt(w**2 + h**2) / 2
        return cv2.linearPolar(image, (w / 2, h / 2), r, flags)

    @staticmethod
    def _polar(image):
        return Images._cv_linear_polar(
            image, cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS)

    @staticmethod
    def _cart(image):
        return Images._cv_linear_polar(
            image,
            cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS + cv2.WARP_INVERSE_MAP)

    @staticmethod
    def _bounded_radius(radius: str):
        return max(1, min(int(radius), 500))

    @commands.command()
    @filter_image
    async def polar(self, _ctx, image=None):
        """
        Transform Cartesian to polar coordinates.
        """
        return np.rot90(self._polar(image), -1)

    @commands.command()
    @filter_image
    async def cart(self, _ctx, image=None):
        """
        Transform from polar to Cartesian coordinates.
        """
        return Images._cart(np.rot90(image))

    @commands.command()
    @filter_image
    async def blur(self, _ctx, iterations='1', image=None):
        """
        Blur the image
        """
        iterations = max(0, min(int(iterations), 100))
        for i in range(iterations):
            image = cv2.GaussianBlur(image, (5, 5), 0)
        return image

    @commands.command(aliases=['left', 'right'])
    @filter_image
    async def hblur(self, _ctx, radius='10', image=None):
        """
        Blur the image horizontally
        """
        radius = self._bounded_radius(radius)
        image = cv2.blur(image, (radius, 1))
        return image

    @commands.command(aliases=['up', 'down'])
    @filter_image
    async def vblur(self, _ctx, radius='10', image=None):
        """
        Blur the image vertically
        """
        radius = self._bounded_radius(radius)
        image = cv2.blur(image, (1, radius))
        return image

    @commands.command(aliases=['zoom', 'radial'])
    @filter_image
    async def rblur(self, _ctx, radius='10', image=None):
        """
        Radial blur
        """
        radius = Images._bounded_radius(radius)
        image = Images._polar(image)
        image = cv2.blur(image, (radius, 1))
        image = Images._cart(image)
        return image

    @commands.command(aliases=['circle', 'circular', 'spin'])
    @filter_image
    async def cblur(self, _ctx, radius='10', image=None):
        """
        Circular blur
        """

        radius = self._bounded_radius(radius)
        half_radius = radius // 2

        # determine values for padding
        height, width = image.shape[:2]
        r = math.sqrt(width**2 + height**2) // 2
        v_pad = int(r - height / 2)
        h_pad = int(r - width / 2)

        # pad border to avoid black regions when transforming image back to
        # normal
        image = cv2.copyMakeBorder(image, v_pad, v_pad, h_pad, h_pad,
                                   cv2.BORDER_REPLICATE)
        image = Images._polar(image)

        # wrap border to avoid the sharp horizontal line when transforming
        # image back to normal
        image = cv2.copyMakeBorder(image, half_radius, half_radius,
                                   half_radius, half_radius, cv2.BORDER_WRAP)
        image = cv2.blur(image, (1, radius))
        image = image[half_radius:-half_radius, half_radius:-half_radius]
        image = Images._cart(image)
        image = image[v_pad:-v_pad, h_pad:-h_pad]

        return image

    @commands.command(aliases=['df', 'dfry', 'fry'])
    @filter_image
    async def deepfry(self, _ctx, iterations='1', image=None):
        """
        Deep fry an image, mhmm
        """

        iterations = max(0, min(int(iterations), 20))
        kernel = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]]) \
            + np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]]) * 0.3

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
    @filter_image
    async def noise(self, _ctx, iterations='1', image=None):
        """
        Add some noise to tha image!!
        """

        iterations = max(0, min(int(iterations), 20))

        for i in range(iterations):
            noise = np.std(image) * np.random.random(image.shape)
            image = cv2.add(image, noise.astype('uint8'))
            image = cv2.addWeighted(image, 1, image, 0, -np.std(image) * 0.49)

        return image


def setup(bot):
    bot.add_cog(Images(bot))
