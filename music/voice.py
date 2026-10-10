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
from utils.is_owner import SilentNotOwner

def requires_voice():
    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> You are restricted from using this command!\n"
                    "<:space:1556658570198515804><:wickarrow3:1556658291998851162> Restriction Reason ~\n"
                    "<:space:1556658570198515804><:space:1556658570198515804> `Voice Connection`"
                ),
                color=default_color
            )
            await ctx.send(embed=embed, delete_after=7)
            raise SilentNotOwner()
        
        if ctx.voice_client and ctx.voice_client.channel != ctx.author.voice.channel:
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> You are restricted from using this command!\n"
                    "<:space:1556658570198515804><:wickarrow3:1556658291998851162> Restriction Reason ~\n"
                    "<:space:1556658570198515804><:space:1556658570198515804> `Same VoiceChannel`"
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
