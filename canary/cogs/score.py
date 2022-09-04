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

# Rewritten by @le-potate

# discord.py requirements
import discord
from discord.ext import commands

# For type hinting
from ..bot import Canary

# For DB functionality
import aiosqlite
import json
from .base_cog import CanaryCog
from .utils.members import add_member_if_needed

# For argument parsing
from discord.ext.commands import MemberConverter, PartialEmojiConverter
from .utils.arg_converter import ArgConverter

# For pagination
from .utils.paginator import Pages

f = open("data/premade/emoji.json", encoding="utf8")
EMOJI = json.load(f)


class TotalEmojiConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await PartialEmojiConverter().convert(ctx, argument)
        except commands.BadArgument:
            if not any(argument in d.values() for d in EMOJI.values()):
                raise commands.BadArgument(
                    "Not in the current list of Discord Unicode Emojis and no Custom Emoji found"
                )
            return argument


class FromConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if "from" not in argument.lower():
            raise commands.BadArgument("No `from` flag")
        if len(argument) < 6:
            raise commands.BadArgument("No argument specified for `from` flag")
        arg = argument[5:]
        if arg.lower() == "all":
            return "all"
        else:
            try:
                return await MemberConverter().convert(ctx, arg)
            except commands.BadArgument:
                raise commands.BadArgument("Member specified for `from` flag could not be found")


class ToConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if "to" not in argument.lower():
            raise commands.BadArgument("No `to` flag")
        if len(argument) < 4:
            raise commands.BadArgument("No argument specified for `to` flag")
        arg = argument[3:]
        if arg.lower() == "all":
            return "all"
        else:
            try:
                return await MemberConverter().convert(ctx, arg)
            except commands.BadArgument:
                raise commands.BadArgument("Member specified for `to` flag could not be found")


class EmojiTypeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if "emojitype" not in argument.lower():
            raise commands.BadArgument("No `emojitype` flag")
        if len(argument) < 11:
            raise commands.BadArgument("No argument specified for `emojitype` flag")
        result = argument[10:].lower()
        if result not in ("all", "unicode", "custom", "here", "nothere", "score"):
            raise commands.BadArgument("Unknown emoji type specified for `emojitype` flag")
        return result


class EmojiNameConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if len(argument) > 2 and argument[0] == ":" and argument[-1] == ":":
            return argument
        if "emojiname" not in argument.lower():
            raise commands.BadArgument("No `emojiname` flag")
        if len(argument) < 11:
            raise commands.BadArgument("No argument specified for `emojiname` flag")
        return f":{argument[10:]}:"


class SelfConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if "self" not in argument.lower():
            raise commands.BadArgument("No `self` flag")
        if len(argument) < 6:
            raise commands.BadArgument("No argument specified for `self` flag")
        arg = argument[5:].lower()
        if arg == "true" or arg == "1":
            return True
        if arg == "false" or arg == "0":
            return False
        raise commands.BadArgument("`self` flag should take a boolean as input")


class BeforeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if "before" not in argument.lower():
            raise commands.BadArgument("No `before` flag")
        if len(argument) < 8:
            raise commands.BadArgument("No argument specified for `before` flag")
        try:
            return int(argument[7:])
        except ValueError:
            raise commands.BadArgument("`before` flag should take an integer as input")


class AfterConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if "after" not in argument.lower():
            raise commands.BadArgument("No `after` flag")
        if len(argument) < 7:
            raise commands.BadArgument("No argument specified for `after` flag")
        try:
            return int(argument[6:])
        except ValueError:
            raise commands.BadArgument("`after` flag should take an integer as input")


class Score(CanaryCog):
    def __init__(self, bot: Canary):
        super().__init__(bot)

        self.UPMARTLET: discord.Emoji | None = None
        self.DOWNMARTLET: discord.Emoji | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        await super().on_ready()

        self.UPMARTLET = discord.utils.get(self.guild.emojis, name=self.bot.config.upvote_emoji)
        self.DOWNMARTLET = discord.utils.get(self.guild.emojis, name=self.bot.config.downvote_emoji)

    @staticmethod
    async def _get_converted_args_dict(ctx, args, from_xnor_to=False, from_nand_to=False, member=True, emoji=True):
        # this will make an arg_converter with the possible values the
        # score, ranking, and emoji_ranking function can take, then do
        # additional checks to restrict it further
        # If from_xnor_to, then if there is a `from` flag there must be a
        # `to` flag and vice versa (used by score and emoji_ranking)
        # If from_nand_to, there can either be a `from` or a `to` flag
        # or nothing, not both (used by ranking)
        # If member, then a member can be input (will still look for
        # from/to flags but will raise an exception if both a member and
        # a from/to flag is found). If no member or from/to flag
        # is found, will set it to ctx.message.author
        # If emoji, then an emoji can be input (will still look for
        # emojitype flag but will raise an exception if both an emoji and
        # an emojitype flag is found). If no emoji or emojitype flag
        # is found, will set it to emojitype="score"

        converters_dict = {
            "from_member": (FromConverter(), None),
            "to_member": (ToConverter(), None),
            "emojitype": (EmojiTypeConverter(), None),
            "self": (SelfConverter(), False),
            "before": (BeforeConverter(), None),
            "after": (AfterConverter(), None),
        }
        if emoji:
            converters_dict["emoji"] = (TotalEmojiConverter(), None)
            converters_dict["emojiname"] = (EmojiNameConverter(), None)
        # it's important that member is the last key as it is less restrictive
        # than the others. For example, if a user named themselves
        # "from:all", if member was placed first it would break all commands
        # using from:all since they would see this as a member input. Since
        # ArgConverter goes through the dict by order, this ensures that
        # it was checked that it is not another flag before
        if member:
            converters_dict["member"] = (MemberConverter(), None)

        arg_converter = ArgConverter(converters_dict)
        try:
            args_dict = await arg_converter.convert(ctx, args)
        except commands.BadArgument as err:
            raise commands.BadArgument(str(err))

        # additional checks
        if member:
            if args_dict["member"] and (args_dict["from_member"] or args_dict["to_member"]):
                raise commands.BadArgument(
                    "Invalid input: A user cannot be specified without flag "
                    "if there is also a user specified for the `from` or "
                    "`to` flag"
                )
            # default value
            if not args_dict["from_member"] and not args_dict["to_member"] and not args_dict["member"]:
                args_dict["member"] = ctx.message.author

        if emoji:
            if sum(map(bool, (args_dict["emoji"], args_dict["emojitype"], args_dict["emojiname"]))) > 1:
                raise commands.BadArgument(
                    "Invalid input: Only one of either an emoji, "
                    "the emojitype flag or the emojiname flag can be used"
                )
            # default value
            if not any((args_dict["emoji"], args_dict["emojitype"], args_dict["emojiname"])):
                args_dict["emojitype"] = "score"

        if from_xnor_to and not (
            (args_dict["from_member"] and args_dict["to_member"])
            or (not args_dict["from_member"] and not args_dict["to_member"])
        ):
            raise commands.BadArgument(
                "Invalid input: For this function, if a `from` flag is "
                "input, a `to` flag must also be input and vice versa"
            )

        if from_nand_to and args_dict["from_member"] and args_dict["to_member"]:
            raise commands.BadArgument(
                "Invalid input: For this function, only one of either a" "`from` flag or a `to` flag can be input"
            )

        return args_dict

    def _where_str_and_values_from_args_dict(self, args_dict, prefix=None):
        where_list = []
        values_list = []
        guild_emojis = [str(emoji) for emoji in self.guild.emojis]
        if "member" in args_dict and args_dict["member"]:
            where_list.append("ReacteeID = ?")
            values_list.append(args_dict["member"].id)
        if args_dict["from_member"] and args_dict["from_member"] != "all":
            where_list.append("ReacterID = ?")
            values_list.append(args_dict["from_member"].id)
        # if args_dict["from_member"] == "all", there are no restrictions
        if args_dict["to_member"] and args_dict["to_member"] != "all":
            where_list.append("ReacteeID = ?")
            values_list.append(args_dict["to_member"].id)
        # if args_dict["to_member"] == "all", there are no restrictions
        if "emoji" in args_dict:
            if args_dict["emoji"]:
                where_list.append("ReactionName = ?")
                values_list.append(str(args_dict["emoji"]))
            elif args_dict["emojiname"]:
                where_list.append("instr(ReactionName, ?) > 0")
                values_list.append(str(args_dict["emojiname"]))
        if args_dict["emojitype"] == "unicode":
            where_list.append("instr(ReactionName, '<') = 0")
        elif args_dict["emojitype"] == "custom":
            where_list.append("instr(ReactionName, '<') = 1")
        elif args_dict["emojitype"] == "here":
            where_list.append(f"ReactionName IN ({','.join(['?']*len(guild_emojis))})")
            values_list = values_list + guild_emojis
        elif args_dict["emojitype"] == "nothere":
            # must be a custom react
            where_list.append("instr(ReactionName, '<') = 1")
            where_list.append(f"ReactionName NOT IN ({','.join(['?']*len(guild_emojis))})")
            values_list = values_list + guild_emojis
        # elif args_dict["emojitype"] == "all", there are no restrictions
        # elif args_dict["emojitype"] == "score", this must be dealt with
        # outside this function as this does not use a where close
        if not args_dict["self"]:
            where_list.append("ReacterID != ReacteeID")
        if args_dict["before"]:
            where_list.append(f"MessageID < {int(args_dict['before'])}")
        if args_dict["after"]:
            where_list.append(f"MessageID > {int(args_dict['after'])}")
        # normally it is certain that args_dict['before'] and
        # args_dict['after'] are int, but we still cast to int in case the
        # args_dict that is passed didn't respect thisto take no risk
        # of injection

        # If there is nothing in the where_list, we must make sure that
        # we still give a condition since this returns a string to place after
        # starting a WHERE clause
        if not where_list:
            where_list = ["1 = 1"]

        if prefix:
            where_list = [f"{prefix}.{item}" for item in where_list]
        where_str = " AND ".join(where_list)
        return where_str, tuple(values_list)

    async def _add_or_remove_reaction_from_db(self, payload, remove=False):
        channel = self.bot.get_channel(payload.channel_id)
        message_id = payload.message_id

        try:
            message = await channel.fetch_message(message_id)
        except discord.errors.NotFound:
            return

        db: aiosqlite.Connection
        async with self.db() as db:
            reacter_id = self.bot.get_user(payload.user_id).id
            await add_member_if_needed(self, db, reacter_id)
            reactee_id = message.author.id
            await add_member_if_needed(self, db, reactee_id)

            emoji = payload.emoji

            if remove:
                await db.execute(
                    "DELETE FROM Reactions WHERE ReacterID = ? AND ReacteeID = ? AND ReactionName = ? "
                    "AND MessageID = ?",
                    (reacter_id, reactee_id, str(emoji), message_id),
                )
            else:
                await db.execute(
                    "INSERT OR IGNORE INTO Reactions VALUES (?,?,?,?)", (reacter_id, reactee_id, str(emoji), message_id)
                )

            await db.commit()

    @CanaryCog.listener()
    async def on_raw_reaction_add(self, payload):
        if self.guild is None:
            return

        if payload.guild_id == self.guild.id:
            await self._add_or_remove_reaction_from_db(payload)

    @CanaryCog.listener()
    async def on_raw_reaction_remove(self, payload):
        if self.guild is None:
            return

        if payload.guild_id == self.guild.id:
            await self._add_or_remove_reaction_from_db(payload, remove=True)

    @commands.command()
    async def score(self, ctx: commands.Context, *args):
        """Display emoji score

        Basic examples:
        -`?score`: Your total score (upmartlets - downmartlets)
        -`?score @user`: @user's total score
        -`?score emoji`: Your score for an emoji
        -`?score @user emoji`: @user's score for an emoji

        Arguments (Without the quotes and order doesn't matter):
        - Optional: `@user` OR (`from:@userA` AND `to:@userB`)
            -If @user or User, gives the score for this user.
            -If from and to flags, gives the score given from @userA to @userB. `from:all` and `to:all` can be used.
            -If nothing, gives your score
            Note that it is possible to give usernames without mention. This is case-sensitive. If a username contains a
            space, the username and flag must be included in quotes, e.g. "to:user name"

        - Optional: `emoji` OR `emojitype:type` OR `emojiname:name` OR `:name:`
            -If emoji, gives the score for this emoji
            -If emojitype flag, gives the score for this emojitype (see below for types)
            -If emojiname flag or :name:, gives the score for all custom emojis of this name
            -If nothing, gives the total upmartlet - downmartlet score

        - Optional: `self:bool` (true or false)
            -If true, self-upvotes are counted
            -This is set to self:false by default

        - Optional: `before:message_id` AND/OR `after:message_id`
            -If given, will only count reacts given on messages sent before/after the message_id

        -Available emojitypes for this function:
            -"all" (All emoji),
            -"unicode" (All unicode emoji),
            -"custom" (All custom emoji either in the server or not in the server),
            -"here" (All custom emojis in the server),
            -"nothere" (All custom emoji not in the server),
            -"score" (The emojis used as upvotes and downvotes)
        """
        try:
            args_dict = await self._get_converted_args_dict(ctx, args, from_xnor_to=True)
        except commands.BadArgument as err:
            await ctx.send(str(err))
            return

        # get the WHERE conditions and the values
        where_str, t = self._where_str_and_values_from_args_dict(args_dict)

        db: aiosqlite.Connection
        async with self.db() as db:
            c: aiosqlite.Cursor

            if args_dict["emojitype"] != "score":
                async with db.execute(f"SELECT count(ReacteeID) FROM Reactions WHERE {where_str}", t) as c:
                    react_count = (await c.fetchone())[0]
            else:
                async with db.execute(
                    (
                        f"SELECT COUNT(IIF (ReactionName = ?1, 1, NULL)) - "
                        f"COUNT(IIF (ReactionName = ?2, 1, NULL)) "
                        f"FROM Reactions "
                        f"WHERE {where_str} "
                        f"AND (ReactionName = ?1 OR ReactionName=?2) "
                    ),
                    (str(self.UPMARTLET), str(self.DOWNMARTLET), *t),
                ) as c:
                    react_count = (await c.fetchone())[0]

        await ctx.send(react_count)

    @commands.command()
    async def ranking(self, ctx, *args):
        """Ranking of total or emoji score

        Basic examples:
        `?ranking`: Ranking of the total score (upmartlets - downmartlets) of each user
        `?ranking emoji`: Ranking of the score of each user for an emoji

        Arguments (Without the quotes and order doesn't matter):
        - Optional: `from:@user` AND `to:@user` (not both)
            -If from flag: gives the score received by every user from this user. `from:all` can be used.
            -If to flag: gives the score received by this user from every user. `to:all` can be used.
            -If nothing, gives the score of every user
            Note that it is possible to give usernames without mention. This is case-sensitive. If a username contains a
            space, the username and flag must be included in quotes, e.g. "to:user name"

        - Optional: `emoji` OR `emojitype:type` OR `emojiname:name` OR `:name:`
            -If emoji, gives the score for this emoji
            -If emojitype flag, gives the score for this emojitype (see below for types)
            -If emojiname flag or :name:, gives the score for all custom emojis of this name
            -If nothing, gives the total upmartlet - downmartlet score

        - Optional: `self:bool` (true or false)
            -If true, self-upvotes are counted
            -This is set to self:false by default

        - Optional: `before:message_id` AND/OR `after:message_id`
            -If given, will only count reacts given on messages sent before/after the message_id

        -Available emojitypes for this function:
            -"all" (All emoji),
            -"unicode" (All unicode emoji),
            -"custom" (All custom emoji either in the server or not in the server),
            -"here" (All custom emojis in the server),
            -"nothere" (All custom emoji not in the server),
            -"score" (The emojis used as upvotes and downvotes)
        """

        try:
            args_dict = await self._get_converted_args_dict(ctx, args, from_nand_to=True, member=False)
        except commands.BadArgument as err:
            await ctx.send(err)
            return

        select_id = "ReacterID" if args_dict["to_member"] else "ReacteeID"

        if args_dict["emojitype"] != "score":
            # get the WHERE conditions and the values
            where_str, t = self._where_str_and_values_from_args_dict(args_dict)
            q = (
                f"SELECT printf('%d. %s', ROW_NUMBER() OVER (ORDER BY count(*) DESC), M.Name), "
                f"printf('%d %s', count(*), "
                f"IIF (count(*)!=1, 'times', 'time')) "
                f"FROM Reactions AS R, Members as M "
                f"WHERE {where_str} "
                f"AND R.{select_id} = M.ID "
                f"GROUP BY R.{select_id} "
                f"ORDER BY count(*) DESC"
            )
            not_found_err = "This reaction was never used on this server."
        else:
            # get the WHERE conditions and the values
            where_str, tp = self._where_str_and_values_from_args_dict(args_dict, prefix="R")
            t = (str(self.UPMARTLET), str(self.DOWNMARTLET), *tp)
            q = (
                f"SELECT printf('%d. %s', "
                f"ROW_NUMBER() OVER (ORDER BY TotalCount DESC), Name), "
                f"TotalCount FROM "
                f"(SELECT M.Name, "
                f"COUNT(IIF (ReactionName = ?1, 1, NULL)) - "
                f"COUNT(IIF (ReactionName = ?2, 1, NULL)) "
                f"AS TotalCount "
                f"FROM Reactions AS R, Members as M "
                f"WHERE {where_str} "
                f"AND (ReactionName = ?1 OR ReactionName=?2) "
                f"AND R.{select_id} = M.ID "
                f"GROUP BY R.{select_id})"
            )
            not_found_err = "No results found"

        counts = list(zip(*(await self.fetch_list(q, t))))
        if not counts:
            await ctx.send(embed=discord.Embed(title=not_found_err))
            return

        names, values = counts

        paginator_dict = {"names": names, "values": values}
        p = Pages(ctx, item_list=paginator_dict, title="Score ranking", display_option=(2, 9), editable_content=False)

        await p.paginate()

    @commands.command()
    async def emojiranking(self, ctx: commands.Context, *args):
        """Ranking of how many times emojis were used

        Basic example:
        `?emojiranking`: How many times each emoji was used (no self-reactions)

        Arguments (order doesn't matter):

        - Optional: `from:@userA` AND `to:@userB`
            -If from and to flags, gives the score given from @userA to @userB. `from:all` and `to:all` can be used.
            Note that it is possible to give usernames without mention. If a username contains a space, the username and
            flag must be included in quotes, e.g. "to:user name"

        - Optional: `emojitype:type`
            -If emojitype flag, gives the score for this emojitype (see below for types)
            -This is set to emojitype:all by default

        - Optional: `self:bool` (true or false)
            -If true, self-upvotes are counted
            -This is set to self:false by default

        - Optional: `before:message_id` AND/OR `after:message_id`
            -If given, will only count reacts given on messages sent before/after the message_id

        -Available emojitypes for this function:
            -"all" (All emoji),
            -"unicode" (All unicode emoji),
            -"custom" (All custom emoji either in the server or not in the server),
            -"here" (All custom emojis in the server),
            -"nothere" (All custom emoji not in the server)
        """

        try:
            args_dict = await self._get_converted_args_dict(ctx, args, from_xnor_to=True, member=False, emoji=False)
        except commands.BadArgument as err:
            await ctx.send(str(err))
            return

        if args_dict["emojitype"] == "score":
            await ctx.send("Invalid input: Emojitype flag cannot use type score for this function")
        # get the WHERE conditions and the values
        where_str, t = self._where_str_and_values_from_args_dict(args_dict)

        counts = list(
            zip(
                *(
                    await self.fetch_list(
                        (
                            f"SELECT printf('%d. %s', "
                            f"ROW_NUMBER() OVER (ORDER BY count(*) DESC), "
                            f"ReactionName), printf('%d %s', count(*), "
                            f"IIF (count(*)!=1, 'times', 'time')) "
                            f"FROM Reactions "
                            f"WHERE {where_str} "
                            f"GROUP BY ReactionName "
                        ),
                        t,
                    )
                )
            )
        )

        if not counts:
            await ctx.send(embed=discord.Embed(title="No results found"))
            return

        names, values = counts

        paginator_dict = {"names": names, "values": values}
        p = Pages(ctx, item_list=paginator_dict, title="Emoji ranking", display_option=(2, 9), editable_content=False)

        await p.paginate()

    # =========================================================================
    # Table building functions that were used to make the initial
    # Reactions table and fill the Members table with users that were in the
    # Reactions table but not in the Members table.
    # These are inefficient and provided for reference only. If used, should be
    # done on a separate bot instance, with all other DB operations turned off
    # (remindme, quotes, etc.)
    # =========================================================================
    # # You need to import time and datetime for this command
    # @commands.command()
    # async def build_react_database(self, ctx):
    #     conn = sqlite3.connect(self.bot.config.db_path)
    #     conn.execute("PRAGMA foreign_keys = ON")
    #     c = conn.cursor()
    #     t0 = time.perf_counter()
    #     now = datetime.datetime.now()
    #     print("Starting at {}:{}".format(now.hour, now.minute))
    #     for channel in self.bot.get_guild(236668784948019202).text_channels:
    #         now = datetime.datetime.now()
    #         print("Starting {} at {}:{}".format(channel.name, now.hour,
    #                                             now.minute))
    #         i = 0
    #         try:
    #             async for message in channel.history(limit=None,
    #                                                  oldest_first=True,
    #                                                  # can also use
    #                                                  # after=datetime
    #                                                  # .datetime(2020, 7, 20)
    #                                                  ):
    #                 for reaction in message.reactions:
    #                     async for user in reaction.users():
    #                         await add_member_if_needed(self, c, user.id)
    #                         c.execute(
    #                             "INSERT OR IGNORE "
    #                             "INTO Reactions VALUES (?,?,?,?)",
    #                             (user.id, message.author.id, str(
    #                                 reaction.emoji), message.id))
    #                         i += 1
    #                         if i == 10:
    #                             conn.commit()
    #                             i = 0
    #             conn.commit()
    #         except discord.errors.Forbidden:
    #             pass
    #         now = datetime.datetime.now()
    #         print("Completed {} at {}:{}".format(channel.name, now.hour,
    #                                              now.minute))
    #     t1 = time.perf_counter() - t0
    #     print("Completed in {} seconds".format(t1))
    #     conn.close()
    # =========================================================================
    # @commands.command()
    # async def build_members_database(self, ctx):
    #     """Builds the members database from the list of reacts and
    #     current users.
    #     """
    #     async def get_id_and_username(user_id):
    #         try:
    #             user = self.bot.get_user(user_id)
    #             if user is None:
    #                 raise AttributeError
    #             username = str(user)
    #             # print("get_user returned: " + username)
    #         except AttributeError:
    #             try:
    #                 user = await self.bot.fetch_user(user_id)
    #                 username = str(user)
    #                 if "Deleted User" in username:
    #                     username = str(user_id)
    #                 # print("fetch_user returned: " + username)
    #             except discord.errors.NotFound:
    #                 username = str(user_id)
    #         return user_id, username
    #
    #     conn = sqlite3.connect(self.bot.config.db_path)
    #     c = conn.cursor()
    #
    #     c.execute(
    #         "SELECT DISTINCT * FROM (SELECT ReacterID FROM Reactions WHERE "
    #         "ReacterID NOT IN (SELECT ID FROM Members) "
    #         "UNION SELECT ReacteeID FROM Reactions WHERE "
    #         "ReacteeID NOT IN (SELECT ID FROM Members) )")
    #
    #     react_ids = list(list(zip(*c.fetchall()))[0])
    #     ids = set(react_ids + list(map(lambda x: x.id, self.guild.members)))
    #     i = 0
    #     for user_id in ids:
    #         t = await get_id_and_username(user_id)
    #         c.execute("INSERT OR REPLACE INTO Members VALUES (?,?)", t)
    #         i += 1
    #         if i == 10:
    #             conn.commit()
    #             i = 0
    #     conn.commit()
    #     await ctx.send("Task ended")
    #
    #     conn.close()


def setup(bot):
    bot.add_cog(Score(bot))
