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

from random import randint


def dice_roll(sides=20, n=1, modifier=0, mpr=False):
    """
    Rolls a die with given parameters
    Set mpr to True to mod each roll, otherwise, only the sum is modified
    """
    roll_mod = modifier if mpr else 0
    total_mod = 0 if mpr else modifier
    roll_list = [randint(1, sides) + roll_mod for _ in range(n)]
    return roll_list, sum(roll_list) + total_mod, max(roll_list), min(roll_list)
