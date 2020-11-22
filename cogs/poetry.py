import os
import pickle
from typing import List, Tuple, Dict
import random
from discord.ext import commands
from .utils.poetry_toolz import PoetryGen, parse_poem_config


class Poems(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        rel_path = os.path.abspath(os.path.dirname(__file__))
        markov_file = open(os.path.join(rel_path, "utils/rev_markov.pickle"),
                           "rb")
        rhyme_file = open(os.path.join(rel_path, "utils/rhyme_dict.pickle"),
                          "rb")
        self.poem_machine = PoetryGen(pickle.load(markov_file),
                                      pickle.load(rhyme_file))
        markov_file.close()
        rhyme_file.close()

    @commands.command()
    async def poem(self, ctx, *, command: str = None):
        """
        Generate a poem from one of our prebuilt configurations using our (not) state of the poetry generator!
        Either call "?poem" for a random configration, or call "?poem x" where x is one of the valid prebuilts.
        Valid prebuilts are: haiku, limerick and alexandrine
        """
        conf_dict: Dict[str, List[List[Tuple[str, int]]]] = {
            "haiku": [("A", 5), ("B", 7), ("C", 5)],
            "limerick": [("A", 10), ("A", 10), ("B", 7), ("B", 7), ("A", 10)],
            "alexandrine": [("A", 12), ("A", 12), ("A", 12), ("A", 12)],
        }
        if command is None:
            await ctx.trigger_typing()
            await ctx.send("\n".join(
                self.poem_machine.mk_poem(
                    random.choice(list(conf_dict.values())))))
            return
        if command not in conf_dict:
            await ctx.send(
                f"invalid option, valid options are: {sorted(conf_dict.keys())}"
            )
            return
        await ctx.trigger_typing()
        await ctx.send("\n".join(self.poem_machine.mk_poem(conf_dict[command]))
                       )

    @commands.command(aliases=["poem_custom"])
    async def poemc(self, ctx, *, config_str: str = None):
        """
        Generate a poem from a custom configuration using our (not) state of the poetry generator!
        Configurations are ordered as so: each line config is split by a space, where each line config
        is first a letter (either capitalized or lowered), representing the rhyme of the line
        (differently cased letters are parsed as different rhymes), and the rest
        of the config is an integer, representing an amount of syllables for that line.
        Examples of valid poemc calls:
        > ?poemc A5 B7 A5 <- generates a haiku
        > ?poemc A10 A10 B7 B7 A10 <- generates a limerick
        > ?poemc o7 o7 o7 o7 o7 <- generates comradery
        """
        try:
            poem_conf: List[Tuple[str, int]] = parse_poem_config(config_str)
        except ValueError:
            await ctx.send("invalid config")
            return
        await ctx.trigger_typing()
        await ctx.send("\n".join(self.poem_machine.mk_poem(poem_conf)))

    @commands.command(aliases=["random_gen"])
    async def genr(self, ctx, *, text_len: int = None):
        """
        Generate a random text using our (not) state of the text generator (fun fact: it generates text in reverse)!
        Takes one command, which must specify the length of the text to be generated.
        """
        if text_len is None:
            await ctx.send("length of text to generate must be specified")
            return
        await ctx.trigger_typing()
        await ctx.send(" ".join(self.poem_machine.rev_gen(text_len)))


def setup(bot):
    bot.add_cog(Poems(bot))
