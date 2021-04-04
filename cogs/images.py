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
from discord.ext import commands

# misc imports
import os
from .utils import image_helpers


class Images(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not os.path.exists("./tmp/"):
            os.mkdir("./tmp/", mode=0o755)

    @commands.command()
    async def polar(self, ctx):
        """
        Transform Cartesian to polar coordinates.
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.polar,
                                         ctx)

    @commands.command()
    async def cart(self, ctx):
        """
        Transform from polar to Cartesian coordinates.
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.cart,
                                         ctx)

    @commands.command()
    async def blur(self, ctx, radius: int = 10):
        """
        Blur the image
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.blur,
                                         ctx, radius)

    @commands.command(aliases=['left', 'right'])
    async def hblur(self, ctx, radius: int = 10):
        """
        Blur the image horizontally
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.hblur,
                                         ctx, radius)

    @commands.command(aliases=['up', 'down'])
    async def vblur(self, ctx, radius: int = 10):
        """
        Blur the image vertically
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.vblur,
                                         ctx, radius)

    @commands.command(aliases=['zoom', 'radial'])
    async def rblur(self, ctx, radius: int = 10):
        """
        Radial blur
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.rblur,
                                         ctx, radius)

    @commands.command(aliases=['circle', 'circular', 'spin'])
    async def cblur(self, ctx, radius: int = 10):
        """
        Circular blur
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.cblur,
                                         ctx, radius)

    @commands.command(aliases=['df', 'dfry', 'fry'])
    async def deepfry(self, ctx, iterations: int = 1):
        """
        Deep fry an image, mhmm
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.deepfry,
                                         ctx, iterations)

    @commands.command()
    async def noise(self, ctx, iterations: int = 1):
        """
        Add some noise to tha image!!
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.noise,
                                         ctx, iterations)


def setup(bot):
    bot.add_cog(Images(bot))
