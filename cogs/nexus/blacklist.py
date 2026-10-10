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
import json
import asyncio
from typing import cast

import asyncpg
import redis.asyncio as aioredis

from utils.is_owner import is_owner
from utils.subcmds import send_subcommand_help
from utils.paginators import Paginator
from utils.success_send import send_success_message
from utils.send_errors import send_error_embed
from config import default_color, support_url, website

class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = cast(asyncpg.Pool, self.bot.db)
        self.redis = cast(aioredis.Redis, self.bot.redis)
        self.user_key = "blsync:users"
        self.guild_key = "blsync:guilds"
        self.users_cache = set()
        self.guilds_cache = set()
        self.bot.loop.create_task(self.connect_db())

    @property
    def common(self) -> list[discord.ui.Item]:
        footer_content = (
            f"-# If you believe this was a mistake, you can appeal this decision by joining our **[Support Server]({support_url})**. "
            f"Please note that blacklists for intentional abuse or command spamming are generally permanent and irrevocable."
        )
        return [
            discord.ui.Separator(),
            discord.ui.TextDisplay(content=footer_content),
            discord.ui.Separator(visible=False),
            discord.ui.ActionRow(
                discord.ui.Button(label="Support Server", url=support_url, style=discord.ButtonStyle.link),
                discord.ui.Button(label="Website", url=website, style=discord.ButtonStyle.link)
            )
        ]

    async def connect_db(self):
        await self.setup_db()
        await self.warm_cache()
        self._pubsub_task = self.bot.loop.create_task(self._listen_pubsub())

    async def setup_db(self):
        await self.db.execute("CREATE TABLE IF NOT EXISTS blacklists (type INT PRIMARY KEY, ids TEXT DEFAULT '[]')")
        await self.db.execute("INSERT INTO blacklists (type, ids) VALUES (1, '[]') ON CONFLICT DO NOTHING")
        await self.db.execute("INSERT INTO blacklists (type, ids) VALUES (2, '[]') ON CONFLICT DO NOTHING")

    async def warm_cache(self):
        self.users_cache.clear()
        self.guilds_cache.clear()
        
        row_users = await self.db.fetchrow("SELECT ids FROM blacklists WHERE type = 1")
        if row_users and row_users["ids"]:
            self.users_cache = set(json.loads(row_users["ids"]))
                
        row_guilds = await self.db.fetchrow("SELECT ids FROM blacklists WHERE type = 2")
        if row_guilds and row_guilds["ids"]:
            self.guilds_cache = set(json.loads(row_guilds["ids"]))

    async def cog_unload(self):
        task = getattr(self, "_pubsub_task", None)
        if task and not task.done():
            task.cancel()

    async def safe_leave(self, guild: discord.Guild):
        try:
            await guild.leave()
        except Exception:
            pass

    async def _listen_pubsub(self):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.user_key, self.guild_key)

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                try:
                    data = json.loads(message["data"])
                    action = data.get("action")
                    target_id = data.get("id")
                    
                    channel = message["channel"].decode('utf-8') if isinstance(message["channel"], bytes) else message["channel"]

                    if channel == self.user_key:
                        if action == "add":
                            self.users_cache.add(target_id)
                        elif action == "remove":
                            self.users_cache.discard(target_id)
                        elif action == "reset":
                            self.users_cache.clear()
                            
                    elif channel == self.guild_key:
                        if action == "add":
                            self.guilds_cache.add(target_id)
                        elif action == "remove":
                            self.guilds_cache.discard(target_id)
                        elif action == "reset":
                            self.guilds_cache.clear()

                except Exception:
                    continue

        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(self.user_key, self.guild_key)
            await pubsub.close()

    async def add_user_blacklist(self, ctx: commands.Context):
        self.users_cache.add(ctx.author.id)
        await self.db.execute("UPDATE blacklists SET ids = $1 WHERE type = 1", json.dumps(list(self.users_cache)))
        await self.redis.publish(self.user_key, json.dumps({"action": "add", "id": ctx.author.id}))

        intro_content = (
            f"### You have been Blacklisted!\n"
            f"You have been permanently blacklisted from using **{self.bot.user.name}** across all servers. "
            f"This action was taken automatically by our security systems."
        )

        action_content = (
            f"**__Reason for Blacklist__**\n\n"
            f"Your account was flagged for excessive command spamming, which violates our usage policies. "
            f"To protect our infrastructure and ensure fair usage for all members, your access to "
            f"all bot commands has been permanently revoked."
        )
        
        items = [
            discord.ui.Section(
                discord.ui.TextDisplay(content=intro_content),
                accessory=discord.ui.Thumbnail(media=self.bot.user.display_avatar.url)
            ),
            discord.ui.Separator(visible=False),
            discord.ui.TextDisplay(content=action_content)
        ]
        items.extend(self.common)
        
        container = discord.ui.Container(*items, accent_colour=default_color)
        view = discord.ui.LayoutView()
        view.add_item(container)
        
        try:
            await ctx.author.send(view=view)
        except discord.Forbidden:
            pass

    async def add_guild_blacklist(self, guild_id: int):
        self.guilds_cache.add(guild_id)
        await self.db.execute("UPDATE blacklists SET ids = $1 WHERE type = 2", json.dumps(list(self.guilds_cache)))
        await self.redis.publish(self.guild_key, json.dumps({"action": "add", "id": guild_id}))

        guild = self.bot.get_guild(guild_id)
        if guild and guild.owner:
            intro_content = (
                f"### Server Blacklisted!\n"
                f"Your server **`{guild.name}`** has been permanently blacklisted from using **{self.bot.user.name}**. "
                f"The bot will no longer respond to any commands or events within your server."
            )
            
            action_content = (
                f"**__Reason for Blacklist__**\n\n"
                f"Our security systems detected a coordinated command spam attack originating from multiple users "
                f"within your server. To protect our infrastructure, we have permanently disabled all bot functionality "
                f"for this server."
            )
            
            items = [
                discord.ui.Section(
                    discord.ui.TextDisplay(content=intro_content),
                    accessory=discord.ui.Thumbnail(media=self.bot.user.display_avatar.url)
                ),
                discord.ui.Separator(visible=False),
                discord.ui.TextDisplay(content=action_content)
            ]
            items.extend(self.common)
            
            container = discord.ui.Container(*items, accent_colour=default_color)
            view = discord.ui.LayoutView()
            view.add_item(container)
            
            try:
                await guild.owner.send(view=view)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if guild.id in self.guilds_cache:
            await self.safe_leave(guild)

    @commands.hybrid_group(name="blacklist", aliases=["bl"], description="Manage the bot's global blacklist.")
    @commands.guild_only()
    @is_owner()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def blacklist(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await send_subcommand_help(ctx)

    @blacklist.group(name="user", description="Manage blacklisted users.")
    @commands.guild_only()
    @is_owner()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def blacklist_user(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await send_subcommand_help(ctx)

    @blacklist_user.command(name="add", description="Add a user to the blacklist.")
    @commands.guild_only()
    @is_owner()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def user_add(self, ctx: commands.Context, user: discord.User):
        await ctx.defer()
        if user.id in self.users_cache:
            return await send_error_embed(ctx, f"User {user.mention} (`{user.id}`) is already in the blacklist.")
        
        self.users_cache.add(user.id)
        await self.db.execute("UPDATE blacklists SET ids = $1 WHERE type = 1", json.dumps(list(self.users_cache)))
        
        await self.redis.publish(self.user_key, json.dumps({"action": "add", "id": user.id}))
        await send_success_message(ctx, "Blacklist user added", f"User {user.mention} (`{user.id}`) has been added to the blacklist.")

    @blacklist_user.command(name="remove", description="Remove a user from the global blacklist.")
    @commands.guild_only()
    @is_owner()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def user_remove(self, ctx: commands.Context, user: discord.User):
        await ctx.defer()
        if user.id not in self.users_cache:
            return await send_error_embed(ctx, f"User {user.mention} is not in the blacklist.")
        
        self.users_cache.discard(user.id)
        await self.db.execute("UPDATE blacklists SET ids = $1 WHERE type = 1", json.dumps(list(self.users_cache)))
        
        await self.redis.publish(self.user_key, json.dumps({"action": "remove", "id": user.id}))
        await send_success_message(ctx, "Blacklist user removed", f"User {user.mention} (`{user.id}`) has been removed from the blacklist.")

    @blacklist_user.command(name="show", description="Show all blacklisted users.")
    @commands.guild_only()
    @is_owner()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def user_show(self, ctx: commands.Context):
        await ctx.defer()
        user_ids = list(self.users_cache)

        if not user_ids:
            return await send_error_embed(ctx, "There are no blacklisted users.")

        cached_users = [(uid, self.bot.get_user(uid)) for uid in user_ids]
        users = [f"{u.mention} → [`{u.name}`](https://discord.com/users/{u.id})" for _, u in cached_users if u]
        missing_ids = [uid for uid, u in cached_users if not u]

        if missing_ids:
            users.extend(f"<@{uid}> → [`Unknown User`](https://discord.com/users/{uid})" for uid in missing_ids)

        if not users:
            return await send_error_embed(ctx, "Could not find any of the blacklisted users.")

        users_per_page = 15
        embeds = []

        for i in range(0, len(users), users_per_page):
            page_items = users[i:i + users_per_page]
            description = "\n".join(f"**[`{i+j+1:02d}`]** {item}" for j, item in enumerate(page_items))
            embed = discord.Embed(title=f"Blacklisted Users [{len(user_ids)}]", description=description, color=default_color)
            embeds.append(embed)

        paginator = Paginator(ctx, embeds)
        await paginator.start()

    @blacklist.group(name="guild", description="Manage blacklisted guilds.")
    @commands.guild_only()
    @is_owner()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def blacklist_guild(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await send_subcommand_help(ctx)

    @blacklist_guild.command(name="add", description="Add a guild to the blacklist.")
    @commands.guild_only()
    @is_owner()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def guild_add(self, ctx: commands.Context, guild_id: int):
        await ctx.defer()
        if guild_id in self.guilds_cache:
            return await send_error_embed(ctx, f"Guild with ID `{guild_id}` is already in the blacklist.")
        
        self.guilds_cache.add(guild_id)
        await self.db.execute("UPDATE blacklists SET ids = $1 WHERE type = 2", json.dumps(list(self.guilds_cache)))
        
        await self.redis.publish(self.guild_key, json.dumps({"action": "add", "id": guild_id}))
        guild = self.bot.get_guild(guild_id)
        await send_success_message(ctx, "Blacklist guild added", f"Guild `{guild.name if guild else 'Unknown'}` (`{guild_id}`) has been added to the blacklist.")

    @blacklist_guild.command(name="remove", description="Remove a guild from the  blacklist.")
    @commands.guild_only()
    @is_owner()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def guild_remove(self, ctx: commands.Context, guild_id: int):
        await ctx.defer()
        if guild_id not in self.guilds_cache:
            return await send_error_embed(ctx, f"Guild with ID `{guild_id}` is not in the blacklist.")
        
        self.guilds_cache.discard(guild_id)
        await self.db.execute("UPDATE blacklists SET ids = $1 WHERE type = 2", json.dumps(list(self.guilds_cache)))
        
        await self.redis.publish(self.guild_key, json.dumps({"action": "remove", "id": guild_id}))
        guild = self.bot.get_guild(guild_id)
        await send_success_message(ctx, "Blacklist guild removed", f"Guild `{guild.name if guild else 'Unknown'}` (`{guild_id}`) has been removed from the blacklist.")

    @blacklist_guild.command(name="show", description="Show all blacklisted guilds.")
    @commands.guild_only()
    @is_owner()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def guild_show(self, ctx: commands.Context):
        await ctx.defer()
        guild_ids = list(self.guilds_cache)

        if not guild_ids:
            return await send_error_embed(ctx, "There are no blacklisted guilds.")

        cached_guilds = [(gid, self.bot.get_guild(gid)) for gid in guild_ids]
        formatted_guilds = [f"[`{g.name}`](https://discord.com/channels/{g.id}) → `{g.id}`" for _, g in cached_guilds if g]
        missing_ids = [gid for gid, g in cached_guilds if not g]

        if missing_ids:
            formatted_guilds.extend(f"[`Not In Guild`](https://discord.com/channels/{gid}) → `{gid}`" for gid in missing_ids)

        guilds_per_page = 15
        embeds = []

        for i in range(0, len(formatted_guilds), guilds_per_page):
            page_items = formatted_guilds[i:i + guilds_per_page]
            description = "\n".join(f"**[`{i+j+1:02d}`]** {item}" for j, item in enumerate(page_items))
            embed = discord.Embed(title=f"Blacklisted Guilds [{len(guild_ids)}]", description=description, color=default_color)
            embeds.append(embed)

        paginator = Paginator(ctx, embeds)
        await paginator.start()

async def setup(bot):
    await bot.add_cog(Blacklist(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
