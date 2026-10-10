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
from typing import Optional, Union
from enum import Enum
from config import default_color
from utils.bl_ignore import bl_ignore_check

def truncate(name, limit=20):
    if len(name) > limit:
        return f"{name[:limit]} .."
        
    return name

class ImageState(Enum):
    AVATAR = "avatar"
    SERVER_AVATAR = "server_avatar"
    BANNER = "banner"
    SERVER_BANNER = "server_banner"

class ServerImageState(Enum):
    ICON = "icon"
    BANNER = "banner"

BUTTON_LABELS = {
    ImageState.AVATAR: ("Server Avatar", "Banner"),
    ImageState.SERVER_AVATAR: ("Global Avatar", "Banner"),
    ImageState.BANNER: ("Avatar", "Server Banner"),
    ImageState.SERVER_BANNER: ("Avatar", "Global Banner"),
}

class ImageView(discord.ui.LayoutView):
    def __init__(self, bot, user, member, requested_by, initial_state, formatter):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.member = member
        self.requested_by = requested_by
        self.formatter = formatter
        self.message = None
        self.current_state = initial_state
        self.server_banner = None
        self.build()

    def get_data(self):
        name = self.user.name
        display = self.member.display_name if self.member else name

        data = {
            ImageState.AVATAR: (self.user.display_avatar, f"{truncate(name)}'s Avatar"),
            ImageState.SERVER_AVATAR: (self.member.guild_avatar if self.member else None, f"{truncate(display)}'s Server Avatar"),
            ImageState.BANNER: (self.user.banner, f"{truncate(name)}'s Banner"),
            ImageState.SERVER_BANNER: (self.server_banner, f"{truncate(display)}'s Server Banner"),
        }

        return data.get(self.current_state, (self.user.display_avatar, f"{truncate(name)}'s Avatar"))

    def build(self):
        self.clear_items()

        asset, title = self.get_data()
        links = self.formatter(asset) if asset else ""
        image_url = asset.with_size(4096).url if asset else ""
        label1, label2 = BUTTON_LABELS.get(self.current_state, ("Server Avatar", "Banner"))

        btn1 = discord.ui.Button(label=label1, style=discord.ButtonStyle.secondary)
        btn2 = discord.ui.Button(label=label2, style=discord.ButtonStyle.secondary)
        btn1.callback = self.avatar_callback
        btn2.callback = self.banner_callback

        items = [
            discord.ui.TextDisplay(content=f"### {title}\n{links}"),
            discord.ui.MediaGallery(discord.MediaGalleryItem(media=image_url)),
            discord.ui.Separator(),
            discord.ui.TextDisplay(content=f"-# Requested by {self.requested_by.mention}"),
            discord.ui.Separator(visible=False),
            discord.ui.ActionRow(btn1, btn2),
        ]

        container = discord.ui.Container(*items, accent_colour=default_color)
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.requested_by:
            await interaction.response.send_message(content=f"<:wccrossmar:1556658451021701167> | You didn't request this!", ephemeral=True)
            return False
        return True

    async def avatar_callback(self, interaction: discord.Interaction):
        if self.current_state in (ImageState.BANNER, ImageState.SERVER_BANNER):
            self.current_state = ImageState.AVATAR

        elif self.current_state is ImageState.AVATAR:
            if not self.member:
                try:
                    self.member = await interaction.guild.fetch_member(self.user.id)
                except Exception:
                    return await interaction.response.send_message(f"<:wccrossmar:1556658451021701167> | This user is not in this server.", ephemeral=True)

            if not self.member.guild_avatar:
                return await interaction.response.send_message(f"<:wccrossmar:1556658451021701167> | This user does not have a server avatar.", ephemeral=True)
            self.current_state = ImageState.SERVER_AVATAR

        elif self.current_state is ImageState.SERVER_AVATAR:
            self.current_state = ImageState.AVATAR

        self.build()
        await interaction.response.edit_message(view=self, allowed_mentions=discord.AllowedMentions.none())

    async def banner_callback(self, interaction: discord.Interaction):
        if self.current_state is ImageState.BANNER:
            if not self.member:
                try:
                    self.member = await interaction.guild.fetch_member(self.user.id)
                except Exception:
                    return await interaction.response.send_message(f"<:wccrossmar:1556658451021701167> | This user is not in this server.", ephemeral=True)

            try:
                fetched = await interaction.guild.fetch_member(self.user.id)
            except Exception:
                return await interaction.response.send_message(f"<:wccrossmar:1556658451021701167> | Could not fetch server profile for this user.", ephemeral=True)

            if not fetched.guild_banner:
                return await interaction.response.send_message(f"<:wccrossmar:1556658451021701167> | This user does not have a server banner.", ephemeral=True)

            self.member = fetched
            self.server_banner = fetched.guild_banner
            self.current_state = ImageState.SERVER_BANNER

        else:
            user = await self.bot.fetch_user(self.user.id)
            if not user.banner:
                return await interaction.response.send_message(f"<:wccrossmar:1556658451021701167> | This user does not have a banner.", ephemeral=True)

            self.user = user
            self.current_state = ImageState.BANNER

        self.build()
        await interaction.response.edit_message(view=self, allowed_mentions=discord.AllowedMentions.none())

    async def on_timeout(self):
        if not self.message:
            return
        try:
            asset, title = self.get_data()
            links = self.formatter(asset) if asset else ""
            image_url = asset.with_size(4096).url if asset else ""

            timeout_view = discord.ui.LayoutView()
            items = [
                discord.ui.TextDisplay(content=f"### {title}\n{links}"),
                discord.ui.MediaGallery(discord.MediaGalleryItem(media=image_url)),
                discord.ui.Separator(),
                discord.ui.TextDisplay(content=f"-# Requested by {self.requested_by.mention}"),
            ]
            timeout_view.add_item(discord.ui.Container(*items, accent_colour=default_color))
            await self.message.edit(view=timeout_view, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            pass

class ServerImageView(discord.ui.LayoutView):
    def __init__(self, bot, guild, requested_by, initial_type, formatter):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild = guild
        self.requested_by = requested_by
        self.formatter = formatter
        self.message = None
        self.current_type = initial_type
        self.build()

    def get_data(self):
        data = {
            ServerImageState.ICON: (self.guild.icon, f"{truncate(self.guild.name, 26)}'s Icon"),
            ServerImageState.BANNER: (self.guild.banner, f"{truncate(self.guild.name, 26)}'s Banner"),
        }
        return data.get(self.current_type, (self.guild.icon, f"{truncate(self.guild.name, 26)}'s Icon"))

    def build(self):
        self.clear_items()

        asset, title = self.get_data()
        links = self.formatter(asset) if asset else ""
        image_url = asset.with_size(4096).url if asset else ""

        btn_icon = discord.ui.Button(label="Server Icon", style=discord.ButtonStyle.secondary, disabled=(self.current_type is ServerImageState.ICON))
        btn_banner = discord.ui.Button(label="Server Banner", style=discord.ButtonStyle.secondary, disabled=(self.current_type is ServerImageState.BANNER))
        btn_icon.callback = self.icon_callback
        btn_banner.callback = self.banner_callback

        items = [
            discord.ui.TextDisplay(content=f"### {title}\n{links}"),
            discord.ui.MediaGallery(discord.MediaGalleryItem(media=image_url)),
            discord.ui.Separator(),
            discord.ui.TextDisplay(content=f"-# Requested by {self.requested_by.mention}"),
            discord.ui.Separator(visible=False),
            discord.ui.ActionRow(btn_icon, btn_banner),
        ]

        container = discord.ui.Container(*items, accent_colour=default_color)
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.requested_by:
            await interaction.response.send_message(content=f"<:wccrossmar:1556658451021701167> | You didn't request this!", ephemeral=True)
            return False
        return True

    async def icon_callback(self, interaction: discord.Interaction):
        if not self.guild.icon:
            return await interaction.response.send_message(f"<:wccrossmar:1556658451021701167> | This server does not have an icon.", ephemeral=True)

        self.current_type = ServerImageState.ICON
        self.build()
        await interaction.response.edit_message(view=self, allowed_mentions=discord.AllowedMentions.none())

    async def banner_callback(self, interaction: discord.Interaction):
        if not self.guild.banner:
            return await interaction.response.send_message(f"<:wccrossmar:1556658451021701167> | This server does not have a banner.", ephemeral=True)

        self.current_type = ServerImageState.BANNER
        self.build()
        await interaction.response.edit_message(view=self, allowed_mentions=discord.AllowedMentions.none())

    async def on_timeout(self):
        if not self.message:
            return
        try:
            asset, title = self.get_data()
            links = self.formatter(asset) if asset else ""
            image_url = asset.with_size(4096).url if asset else ""

            timeout_view = discord.ui.LayoutView()
            items = [
                discord.ui.TextDisplay(content=f"### {title}\n{links}"),
                discord.ui.MediaGallery(discord.MediaGalleryItem(media=image_url)),
                discord.ui.Separator(),
                discord.ui.TextDisplay(content=f"-# Requested by {self.requested_by.mention}"),
            ]
            timeout_view.add_item(discord.ui.Container(*items, accent_colour=default_color))
            await self.message.edit(view=timeout_view, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            pass

class Pfp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def generate_banner(self, asset):
        if asset:
            png_link = asset.with_format('png').url
            jpg_link = asset.with_format('jpg').url
            webp_link = asset.with_format('webp').url
            links = f"[`PNG`]({png_link}) | [`JPG`]({jpg_link}) | [`WEBP`]({webp_link})"
            if asset.is_animated():
                gif_link = asset.with_format('gif').url
                links += f" | [`GIF`]({gif_link})"
            return links
        return ""

    @commands.hybrid_command(name="avatar", aliases=["av", "pfp"], description="View a user's avatar.")
    @app_commands.describe(user="The user whose avatar you want to see.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def avatar(self, ctx: commands.Context, user: Optional[Union[discord.Member, discord.User]]):
        await ctx.defer()
        user = user or ctx.author

        member = ctx.guild.get_member(user.id)
        full_user = await self.bot.fetch_user(user.id)

        view = ImageView(self.bot, full_user, member, ctx.author, ImageState.AVATAR, self.generate_banner)
        view.message = await ctx.reply(view=view, mention_author=False, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="banner", aliases=["bn"], description="View a user's banner.")
    @app_commands.describe(user="The user whose banner you want to see.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def banner(self, ctx: commands.Context, user: Optional[Union[discord.Member, discord.User]]):
        await ctx.defer()
        user = user or ctx.author

        member = ctx.guild.get_member(user.id)
        full_user = await self.bot.fetch_user(user.id)

        if not full_user.banner:
            return await ctx.reply(f"<:wccrossmar:1556658451021701167> | This user does not have a banner.", mention_author=False, delete_after=5)

        view = ImageView(self.bot, full_user, member, ctx.author, ImageState.BANNER, self.generate_banner)
        view.message = await ctx.reply(view=view, mention_author=False, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="servericon", aliases=["sicon"], description="View the server's icon.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def servericon(self, ctx: commands.Context):
        await ctx.defer()
        if not ctx.guild.icon:
            return await ctx.reply(f"<:wccrossmar:1556658451021701167> | This server does not have an icon.", mention_author=False, delete_after=5)

        view = ServerImageView(self.bot, ctx.guild, ctx.author, ServerImageState.ICON, self.generate_banner)
        view.message = await ctx.reply(view=view, mention_author=False, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="serverbanner", aliases=["sb", "sbanner"], description="View the server's banner.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def serverbanner(self, ctx: commands.Context):
        await ctx.defer()
        if not ctx.guild.banner:
            return await ctx.reply(f"<:wccrossmar:1556658451021701167> | This server does not have a banner.", mention_author=False, delete_after=5)

        view = ServerImageView(self.bot, ctx.guild, ctx.author, ServerImageState.BANNER, self.generate_banner)
        view.message = await ctx.reply(view=view, mention_author=False, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    await bot.add_cog(Pfp(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
