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
import datetime
import time
import psutil
import os
import platform
from typing import cast

import asyncpg
import redis.asyncio as aioredis

from config import default_color, support_url, website
from utils.bl_ignore import bl_ignore_check

def format_number(num):
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"

    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
        
    return str(num)

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = cast(asyncpg.Pool, self.bot.db)
        self.redis = cast(aioredis.Redis, self.bot.redis)

    @commands.hybrid_command(name="stats", description="Displays detailed bot statistics and shard information.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def stats(self, ctx: commands.Context):
        await ctx.defer()
        current_shard = ctx.guild.shard_id if ctx.guild else 0

        try:
            process = psutil.Process(os.getpid())
            ram = f"{process.memory_info().rss / (1024 ** 2):.1f} MB"
            cpu = f"{psutil.cpu_percent(interval=None)}%"
        except Exception:
            ram = "N/A"
            cpu = "N/A"

        s = int((datetime.datetime.now(datetime.timezone.utc) - self.bot.start_time).total_seconds())
        uptime = f"{s // 86400}d {s % 86400 // 3600}h {s % 3600 // 60}m"
        
        usercount = sum((g.member_count or 0) for g in self.bot.guilds)
        guilds = len(self.bot.guilds)
        channels = sum(len(g.channels) for g in self.bot.guilds)
        latency = round(self.bot.latency * 1000) if self.bot.latency != float('inf') else 0
        shard_count = self.bot.shard_count or 1
        total_commands = len([cmd for cmd in self.bot.walk_commands() if cmd.cog is not None])

        items = [
            discord.ui.Section(
                discord.ui.TextDisplay(
                    content=(
                        f"### <:latency:1556658663135912026> {self.bot.user.name}'s Statistics\n"
                        f"Comprehensive real-time overview of **{self.bot.user.name}**'s operational status, "
                        f"resource usage, and shard distribution across the network."
                    )
                ),
                accessory=discord.ui.Thumbnail(media=self.bot.user.display_avatar.url)
            ),
            discord.ui.Separator(visible=False),
            discord.ui.TextDisplay(content=(
                f"The bot is currently serving **{format_number(usercount)}** users across "
                f"**{format_number(guilds)}** servers, managing a total of "
                f"**{format_number(channels)}** channels. It has been running "
                f"continuously for **{uptime}** with a websocket latency of **{latency}ms**."
            )),
            discord.ui.Separator(visible=False),
            discord.ui.TextDisplay(content=(
                f"Running on **{shard_count}** shards, this server is routed through shard "
                f"**{current_shard}**. The bot is consuming **{ram}** of memory and **{cpu}** CPU, "
                f"powered by **Python {platform.python_version()}** and **discord.py {discord.__version__}**. "
                f"A total of **{total_commands}** commands are loaded and operational."
            )),
            discord.ui.Separator(),
            discord.ui.ActionRow(
                discord.ui.Button(label="Website", url=website, style=discord.ButtonStyle.link),
                discord.ui.Button(label="Support Server", url=support_url, style=discord.ButtonStyle.link),
            ),
        ]

        container = discord.ui.Container(*items, accent_colour=default_color)
        view = discord.ui.LayoutView(timeout=180)
        view.add_item(container)
        await ctx.reply(view=view, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="ping", description="Checks the bot's latency")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ping(self, ctx: commands.Context):
        await ctx.defer()

        pg_latency = "N/A"
        if self.db:
            try:
                pg_start = time.monotonic()
                await self.db.execute("SELECT 1")
                pg_latency = f"{round((time.monotonic() - pg_start) * 1000)} ms"
            except Exception:
                pg_latency = "Failed"

        redis_latency = "N/A"
        if self.redis:
            try:
                redis_start = time.monotonic()
                await self.redis.ping() # pyrefly: ignore [not-async]
                redis_latency = f"{round((time.monotonic() - redis_start) * 1000)} ms"
            except Exception:
                redis_latency = "Failed"

        latency = round(self.bot.latency * 1000) if self.bot.latency != float('inf') else 0

        items = [
            discord.ui.Section(
                discord.ui.TextDisplay(content=(
                    f"### <:latency:1556658663135912026> Bot's Latency\n"
                    f"> **__Websocket Latency__ :** `{latency} ms`\n"
                    f"> **__PostgreSQL__ :** `{pg_latency}`\n"
                    f"> **__Redis Cache__ :** `{redis_latency}`"
                )),
                accessory=discord.ui.Thumbnail(media=self.bot.user.display_avatar.url)
            )
        ]

        container = discord.ui.Container(*items, accent_colour=default_color)
        view = discord.ui.LayoutView()
        view.add_item(container)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    await bot.add_cog(Stats(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
