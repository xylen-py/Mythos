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
from discord import app_commands
import json
from dataclasses import dataclass, asdict, field
from typing import cast

import asyncpg
import redis.asyncio as aioredis

from config import default_color
from utils.subcmds import send_subcommand_help
from utils.paginators import Paginator
from utils.success_send import send_success_message
from utils.send_errors import send_error_embed
from utils.bl_ignore import bl_ignore_check

@dataclass
class IgnoreConfig:
    channels: list[int] = field(default_factory=list)
    bypass_users: list[int] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: bytes | str) -> "IgnoreConfig":
        return cls(**json.loads(raw))

    @classmethod
    def from_row(cls, row) -> "IgnoreConfig":
        return cls(**json.loads(row["config"])) if row["config"] else cls()

class Ignore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = cast(asyncpg.Pool, self.bot.db)
        self.redis = cast(aioredis.Redis, self.bot.redis)
        self.redis_key = "ignore:{guild_id}"
        self.bot.loop.create_task(self.connect_db())

    async def connect_db(self):
        await self.setup_db()
        await self.warm_cache()

    async def setup_db(self):
        await self.db.execute("CREATE TABLE IF NOT EXISTS ignore_config (guild_id BIGINT PRIMARY KEY, config JSONB DEFAULT '{}'::jsonb)")

    async def warm_cache(self):
        shard_ids = self.bot.shard_ids or [0]
        
        if 0 not in shard_ids:
            return
            
        rows = await self.db.fetch("SELECT guild_id, config FROM ignore_config")
        pipe = self.redis.pipeline()
        
        for row in rows:
            config = IgnoreConfig.from_row(row)
            pipe.set(self.redis_key.format(guild_id=row["guild_id"]), config.to_json())
            
        await pipe.execute()

    async def get_ignore_config(self, guild_id: int) -> IgnoreConfig:
        data = await self.redis.get(self.redis_key.format(guild_id=guild_id))
        
        if data:
            return IgnoreConfig.from_json(data)
            
        row = await self.db.fetchrow("SELECT config FROM ignore_config WHERE guild_id = $1", guild_id)
        
        if row:
            config = IgnoreConfig.from_row(row)
            await self.redis.set(self.redis_key.format(guild_id=guild_id), config.to_json())
            return config
            
        config = IgnoreConfig()
        await self.redis.set(self.redis_key.format(guild_id=guild_id), config.to_json())
        return config

    async def save_config(self, guild_id: int, config: IgnoreConfig):
        await self.db.execute(
            "INSERT INTO ignore_config (guild_id, config) VALUES ($1, $2::jsonb) "
            "ON CONFLICT (guild_id) DO UPDATE SET config = EXCLUDED.config",
            guild_id, config.to_json()
        )
        await self.redis.set(self.redis_key.format(guild_id=guild_id), config.to_json())

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        config = await self.get_ignore_config(payload.guild_id)
        
        if payload.user.id in config.bypass_users:
            config.bypass_users.remove(payload.user.id)
            await self.save_config(payload.guild_id, config)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        config = await self.get_ignore_config(channel.guild.id)
        
        if channel.id in config.channels:
            config.channels.remove(channel.id)
            await self.save_config(channel.guild.id, config)

    async def send_paginated_list(self, ctx, topic, items):
        if not items:
            return await send_error_embed(ctx, f"There are no ignored {topic.lower()} in this server.")

        embeds = []
        for i in range(0, len(items), 15):
            page_items = items[i:i + 15]
            description = "\n".join(f"**[`{i+j+1:02d}`]** {item}" for j, item in enumerate(page_items))
            embed = discord.Embed(title=f"Ignored {topic.capitalize()} [{len(items)}]", description=description, color=default_color)
            embeds.append(embed)

        paginator = Paginator(ctx, embeds)
        await paginator.start()

    @commands.hybrid_group(name="ignore", description="Manage the server's ignore list.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def ignore(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await send_subcommand_help(ctx)

    @ignore.group(name="channel", description="Manage ignored channels for this server.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def ignore_channel(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await send_subcommand_help(ctx)

    @ignore_channel.command(name="add", description="Add a channel to the server's ignore list.")
    @app_commands.describe(channel="The channel to add in the server's ignore list")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def channel_add(self, ctx: commands.Context, channel: discord.abc.GuildChannel):
        await ctx.defer()
        config = await self.get_ignore_config(ctx.guild.id)

        if channel.id in config.channels:
            return await send_error_embed(ctx, f"Channel {channel.mention} is already in the ignore list.")
        
        config.channels.append(channel.id)
        await self.save_config(ctx.guild.id, config)
        await send_success_message(ctx, "Ignore channel added", f"Channel {channel.mention} has been added to the ignore list.")

    @ignore_channel.command(name="remove", description="Remove a channel from the server's ignore list.")
    @app_commands.describe(channel="The channel to remove from the server's ignore list")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def channel_remove(self, ctx: commands.Context, channel: discord.abc.GuildChannel):
        await ctx.defer()
        config = await self.get_ignore_config(ctx.guild.id)

        if channel.id not in config.channels:
            return await send_error_embed(ctx, f"Channel {channel.mention} is not in the ignore list.")
        
        config.channels.remove(channel.id)
        await self.save_config(ctx.guild.id, config)
        await send_success_message(ctx, "Ignore channel removed", f"Channel {channel.mention} has been removed from the ignore list.")

    @ignore_channel.command(name="show", description="Show all ignored channels for this server.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def channel_show(self, ctx: commands.Context):
        await ctx.defer()
        config = await self.get_ignore_config(ctx.guild.id)

        if not config.channels:
            return await send_error_embed(ctx, "There are no ignored channels in this server.")

        valid_channels = [c.mention for c in map(ctx.guild.get_channel, config.channels) if c]
        await self.send_paginated_list(ctx, "Channels", valid_channels)

    @ignore_channel.command(name="reset", description="Reset the ignored channels list for this server.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def channel_reset(self, ctx: commands.Context):
        await ctx.defer()
        config = await self.get_ignore_config(ctx.guild.id)
        
        config.channels = []
        await self.save_config(ctx.guild.id, config)
        await send_success_message(ctx, "Ignore channel reset", "The ignored channels list has been reset.")

    @ignore.group(name="bypass", description="Manage users that can bypass the ignore list for this server.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def ignore_bypass(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await send_subcommand_help(ctx)

    @ignore_bypass.command(name="add", description="Add a bypass user for this server.")
    @app_commands.describe(user="The user to add in the server's ignore bypass list")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def bypass_add(self, ctx: commands.Context, user: discord.Member):
        await ctx.defer()
        config = await self.get_ignore_config(ctx.guild.id)

        if user.id in config.bypass_users:
            return await send_error_embed(ctx, f"User {user.mention} is already in the bypass list.")
        
        config.bypass_users.append(user.id)
        await self.save_config(ctx.guild.id, config)
        await send_success_message(ctx, "Bypass user added", f"User {user.mention} can now bypass the ignore list.")

    @ignore_bypass.command(name="remove", description="Remove a bypass user for this server.")
    @app_commands.describe(user="The user to remove from the server's ignore bypass list")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def bypass_remove(self, ctx: commands.Context, user: discord.User):
        await ctx.defer()
        config = await self.get_ignore_config(ctx.guild.id)

        if user.id not in config.bypass_users:
            return await send_error_embed(ctx, f"User {user.mention} is not in the bypass list.")
        
        config.bypass_users.remove(user.id)
        await self.save_config(ctx.guild.id, config)
        await send_success_message(ctx, "Bypass user removed", f"User {user.mention} can no longer bypass the ignore list.")

    @ignore_bypass.command(name="show", description="Show all bypass users for this server.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def bypass_show(self, ctx: commands.Context):
        await ctx.defer()
        config = await self.get_ignore_config(ctx.guild.id)
        
        if not config.bypass_users:
            return await send_error_embed(ctx, "There are no bypass users configured for this server.")

        cached_users = [(uid, self.bot.get_user(uid)) for uid in config.bypass_users]
        users = [f"{u.mention} → [`{u.name}`](https://discord.com/users/{u.id})" for _, u in cached_users if u]
        missing_ids = [uid for uid, u in cached_users if not u]

        if missing_ids:
            fetched_members = await ctx.guild.query_members(limit=None, user_ids=missing_ids)
            fetched_ids = {m.id for m in fetched_members}
            
            users.extend(f"{m.mention} → [`{m.name}`](https://discord.com/users/{m.id})" for m in fetched_members)
            dead_ids = set(missing_ids) - fetched_ids
            
            if dead_ids:
                config.bypass_users = [uid for uid in config.bypass_users if uid not in dead_ids]
                await self.save_config(ctx.guild.id, config)

        await self.send_paginated_list(ctx, "Bypass Users", users)

    @ignore_bypass.command(name="reset", description="Reset the bypass users list for this server.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def bypass_reset(self, ctx: commands.Context):
        await ctx.defer()
        config = await self.get_ignore_config(ctx.guild.id)
        
        config.bypass_users = []
        await self.save_config(ctx.guild.id, config)
        await send_success_message(ctx, "Bypass user reset", "The bypass users list has been reset.")

async def setup(bot):
    await bot.add_cog(Ignore(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
