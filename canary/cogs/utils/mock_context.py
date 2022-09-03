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

from dataclasses import dataclass
from discord import User, Member, Guild, ClientUser, Message, VoiceProtocol
from discord.ext.commands import Bot, Cog, Command
from discord.abc import Messageable


@dataclass
class MockContext:
    """Class that can be used to mock a discord context"""

    args: list | None = None
    author: User | Member | None = None
    bot: Bot | None = None
    channel: Messageable | None = None
    cog: Cog | None = None
    command: Command | None = None
    command_failed: bool | None = None
    guild: Guild | None = None
    invoked_parents: list[str] | None = None
    invoked_subcommand: Command | None = None
    invoked_with: str | None = None
    kwargs: dict | None = None
    me: Member | ClientUser | None = None
    message: Message | None = None
    prefix: str | None = None
    subcommand_passed: str | None = None
    valid: bool | None = None
    voice_client: VoiceProtocol | None = None
