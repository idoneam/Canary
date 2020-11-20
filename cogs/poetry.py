from os import path
from pickle import load
from typing import List, Tuple
from random import choice
from discord.ext import commands
from .utils.poetry_toolz import PoetryGen, parse_poem_config


class Poems(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        rel_path = path.abspath(path.dirname(__file__))
        markov_file = open(path.join(rel_path, "utils/rev_markov"), "rb")
        rhyme_file = open(path.join(rel_path, "utils/rhyme_dict"), "rb")
        self.poem_machine = PoetryGen(load(markov_file), load(rhyme_file))
        markov_file.close()
        rhyme_file.close()

    @commands.command()
    async def poem(self, ctx, *, command: str = None):
        """
        """

        configs: List[List[Tuple[str,
                                 int]]] = [[("A", 5), ("B", 7), ("C", 5)],
                                           [("A", 10), ("A", 10), ("B", 7),
                                            ("B", 7), ("A", 10)],
                                           [("A", 12), ("A", 12), ("A", 12),
                                            ("A", 12)]]
        if command is None:
            await ctx.trigger_typing()
            await ctx.send("\n".join(self.poem_machine.mk_poem(
                choice(configs))))
            return
        allowed_configs: List[str] = ["haiku", "limerick", "alexandrine"]
        if command not in allowed_configs:
            await ctx.send(
                f"invalid option, valid options are: {allowed_configs}")
            return
        await ctx.trigger_typing()
        if command == "haiku":
            await ctx.send("\n".join(
                self.poem_machine.mk_poem(configs[0], True)))
        elif command == "limerick":
            await ctx.send("\n".join(
                self.poem_machine.mk_poem(configs[1], True)))
        elif command == "alexandrine":
            await ctx.send("\n".join(
                self.poem_machine.mk_poem(configs[2], True)))

    @commands.command(aliases=["poem_custom"])
    async def poemc(self, ctx, *, config_str: str = None):
        """
        """
        await ctx.trigger_typing()
        await ctx.send("\n".join(
            self.poem_machine.mk_poem(parse_poem_config(config_str, True))))

    @commands.command(aliases=["random_gen"])
    async def genr(self, ctx, *, text_len: int = None):
        """
        """
        if text_len is None:
            await ctx.send("length of text to generate must be specified")
        else:
            await ctx.trigger_typing()
            await ctx.send(" ".join(self.poem_machine.rev_gen(text_len)))


def setup(bot):
    bot.add_cog(Poems(bot))
