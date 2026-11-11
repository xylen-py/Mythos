import discord
from discord.ext import commands
import json
import re
import time
import config
from typing import List, Dict, Any
from utils.bl_ignore import bl_ignore_check
from utils.send_errors import send_error_embed
from utils.subcmds import send_subcommand_help

help_file = "data/pages.json"

class PageSelect(discord.ui.Select):
    def __init__(self, view_instance, options, placeholder):
        super().__init__(placeholder=placeholder, options=options)
        self.view_instance = view_instance

    async def callback(self, interaction: discord.Interaction):
        page_number = int(self.values[0])
        await self.view_instance.send_ephemeral_page(interaction, page_number)

class HelpView(discord.ui.LayoutView):
    def __init__(self, ctx: commands.Context, page_data: List[Dict[str, Any]], replacements: Dict[str, str], module_regex, app_commands: Dict[str, int] = None):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.page_data = page_data
        self.replacements = replacements
        self.module_regex = module_regex
        self.app_commands = app_commands or {}
        self.message = None

        select_options = []
        for i, data in enumerate(self.page_data):
            if i == 0:
                continue
            
            if len(select_options) >= 25:
                break
                
            select_options.append(discord.SelectOption(
                label=data.get("title", f"Page {i+1}"), 
                description=data.get("description", "")[:100], 
                emoji=data.get("emoji"), 
                value=str(i)
            ))
        
        self.dropdown = None
        if select_options:
            self.dropdown = PageSelect(self, select_options, "⤷ Select a module to see")

    def format_text(self, text: str) -> str:
        if not text: 
            return text
        
        matches = self.module_regex.findall(text)
        for cog_name in matches:
            text = text.replace(f"{{module:{cog_name}}}", self.get_cog_commands(cog_name.strip()))

        cmd_matches = re.findall(r'\{command:(.*?)\}', text)
        for cmd_name in cmd_matches:
            text = text.replace(f"{{command:{cmd_name}}}", self.get_single_command(cmd_name.strip()))

        for key, val in self.replacements.items():
            text = text.replace(key, str(val))
        return text

    def get_single_command(self, cmd_name: str) -> str:
        cmd = self.ctx.bot.get_command(cmd_name)
        if not cmd:
            return f"`{cmd_name}`"
        root_name = cmd.root_parent.name if cmd.root_parent else cmd.name
        cmd_id = self.app_commands.get(root_name, 0)
        desc = cmd.description or cmd.help or "No description provided."
        desc = desc.split("\n")[0].strip()
        return f"</{cmd.qualified_name}:{cmd_id}> - {desc}"

    def get_cog_commands(self, cog_name: str) -> str:
        cog = self.ctx.bot.get_cog(cog_name)
        if not cog: return " "
        
        cmd_list = []
        for cmd in cog.get_commands():
            if cmd.hidden: continue
            
            if isinstance(cmd, commands.Group):
                subcmds = [child for child in cmd.walk_commands() if not child.hidden and not (isinstance(child, commands.Group) and child.commands)]
                if subcmds:
                    for child in subcmds:
                        root_name = cmd.name
                        cmd_id = self.app_commands.get(root_name, 0)
                        desc = child.description or child.help or "No description provided."
                        desc = desc.split("\n")[0].strip()
                        cmd_list.append(f"</{child.qualified_name}:{cmd_id}> - {desc}")
                else:
                    root_name = cmd.name
                    cmd_id = self.app_commands.get(root_name, 0)
                    desc = cmd.description or cmd.help or "No description provided."
                    desc = desc.split("\n")[0].strip()
                    cmd_list.append(f"</{cmd.qualified_name}:{cmd_id}> - {desc}")
            else:
                root_name = cmd.name
                cmd_id = self.app_commands.get(root_name, 0)
                desc = cmd.description or cmd.help or "No description provided."
                desc = desc.split("\n")[0].strip()
                cmd_list.append(f"</{cmd.qualified_name}:{cmd_id}> - {desc}")
        
        return "\n".join(cmd_list) if cmd_list else " "

    def _create_container(self, page_index: int, include_dropdown: bool = False) -> discord.ui.Container:
        
        data = self.page_data[page_index]
        layout = data.get("layout", {})
        
        items = []

        header_text = layout.get("header", data.get("title", "") if page_index == 0 else "")
        header = self.format_text(header_text)
        subheader = self.format_text(layout.get("subheader", ""))
        thumb_url = self.format_text(layout.get("thumbnail", ""))
        
        if header:
            content = f"### {header}"
            if subheader:
                content += f"\n{subheader}"
            
            if thumb_url and page_index != 0:
                items.append(discord.ui.Section(
                    discord.ui.TextDisplay(content=content),
                    accessory=discord.ui.Thumbnail(media=thumb_url)
                ))
            else:
                items.append(discord.ui.TextDisplay(content=content))

        desc = self.format_text(layout.get("description", ""))
        if desc:
            if thumb_url and page_index == 0:
                items.append(discord.ui.Section(
                    discord.ui.TextDisplay(content=desc),
                    accessory=discord.ui.Thumbnail(media=thumb_url)
                ))
            else:
                items.append(discord.ui.TextDisplay(content=desc))

        sections = layout.get("sections", [])
        for section in sections:
            title = self.format_text(section.get("title", ""))
            content = self.format_text(section.get("content", ""))
            
            block_content = ""
            if title: 
                if page_index == 0:
                    block_content += f"**{title}**\n"
                else:
                    block_content += f"**{title}**\n\n"
            if content: 
                block_content += f"{content}\n"
            
            if block_content:
                items.append(discord.ui.TextDisplay(content=block_content))

        if include_dropdown and self.dropdown:
            items.append(discord.ui.ActionRow(self.dropdown))

        footer_text = self.format_text(layout.get("footer_text", ""))
        if not footer_text:
             footer_text = f"Powered By {self.ctx.bot.user.name} Devs"
        
        items.append(discord.ui.Separator())
        items.append(discord.ui.TextDisplay(content=f"-# {footer_text}"))

        return discord.ui.Container(*items, accent_colour=config.default_color)

    async def send_ephemeral_page(self, interaction: discord.Interaction, page_number: int):
        container = self._create_container(page_number, include_dropdown=False)
        view = discord.ui.LayoutView()
        view.add_item(container)
        if interaction.response.is_done():
            await interaction.followup.send(view=view, ephemeral=True)
        else:
            await interaction.response.send_message(view=view, ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    async def on_timeout(self):
        try:
            if self.message:
                self.clear_items()
                if self.dropdown:
                    self.dropdown.disabled = True
                
                container = self._create_container(0, include_dropdown=True)
                self.add_item(container)
                await self.message.edit(view=self, allowed_mentions=discord.AllowedMentions.none())
        except:
            pass

    async def start(self):
        container = self._create_container(0, include_dropdown=True)
        self.add_item(container)

        self.message = await self.ctx.reply(view=self)

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.module_regex = re.compile(r'\{module:(.*?)\}')
        
        try:
            with open(help_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.page_data = data.get("pages", [])
        except Exception as e:
            self.page_data = []

    async def get_replacements(self, ctx):
        total_channels = sum(len(guild.channels) for guild in ctx.bot.guilds)
        invite_url = discord.utils.oauth_url(ctx.bot.user.id, permissions=discord.Permissions(8), scopes=("bot", "applications.commands"))
        
        display_prefix = ctx.prefix or config.default_prefix
        if display_prefix.startswith('<@') and str(ctx.bot.user.id) in display_prefix:
            display_prefix = config.default_prefix

        return {
            "{bot:name}": ctx.bot.user.name,
            "{bot:id}": str(ctx.bot.user.id),
            "{bot:avatar}": ctx.bot.user.display_avatar.url,
            "{bot:mention}": ctx.bot.user.mention,
            "{bot:channels}": str(total_channels),
            "{bot:commands}": str(len([cmd for cmd in self.bot.walk_commands() if cmd.cog is not None])),
            "{bot:invite}": invite_url,
            "{bot:support}": config.support_url,
            "{bot:website}": config.website,
            "{server:name}": ctx.guild.name,
            "{server:id}": str(ctx.guild.id),
            "{server:members}": str(ctx.guild.member_count),
            "{server:owner}": str(ctx.guild.owner),
            "{server:prefix}": display_prefix,
            "{user:name}": ctx.author.name,
            "{user:mention}": ctx.author.mention,
            "{user:id}": str(ctx.author.id),
            "{user:avatar}": ctx.author.display_avatar.url,
            "{user:created_at}": ctx.author.created_at.strftime("%Y-%m-%d"),
        }

    async def get_app_commands(self, ctx: commands.Context) -> dict:
        if hasattr(self.bot, "_app_commands_cache") and self.bot._app_commands_cache:
            return self.bot._app_commands_cache

        cache = {}
        try:
            for cmd in self.bot.tree.get_commands():
                cmd_id = getattr(cmd, "id", None)
                if cmd_id:
                    cache[cmd.name] = cmd_id

            global_cmds = await self.bot.tree.fetch_commands()
            for c in global_cmds:
                cache[c.name] = c.id
        except Exception:
            pass

        if ctx.guild:
            try:
                guild_cmds = await self.bot.tree.fetch_commands(guild=ctx.guild)
                for c in guild_cmds:
                    cache[c.name] = c.id
            except Exception:
                pass

        if cache:
            self.bot._app_commands_cache = cache

        return cache

    @commands.hybrid_command(name="help", aliases=["h"], description="Shows the bot's help guide.")
    @discord.app_commands.describe(context="A specific command or group to get details on.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def help(self, ctx: commands.Context, *, context: str | None = None):
        await ctx.defer()
        if context:
            cmd = self.bot.get_command(context)
            
            if not cmd:
                return await send_error_embed(ctx, f"No command or group found named `{context}`.")
            
            original_cmd = ctx.command
            ctx.command = cmd
            
            try:
                if isinstance(cmd, commands.Group):
                    await send_subcommand_help(ctx)
                else:
                    error_cog = self.bot.get_cog("UniversalErrorHandler")
                    if error_cog:
                        await error_cog.send_usage_embed(ctx)
                    else:
                        await send_error_embed(ctx, "Usage handler is currently unavailable.")
            finally:
                ctx.command = original_cmd
            return
        
        page_data = self.page_data
        
        if not page_data:
            return await send_error_embed(ctx, "The help guide is currently unavailable.")
        
        replacements = await self.get_replacements(ctx)
        app_commands = await self.get_app_commands(ctx)
        view = HelpView(ctx, page_data, replacements, self.module_regex, app_commands)
        await view.start()

async def setup(bot):
    await bot.add_cog(Help(bot))