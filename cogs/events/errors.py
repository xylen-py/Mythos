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
import sys
import traceback
from discord.ext import commands
from utils.is_owner import SilentNotOwner
from config import default_color

class UniversalErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown_notified = set() 

    async def send_usage_embed(self, ctx: commands.Context):
        signature = f"{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}"
        description_parts = []

        description_parts.append("```yml\n<..> <required> | [..] [optional]\n```")
        description_parts.append(f"> **`{signature}`**\n")

        if ctx.command.aliases:
            aliases_str = " , ".join(f"`{alias}`" for alias in ctx.command.aliases)
            description_parts.append(f"<:space:1556658570198515804><:whitearrow:1556658135471489247> **Aliases :** {aliases_str}")

        cmd_description = ctx.command.help or ctx.command.description
        if cmd_description:
            description_parts.append(f"<:space:1556658570198515804><:whitearrow:1556658135471489247> {cmd_description}")

        final_description = "\n".join(description_parts)
        
        class Components(discord.ui.LayoutView): 
            container1 = discord.ui.Container(
                discord.ui.TextDisplay(content=final_description)
        )
            
        await ctx.reply(view=Components(), allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if hasattr(ctx.command, 'on_error'):
            return
        
        error = getattr(error, 'original', error)
        
        if isinstance(error, (commands.CommandNotFound, commands.NoPrivateMessage, commands.NotOwner, SilentNotOwner)):
            return

        if isinstance(error, commands.DisabledCommand):
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> You are restricted from using this command!\n"
                    "<:space:1556658570198515804><:wickarrow3:1556658291998851162> Restriction Reason ~\n"
                    "<:space:1556658570198515804><:space:1556658570198515804> `Disabled Command`"
                ),
                color=default_color
            )
            return await ctx.send(embed=embed)

        if isinstance(error, (commands.UserInputError, commands.BadArgument, commands.MissingRequiredArgument, commands.ArgumentParsingError, commands.BadUnionArgument, commands.UnexpectedQuoteError, commands.InvalidEndOfQuotedStringError, commands.ExpectedClosingQuoteError)):
            return await self.send_usage_embed(ctx)

        elif isinstance(error, commands.CommandOnCooldown):
            cooldown_key = (ctx.author.id, ctx.command.qualified_name)
            if cooldown_key in self.cooldown_notified:
                return

            self.cooldown_notified.add(cooldown_key)
            self.bot.loop.call_later(error.retry_after, self.cooldown_notified.discard, cooldown_key)
            
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> You are under cooldown to this command!\n"
                    f"<:space:1556658570198515804><:wickarrow3:1556658291998851162> Cooldown ~ `{error.retry_after:.2f} s`"
                ),
                color=default_color
            )
            return await ctx.send(embed=embed)

        elif isinstance(error, commands.MaxConcurrencyReached):
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> This command has reached its max concurrency!\n"
                    f"<:space:1556658570198515804><:wickarrow3:1556658291998851162> Max Concurrency ~ `{error.number} / {error.per.name}`"
                ),
                color=default_color
            )
            return await ctx.send(embed=embed)

        elif isinstance(error, commands.MissingPermissions):
            perms = "\n".join(f"<:space:1556658570198515804><:space:1556658570198515804> `{perm.replace('_', ' ').title()}`" for perm in error.missing_permissions)
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> You need certain User Permissions to use this command!\n"
                    "<:space:1556658570198515804><:wickarrow3:1556658291998851162> You lack these permissions there ~\n"
                    f"{perms}"
                ),
                color=default_color
            )
            return await ctx.send(embed=embed)

        elif isinstance(error, commands.BotMissingPermissions):
            perms = "\n".join(f"<:space:1556658570198515804><:space:1556658570198515804> `{perm.replace('_', ' ').title()}`" for perm in error.missing_permissions)
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> I need certain Bot Permissions to use this command!\n"
                    "<:space:1556658570198515804><:wickarrow3:1556658291998851162> I lack these permissions there ~\n"
                    f"{perms}"
                ),
                color=default_color
            )
            return await ctx.send(embed=embed)

        elif isinstance(error, commands.NSFWChannelRequired):
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> You are restricted from using this command!\n"
                    "<:space:1556658570198515804><:wickarrow3:1556658291998851162> Restriction Reason ~\n"
                    "<:space:1556658570198515804><:space:1556658570198515804> `NSFW Channel Only`"
                ),
                color=default_color
            )
            return await ctx.send(embed=embed)

        elif isinstance(error, commands.PrivateMessageOnly):
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> You are restricted from using this command!\n"
                    "<:space:1556658570198515804><:wickarrow3:1556658291998851162> Restriction Reason ~\n"
                    "<:space:1556658570198515804><:space:1556658570198515804> `DM Only`"
                ),
                color=default_color
            )
            return await ctx.send(embed=embed)

        elif isinstance(error, commands.CheckFailure):
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> You do not meet the requirements to run this command!\n"
                    "<:space:1556658570198515804><:wickarrow3:1556658291998851162> Restriction Reason ~\n"
                    "<:space:1556658570198515804><:space:1556658570198515804> `Requirements Not Met`"
                ),
                color=default_color
            )
            return await ctx.send(embed=embed)

        elif isinstance(error, discord.Forbidden):
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> I don't have the necessary permissions to perform this action!\n"
                    "<:space:1556658570198515804><:wickarrow3:1556658291998851162> Restriction Reason ~\n"
                    "<:space:1556658570198515804><:space:1556658570198515804> `Missing Permissions [BOT]`"
                ),
                color=default_color
            )
            return await ctx.send(embed=embed)

        elif isinstance(error, discord.HTTPException):
            embed = discord.Embed(
                title="You can't use this command!",
                description=(
                    "<:cross:1556658187124613120> An error occurred while communicating with Discord!\n"
                    "<:space:1556658570198515804><:wickarrow3:1556658291998851162> Error Reason ~\n"
                    f"<:space:1556658570198515804><:space:1556658570198515804> `API Error '{error.status}'`"
                ),
                color=default_color
            )
            return await ctx.send(embed=embed)

        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

async def setup(bot):
    await bot.add_cog(UniversalErrorHandler(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
