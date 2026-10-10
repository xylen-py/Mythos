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
from discord import ui
import datetime
import config

class Advertise(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if not self.bot.user:
            return
        
        embed = discord.Embed(
            description=(
                "<:greydot:1556658333023346840> **Thanks for adding !**\n\n"
                "<:greydot:1556658333023346840> My default prefix is `.`\n"
                "<:greydot:1556658333023346840> Use `.help` or `/help` in the server for commands\n"
                f"<:greydot:1556658333023346840> For questions or details join **[Support server]({config.support_url})**"
            ),
            color=discord.Color.from_rgb(54, 57, 63),
            timestamp=datetime.datetime.utcnow()
        )

        bot_user = self.bot.user

        if bot_user.avatar:
            embed.set_footer(text=f"By {config.support_server_name}", icon_url=bot_user.avatar.url)
            embed.set_thumbnail(url=bot_user.avatar.url)

        else:
            embed.set_footer(text=f"By {config.support_server_name}")

        adder = None

        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                if entry.target and entry.target.id == self.bot.user.id:
                    adder = entry.user
                    break
                
        except Exception:
            pass

        target_channel = None
        
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            target_channel = guild.system_channel

        else:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break

        if adder and not adder.bot:

            dm_view = ui.View()
            dm_view.add_item(ui.Button(label="Support Server", style=discord.ButtonStyle.link, url=config.support_url))
            dm_view.add_item(ui.Button(label="Website", style=discord.ButtonStyle.link, url=config.website))

            if target_channel:
                guild_name = (guild.name[:20] + '...') if len(guild.name) > 23 else guild.name
                dm_view.add_item(ui.Button(label=f"Go to {guild_name}", style=discord.ButtonStyle.link, url=target_channel.jump_url))

            try:
                await adder.send(embed=embed, view=dm_view)
            except Exception:
                pass

        if target_channel:

            server_view = ui.View()
            server_view.add_item(ui.Button(label="Support Server", style=discord.ButtonStyle.link, url=config.support_url))
            server_view.add_item(ui.Button(label="Website", style=discord.ButtonStyle.link, url=config.website))

            try:
                await target_channel.send(embed=embed, view=server_view)
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Advertise(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
