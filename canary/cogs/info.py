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

import subprocess
from discord.ext import commands
from .base_cog import CanaryCog


class Info(CanaryCog):
    @commands.command()
    async def version(self, ctx):
        # TODO: use asyncio.create_subprocess_shell
        version = subprocess.check_output(("git", "describe", "--tags"), universal_newlines=True).strip()
        commit, authored = (
            subprocess.check_output(("git", "log", "-1", "--pretty=format:%h %aI"), universal_newlines=True)
            .strip()
            .split(" ")
        )
        await ctx.send(f"Version: `{version}`\nCommit: `{commit}` " f"authored `{authored}`")


def setup(bot):
    bot.add_cog(Info(bot))
