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
from cachetools import TTLCache
from utils.bl_ignore import bl_ignore_check
from config import default_color

class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.presence_cache = TTLCache(maxsize=1000, ttl=5)

    async def get_presence_count(self, guild_id):
        if guild_id in self.presence_cache:
            return self.presence_cache[guild_id]

        try:
            fetched = await self.bot.fetch_guild(guild_id, with_counts=True)
            count = fetched.approximate_presence_count or 0
        except Exception:
            count = 0

        self.presence_cache[guild_id] = count
        return count

    @commands.hybrid_command(name="membercount", aliases=["mc"], help="Shows server member statistics.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def membercount(self, ctx: commands.Context):
        guild = ctx.guild

        if not guild.chunked:
            await guild.chunk()

        total_users = guild.member_count
        bot_members = sum(1 for m in guild.members if m.bot)
        human_members = total_users - bot_members

        online = await self.get_presence_count(guild.id)
        offline = max(total_users - online, 0)
        guild_icon = guild.icon.url if guild.icon else self.bot.user.display_avatar.url

        items = [
            discord.ui.Section(
                discord.ui.TextDisplay(content=(
                    f"### <:members:1556658345941934100> Member Count\n"
                    f"> **__Humans__ :** `{human_members}`\n"
                    f"> **__Bots__ :** `{bot_members}`\n"
                    f"> **__Total__ :** `{total_users}`"
                )),
                accessory=discord.ui.Thumbnail(media=guild_icon)
            ),
            discord.ui.Separator(),
            discord.ui.TextDisplay(content=(
                f"<:online:1556658360512680016> **Online :** `{online}`\n"
                f"<:invisible:1556658199883419821> **Offline :** `{offline}`"
            )),
        ]

        container = discord.ui.Container(*items, accent_colour=default_color)
        view = discord.ui.LayoutView()
        
        view.add_item(container)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="boostcount", aliases=["bc"], help="Shows the server's boost level and count.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def boostcount(self, ctx: commands.Context):
        guild = ctx.guild
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count

        container = discord.ui.Container(
            discord.ui.TextDisplay(content=(
                f"**Boost Info !**\n"
                f"<:space:1556658570198515804><:wickarrow:1556658373288796240> The server Boost Level is **__{boost_level}__** with **__{boost_count}__** Boosts"
            )),
            accent_colour=default_color
        )
        view = discord.ui.LayoutView()
        view.add_item(container)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="joinedat", aliases=["ja"], help="Shows when a member joined the server.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def joinedat(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        timestamp = discord.utils.format_dt(member.joined_at, style='F')

        container = discord.ui.Container(
            discord.ui.TextDisplay(content=(
                f"**{member.name}'s Join Date !**\n"
                f"<:space:1556658570198515804><:wickarrow:1556658373288796240> User joined the server at **__{timestamp}__**"
            )),
            accent_colour=default_color
        )
        view = discord.ui.LayoutView()
        view.add_item(container)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    await bot.add_cog(Info(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
