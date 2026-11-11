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
from typing import Union

successColor = discord.Color.from_str("#008001")

async def send_success_message(
    ctx: Union[commands.Context, discord.Interaction, discord.abc.Messageable], 
    topic: str, 
    description: str
):
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=(
            f"**{topic.title()}**\n"
            f"<:warrow:1569984073139753010> {description}"
        )),
        accent_colour=successColor
    )

    view = discord.ui.LayoutView()
    view.add_item(container)

    if not isinstance(ctx, discord.Interaction):
        return await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    if ctx.response.is_done():
        return await ctx.followup.send(view=view, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True)
        
    await ctx.response.send_message(view=view, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True)
    return await ctx.original_response()

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
