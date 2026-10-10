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
from discord.ext        import commands
import random
from lavalink.filters   import (Equalizer, Karaoke, Timescale, 
                               Tremolo, Vibrato, Rotation, 
                               Distortion, ChannelMix, LowPass)

from utils.success_send import send_success_message
from utils.send_errors  import send_error_embed
from utils.subcmds      import send_subcommand_help
from utils.bl_ignore    import bl_ignore_check
from music              import requires_voice

FILTER_LABELS = {
    "bassboost":  "Bassboost ✨",
    "nightcore":  "Nightcore ✨",
    "vaporwave":  "Vaporwave ✨",
    "karaoke":    "Karaoke",
    "timescale":  "Timescale ✨",
    "tremolo":    "Tremolo",
    "vibrato":    "Vibrato",
    "rotation":   "Rotation",
    "distortion": "Distortion 💥",
    "channelmix": "Channel Mix",
    "lowpass":    "Low Pass",
    "pop":        "Pop ✨",
    "radio":      "Radio",
    "soft":       "Soft"
}

class FilterSelect(discord.ui.Select):
    def __init__(self, view_ref):
        self.view_ref = view_ref
        custom_filters = view_ref.player.fetch('custom_filters') or {}

        options = []
        for key, label in FILTER_LABELS.items():
            active = custom_filters.get(key, False)
            options.append(discord.SelectOption(
                label=label,
                value=key,
                description="⤷ Filter is enabled" if active else "⤷ Filter is disabled",
                emoji="<:wccheckmark:1556658412106817567>" if active else "<:space:1556658570198515804>",
            ))

        super().__init__(
            placeholder="» Select filters to toggle",
            min_values=1,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        custom_filters = self.view_ref.player.fetch('custom_filters') or {}

        for name in self.values:
            if name in custom_filters:
                del custom_filters[name]
            else:
                custom_filters[name] = True

        self.view_ref.player.store('custom_filters', custom_filters)
        await self.view_ref.cog.update_filters(self.view_ref.player)

        self.view_ref.update_components()
        await interaction.response.edit_message(view=self.view_ref)

class FilterView(discord.ui.LayoutView):
    def __init__(self, cog, player, user: discord.Member, ctx=None):
        super().__init__(timeout=120)
        self.cog = cog
        self.player = player
        self.user = user
        self.ctx = ctx
        self.message = None
        self.update_components()

    def update_components(self):
        self.clear_items()
        container = self.build_container()
        self.add_item(container)

    def build_container(self) -> discord.ui.Container:
        items = []
        custom_filters = self.player.fetch('custom_filters') or {}
        active = [FILTER_LABELS[k] for k, v in custom_filters.items() if v]
        count = len(active)

        header = discord.ui.TextDisplay(
            content="### Toggle Music Filters <:duration:1556658117750693949>"
        )
        items.append(header)

        desc = (
            "**Toggle Music filters based on your Mood !**\n"
            "**<:space:1556658570198515804> ⤷ Reset filters using the Reset Button !**\n"
            "**<:space:1556658570198515804> ⤷ Use Surprise Me Button & Vibe !**"
        )
        items.append(discord.ui.TextDisplay(content=desc))
        items.append(discord.ui.Separator())

        if active:
            filters_text = ",\n".join(f"`{f}`" for f in active)
        else:
            filters_text = "`No filters enabled`"

        items.append(discord.ui.TextDisplay(content=f"**__Enabled Filters__ :**\n\n{filters_text}"))
        items.append(discord.ui.Separator())

        items.append(discord.ui.ActionRow(FilterSelect(self)))

        reset_btn = discord.ui.Button(
            label="Reset",
            emoji="<:delete:1556658174176665720>",
            style=discord.ButtonStyle.secondary,
            custom_id="filter_reset_btn"
        )
        surprise_btn = discord.ui.Button(
            label="Surprise Me",
            emoji="✨",
            style=discord.ButtonStyle.secondary,
            custom_id="filter_surprise_btn"
        )
        items.append(discord.ui.ActionRow(reset_btn, surprise_btn))

        items.append(discord.ui.Separator())
        items.append(discord.ui.TextDisplay(
            content=f"-# Requested By {self.user.display_name} | {count} Enabled"
        ))

        return discord.ui.Container(*items)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You can't use this menu.", ephemeral=True)
            return False

        if interaction.data and interaction.data.get("custom_id") == "filter_reset_btn":
            await self.handle_reset(interaction)
            return False

        if interaction.data and interaction.data.get("custom_id") == "filter_surprise_btn":
            await self.handle_surprise(interaction)
            return False

        return True

    async def handle_reset(self, interaction: discord.Interaction):
        self.player.store('custom_filters', {})
        await self.cog.update_filters(self.player)

        self.update_components()
        await interaction.response.edit_message(view=self)
        await send_success_message(self.ctx, "Filters Reset", "All audio filters have been disabled.")

    async def handle_surprise(self, interaction: discord.Interaction):
        pool = list(FILTER_LABELS.keys())
        count = random.randint(2, 4)
        picked = random.sample(pool, count)

        new_filters = {name: True for name in picked}
        self.player.store('custom_filters', new_filters)
        await self.cog.update_filters(self.player)

        labels = [f"`{FILTER_LABELS[k]}`" for k in picked]
        self.update_components()
        
        await interaction.response.edit_message(view=self)
        await send_success_message(interaction, "Surprise Filters", f"Randomly applied filters just for you `╰(*°▽°*)╯`")

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except Exception:
                pass
        self.stop()

class Filter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_player(self, guild_id: int):
        
        if not self.bot.lavalink:
            return None

        return self.bot.lavalink.player_manager.get(guild_id)

    async def update_filters(self, player):
        custom_filters = player.fetch('custom_filters') or {}

        if not custom_filters:
            
            for filter_key in list(player.filters.keys()):
                await player.remove_filter(filter_key)

            return await player.set_filters()

        for filter_key in list(player.filters.keys()):
            await player.remove_filter(filter_key)

        if custom_filters.get("bassboost"):
            eq = Equalizer()
            eq.update(bands=[(0, 0.25), (1, 0.20), (2, 0.15), (3, 0.10), (4, 0.05)])
            await player.set_filter(eq)

        elif custom_filters.get("pop"):
            eq = Equalizer()
            eq.update(bands=[(0, -0.05), (1, -0.05), (2, 0.05), (3, 0.10), (4, 0.15), (5, 0.15), (6, 0.10)])
            await player.set_filter(eq)

        elif custom_filters.get("soft"):
            eq = Equalizer()
            eq.update(bands=[(0, 0), (1, 0), (2, 0), (3, 0), (4, -0.05), (5, -0.10), (6, -0.15)])
            await player.set_filter(eq)

        elif custom_filters.get("radio"):
            eq = Equalizer()
            eq.update(bands=[(0, -0.25), (1, -0.25), (2, -0.25), (11, -0.25), (12, -0.25), (13, -0.25), (14, -0.25)])
            await player.set_filter(eq)

        if custom_filters.get("nightcore"):
            ts = Timescale()
            ts.update(speed=1.2, pitch=1.2, rate=1.0)
            await player.set_filter(ts)

        elif custom_filters.get("vaporwave"):
            ts = Timescale()
            ts.update(speed=0.8, pitch=0.8, rate=1.0)
            await player.set_filter(ts)

        elif custom_filters.get("timescale"):
            ts = Timescale()
            ts.update(speed=1.0, pitch=1.0, rate=1.0)
            await player.set_filter(ts)

        if custom_filters.get("karaoke"):
            k = Karaoke()
            k.update(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
            await player.set_filter(k)

        if custom_filters.get("tremolo"):
            t = Tremolo()
            t.update(frequency=2.0, depth=0.5)
            await player.set_filter(t)

        if custom_filters.get("vibrato"):
            v = Vibrato()
            v.update(frequency=2.0, depth=0.5)
            await player.set_filter(v)

        if custom_filters.get("rotation"):
            r = Rotation()
            r.update(rotation_hz=0.2)
            await player.set_filter(r)

        if custom_filters.get("distortion"):
            d = Distortion()
            d.update(sin_offset=0, sin_scale=0.2, cos_offset=0, cos_scale=0.2, tan_offset=0, tan_scale=0.2, offset=0.3, scale=0.5)
            await player.set_filter(d)

        if custom_filters.get("channelmix"):
            cm = ChannelMix()
            cm.update(left_to_left=1.0, left_to_right=0.0, right_to_left=0.0, right_to_right=1.0)
            await player.set_filter(cm)

        if custom_filters.get("lowpass"):
            lp = LowPass()
            lp.update(smoothing=20.0)
            await player.set_filter(lp)

        await player.set_filters()

    @commands.hybrid_group(name="filter", description="Apply or manage audio filters.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def filter(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await send_subcommand_help(ctx)

    @filter.command(name="toggle", description="Toggle audio filters with a dropdown menu.")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def filter_toggle(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)

        if not player or not player.current:
            return await send_error_embed(ctx, "No music is currently playing in the server.")

        view = FilterView(self, player, ctx.author, ctx)
        msg = await ctx.send(view=view)
        view.message = msg

    @filter.command(name="reset", description="Disables all active audio filters.")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def filter_reset(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)

        if not player or not player.current:
            return await send_error_embed(ctx, "No music is currently playing there.")
        
        player.store('custom_filters', {})
        await self.update_filters(player)

        await send_success_message(ctx, "Filters reset", "All audio filters have been disabled.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Filter(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
