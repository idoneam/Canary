# Copyright (C) idoneam (2016-2022)
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

# discord-py requirements
from discord.ext import commands
import discord

# Other utilities
import aiohttp
import random
from .base_cog import CanaryCog
from .utils.auto_incorrect import auto_incorrect


class Memes(CanaryCog):
    @commands.command()
    async def bac(self, ctx: commands.Context, *, input_str: str | None = None):
        """
        Purposefully auto-incorrects inputted sentences
        Inputted text is either the content of the message to
        after the command or the content of the message to which
        the invoking message is replying to. If the invoking message
        is replying a message, the bot will reply to that message as
        well. Invoking message will be deleted.
        """
        replying: bool = ctx.message.reference and ctx.message.reference.resolved
        if input_str is None:
            if not replying:
                return
            input_str = ctx.message.reference.resolved.content
        msg = auto_incorrect(input_str)
        self.bot.mod_logger.info(
            f"?bac invoked: Author: '{ctx.message.author}', "
            f"Message: '{ctx.message.content}'"
            + (
                (
                    f", Used on {str(ctx.message.reference.resolved.author)}"
                    f"'s message: '{ctx.message.reference.resolved.content}'"
                )
                if replying
                else ""
            )
        )
        await ctx.send(msg, reference=ctx.message.reference, mention_author=False)
        await ctx.message.delete()

    @commands.command()
    async def lenny(self, ctx):
        """
        Lenny face
        """
        await ctx.send("( ͡° ͜ʖ ͡°) ")
        await ctx.message.delete()

    @commands.command()
    async def license(self, ctx):
        """
        License
        """
        await ctx.send(
            "This bot is free software: you can redistribute"
            " it and/or modify it under the terms of the GNU"
            " General Public License as published by the "
            "Free Software Foundation, either version 3 of "
            "the License, or (at your option) any later "
            "version. **This bot is distributed in the hope "
            "that it will be useful**, but WITHOUT ANY "
            "WARRANTY; without even the implied warranty of "
            "MERCHANTABILITY or **FITNESS FOR A PARTICULAR "
            "PURPOSE**.  See the GNU General Public License "
            "for more details. This bot is developed "
            "primarily by student volunteers with better "
            "things to do. A copy of the GNU General Public "
            "License is provided in the LICENSE.txt file "
            "along with this bot. The GNU General Public "
            "License can also be found at "
            "<http://www.gnu.org/licenses/>."
        )
        await ctx.message.delete()

    @commands.command()
    async def cheep(self, ctx):
        """:^)"""
        await ctx.send("CHEEP CHEEP")

    @commands.command()
    async def mix(self, ctx, *, input_str: str | None = None):
        """Alternates upper/lower case for input string.
        Inputted text is either the content of the message to
        after the command or the content of the message to which
        the invoking message is replying to. If the invoking message
        is replying a message, the bot will reply to that message as
        well. Invoking message will be deleted.
        """
        replying: bool = ctx.message.reference and ctx.message.reference.resolved
        if input_str is None:
            if not replying:
                return
            input_str = ctx.message.reference.resolved.content
        msg = "".join((c.upper() if random.randint(0, 1) else c.lower()) for c in input_str)
        self.bot.mod_logger.info(
            f"?mix invoked: Author: '{ctx.message.author}', "
            f"Message: '{ctx.message.content}'"
            + (
                (
                    f", Used on {str(ctx.message.reference.resolved.author)}"
                    f"'s message: '{ctx.message.reference.resolved.content}'"
                )
                if replying
                else ""
            )
        )
        await ctx.send(msg, reference=ctx.message.reference, mention_author=False)
        await ctx.message.delete()

    @commands.command(aliases=["boot"])
    async def pyramid(self, ctx, num: int = 2, emoji: str = "👢"):
        """
        Draws a pyramid of boots, default is 2 unless user specifies an integer
        number of levels of boots between -8 and 8. Also accepts any other
        emoji, word or multiword (in quotes) string.
        """

        def pyramidy(n, m):
            # Limit emoji/string to 8 characters or Discord/potate mald
            return f"{' ' * ((m - n) * 3)}{(emoji[:8] + ' ') * n}"

        # Limit num to a maximum of +/- 8 or herre malds
        abs_num = max(min(abs(num), 8), 1)
        rng = (1, abs_num + 1) if num > 0 else (abs_num, 0, -1)

        msg = "\n".join(pyramidy(ln, abs_num) for ln in range(*rng))
        await ctx.send(f"**\n{msg}**")

    @commands.command()
    async def xkcd(self, ctx, command: str | None = None):
        """
        Enjoy a nice xkcd comic with some strangers on the internet!
        If no issue number is passed, returns a random xkcd.
        Valid options are: nothing, 'latest' or a positive integer greater
        than one and at most equal to the latest issue number.
        """

        await ctx.trigger_typing()

        async with aiohttp.ClientSession() as session:
            if command is None:
                async with session.get("https://c.xkcd.com/comic/random") as r:
                    if r.status != 200:
                        await ctx.send(f"failure: random xkcd request returned `{r.status}`")
                        return
                    url = str(r.url)
            elif command == "latest":
                url = "https://xkcd.com/"
            else:
                try:
                    num = int(command)
                except ValueError:
                    await ctx.send(f"invalid input: `{command}` does not parse to an integer")
                    return
                if num < 1:
                    await ctx.send(f"invalid input: `{command}` does not parse to a positive integer")
                    return
                url = f"https://xkcd.com/{num}/"

            async with session.get(f"{url}info.0.json") as r:
                if r.status == 200:
                    data = await r.json()
                elif r.status == 404:
                    async with session.get("https://xkcd.com/info.0.json") as r:
                        if r.status != 200:
                            await ctx.send(f"failure: xkcd request returned `{r.status}`")
                            return
                        data = await r.json()
                else:
                    await ctx.send(f"failure: xkcd request returned `{r.status}`")
                    return

        await ctx.send(
            embed=discord.Embed(
                title=f"{data['title']} (#{data['num']}, {data['year']}-{data['month']:0>2}-{data['day']:0>2})", url=url
            )
            .set_image(url=data["img"])
            .set_footer(text=data["alt"])
        )


def setup(bot):
    bot.add_cog(Memes(bot))
