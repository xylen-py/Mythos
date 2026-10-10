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
from typing import Union, Optional
from config import default_color

async def send_success_message(
    ctx: Union[commands.Context, discord.Interaction, discord.abc.Messageable], 
    topic: str, 
    description: str, 
    user: Optional[Union[discord.Member, discord.User]] = None
):
    now = discord.utils.utcnow()
    start_time = now

    if isinstance(ctx, commands.Context):
        start_time = ctx.message.created_at
        user = user or ctx.author
        
    elif isinstance(ctx, discord.Interaction):
        start_time = ctx.created_at
        user = user or ctx.user
    
    execution_time = (now - start_time).total_seconds()

    # footer_text = f"-# Action in `{execution_time:.1f}s`"
    footer_text = f""
    # if user:
    #     footer_text += f"-# Action by {user.mention} (`{user.name}`)"

    content_text = (
        f"**<:wccheckmark:1556658412106817567> {topic.title()}**\n"
        f"<:arrow:1556658266056953899> {description}\n\n"
        f"{footer_text}"
    )

    container = discord.ui.Container(
        discord.ui.TextDisplay(content=content_text),
        accent_colour=default_color
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
