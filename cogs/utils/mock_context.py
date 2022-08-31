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
from typing import Union, Optional
from discord import User, Member, Guild, ClientUser, Message, VoiceProtocol
from discord.ext.commands import Bot, Cog, Command
from discord.abc import Messageable


@dataclass
class MockContext:
    """Class that can be used to mock a discord context"""

    args: Optional[list] = None
    author: Optional[Union[User, Member]] = None
    bot: Optional[Bot] = None
    channel: Optional[Union[Messageable]] = None
    cog: Optional[Cog] = None
    command: Optional[Command] = None
    command_failed: Optional[bool] = None
    guild: Optional[Guild] = None
    invoked_parents: Optional[list[str]] = None
    invoked_subcommand: Optional[Command] = None
    invoked_with: Optional[str] = None
    kwargs: Optional[dict] = None
    me: Optional[Union[Member, ClientUser]] = None
    message: Optional[Message] = None
    prefix: Optional[str] = None
    subcommand_passed: Optional[str] = None
    valid: Optional[bool] = None
    voice_client: Optional[VoiceProtocol] = None
