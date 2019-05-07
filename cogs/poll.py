import discord
import string
from discord.ext.commands import Bot

ALPHABET = list(string.ascii_uppercase)
EMOJI_ALPHABET = [
    u"\U0001F1E6", u"\U0001F1E7", u"\U0001F1E8", u"\U0001F1E9", u"\U0001F1EA",
    u"\U0001F1EB", u"\U0001F1EC", u"\U0001F1ED", u"\U0001F1EE", u"\U0001F1EF",
    u"\U0001F1F0", u"\U0001F1F1", u"\U0001F1F2", u"\U0001F1F3", u"\U0001F1F4",
    u"\U0001F1F5", u"\U0001F1F6", u"\U0001F1F7", u"\U0001F1F8", u"\U0001F1F9"
]
client = Bot(command_prefix=BOT_PREFIX)


@client.command()
async def poll(ctx, question, *args):
    if len(args) > 20:
        await ctx.send("Please use 20 options or less")
        return
    username = ctx.message.author.name
    pfp = ctx.message.author.avatar_url
    embed = discord.Embed(
        colour=discord.Colour(0x972b67),
        description="```{}```**To vote, click on one or many emojis**".format(
            question))    #if single choice is implemented, correct this
    embed.set_author(
        name="{} created a poll with {} choices!".format(username, len(args)),
        icon_url=pfp)
    #eventually add this: embed.set_footer(text="5 users voted • Current winner: D (or top n if specificed) • Options: Non-anonymous, Multiple choice")

    pos = 0
    for arg in args:
        embed.add_field(name="Option {}".format(ALPHABET[pos]), value=arg)
        pos += 1

    bot_message = await ctx.send(embed=embed)

    pos = 0
    for arg in args:
        await bot_message.add_reaction(EMOJI_ALPHABET[pos])
        pos += 1
    return
    #need to also eventually add options for anonymous voting in DMs
    #restricting to only one choice only and
    #add a duration for polls.
