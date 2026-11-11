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

errorColor = discord.Color.from_str("#f44336")

async def send_error_embed(
    ctx: Union[commands.Context, discord.Interaction, discord.abc.Messageable],
    error_message: str,
    delete_after: Optional[int] = None
):
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"<:wccrossmar:1556658451021701167> {error_message}"),
        accent_colour=errorColor
    )

    view = discord.ui.LayoutView()
    view.add_item(container)

    interaction = ctx if isinstance(ctx, discord.Interaction) else ctx.interaction

    if interaction and not interaction.is_expired():
        
        if interaction.response.is_done():
            return await interaction.followup.send(view=view, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True)

        await interaction.response.send_message(view=view, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True)
        return await interaction.original_response()

    return await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none(), delete_after=delete_after)

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
