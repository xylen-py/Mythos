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
import copy
import io
import json
import asyncio

from config import default_color
from utils.send_errors import send_error_embed

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="force", aliases=["f"], description="Forcefully execute a command bypassing all checks.", hidden=True)
    @commands.is_owner()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def force(self, ctx: commands.Context, *, command: str):
        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg)

        if new_ctx.command:
            await new_ctx.command.reinvoke(new_ctx)

    @commands.command(name="mutuals", description="Show mutual servers with a user.", hidden=True)
    @commands.is_owner()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def mutuals(self, ctx: commands.Context, user: discord.User):
        mutual_guilds = []
        for guild in self.bot.guilds:
            if guild.get_member(user.id):
                mutual_guilds.append(guild)
        
        if not mutual_guilds:
            return await send_error_embed(ctx, f"No mutual servers found with {user.mention}.")
            
        mutual_guilds.sort(key=lambda g: g.member_count or 0, reverse=True)
        
        lines = []
        for i, g in enumerate(mutual_guilds[:20], 1):
            name = g.name if len(g.name) <= 26 else g.name[:23] + " .."
            link = f"https://discord.com/channels/{g.id}"
            lines.append(f"[ `{i:02d}` ] - [`{name}`]({link})")
            
        if len(mutual_guilds) > 20:
            lines.append(f"\n*... and **{len(mutual_guilds) - 20}** more servers.*")
        
        mutuals_content = (f"### Mutual Servers [{len(mutual_guilds)}]\n\n" + "\n".join(lines))[:4000]
        
        items = [
            discord.ui.Section(
                discord.ui.TextDisplay(content=mutuals_content),
                accessory=discord.ui.Thumbnail(media=user.display_avatar.url)
            )
        ]
            
        container = discord.ui.Container(*items, accent_colour=default_color)
        view = discord.ui.LayoutView()
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="updatearl", description="Update the Deezer ARL across all nodes.", hidden=True)
    @commands.is_owner()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def update_arl(self, ctx: commands.Context, *, arl: str):
        if not self.bot.lavalink:
            return await send_error_embed(ctx, "Lavalink is not connected.")
            
        available_nodes = [node for node in self.bot.lavalink.nodes if node.available]
        
        if not available_nodes:
            return await send_error_embed(ctx, "No Lavalink nodes are currently available.")
            
        for node in available_nodes:
            try:
                await node.request("PATCH", "/lavasrc/config", json={"deezer": {"arl": arl}})
            except Exception:
                pass
            
        await ctx.message.add_reaction("<:ztunes:1556658555581628518>")

    @commands.command(name="getinvite", aliases=["getinv"], description="Get an invite to a specific server.", hidden=True)
    @commands.is_owner()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def getinvite(self, ctx: commands.Context, guild_id: int):
        guild = self.bot.get_guild(guild_id)

        if not guild:
            try:
                guild = await self.bot.fetch_guild(guild_id)
            except discord.NotFound:
                return await send_error_embed(ctx, "Could not find a guild with that ID.")
            except discord.Forbidden:
                return await send_error_embed(ctx, "I do not have access to that guild.")

        invites_found = []
        
        try:
            invites = await guild.invites()
            for invite in invites:
                if not invite.revoked:
                    invites_found.append(invite)
        except:
            pass
        
        if not invites_found:
            channels = await guild.fetch_channels()
            text_channels = [c for c in channels if isinstance(c, discord.TextChannel)]

            for channel in text_channels:
                try:
                    invite = await channel.create_invite(max_age=0, max_uses=0)
                    invites_found.append(invite)
                    break
                except:
                    continue
        
        if not invites_found:
            return await send_error_embed(ctx, "Could not get or create an invite.")

        lines = []
        for i, invite in enumerate(invites_found[:10], 1):
            lines.append(f"[ `{i:02d}` ] - [`{invite.code}`]({invite.url})")

        invites_content = f"### Server Invites\n\n" + "\n".join(lines)
        items = []

        if not guild.icon:
            items.append(discord.ui.TextDisplay(content=invites_content))

        if guild.icon:
            items.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(content=invites_content),
                    accessory=discord.ui.Thumbnail(media=guild.icon.url)
                )
            )
        container = discord.ui.Container(*items, accent_colour=default_color)
        view = discord.ui.LayoutView()
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="leaveguild", aliases=["gleave"], description="Force the bot to leave a specific server.", hidden=True)
    @commands.is_owner()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def leaveguild(self, ctx: commands.Context, guild_id: int):
        guild = self.bot.get_guild(guild_id)

        if not guild:
            try:
                guild = await self.bot.fetch_guild(guild_id)
            except discord.NotFound:
                return await send_error_embed(ctx, "Could not find a guild with that ID.")
            except discord.Forbidden:
                return await send_error_embed(ctx, "I do not have access to that guild.")

        try:
            await guild.leave()
        except discord.HTTPException:
            return await send_error_embed(ctx, "Failed to leave the guild.")

        leave_content = f"Successfully left **{guild.name}** (`{guild_id}`) with **{guild.member_count or 0:,}** members!"
        items = []
        
        if not guild.icon:
            items.append(discord.ui.TextDisplay(content=leave_content))
            
        if guild.icon:
            items.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(content=leave_content),
                    accessory=discord.ui.Thumbnail(media=guild.icon.url)
                )
            )
            
        container = discord.ui.Container(*items, accent_colour=default_color)
        view = discord.ui.LayoutView()
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name="enforcement", aliases=["sunyastra"], description="Ban a user across all servers.", hidden=True)
    @commands.is_owner()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def enforcement(self, ctx: commands.Context, user_id: int):
        mutual_guilds = [g for g in self.bot.guilds if g.get_member(user_id)]

        if not mutual_guilds:
            return await send_error_embed(ctx, "No mutual servers found with that user.")

        prompt_msg = await ctx.send(f"This will ban `{user_id}` from **{len(mutual_guilds)}** mutual servers. Type `go` to proceed.")

        try:
            msg = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "go",
                timeout=30.0
            )
            await prompt_msg.delete()
            
            try:
                await msg.delete()
            except Exception:
                pass
            
        except asyncio.TimeoutError:
            await prompt_msg.delete()
            return await send_error_embed(ctx, "Enforcement cancelled. Timed out.")

        success = 0
        failed = 0

        for guild in mutual_guilds:
            if not guild.me.guild_permissions.ban_members:
                failed += 1
                continue
            
            try:
                await guild.ban(discord.Object(id=user_id), reason="[Enforcement] Violation of Discord TOS & ZEON Guidelines")
                success += 1
            except Exception:
                failed += 1

        await ctx.send(f"**Banned** `{user_id}` across **{success}** servers. Failed in **{failed}** servers.")

    @commands.command(name="auditfetch", description="Fetch recent audit logs from a guild as a JSON file.", hidden=True)
    @commands.is_owner()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def auditfetch(self, ctx: commands.Context, guild_id: int, limit: int = 50):
        guild = self.bot.get_guild(guild_id)

        if not guild:
            try:
                guild = await self.bot.fetch_guild(guild_id)
            except discord.NotFound:
                return await send_error_embed(ctx, "Could not find a guild with that ID.")
            except discord.Forbidden:
                return await send_error_embed(ctx, "I do not have access to that guild.")
            
        try:
            entries = [entry async for entry in guild.audit_logs(limit=limit)]
        except discord.Forbidden:
            return await send_error_embed(ctx, "I do not have permission to view audit logs in that guild.")
        except discord.HTTPException as e:
            return await send_error_embed(ctx, f"Failed to fetch audit logs: {e}")
            
        data = []
        for entry in entries:
            data.append({
                "id": str(entry.id),
                "action": str(entry.action),
                "user": f"{entry.user.name} ({entry.user.id})" if entry.user else "Unknown",
                "target": str(entry.target),
                "reason": entry.reason,
                "created_at": entry.created_at.isoformat()
            })
            
        file_content = json.dumps(data, indent=4)
        file = discord.File(io.BytesIO(file_content.encode("utf-8")), filename=f"audit_logs_{guild_id}.json")
        await ctx.send(f"Fetched `{len(data)}` audit logs from **{guild.name}**", file=file)

    @commands.command(name="getguild", aliases=["ginfo"], description="Get detailed information about any server the bot is in.", hidden=True)
    @commands.is_owner()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def getguild(self, ctx: commands.Context, guild_id: int):
        guild = self.bot.get_guild(guild_id)

        if not guild:
            try:
                guild = await self.bot.fetch_guild(guild_id)
            except discord.NotFound:
                return await send_error_embed(ctx, "Could not find a guild with that ID.")
            except discord.Forbidden:
                return await send_error_embed(ctx, "I do not have access to that guild.")

        bot_perms = guild.me.guild_permissions if guild.me else None
        key_perms = []
        
        if bot_perms:
            if bot_perms.administrator:
                key_perms.append("Administrator")

            if not bot_perms.administrator:
                for perm, val in [
                    ("Ban Members", bot_perms.ban_members), 
                    ("Kick Members", bot_perms.kick_members),
                    ("Manage Guild", bot_perms.manage_guild), 
                    ("Manage Roles", bot_perms.manage_roles),
                    ("Manage Channels", bot_perms.manage_channels), 
                    ("Manage Messages", bot_perms.manage_messages)
                ]:
                    if val:
                        key_perms.append(perm)

        perms_text = ", ".join(key_perms) if key_perms else "None"
        header_content = (
            f"### Server Info\n"
            f"**Name :** {guild.name}\n"
            f"**ID :** `{guild.id}`"
        )
        info_content = (
            f"**Owner :** {guild.owner.mention if guild.owner else 'Unknown'} (`{guild.owner_id}`)\n"
            f"**Members :** `{guild.member_count or 0:,}`\n"
            f"**Vanity :** __{guild.vanity_url or 'None'}__\n\n"
            f"**__Bot Permissions__ :**\n\n`{perms_text}`"
        )

        items = []
        if guild.icon:
            items.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(content=header_content),
                    accessory=discord.ui.Thumbnail(media=guild.icon.url)
                )
            )
        if not guild.icon:
            items.append(discord.ui.TextDisplay(content=header_content))

        items.extend([
            discord.ui.Separator(visible=True),
            discord.ui.TextDisplay(content=info_content)
        ])
        
        container = discord.ui.Container(*items, accent_colour=default_color)
        view = discord.ui.LayoutView()
        view.add_item(container)
        await ctx.send(view=view)
        
async def setup(bot):
    await bot.add_cog(Owner(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
