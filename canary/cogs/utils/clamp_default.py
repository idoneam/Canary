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

from typing import Any


def clamp_default(val: str | int | None, min_val: int, max_val: int, default: Any):
    """
    Enforces a minimum and maximum (closed) bound on an integer.
    Returns a default value if val is not an integer or false-y.
    """
    try:
        if val or isinstance(val, int):
            return min(max(min_val, int(val)), max_val)
    except ValueError:
        pass
    return default
