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

def dnd_roll(sides=20, n=1, modifier=0, mpr=False):
    """
    Rolls a die with given parameters
    Set mpr to True to mod each roll, otherwise, only the sum is modified
    """
    roll_list = []
    
    if mpr = True:
        roll_mod = modifier
        total_mod = 0
    else:
        roll_mod = 0
        total_mod = modifier
    
    for i in range(n):
        result = randint(1,sides)
        roll_list.append(result + roll_mod)
    
    total = sum(roll_list) + total_mod
    
    return roll_list, total, max(roll_list), min(roll_list)