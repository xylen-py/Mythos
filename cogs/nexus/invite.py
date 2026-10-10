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

from config import default_color, support_url, website
from utils.bl_ignore import bl_ignore_check

class Invite(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="invite", aliases=["support"], description="Get the bot's invite link and support server.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def invite(self, ctx: commands.Context):
        invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=discord.Permissions.all(),
            scopes=["bot", "applications.commands"]
        )

        items = [
            discord.ui.TextDisplay(
                content=f"### Invite {self.bot.user.name} !\n"
                f"<:space:1556658570198515804><:arrow:1556658266056953899> Thank you for your interest in using {self.bot.user.name}, get ready to maximize the security for your server & visit our **[Website]({website})** for more information."
            ),
            discord.ui.Separator(),
            discord.ui.ActionRow(
                discord.ui.Button(label="Invite Me", url=invite_url, style=discord.ButtonStyle.link),
                discord.ui.Button(label="Support Server", url=support_url, style=discord.ButtonStyle.link),
            ),
        ]

        container = discord.ui.Container(*items, accent_colour=default_color)
        view = discord.ui.LayoutView()
        view.add_item(container)
        await ctx.reply(view=view, mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(Invite(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
