# -*- coding: utf-8 -*-
#
# Copyright (C) idoneam (2016-2019)
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

# Utilities
import random
from ..utils.auto_incorrect import auto_incorrect


class MemesController():
    def __init__(self, logger):
        self.logger = logger

    def bac(self, author: str, content: str, input_str: str):
        self.logger.info(f'input string: {input_str}')
        msg = auto_incorrect(input_str)
        self.logger.info('?bac invoked: Author: {}, Message: {}'.format(
            author, content))
        return msg

    def mix(self, author: str, content: str, input_str: str):
        msg = "".join([(c.upper() if random.randint(0, 1) else c.lower())
                       for c in input_str])
        self.logger.info('?mix invoked: Author: {}, Message: {}'.format(
            author, content))
        return msg

    def pyramid(self, num: int = 2, emoji: str = "👢"):
        """Draws a pyramid of boots, default is 2 unless user specifies an integer number of levels of boots between -8 and 8. Also accepts any other emoji, word or multiword (in quotes) string."""
        def pyramidy(n, m):
            return "{spaces}{emojis}".format(spaces=" " * ((m - n) * 3),
                                             emojis=(emoji + " ") * n)

        if (num > 0):
            num = max(min(num, 8), 1)    # Above 8, herre gets angry
            msg = "\n".join(pyramidy(ln, num) for ln in range(1, num + 1))
        else:
            num = min(max(num, -8), -1)    # Below -8, herre gets angry
            msg = "\n".join(
                pyramidy(ln, abs(num))
                for ln in reversed(range(1,
                                         abs(num) + 1)))

        return msg
