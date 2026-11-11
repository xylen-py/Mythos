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
from utils.blacklist_check import is_guild_blacklisted, is_user_blacklisted

class OnMention(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 5.0, commands.BucketType.user)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild or message.content.lower() != f"<@{self.bot.user.id}>":
            return

        bucket = self.cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        
        if retry_after:
            return

        if await is_user_blacklisted(self.bot, message.author.id) or await is_guild_blacklisted(self.bot, message.guild.id):
            return

        items = [
            discord.ui.TextDisplay(
                content=f"{message.author.mention}**, Bot's prefix** is `/` or `@{self.bot.user.name}`\n"
                        f"-# **<:string:1509936991763038409> Use `/help` or `@{self.bot.user.name} help` to get started with us!**"
            )
        ]

        container = discord.ui.Container(*items, accent_colour=default_color)
        view = discord.ui.LayoutView()
        view.add_item(container)
        await message.reply(view=view, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot: commands.Bot):
    await bot.add_cog(OnMention(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
