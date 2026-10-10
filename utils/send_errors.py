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

async def send_error_embed(ctx: Union[commands.Context, discord.Interaction, discord.abc.Messageable], error_message: str, delete_after: int = None, user: Optional[Union[discord.Member, discord.User]] = None):
    if isinstance(ctx, commands.Context):
        user = user or ctx.author
        
    elif isinstance(ctx, discord.Interaction):
        user = user or ctx.user

    footer_text = ""
    # if user:
    #     footer_text = f"-# Action by {user.mention} (`{user.name}`)"

    items = [
        discord.ui.TextDisplay(content=(
            f"**Process Denied !**\n"
            f"<:space:1556658570198515804><:wccrossmar:1556658451021701167> {error_message}"
        ))
    ]

    if footer_text:
        items.append(discord.ui.Separator(visible=False))
        items.append(discord.ui.TextDisplay(content=footer_text))

    container = discord.ui.Container(
        *items,
        accent_colour=discord.Colour(0xF44336)
    )

    view = discord.ui.LayoutView()
    view.add_item(container)

    if not isinstance(ctx, discord.Interaction):
        return await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none(), delete_after=delete_after)

    if ctx.response.is_done():
        return await ctx.followup.send(view=view, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True)
        
    await ctx.response.send_message(view=view, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True)
    return await ctx.original_response()

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
