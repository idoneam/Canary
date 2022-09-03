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
import sqlite3
import requests
from io import BytesIO
from PIL import Image, UnidentifiedImageError, ImageSequence

from ..bot import Canary
from .utils.checks import is_moderator


class Banner(commands.Cog):
    # Written by @le-potate
    def __init__(self, bot: Canary):
        self.bot = bot
        self.guild: discord.Guild | None = None

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

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.bot.config.server_id)
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

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT Value FROM Settings WHERE Key = ?", ("BannerContestInfo",))
        fetched = c.fetchone()
        if fetched:
            banner_dict = json.loads(fetched[0])
            timestamp = banner_dict["timestamp"]
            if timestamp:
                self.start_datetime = datetime.datetime.fromtimestamp(timestamp)
                self.week_name = banner_dict["week_name"]
                self.send_reminder = banner_dict["send_reminder"]
        conn.close()

        self.check_banner_contest_reminder.start()

    @tasks.loop(minutes=1.0)
    async def check_banner_contest_reminder(self):
        # todo: make general scheduled events db instead
        if not all((self.guild, self.banner_reminders_role, self.banner_submissions_channel, self.start_datetime)):
            return

        if datetime.datetime.now() < self.start_datetime or not self.send_reminder:
            return

        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        await self.banner_submissions_channel.send(
            f"{self.banner_reminders_role.mention} "
            f"Submissions are now open for the banner picture of the week! "
            f"Read the rules pinned in {self.banner_of_the_week_channel.mention} to submit a picture. "
            f"The winner will be chosen in around 12 hours "
            f"(To get these reminders, type `.iam Banner Submissions` in {self.bots_channel.mention})"
        )
        c.execute("SELECT Value FROM Settings WHERE Key = ?", ("BannerContestInfo",))
        fetched = c.fetchone()
        if fetched:
            self.send_reminder = False
            banner_dict = json.loads(fetched[0])
            banner_dict["send_reminder"] = False
            c.execute("REPLACE INTO Settings VALUES (?, ?)", ("BannerContestInfo", json.dumps(banner_dict)))
            conn.commit()
        conn.close()

    async def reset_banner_contest(self):
        self.start_datetime = None
        self.week_name = None
        self.send_reminder = None

        banner_dict = {"timestamp": None, "week_name": None, "send_reminder": None}
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("REPLACE INTO Settings VALUES (?, ?)", ("BannerContestInfo", json.dumps(banner_dict)))
        c.execute("DELETE FROM BannerSubmissions")
        conn.commit()
        conn.close()

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
        date_str = date_msg.content

        if date_str.lower() == "quit":
            await ctx.send("Command exited.")
            return

        if date_str.lower() == "now":
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

        banner_dict = {"timestamp": timestamp, "week_name": week_name, "send_reminder": True}
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("REPLACE INTO Settings VALUES (?, ?)", ("BannerContestInfo", json.dumps(banner_dict)))
        c.execute("DELETE FROM BannerSubmissions")
        conn.commit()

        self.start_datetime = datetime.datetime.fromtimestamp(timestamp)
        self.week_name = week_name
        self.send_reminder = True

        await ctx.send(
            f"Start time for the banner contest of the week of `{week_name}` successfully set to "
            f"`{self.start_datetime.strftime('%Y-%m-%d %H:%M')}`."
        )
        conn.close()

    @commands.command(aliases=["bannerwinner", "setbannerwinner", "set_banner_winner"])
    @is_moderator()
    async def banner_winner(self, ctx, winner: discord.Member = None):
        """
        Select the winner for an ongoing Banner Picture of the Week contest

        The winning picture is then set as the server's Banner and the submission is published on the Banner of the week channel.
        The winning user receives the Banner of the Week Winner role, and the submission previews are pinned in the
        Banner Submissions and Converted Banner Submissions channels.

        This command can be used with a user as argument. Otherwise, a prompt will ask for the user.
        The user must have submitted a banner using the submitbanner command during the contest.
        There will then be a prompt with the selected picture to confirm that it is the correct one.

        You must be a moderator to use this command.
        """

        if not self.guild:
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
                "Please enter the username of the winner "
                "or `None` to end the contest without any winner.\n"
                "Type `quit` to leave."
            )

            try:
                winner_msg = await self.bot.wait_for("message", check=msg_check, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send("Command timed out.")
                return

            winner_str = winner_msg.content
            if winner_str.lower() == "none":
                await self.reset_banner_contest()
                await ctx.send("Successfully ended banner contest.")
                return
            elif winner_str.lower() == "quit":
                await ctx.send("Command exited.")
                return
            else:
                try:
                    winner = await commands.MemberConverter().convert(ctx, winner_str)
                except commands.BadArgument:
                    await ctx.send("Could not find user.")
                    return

        if "BANNER" not in self.guild.features:
            await ctx.send("This server cannot upload and use a banner")
            return

        winner_id = winner.id
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM BannerSubmissions WHERE UserID = ?", (winner_id,))
        fetched = c.fetchone()
        conn.close()

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
                reason=f"Banner of the week winner submitted by {winner} " f"(Approved by {ctx.author})"
            )
        except discord.errors.HTTPException as e:
            if e.code == 30003:  # Discord API code for full pins
                pins = await self.banner_submissions_channel.pins()
                await pins[-1].unpin(reason="#banner_submissions pins are full")
                await preview_message.pin(
                    reason=f"Banner of the week winner submitted by {winner} " f"(Approved by {ctx.author})"
                )
            else:
                raise e

        try:
            await converted_message.pin(
                reason=f"Banner of the week winner submitted by {winner} " f"(Approved by {ctx.author})"
            )
        except discord.errors.HTTPException as e:
            if e.code == 30003:
                pins = await self.banner_converted_channel.pins()
                await pins[-1].unpin(reason="#converted_banner_submissions pins are full")
                await converted_message.pin(
                    reason=f"Banner of the week winner submitted by {winner} " f"(Approved by {ctx.author})"
                )
            else:
                raise e

        await winner.add_roles(self.banner_winner_role, reason=f"Banner of the week winner (Approved by {ctx.author})")
        converted_read = await converted.read()
        await self.guild.edit(
            banner=converted_read,
            reason=f"Banner of the week winner submitted by {winner} " f"(Approved by {ctx.author})",
        )
        await self.reset_banner_contest()
        await ctx.send("Successfully set banner and ended contest.")

    @commands.command(aliases=["submitbanner"])
    async def submit_banner(self, ctx: commands.Context, *args):
        """
        Submit a picture for an Banner Picture of the Week contest

        There must be an ongoing Banner contest to use this command; check the Banner of the Week channel for more information.
        This command can be used in a picture caption or with a url as argument.
        The image will be scaled to maximum fit and centered; you can add -stretch to the command for the image to be stretched instead.
        For better results, your picture must be at least 960x540 pixels in a 16:9 aspect ratio.

        You must be a verified user to use this command.
        """
        conn = sqlite3.connect(self.bot.config.db_path)
        c = conn.cursor()

        if not (
            discord.utils.get(ctx.author.roles, name=self.bot.config.mcgillian_role)
            or discord.utils.get(ctx.author.roles, name=self.bot.config.honorary_mcgillian_role)
        ):
            await ctx.send("You must be a verified user.")
            return

        if discord.utils.get(ctx.author.roles, name=self.bot.config.trash_tier_banner_role):
            await ctx.send("You cannot submit banners if you have the Trash Tier Banner Submissions role")
            return

        c.execute("SELECT Value FROM Settings WHERE Key = ?", ("BannerContestInfo",))

        fetched = c.fetchone()
        if not fetched:
            await ctx.send("No banner contest is currently set")
            return

        banner_dict = json.loads(fetched[0])

        timestamp = banner_dict["timestamp"]
        if not timestamp:
            await ctx.send("No banner contest is currently set")
            return
        start_datetime = datetime.datetime.fromtimestamp(timestamp)

        if datetime.datetime.now() < start_datetime:
            await ctx.send(f"You must wait for {start_datetime.strftime('%Y-%m-%d %H:%M')} to submit!")
            return

        if self.send_reminder:
            await ctx.send(
                f"Please wait a minute for the start message to be sent in {self.banner_submissions_channel.mention}"
            )
            return

        stretch = "-stretch" in args or "-stretched" in args

        url = None
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
            else:
                for arg in args:
                    if arg != "-stretch" and arg != "-stretched":
                        url = arg

        user_image_file = BytesIO(requests.get(url).content)
        if user_image_file.getbuffer().nbytes >= 10000000:
            await ctx.send("Image must be less than 10 MB.")
            return

        try:
            with Image.open("./data/premade/banner_converter.png") as overlay_mask, Image.open(
                "./data/premade/banner_preview.png"
            ) as preview_mask, Image.open(user_image_file) as user_image:

                animated = user_image.is_animated

                overlay_mask_user_canvas_size = overlay_mask.size
                preview_mask_user_canvas_size = (240, 135)
                preview_mask_user_box_start = (5, 5)

                overlay_frames = []
                preview_frames = []
                if animated:
                    durations = []
                    await ctx.send("Converting animated banner, this may take some time...")

                for frame in ImageSequence.Iterator(user_image):
                    if animated:
                        durations.append(frame.info["duration"])
                    frame = frame.copy()
                    rgba_frame = frame.convert("RGBA")
                    if stretch:
                        overlay_frames.append(
                            Image.alpha_composite(rgba_frame.resize(overlay_mask_user_canvas_size), overlay_mask)
                        )
                        preview_user_image = Image.new("RGBA", preview_mask.size, (0, 0, 0, 0))
                        preview_user_image.paste(
                            rgba_frame.resize(preview_mask_user_canvas_size), preview_mask_user_box_start
                        )
                        preview_frames.append(Image.alpha_composite(preview_user_image, preview_mask))
                    else:
                        overlay_ratio = max(
                            overlay_mask_user_canvas_size[0] / rgba_frame.size[0],
                            overlay_mask_user_canvas_size[1] / rgba_frame.size[1],
                        )
                        overlay_user_image = Image.new("RGBA", overlay_mask_user_canvas_size, (0, 0, 0, 0))
                        overlay_user_size = (
                            int(rgba_frame.size[0] * overlay_ratio),
                            int(rgba_frame.size[1] * overlay_ratio),
                        )
                        overlay_mask_user_image_start = (
                            int(overlay_mask_user_canvas_size[0] / 2 - overlay_user_size[0] / 2),
                            int(overlay_mask_user_canvas_size[1] / 2 - overlay_user_size[1] / 2),
                        )
                        overlay_user_image.paste(rgba_frame.resize(overlay_user_size), overlay_mask_user_image_start)
                        overlay_frames.append(Image.alpha_composite(overlay_user_image, overlay_mask))

                        preview_ratio = max(
                            preview_mask_user_canvas_size[0] / rgba_frame.size[0],
                            preview_mask_user_canvas_size[1] / rgba_frame.size[1],
                        )
                        preview_user_image = Image.new("RGBA", preview_mask.size, (0, 0, 0, 0))
                        preview_user_size = (
                            int(rgba_frame.size[0] * preview_ratio),
                            int(rgba_frame.size[1] * preview_ratio),
                        )
                        preview_mask_user_image_start = (
                            5 + int(preview_mask_user_canvas_size[0] / 2 - preview_user_size[0] / 2),
                            5 + int(preview_mask_user_canvas_size[1] / 2 - preview_user_size[1] / 2),
                        )
                        preview_user_image.paste(rgba_frame.resize(preview_user_size), preview_mask_user_image_start)
                        preview_frames.append(Image.alpha_composite(preview_user_image, preview_mask))
        except UnidentifiedImageError or requests.exceptions.MissingSchema:
            await ctx.send(f"Image couldn't be opened.")
            return

        replaced_message = False
        c.execute("SELECT PreviewMessageID FROM BannerSubmissions WHERE UserID = ?", (ctx.author.id,))
        fetched = c.fetchone()
        if fetched:
            try:
                message_to_replace = await self.banner_submissions_channel.fetch_message(fetched[0])
                await message_to_replace.delete()
            except discord.errors.NotFound:
                await ctx.send(
                    f"Could not delete previously posted submission from {self.banner_submissions_channel.mention}. "
                    f"It might have been manually deleted."
                )
            replaced_message = True

        async def send_picture(frames, channel, filename):
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

        filetype = "gif" if animated else "png"
        converted_message = await send_picture(
            overlay_frames, self.banner_converted_channel, f"converted_banner.{filetype}"
        )
        preview_message = await send_picture(
            preview_frames, self.banner_submissions_channel, f"banner_preview.{filetype}"
        )
        await preview_message.add_reaction(self.banner_vote_emoji)

        c.execute(
            "REPLACE INTO BannerSubmissions VALUES (?, ?, ?)", (ctx.author.id, preview_message.id, converted_message.id)
        )
        conn.commit()
        conn.close()
        await ctx.send(f"Banner successfully {'resubmitted' if replaced_message else 'submitted'}!")


def setup(bot):
    bot.add_cog(Banner(bot))
