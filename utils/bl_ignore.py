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

import discord
from discord.ext import commands
from config import default_color

from .is_owner import SilentNotOwner
from .blacklist_check import blacklist_check

ignore_checks = {
    "Channel": lambda ctx, config: ctx.channel.id in config.channels,
    "Category": lambda ctx, config: getattr(ctx.channel, "category_id", None) in config.channels,
}

def bl_ignore_check():
    async def predicate(ctx: commands.Context) -> bool:
        await blacklist_check().predicate(ctx)
        
        if not ctx.guild or ctx.author.id == ctx.guild.owner_id:
            return True
            
        ignore_cog = ctx.bot.get_cog('Ignore')

        if ignore_cog:
            config = await ignore_cog.get_ignore_config(ctx.guild.id)
            
            if ctx.author.id in config.bypass_users:
                return True
            
            reason = next((r for r, check in ignore_checks.items() if check(ctx, config)), None)
            
            if reason:
                embed = discord.Embed(
                    title="You can't use this command!",
                    description=(
                        "<:cross:1556658187124613120> You are restricted from using this command!\n"
                        "<:space:1556658570198515804><:wickarrow3:1556658291998851162> Restriction Reason ~\n"
                        f"<:space:1556658570198515804><:space:1556658570198515804> `Ignored {reason}`"
                    ),
                    color=default_color
                )
                await ctx.send(embed=embed, delete_after=7)
                raise SilentNotOwner()
            
        return True
        
    return commands.check(predicate)

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
