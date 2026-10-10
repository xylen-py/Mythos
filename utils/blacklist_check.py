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
from .is_owner import OWNER_IDS, SilentNotOwner

async def is_user_blacklisted(bot, user_id: int) -> bool:
    blacklist_cog = bot.get_cog('Blacklist')

    if blacklist_cog and user_id in blacklist_cog.users_cache:
        return True

    return False

async def is_guild_blacklisted(bot, guild_id: int) -> bool:
    if not guild_id:
        return False

    blacklist_cog = bot.get_cog('Blacklist')

    if blacklist_cog and guild_id in blacklist_cog.guilds_cache:
        return True

    return False

def blacklist_check():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.author.id in OWNER_IDS:
            return True
            
        if await is_user_blacklisted(ctx.bot, ctx.author.id):
            raise SilentNotOwner()
            
        if ctx.guild and await is_guild_blacklisted(ctx.bot, ctx.guild.id):
            raise SilentNotOwner()
            
        return True
    return commands.check(predicate)

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
