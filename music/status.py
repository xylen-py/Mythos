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

_last_status: dict[int, str] = {}

def sanitize_title(title: str, max_length: int = 33) -> str:
    sanitized = title.replace('[', '{').replace(']', '}')
    
    if len(sanitized) > max_length:
        return sanitized[:max_length] + " .."
    
    return sanitized

async def update_vc_status(player, bot):
    if not player:
        return
    
    guild = bot.get_guild(player.guild_id)

    if not guild or not guild.voice_client:
        return
    
    channel = guild.voice_client.channel
    
    if not channel:
        return
    
    status = ""
    
    if player.current:
        info = f"{sanitize_title(player.current.title)} - {sanitize_title(player.current.author)}"
        status = f"<:stream:1556658490125324319> ● **{info[:45]}**"

    if _last_status.get(player.guild_id) == status:
        return

    try:
        await channel.edit(status=status)
        _last_status[player.guild_id] = status
    except discord.HTTPException:
        pass

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
