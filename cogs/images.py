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
        self.max_size = self.bot.config.images["max_image_size"]
        self.hist_lim = self.bot.config.images["image_history_limit"]
        self.max_rad = self.bot.config.images["max_radius"]
        self.max_itr = self.bot.config.images["max_iterations"]

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
                                         ctx, self.hist_lim, self.max_size)

    @commands.command()
    async def cart(self, ctx):
        """
        Transform from polar to Cartesian coordinates.
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.cart,
                                         ctx, self.hist_lim, self.max_size)

    @commands.command()
    async def blur(self, ctx, iterations: int = 1):
        """
        Blur the image
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.blur,
                                         ctx, self.hist_lim, self.max_size, iterations, self.max_itr)

    @commands.command(aliases=['left', 'right'])
    async def hblur(self, ctx, radius: int = 10):
        """
        Blur the image horizontally
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.hblur,
                                         ctx, self.hist_lim, self.max_size, radius, self.max_rad)

    @commands.command(aliases=['up', 'down'])
    async def vblur(self, ctx, radius: int = 10):
        """
        Blur the image vertically
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.vblur,
                                         ctx, self.hist_lim, self.max_size, radius, self.max_rad)

    @commands.command(aliases=['zoom', 'radial'])
    async def rblur(self, ctx, radius: int = 10):
        """
        Radial blur
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.rblur,
                                         ctx, self.hist_lim, self.max_size, radius, self.max_rad)

    @commands.command(aliases=['circle', 'circular', 'spin'])
    async def cblur(self, ctx, radius: int = 10):
        """
        Circular blur
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.cblur,
                                         ctx, self.hist_lim, self.max_size, radius, self.max_rad)

    @commands.command(aliases=['df', 'dfry', 'fry'])
    async def deepfry(self, ctx, iterations: int = 1):
        """
        Deep fry an image, mhmm
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.deepfry,
                                         ctx, self.hist_lim, self.max_size, iterations, self.max_itr)

    @commands.command()
    async def noise(self, ctx, iterations: int = 1):
        """
        Add some noise to tha image!!
        """
        await image_helpers.fitler_image(self.bot.loop, image_helpers.noise,
                                         ctx, self.hist_lim, self.max_size, iterations, self.max_itr)


def setup(bot):
    bot.add_cog(Images(bot))
