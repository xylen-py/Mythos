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
import asyncio
import aiohttp
from lavalink          import DefaultPlayer, AudioTrack
from cogs.music        import format_duration, track_uri
from music             import sanitize_title, requires_voice
from typing            import Optional
from discord.ext       import commands
from utils.send_errors import send_error_embed
from utils.bl_ignore   import bl_ignore_check
from config            import default_color
from dataclasses       import dataclass

@dataclass
class TrackLyrics:
    lines: list
    synced: bool

    @classmethod
    def from_raw(cls, data: dict) -> Optional["TrackLyrics"]:
        if not data or not data.get("lines"):
            return None
            
        lines_data = data["lines"]
            
        if data.get("type") == "timed":
            lines = []

            for entry in lines_data:
                timestamp, text = entry.get("range", {}).get("start", 0), entry.get("line", "")
                
                if text:
                    lines.append((timestamp, text))

            return cls(lines, synced=True)
            
        lines = [entry.get("line", "") for entry in lines_data if entry.get("line")]
        return cls(lines, synced=False)

class LyricsView(discord.ui.LayoutView):
    def __init__(self, cog, player: DefaultPlayer, track: AudioTrack, lines, user, synced: bool = True):
        super().__init__(timeout=180 if synced else 120)
        self.cog = cog
        self.player = player
        self.track = track
        self.lines = lines
        self.user = user
        self.synced = synced
        self.msg = None
        self.last_index = -1
        self._task = None
        
        if self.synced:
            self.update_components()
        else:
            self.build_static()

    def build_layout(self, lyrics: str):
        items = []

        header_text = (
            f"### <:lyrics:1556658278912622674> __{'Synced Lyrics' if self.synced else 'Lyrics'}__\n"
            f"**[{sanitize_title(self.track.title)}]({track_uri(self.track)})** - [{sanitize_title(self.track.author)}]({track_uri(self.track)})\n"
            f"Duration: `{format_duration(self.track.duration)}`\n"
        )

        header = discord.ui.TextDisplay(content=header_text)
        
        if self.track.artwork_url:
            header = discord.ui.Section(
                header,
                accessory=discord.ui.Thumbnail(media=self.track.artwork_url)
            )

        items.append(header)
        items.append(discord.ui.TextDisplay(content=lyrics))
        items.append(discord.ui.Separator())
        
        footer = discord.ui.TextDisplay(content=f"-# Requested by {self.user.mention} (`{self.user.name}`)")
        
        if self.synced:
            footer = discord.ui.Section(
                footer,
                accessory=discord.ui.Button(emoji="<:delete:1556658174176665720>", style=discord.ButtonStyle.secondary, custom_id="lyrics_stop_btn")
            )
            
        items.append(footer)

        self.add_item(discord.ui.Container(*items, accent_colour=default_color))

    def build_static(self):
        if not self.lines:
            return self.build_layout("*No lyrics available for this track.*")
            
        lyrics = ""
        
        for line in self.lines:
            if len(lyrics) + len(line) > 3900:
                break

            lyrics += f"{line}\n"

        self.build_layout(lyrics.strip())

    def update_components(self, current_index=0):
        self.clear_items()
        
        if not self.lines:
            return self.build_layout("*No synced lyrics available.*")

        start = max(0, min(current_index - 7, len(self.lines) - 14))
        end = min(len(self.lines), start + 14)

        window = []

        for i in range(start, end):
            text = self.lines[i][1].strip() or "♪"
            window.append(f"**» {text}**" if i == current_index else f"-# ~~{text}~~" if i < current_index else f"-# {text}")

        self.build_layout("\n".join(window))

    def get_current_index(self):
        if not self.synced:
            return 0

        current = 0
        
        for i, (ts_ms, _) in enumerate(self.lines):
            if ts_ms <= self.player.position:
                current = i
                
            elif ts_ms > self.player.position:
                break

        return current

    async def start_updates(self):
        if self.synced:
            self._task = asyncio.create_task(self._update_loop())

    async def _update_loop(self):
        try:
            while not self.is_finished():
                if not self.player or not self.player.current:
                    break

                idx = self.get_current_index()
                
                if idx != self.last_index:
                    self.last_index = idx
                    self.update_components(idx)

                    try:
                        await self.msg.edit(view=self, allowed_mentions=discord.AllowedMentions.none())
                    except Exception:
                        break

                if idx + 1 < len(self.lines):
                    next_ts = self.lines[idx + 1][0]
                    sleep_ms = next_ts - self.player.position
                    
                    if sleep_ms > 0:
                        await asyncio.sleep(min(sleep_ms / 1000.0, 0.5))
                    else:
                        await asyncio.sleep(0.1)
                else:
                    break
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You can't use this menu.", ephemeral=True)
            return False

        if interaction.data and interaction.data.get("custom_id") == "lyrics_stop_btn":
            await self.on_timeout()
            return False

        return True

    async def on_timeout(self):
        if self._task:
            self._task.cancel()

        if self.msg:
            try:
                await self.msg.delete()
            except Exception:
                pass

        self.stop()

class Lyrics(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_lyrics = {}

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session

    def cog_unload(self):
        for guild_id, view in self.active_lyrics.items():
            try:
                if hasattr(view, '_task') and view._task:
                    view._task.cancel()
                view.stop()
            except Exception:
                pass

    def get_player(self, guild_id: int) -> Optional[DefaultPlayer]:

        if not self.bot.lavalink:
            return None

        return self.bot.lavalink.player_manager.get(guild_id)

    @commands.hybrid_command(name="lyrics", description="Get lyrics for the currently playing track.")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lyrics(self, ctx: commands.Context | discord.Interaction):
        if isinstance(ctx, discord.Interaction):
            if not ctx.response.is_done():
                await ctx.response.defer()
            
        if not isinstance(ctx, discord.Interaction):
            await ctx.defer()
            
        author = ctx.user if isinstance(ctx, discord.Interaction) else ctx.author
        send_method = ctx.followup.send if isinstance(ctx, discord.Interaction) else ctx.send
            
        player = self.get_player(ctx.guild.id)

        if not player or not player.current:
            return await send_error_embed(ctx, "No music is currently playing in the server.")

        data = await player.node.request("GET", f"sessions/{player.node.session_id}/players/{ctx.guild.id}/lyrics")
        parsed_lyrics = TrackLyrics.from_raw(data if isinstance(data, dict) else None)

        if not parsed_lyrics or not parsed_lyrics.lines:
            return await send_error_embed(ctx, f"No lyrics found for **{player.current.title}** by **{player.current.author}**.")

        existing = self.active_lyrics.get(ctx.guild.id)
        
        if existing:
            try:
                if hasattr(existing, '_task') and existing._task:
                    existing._task.cancel()
                    
                existing.stop()
                
                if existing.msg:
                    await existing.msg.delete()

            except Exception:
                pass

            self.active_lyrics.pop(ctx.guild.id, None)

        is_synced = parsed_lyrics.synced
        view = LyricsView(self, player, player.current, parsed_lyrics.lines, author, synced=is_synced)
        msg = await send_method(view=view, allowed_mentions=discord.AllowedMentions.none())
        view.msg = msg
        self.active_lyrics[ctx.guild.id] = view
        
        if is_synced:
            await view.start_updates()

async def setup(bot: commands.Bot):
    await bot.add_cog(Lyrics(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
