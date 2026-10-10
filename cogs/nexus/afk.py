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
import asyncpg
import json

from typing import cast, List
from dataclasses import dataclass, field, asdict
from config import default_color, support_url
from utils.bl_ignore import bl_ignore_check

@dataclass
class AfkMention:
    mentioner_id: int
    message_id: int
    channel_id: int

@dataclass
class AfkData:
    reason: str
    time: datetime.datetime
    guild_id: int
    mentions: List[AfkMention] = field(default_factory=list)

    def to_dict(self):
        return {
            "reason": self.reason,
            "time": self.time.isoformat(),
            "guild_id": self.guild_id,
            "mentions": [asdict(m) for m in self.mentions]
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            reason=data["reason"],
            time=datetime.datetime.fromisoformat(data["time"]),
            guild_id=data.get("guild_id", 0),
            mentions=[AfkMention(**m) for m in data.get("mentions", [])]
        )

class Afk(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = cast(asyncpg.Pool, self.bot.db)
        self.cache = {}
        self.default_reason = "~ Busy </>"
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 10, commands.BucketType.member)
        self.bot.loop.create_task(self.connect_db())

    async def connect_db(self):
        await self.setup_db()
        await self.warm_cache()

    async def setup_db(self):
        await self.db.execute("CREATE TABLE IF NOT EXISTS afk (user_id BIGINT PRIMARY KEY, config JSONB DEFAULT '{}'::jsonb)")

    async def warm_cache(self):
        self.cache.clear()
        rows = await self.db.fetch("SELECT user_id, config FROM afk")

        for row in rows:
            user_id = row['user_id']
            config = json.loads(row['config'])
            self.cache[user_id] = {int(gid): AfkData.from_dict(data) for gid, data in config.items()}

    def get_afk_config(self, user_id: int) -> dict:
        if user_id not in self.cache:
            self.cache[user_id] = {}
            
        return self.cache[user_id]

    async def save_config(self, user_id: int):
        if user_id not in self.cache or not self.cache[user_id]:
            await self.db.execute("DELETE FROM afk WHERE user_id = $1", user_id)
            return self.cache.pop(user_id, None)

        config = {str(gid): data.to_dict() for gid, data in self.cache[user_id].items()}
        await self.db.execute(
            "INSERT INTO afk (user_id, config) VALUES ($1, $2::jsonb) "
            "ON CONFLICT (user_id) DO UPDATE SET config = EXCLUDED.config", 
            user_id, json.dumps(config)
        )

    async def update_nickname(self, member: discord.Member, afk: bool = True):
        if not member.guild.me.guild_permissions.manage_nicknames:
            return

        if member.top_role >= member.guild.me.top_role:
            return
        
        try:
            if afk and not member.display_name.startswith("[AFK]"):
                return await member.edit(nick=f"[AFK] {member.display_name}"[:32], reason="[AFK] AFK Status Set")
                    
            elif member.display_name.startswith("[AFK] "):
                await member.edit(nick=member.display_name[6:], reason="[AFK] AFK Status Removed")

        except:
            pass

    async def send_return(self, message: discord.Message, afk_info: AfkData):
        del self.cache[message.author.id][message.guild.id]
        await self.save_config(message.author.id)
        await self.update_nickname(message.author, afk=False)

        embed = discord.Embed(description=f"You went AFK <t:{int(afk_info.time.timestamp())}:R> with the reason [**{afk_info.reason}**]({support_url})", color=default_color)
        embed.set_author(name=f"{message.author.name}, Welcome Back!", icon_url=message.author.display_avatar.url)

        if afk_info.mentions:
            field_value = []

            for mention in afk_info.mentions[-8:]:
                link = f"https://discord.com/channels/{message.guild.id}/{mention.channel_id}/{mention.message_id}"
                field_value.append(f"<@{mention.mentioner_id}> - [Jump to message]({link})")

            if field_value:
                embed.add_field(name="Mentions", value="\n".join(field_value), inline=False)

        await message.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="afk", description="Set your AFK status for this server.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def afk(self, ctx, *, reason: str = None):
        reason = reason or self.default_reason
        self.get_afk_config(ctx.author.id)
        
        self.cache[ctx.author.id][ctx.guild.id] = AfkData(
            reason=reason, time=discord.utils.utcnow(), guild_id=ctx.guild.id, mentions=[]
        )

        await self.save_config(ctx.author.id)
        await self.update_nickname(ctx.author, afk=True)
        
        embed = discord.Embed(color=default_color)
        embed.set_author(name=f"{ctx.author.name}, Your AFK has been set!", icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        ctx = await self.bot.get_context(message)
        
        if ctx.valid and ctx.command and ctx.command.name == "afk":
            return

        author_config = self.get_afk_config(message.author.id)

        if message.guild.id in author_config:
            return await self.send_return(message, author_config[message.guild.id])

        for user in message.mentions:
            if user.bot:
                continue
            
            user_config = self.get_afk_config(user.id)
            
            if message.guild.id in user_config:
                bucket = self.cooldown.get_bucket(message)
                
                if bucket and bucket.update_rate_limit():
                    continue

                afk_info = user_config[message.guild.id]
                new_mention = AfkMention(mentioner_id=message.author.id, message_id=message.id, channel_id=message.channel.id)
                self.cache[user.id][message.guild.id].mentions.append(new_mention)
                await self.save_config(user.id)

                embed = discord.Embed(description=f"Went AFK <t:{int(afk_info.time.timestamp())}:R> with the reason [**{afk_info.reason}**]({support_url})", color=default_color)
                embed.set_author(name=f"{user.name}, away from keyboard ...!!", icon_url=user.display_avatar.url)
                
                await message.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())
                break

async def setup(bot):
    await bot.add_cog(Afk(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
