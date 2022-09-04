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

from discord.ext import commands

from ..bot import Canary
from .base_cog import CanaryCog
from .utils import image_helpers as ih


class Images(CanaryCog):
    def __init__(self, bot: Canary):
        super().__init__(bot)
        self.max_size: int = self.bot.config.images["max_image_size"]
        self.hist_lim: int = self.bot.config.images["image_history_limit"]
        self.max_rad: int = self.bot.config.images["max_radius"]
        self.max_itr: int = self.bot.config.images["max_iterations"]

    @commands.command()
    async def polar(self, ctx: commands.Context):
        """
        Transform Cartesian to polar coordinates.
        """
        await ih.filter_image(self.bot.loop, ih.polar, ctx, self.hist_lim, self.max_size)

    @commands.command()
    async def cart(self, ctx: commands.Context):
        """
        Transform from polar to Cartesian coordinates.
        """
        await ih.filter_image(self.bot.loop, ih.cart, ctx, self.hist_lim, self.max_size)

    @commands.command()
    async def blur(self, ctx: commands.Context, iterations: int = 1):
        """
        Blur the image
        """
        await ih.filter_image(self.bot.loop, ih.blur, ctx, self.hist_lim, self.max_size, iterations, self.max_itr)

    @commands.command(aliases=["left", "right"])
    async def hblur(self, ctx: commands.Context, radius: int = 10):
        """
        Blur the image horizontally
        """
        await ih.filter_image(self.bot.loop, ih.hblur, ctx, self.hist_lim, self.max_size, radius, self.max_rad)

    @commands.command(aliases=["up", "down"])
    async def vblur(self, ctx: commands.Context, radius: int = 10):
        """
        Blur the image vertically
        """
        await ih.filter_image(self.bot.loop, ih.vblur, ctx, self.hist_lim, self.max_size, radius, self.max_rad)

    @commands.command(aliases=["zoom", "radial"])
    async def rblur(self, ctx: commands.Context, radius: int = 10):
        """
        Radial blur
        """
        await ih.filter_image(self.bot.loop, ih.rblur, ctx, self.hist_lim, self.max_size, radius, self.max_rad)

    @commands.command(aliases=["circle", "circular", "spin"])
    async def cblur(self, ctx: commands.Context, radius: int = 10):
        """
        Circular blur
        """
        await ih.filter_image(self.bot.loop, ih.cblur, ctx, self.hist_lim, self.max_size, radius, self.max_rad)

    @commands.command(aliases=["df", "dfry", "fry"])
    async def deepfry(self, ctx: commands.Context, iterations: int = 1):
        """
        Deep fry an image, mhmm
        """
        await ih.filter_image(self.bot.loop, ih.deepfry, ctx, self.hist_lim, self.max_size, iterations, self.max_itr)

    @commands.command()
    async def noise(self, ctx: commands.Context, iterations: int = 1):
        """
        Add some noise to tha image!!
        """
        await ih.filter_image(self.bot.loop, ih.noise, ctx, self.hist_lim, self.max_size, iterations, self.max_itr)


def setup(bot):
    bot.add_cog(Images(bot))
