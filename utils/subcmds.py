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
from .paginators import Paginator

async def send_subcommand_help(ctx: commands.Context, per_page: int = 7):
    group = ctx.command

    if not isinstance(group, commands.Group):
        return
    
    subcommands = sorted(group.commands, key=lambda cmd: cmd.name)

    if not subcommands:
        await ctx.send(f"The `{group.name}` command has no subcommands.")
        return
    
    embeds = []
    title = f"{ctx.bot.user.name} {group.name} [{len(subcommands)}]"
    total_pages = (len(subcommands) - 1) // per_page

    for page_num in range(total_pages + 1):
        start = page_num * per_page
        end = start + per_page
        page_subcommands = subcommands[start:end]
        
        description = "```yml\n<..> <required> | [..] [optional]```\n\n"

        for subcommand in page_subcommands:
            signature = f"{ctx.prefix}{group.qualified_name} {subcommand.name}"

            sub_desc = subcommand.description or "No description available."

            description += f"> **`{signature}`**\n"
            description += f"<:space:1556658570198515804><:whitearrow:1556658135471489247> {sub_desc.capitalize()}\n\n"

        embed = discord.Embed(title=title , description=description.strip(), color=None)
        embeds.append(embed)

    paginator = Paginator(ctx, embeds)
    await paginator.start()

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
