"""
Mythos - A Feature-Rich Discord Music Bot
Copyright (C) 2026 xylen-py

This file is part of Mythos.
Mythos is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Mythos is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Mythos. If not, see <https://www.gnu.org/licenses/>.

Author: xylen-py
GitHub: https://github.com/xylen-py
"""

import re
from datetime import timedelta

def parse_duration(duration_str: str):
    if not duration_str:
        return None
    parts = re.findall(r'(\d+)\s*(y|w|d|h|m|s)', duration_str.lower())
    if not parts:
        return None
    time_delta = timedelta()
    for value, unit in parts:
        value = int(value)
        if unit == 's':
            time_delta += timedelta(seconds=value)
        elif unit == 'm':
            time_delta += timedelta(minutes=value)
        elif unit == 'h':
            time_delta += timedelta(hours=value)
        elif unit == 'd':
            time_delta += timedelta(days=value)
        elif unit == 'w':
            time_delta += timedelta(weeks=value)
        elif unit == 'y':
            time_delta += timedelta(days=value * 365)
            
    return time_delta

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
