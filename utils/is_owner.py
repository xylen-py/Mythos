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

from discord.ext import commands

OWNER_IDS: set[int] = set()

class SilentNotOwner(commands.CheckFailure):
    pass

def is_owner():
    async def predicate(ctx: commands.Context) -> bool:
        
        if ctx.author.id not in OWNER_IDS:
            raise SilentNotOwner()
        
        return True
    return commands.check(predicate)

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
