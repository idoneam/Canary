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
# discord-py requirements
import discord
from discord.ext import commands, tasks
from discord import utils

# Other utilities
import asyncio
import datetime
import json
import requests
from io import BytesIO
from PIL import Image, UnidentifiedImageError, ImageSequence

from ..bot import Canary
from .base_cog import CanaryCog
from .utils.checks import is_moderator


class Banner(CanaryCog):
    CONVERTER_FILE = "./data/premade/banner_converter.png"
    PREVIEW_FILE = "./data/premade/banner_preview.png"

    PREVIEW_MASK_USER_CANVAS_SIZE = (240, 135)
    PREVIEW_MASK_USER_BOX_START = (5, 5)
    TRANSPARENT = (0, 0, 0, 0)

    # Written by @le-potate
    def __init__(self, bot: Canary):
        super().__init__(bot)

        self.banner_of_the_week_channel: discord.TextChannel | None = None
        self.banner_submissions_channel: discord.TextChannel | None = None
        self.banner_converted_channel: discord.TextChannel | None = None
        self.bots_channel: discord.TextChannel | None = None

        self.banner_reminders_role: discord.Role | None = None
        self.banner_winner_role: discord.Role | None = None
        self.banner_vote_emoji: discord.Emoji | None = None

        self.start_datetime: datetime.datetime | None = None
        self.week_name: str | None = None
        self.send_reminder: str | None = None

    @CanaryCog.listener()
    async def on_ready(self):
        await super().on_ready()

        if not self.guild:
            return

        self.banner_of_the_week_channel = utils.get(
            self.guild.text_channels, name=self.bot.config.banner_of_the_week_channel
        )
        self.banner_submissions_channel = utils.get(
            self.guild.text_channels, name=self.bot.config.banner_submissions_channel
        )
        self.banner_converted_channel = utils.get(
            self.guild.text_channels, name=self.bot.config.banner_converted_channel
        )
        self.bots_channel = utils.get(self.guild.text_channels, name=self.bot.config.bots_channel)
        self.banner_reminders_role = utils.get(self.guild.roles, name=self.bot.config.banner_reminders_role)
        self.banner_winner_role = utils.get(self.guild.roles, name=self.bot.config.banner_winner_role)
        self.banner_vote_emoji = utils.get(self.guild.emojis, name=self.bot.config.banner_vote_emoji)

        banner_dict: dict | None
        if (banner_dict := await self.get_banner_contest_info()) is not None:
            if timestamp := banner_dict["timestamp"]:
                self.start_datetime = datetime.datetime.fromtimestamp(timestamp)
                self.week_name = banner_dict["week_name"]
                self.send_reminder = banner_dict["send_reminder"]

        self.check_banner_contest_reminder.start()

    async def get_banner_contest_info(self):
        return await self.get_settings_key("BannerContestInfo", deserialize=json.loads)

    async def set_banner_contest_info(self, banner_dict: dict, pre_commit: list[str] | None = None):
        timestamp = banner_dict.get("timestamp")
        self.start_datetime = datetime.datetime.fromtimestamp(timestamp) if timestamp is not None else None
        self.week_name = banner_dict.get("week_name")
        self.send_reminder = banner_dict.get("send_reminder")
        await self.set_settings_key("BannerContestInfo", banner_dict, serialize=json.dumps, pre_commit=pre_commit)

    @tasks.loop(minutes=1.0)
    async def check_banner_contest_reminder(self):
        # todo: make general scheduled events db instead
        if not all((self.guild, self.banner_reminders_role, self.banner_submissions_channel, self.start_datetime)):
            return

        if datetime.datetime.now() < self.start_datetime or not self.send_reminder:
            return

        await self.banner_submissions_channel.send(
            f"{self.banner_reminders_role.mention} "
            f"Submissions are now open for the banner picture of the week! "
            f"Read the rules pinned in {self.banner_of_the_week_channel.mention} to submit a picture. "
            f"The winner will be chosen in around 12 hours "
            f"(To get these reminders, type `.iam Banner Submissions` in {self.bots_channel.mention})"
        )

        banner_dict: dict | None
        if (banner_dict := await self.get_banner_contest_info()) is not None:
            await self.set_banner_contest_info({**banner_dict, "send_reminder": False})

    async def reset_banner_contest(self):
        await self.set_banner_contest_info({"timestamp": None, "week_name": None, "send_reminder": None})

    @commands.command(aliases=["setbannercontest"])
    @is_moderator()
    async def set_banner_contest(self, ctx):
        """
        Set a Banner Picture of the Week contest for the server.

        When calling this command, you will be prompted for the start date and time of the contest,
        and for the 'name' of the week, which is for example used to say `Banner picture of the week of [...]`.
        A reminder will be sent in the Banner Submissions channel when the contest starts.
        You may still plan the next banner contest if the server cannot currently upload and use a banner.

        You must be a moderator to use this command.
        """

        if "BANNER" not in self.guild.features:
            await ctx.send(
                "Warning: This server cannot currently upload and use a banner. "
                "You may still set the next banner contest."
            )

        if self.start_datetime:
            if datetime.datetime.now() < self.start_datetime:
                await ctx.send(
                    f"Note: A banner contest is currently set with start time "
                    f"{self.start_datetime.strftime('%Y-%m-%d %H:%M')}. "
                    f"You may change this date:"
                )
            else:
                await ctx.send(
                    f"There is an ongoing banner contest. "
                    f"If a new start time is set, the current banner contest will be overwritten "
                    f"and current banner submissions will be discarded."
                )

        await ctx.send(
            "Please write the start time of the banner contest in format `YYYY-MM-DD HH:MM` "
            "or type `now` to start now. Type `quit` to leave."
        )

        def msg_check(msg):
            return all((msg.author == ctx.message.author, msg.channel == ctx.channel))

        try:
            date_msg = await self.bot.wait_for("message", check=msg_check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Command timed out.")
            return

        date_str = date_msg.content.lower()

        if date_str == "quit":
            await ctx.send("Command exited.")
            return

        if date_str == "now":
            timestamp = datetime.datetime.now().timestamp()
        else:
            try:
                timestamp = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M").timestamp()
            except ValueError:
                await ctx.send("Invalid date format. Please run the command again")
                return

        await ctx.send(
            "Please write the name of the week the banner contest is for, for example `May 18`.\n"
            "(This is for example used to say `Banner picture of the week of [...]`)"
        )

        try:
            week_msg = await self.bot.wait_for("message", check=msg_check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Command timed out.")
            return

        week_name = week_msg.content

        await self.set_banner_contest_info(
            {"timestamp": timestamp, "week_name": week_name, "send_reminder": True},
            pre_commit=["DELETE FROM BannerSubmissions"],
        )

        await ctx.send(
            f"Start time for the banner contest of the week of `{week_name}` successfully set to "
            f"`{self.start_datetime.strftime('%Y-%m-%d %H:%M')}`."
        )

    @commands.command(aliases=["bannerwinner", "setbannerwinner", "set_banner_winner"])
    @is_moderator()
    async def banner_winner(self, ctx: commands.Context, winner: discord.Member = None):
        """
        Select the winner for an ongoing Banner Picture of the Week contest

        The winning picture is then set as the server's Banner and the submission is published on the Banner of the week
        channel. The winning user receives the Banner of the Week Winner role, and the submission previews are pinned in
        the Banner Submissions and Converted Banner Submissions channels.

        This command can be used with a user as argument. Otherwise, a prompt will ask for the user.
        The user must have submitted a banner using the submitbanner command during the contest.
        There will then be a prompt with the selected picture to confirm that it is the correct one.

        You must be a moderator to use this command.
        """

        if not self.guild:
            return

        if not self.banner_of_the_week_channel:
            await ctx.send("No banner of the week channel set.")
            return

        if not self.banner_submissions_channel:
            await ctx.send("No banner submissions channel set.")
            return

        if not self.banner_converted_channel:
            await ctx.send("No converted banner channel set.")
            return

        if not self.start_datetime:
            await ctx.send("There is no banner contest right now.")
            return

        if datetime.datetime.now() < self.start_datetime:
            await ctx.send(
                f"Banner contest has not started yet! (Starts at {self.start_datetime.strftime('%Y-%m-%d %H:%M')})"
            )
            return

        def msg_check(msg):
            return all((msg.author == ctx.message.author, msg.channel == ctx.channel))

        if not winner:
            await ctx.send(
                "Please enter the username of the winner or `None` to end the contest without any winner.\n"
                "Type `quit` to leave."
            )

            try:
                winner_msg = await self.bot.wait_for("message", check=msg_check, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send("Command timed out.")
                return

            winner_str = winner_msg.content
            match winner_str.lower():
                case "none":
                    await self.reset_banner_contest()
                    await ctx.send("Successfully ended banner contest.")
                    return
                case "quit":
                    await ctx.send("Command exited.")
                    return
                case _:
                    try:
                        winner = await commands.MemberConverter().convert(ctx, winner_str)
                    except commands.BadArgument:
                        await ctx.send("Could not find user.")
                        return

        if "BANNER" not in self.guild.features:
            await ctx.send("This server cannot upload and use a banner")
            return

        winner_id = winner.id

        fetched = await self.fetch_one("SELECT * FROM BannerSubmissions WHERE UserID = ?", (winner_id,))

        if not fetched:
            await ctx.send("No submission by this user in database. Exiting command.")
            return

        preview_message_id = fetched[1]
        converted_message_id = fetched[2]

        try:
            preview_message = await self.banner_submissions_channel.fetch_message(preview_message_id)
        except discord.errors.NotFound:
            await ctx.send(
                f"Could not find submission in {self.banner_submissions_channel.mention}. "
                f"It might have been manually deleted. Exiting command."
            )
            return

        try:
            converted_message = await self.banner_converted_channel.fetch_message(converted_message_id)
        except discord.errors.NotFound:
            await ctx.send(
                f"Could not find submission in {self.banner_converted_channel.mention}. "
                f"It might have been manually deleted. Exiting command."
            )
            return

        voters = await utils.get(preview_message.reactions, emoji=self.banner_vote_emoji).users().flatten()
        if self.bot.user in voters:
            voters.remove(self.bot.user)
        votes = len(voters)

        preview = preview_message.attachments[0]
        converted = converted_message.attachments[0]

        with BytesIO() as preview_image_binary, BytesIO() as converted_image_binary:
            await preview.save(preview_image_binary)
            preview_image_binary.seek(0)
            await converted.save(converted_image_binary)
            converted_image_binary.seek(0)
            await ctx.send(
                "Do you want to select the following banner as winner? "
                "Please type `yes` to confirm. (Type anything otherwise)",
                files=[
                    discord.File(fp=preview_image_binary, filename="banner_preview.png"),
                    discord.File(fp=converted_image_binary, filename="converted_banner.png"),
                ],
            )

        try:
            confirmation_msg = await self.bot.wait_for("message", check=msg_check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Command timed out.")
            return

        if confirmation_msg.content.lower() != "yes":
            await ctx.send("Exiting without selecting winner.")
            return

        with BytesIO() as image_binary:
            await preview.save(image_binary)
            image_binary.seek(0)
            await self.banner_of_the_week_channel.send(
                f"With {votes} votes, here is the banner picture of the week "
                f"of {self.week_name}, submitted by {winner.mention}!",
                file=discord.File(fp=image_binary, filename="banner_preview.png"),
            )

        try:
            await preview_message.pin(
                reason=f"Banner of the week winner submitted by {winner} (Approved by {ctx.author})"
            )
        except discord.errors.HTTPException as e:
            if e.code != 30003:  # Discord API code for full pins
                raise e
            pins = await self.banner_submissions_channel.pins()
            await pins[-1].unpin(reason="#banner_submissions pins are full")
            await preview_message.pin(
                reason=f"Banner of the week winner submitted by {winner} (Approved by {ctx.author})"
            )

        try:
            await converted_message.pin(
                reason=f"Banner of the week winner submitted by {winner} (Approved by {ctx.author})"
            )
        except discord.errors.HTTPException as e:
            if e.code != 30003:
                raise e
            pins = await self.banner_converted_channel.pins()
            await pins[-1].unpin(reason="#converted_banner_submissions pins are full")
            await converted_message.pin(
                reason=f"Banner of the week winner submitted by {winner} (Approved by {ctx.author})"
            )

        await winner.add_roles(self.banner_winner_role, reason=f"Banner of the week winner (Approved by {ctx.author})")
        converted_read = await converted.read()
        await self.guild.edit(
            banner=converted_read,
            reason=f"Banner of the week winner submitted by {winner} (Approved by {ctx.author})",
        )
        await self.reset_banner_contest()
        await ctx.send("Successfully set banner and ended contest.")

    @staticmethod
    def calc_ratio_max(canvas_dims: tuple[int, int], frame: Image) -> float:
        return max(canvas_dims[0] / frame.size[0], canvas_dims[1] / frame.size[1])

    @commands.command(aliases=["submitbanner"])
    async def submit_banner(self, ctx: commands.Context, *args):
        """
        Submit a picture for a Banner Picture of the Week contest

        There must be an ongoing Banner contest to use this command; check the Banner of the Week channel for more
        information.
        This command can be used in a picture caption or with a URL as an argument.
        The image will be scaled to maximum fit and centered; you can add -stretch to the command for the image to be
        stretched instead.
        For better results, your picture must be at least 960x540 pixels in a 16:9 aspect ratio.

        You must be a verified user to use this command.
        """

        if not self.banner_submissions_channel:
            await ctx.send("No banner submissions channel set.")
            return

        # TODO: this is not portable to other server setups
        if not (
            discord.utils.get(ctx.author.roles, name=self.bot.config.mcgillian_role)
            or discord.utils.get(ctx.author.roles, name=self.bot.config.honorary_mcgillian_role)
        ):
            await ctx.send("You must be a verified user.")
            return

        if discord.utils.get(ctx.author.roles, name=self.bot.config.trash_tier_banner_role):
            await ctx.send("You cannot submit banners if you have the Trash Tier Banner Submissions role")
            return

        banner_dict: dict | None = await self.get_banner_contest_info()
        if banner_dict is None:
            await ctx.send("No banner contest is currently set")
            return

        timestamp = banner_dict["timestamp"]
        if not timestamp:
            await ctx.send("No banner contest is currently set")
            return
        if datetime.datetime.now() < (start_datetime := datetime.datetime.fromtimestamp(timestamp)):
            await ctx.send(f"You must wait for {start_datetime.strftime('%Y-%m-%d %H:%M')} to submit!")
            return

        if self.send_reminder:
            await ctx.send(
                f"Please wait a minute for the start message to be sent in {self.banner_submissions_channel.mention}"
            )
            return

        stretch: bool = "-stretch" in args or "-stretched" in args

        url: str | None = None
        if (stretch and len(args) == 1) or (not stretch and len(args) == 0):
            try:
                url = ctx.message.attachments[0].url
            except IndexError:
                await ctx.send("No image sent with message")
                return
        elif ctx.message.embeds:
            url = ctx.message.embeds[0].thumbnail.url
        # sometimes, for some users sending a link doesn't send an embed,
        # while for others it does (with the same exact command), so we do this check
        else:
            if stretch and len(args) > 2 or not stretch and len(args) > 1:
                await ctx.send("Too many arguments or misspelled flag")
                return

            # If the arguments look good: pull the URL out (a non-flag argument)
            for arg in args:
                if arg != "-stretch" and arg != "-stretched":
                    url = arg

        if url is None:
            return

        user_image_file = BytesIO(requests.get(url).content)
        if user_image_file.getbuffer().nbytes >= 10000000:
            await ctx.send("Image must be less than 10 MB.")
            return

        try:
            with Image.open(Banner.CONVERTER_FILE) as overlay_mask, Image.open(
                Banner.PREVIEW_FILE
            ) as preview_mask, Image.open(user_image_file) as user_image:

                animated = user_image.is_animated

                overlay_mask_user_canvas_size = overlay_mask.size

                overlay_frames: list[Image] = []
                preview_frames: list[Image] = []
                durations: list[float] = []

                if animated:
                    await ctx.send("Converting animated banner, this may take some time...")

                for frame in ImageSequence.Iterator(user_image):
                    if animated:
                        durations.append(frame.info["duration"])

                    frame = frame.copy()
                    rgba_frame = frame.convert("RGBA")

                    # If we're stretching the banner, things are a bit easier for us, as we don't have to find a
                    # good 'fit' for the image.
                    if stretch:
                        overlay_frames.append(
                            Image.alpha_composite(rgba_frame.resize(overlay_mask_user_canvas_size), overlay_mask)
                        )
                        preview_user_image = Image.new("RGBA", preview_mask.size, Banner.TRANSPARENT)
                        preview_user_image.paste(
                            rgba_frame.resize(Banner.PREVIEW_MASK_USER_CANVAS_SIZE), Banner.PREVIEW_MASK_USER_BOX_START
                        )
                        preview_frames.append(Image.alpha_composite(preview_user_image, preview_mask))
                        continue

                    # Otherwise, we have to fit the image nicely into the frame
                    overlay_ratio: float = Banner.calc_ratio_max(overlay_mask_user_canvas_size, rgba_frame)
                    overlay_user_image: Image = Image.new("RGBA", overlay_mask_user_canvas_size, Banner.TRANSPARENT)
                    overlay_user_size: tuple[int, int] = (
                        int(rgba_frame.size[0] * overlay_ratio),
                        int(rgba_frame.size[1] * overlay_ratio),
                    )
                    overlay_mask_user_image_start: tuple[int, int] = (
                        int(overlay_mask_user_canvas_size[0] / 2 - overlay_user_size[0] / 2),
                        int(overlay_mask_user_canvas_size[1] / 2 - overlay_user_size[1] / 2),
                    )
                    overlay_user_image.paste(rgba_frame.resize(overlay_user_size), overlay_mask_user_image_start)
                    overlay_frames.append(Image.alpha_composite(overlay_user_image, overlay_mask))

                    preview_ratio: float = Banner.calc_ratio_max(Banner.PREVIEW_MASK_USER_CANVAS_SIZE, rgba_frame)
                    preview_user_image: Image = Image.new("RGBA", preview_mask.size, Banner.TRANSPARENT)
                    preview_user_size: tuple[int, int] = (
                        int(rgba_frame.size[0] * preview_ratio),
                        int(rgba_frame.size[1] * preview_ratio),
                    )
                    preview_mask_user_image_start: tuple[int, int] = (
                        5 + int(Banner.PREVIEW_MASK_USER_CANVAS_SIZE[0] / 2 - preview_user_size[0] / 2),
                        5 + int(Banner.PREVIEW_MASK_USER_CANVAS_SIZE[1] / 2 - preview_user_size[1] / 2),
                    )
                    preview_user_image.paste(rgba_frame.resize(preview_user_size), preview_mask_user_image_start)
                    preview_frames.append(Image.alpha_composite(preview_user_image, preview_mask))

        except UnidentifiedImageError or requests.exceptions.MissingSchema:
            await ctx.send(f"Image couldn't be opened.")
            return

        replaced_message = False

        fetched: tuple[int] | None = await self.fetch_one(
            "SELECT PreviewMessageID FROM BannerSubmissions WHERE UserID = ?",
            (ctx.author.id,),
        )

        if fetched:
            try:
                message_to_replace = await self.banner_submissions_channel.fetch_message(fetched[0])
                await message_to_replace.delete()
            except discord.errors.NotFound:
                await ctx.send(
                    f"Could not delete previously posted submission from "
                    f"{self.banner_submissions_channel.mention}. It might have been manually deleted."
                )
            replaced_message = True

        async def send_picture(frames: list, channel: discord.TextChannel, filename: str) -> discord.Message:
            with BytesIO() as image_binary:
                if animated:
                    frames[0].save(
                        image_binary, "GIF", save_all=True, append_images=frames[1:], loop=0, duration=durations
                    )
                else:
                    frames[0].save(image_binary, "PNG")
                image_binary.seek(0)
                message = await channel.send(
                    f"{ctx.author.mention}'s submission for the week of "
                    f"{self.week_name}{' (resubmission)' if replaced_message else ''}:",
                    file=discord.File(fp=image_binary, filename=filename),
                )
                return message

        filetype: str = "gif" if animated else "png"
        converted_message: discord.Message = await send_picture(
            overlay_frames, self.banner_converted_channel, f"converted_banner.{filetype}"
        )
        preview_message: discord.Message = await send_picture(
            preview_frames, self.banner_submissions_channel, f"banner_preview.{filetype}"
        )
        await preview_message.add_reaction(self.banner_vote_emoji)

        async with self.db() as db:
            await db.execute(
                "REPLACE INTO BannerSubmissions VALUES (?, ?, ?)",
                (ctx.author.id, preview_message.id, converted_message.id),
            )
            await db.commit()

        await ctx.send(f"Banner successfully {'resubmitted' if replaced_message else 'submitted'}!")


def setup(bot):
    bot.add_cog(Banner(bot))