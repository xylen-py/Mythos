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
from discord.ext        import commands, tasks
from discord            import app_commands
import re
import random
import asyncio
import urllib.parse
import lavalink
from typing             import cast, Optional, Sequence
from collections        import deque
import itertools
from lavalink           import DefaultPlayer, AudioTrack
from lavalink.events    import TrackStartEvent, TrackEndEvent, QueueEndEvent
from lavalink.server    import LoadType
from music              import sanitize_title, update_vc_status, requires_voice, LavalinkVoiceClient
from config             import default_color, support_url, source_emojis, default_source, nodes
from utils.success_send import send_success_message
from utils.send_errors  import send_error_embed
from utils.bl_ignore    import bl_ignore_check
from utils.is_owner     import SilentNotOwner
from utils.paginators   import Paginator

SourceMap = {
    "music.youtube": "ytsearch",
    "youtube":       "ytsearch",
    "youtu.be":      "ytsearch",
    "spotify":       "spsearch",
    "soundcloud":    "scsearch",
    "apple":         "amsearch",
    "deezer":        "dzsearch",
    "jiosaavn":      "jssearch",
    "gaana":         "gnsearch",
    "amazon":        "azsearch",
    "pandora":       "pdsearch"
}

DefaultEmoji = "<:ztunes:1556658555581628518>"

def get_source_emoji(uri: str) -> str:
    uri_lower = uri.lower()
    return next((source_emojis.get(code, " ") for key, code in SourceMap.items() if key in uri_lower), DefaultEmoji)

def track_uri(track: AudioTrack) -> str:
    return track.uri or f"https://soundcloud.com/search?q={urllib.parse.quote(track.title)}"

Intervals = {
    'd': 86400, 
    'h': 3600, 
    'm': 60, 
    's': 1
}

def format_duration(time: int, clock: bool = False) -> str:
    if not time:
        return "Live"
        
    seconds = time // 1000
    
    if clock:
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        
        if hrs > 0:
            return f"{int(hrs)}:{int(mins):02d}:{int(secs):02d}"
            
        return f"{int(mins)}:{int(secs):02d}"

    parts = []
    
    for suffix, count in Intervals.items():
        value, seconds = divmod(seconds, count)
        
        if value:
            parts.append(f"{int(value):02d}{suffix}" if suffix == 's' and parts else f"{int(value)}{suffix}")
            
    return " ".join(parts) or "0s"

def format_bytes(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024.0:
            return f"{size:.2f} {unit}"
        
        size /= 1024.0

    return f"{size:.2f} PB"

async def send_response(
    interaction: discord.Interaction, 
    text: str, 
    *,
    error: bool = False,
    ephemeral: bool = False,
    delete_after: Optional[int] = None
):
    view = discord.ui.LayoutView()
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"{'<:wccrossmar:1556658451021701167>' if error else '<:wccheckmark:1556658412106817567>'} {text}"),
        discord.ui.Separator(),
        discord.ui.TextDisplay(content=f"-# Action by {interaction.user.mention} (`{interaction.user.name}`)"),
        accent_colour=discord.Colour(0xBD3B3B) if error else discord.Colour(0x2B764A)
    )
    view.add_item(container)
    
    if not interaction.response.is_done():
        return await interaction.response.send_message(
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
            ephemeral=ephemeral,
            delete_after=delete_after
        )
        
    msg = await interaction.followup.send(
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
        ephemeral=ephemeral,
        wait=True
    )

    if delete_after:
        await msg.delete(delay=delete_after)

class MusicControls(discord.ui.LayoutView):
    def __init__(self, bot, player, track=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.player = player
        self.track = track or player.current
        self.build_components()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False

        vc = guild.voice_client
        
        if not vc:
            await send_response(interaction, "No active music session.", error=True, ephemeral=True)
            return False

        if interaction.user.voice and interaction.user.voice.channel == vc.channel:
            return True

        await send_response(interaction, "You must be in the same voice channel as the bot.", error=True, ephemeral=True)
        return False

    def build_components(self):
        self.clear_items()

        track = self.track or self.player.current
        if not track:
            return

        author_name = track.author or "Unknown Author"
        source_icon = get_source_emoji(track.uri)

        requester = self.bot.get_user(track.requester) if track.requester else None
        requester_text = f"({requester.mention})" if requester else f"({self.bot.user.mention})"
        thumb_url = track.artwork_url or (self.bot.user.display_avatar.url)

        section_body = discord.ui.TextDisplay(
            content=(
                f"**[Now Playing]({support_url})** <:highquality:1556658386039472220>\n\n"
                f"{source_icon} **[{sanitize_title(track.title)}]({track_uri(track)})** - [{sanitize_title(author_name)}]({track_uri(track)})\n"
                f"Duration: `{format_duration(track.duration)}`\n"
                f"-# Requested by {requester_text}"
            )
        )
        section = discord.ui.Section(section_body, accessory=discord.ui.Thumbnail(media=thumb_url))

        has_history = len(self.player.history) > 0
        is_paused = self.player.paused

        btn_prev = discord.ui.Button(emoji="<:previous:1556658319438123050>", style=discord.ButtonStyle.secondary)
        btn_prev.callback = self.previous
        btn_prev.disabled = not has_history

        btn_playpause = discord.ui.Button(
            emoji="<:play:1556658516159369257>" if is_paused else "<:pause:1556658148276830360>", 
            style=discord.ButtonStyle.secondary
        )
        btn_playpause.callback = self.play_pause

        btn_next = discord.ui.Button(emoji="<:next:1556658637013917863>", style=discord.ButtonStyle.secondary)
        btn_next.callback = self.skip

        btn_lyrics = discord.ui.Button(emoji="<:lyrics:1556658278912622674>", style=discord.ButtonStyle.secondary)
        btn_lyrics.callback = self.show_lyrics

        btn_stop = discord.ui.Button(emoji="<:stop:1556658583041744967>", style=discord.ButtonStyle.danger)
        btn_stop.callback = self.disconnect

        btn_loop = discord.ui.Button(emoji="<:loop:1556658528918315051>", label="Loop", style=discord.ButtonStyle.secondary)
        btn_loop.callback = self.loop

        btn_shuffle = discord.ui.Button(emoji="<:shuffle:1556658226010001488>", label="Shuffle", style=discord.ButtonStyle.secondary)
        btn_shuffle.callback = self.shuffle_queue

        btn_autoplay = discord.ui.Button(emoji="<:replay:1556658212483375116>", label="Autoplay", style=discord.ButtonStyle.secondary)
        btn_autoplay.callback = self.autoplay

        row0 = discord.ui.ActionRow(btn_prev, btn_playpause, btn_next, btn_lyrics, btn_stop)
        row1 = discord.ui.ActionRow(btn_loop, btn_shuffle, btn_autoplay)

        container = discord.ui.Container(
            section, discord.ui.Separator(visible=False), discord.ui.Separator(visible=False), row0, row1,
            accent_colour=default_color
        )

        self.add_item(container)

    async def previous(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not self.player.history:
            return await send_response(interaction, "No previous track in history.", error=True, ephemeral=True, delete_after=7)

        try:
            previous_track = self.player.history.pop()

            if self.player.current:
                self.player.current.extra['_skip_history'] = True
                self.player.add(self.player.current, requester=self.player.current.requester, index=0)

            self.player.add(previous_track, requester=previous_track.requester, index=0)
            await self.player.skip()

        except Exception:
            pass

    async def play_pause(self, interaction: discord.Interaction):
        await self.player.set_pause(not self.player.paused)
        self.build_components()
        await interaction.response.edit_message(view=self, allowed_mentions=discord.AllowedMentions.none())
        await send_response(interaction, f"Playback {'paused' if self.player.paused else 'resumed'} successfully.")

    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.player.skip()
        await send_response(interaction, "Skipped the current track.", delete_after=10)

    async def show_lyrics(self, interaction: discord.Interaction):
        lyrics_cog = self.bot.get_cog("Lyrics")

        if not lyrics_cog:
            return await send_response(interaction, "Lyrics system is not available.", error=True, ephemeral=True)
            
        try:
            await lyrics_cog.lyrics(interaction)
        except Exception:
            pass

    async def loop(self, interaction: discord.Interaction):
        loop_map = {
            self.player.LOOP_NONE: (self.player.LOOP_SINGLE, "Track Loop"),
            self.player.LOOP_SINGLE: (self.player.LOOP_QUEUE, "Queue Loop"),
            self.player.LOOP_QUEUE: (self.player.LOOP_NONE, "Disabled")
        }
        new_loop, state = loop_map.get(self.player.loop, (self.player.LOOP_NONE, "Disabled"))
        
        self.player.set_loop(new_loop)
        await send_response(interaction, f"Loop mode set to **{state}**.", delete_after=7)

    async def disconnect(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = self.bot.get_guild(self.player.guild_id)

        if guild and guild.voice_client:
            player_cog = self.bot.get_cog("MusicControls")
            
            if player_cog and player_cog.voice_247.get(guild.id) == guild.voice_client.channel.id:
                return await send_response(interaction, "I cannot leave a designated 24/7 voice channel.", error=True, ephemeral=True, delete_after=7)
                
            await guild.voice_client.disconnect(force=True)

        await delete_controller(self.player)
        await self.player.stop()
        await send_response(interaction, "Disconnected from the voice channel.", delete_after=7)

    async def autoplay(self, interaction: discord.Interaction):
        self.player.autoplay = not self.player.autoplay
        await send_response(interaction, f"Autoplay has been **{'enabled' if self.player.autoplay else 'disabled'}**.", delete_after=7)

    async def shuffle_queue(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        if not self.player.queue or len(self.player.queue) < 2:
            return await send_response(interaction, "Cannot shuffle the queue with less than 2 tracks.", error=True, ephemeral=True, delete_after=7)

        random.shuffle(self.player.queue)
        await send_response(interaction, "Queue has been shuffled.", delete_after=7)

async def delete_controller(player):
    if player.controller:
        try:
            await player.controller.delete()
        except:
            pass
        player.controller = None

async def resolve_stage(guild: discord.Guild):
    if guild.me.voice:
        try:
            await guild.me.edit(suppress=False)
        except Exception:
            try:
                await guild.me.request_to_speak()
            except Exception:
                pass

class QueueTrackSelect(discord.ui.Select):
    def __init__(self, player, chunks):
        self.player = player
        self.chunks = chunks
        self.track_map = {}

        options = []
        for j, track in enumerate(chunks[0]):
            label = sanitize_title(track.title)[:100]
            options.append(discord.SelectOption(label=label, value=str(j), description=f"#{j + 1} in queue"))
            self.track_map[str(j)] = j

        super().__init__(placeholder="⤷ Select for PlayNext", options=options, row=1)

    def update_page(self, page: int):
        self.track_map.clear()
        self.options.clear()

        chunk = self.chunks[page] if page < len(self.chunks) else []
        offset = page * len(self.chunks[0]) if self.chunks else 0

        for j, track in enumerate(chunk):
            absolute_index = offset + j
            label = sanitize_title(track.title)[:100]
            self.options.append(discord.SelectOption(label=label, value=str(absolute_index), description=f"#{absolute_index + 1} in queue"))
            self.track_map[str(absolute_index)] = absolute_index

    async def callback(self, interaction: discord.Interaction):
        index = self.track_map.get(self.values[0])

        if index is None or index >= len(self.player.queue):
            return await send_error_embed(interaction, "That track is no longer in the queue.")

        track = self.player.queue.pop(index)
        self.player.queue.insert(0, track)
        await send_success_message(interaction, "Track Moved", f"Moved [`{sanitize_title(track.title)}`]({track_uri(track)}) to play next.")

class HistoryTrackSelect(discord.ui.Select):
    def __init__(self, player, chunks):
        self.player = player
        self.chunks = chunks
        self.track_map = {}

        options = []
        for j, track in enumerate(chunks[0]):
            label = sanitize_title(track.title)[:100]
            options.append(discord.SelectOption(label=label, value=str(j), description=f"#{j + 1} in history"))
            self.track_map[str(j)] = track

        super().__init__(placeholder="⤷ Select to add to Queue", options=options, row=1)

    def update_page(self, page: int):
        self.track_map.clear()
        self.options.clear()

        chunk = self.chunks[page] if page < len(self.chunks) else []
        offset = page * len(self.chunks[0]) if self.chunks else 0

        for j, track in enumerate(chunk):
            absolute_index = offset + j
            label = sanitize_title(track.title)[:100]
            self.options.append(discord.SelectOption(label=label, value=str(absolute_index), description=f"#{absolute_index + 1} in history"))
            self.track_map[str(absolute_index)] = track

    async def callback(self, interaction: discord.Interaction):
        track = self.track_map.get(self.values[0])

        if track is None:
            return await send_error_embed(interaction, "That track is no longer available.")

        self.player.add(track, requester=interaction.user.id)

        if not self.player.is_playing:
            await self.player.play()

        await send_success_message(interaction, "Track Added", f"Added [`{sanitize_title(track.title)}`]({track_uri(track)}) to the queue.")

class AddedToQueueControls(discord.ui.LayoutView):
    def __init__(self, player, track, section, is_first: bool):
        super().__init__(timeout=180)
        self.player = player
        self.track = track
        self.btn_next = None
        self.btn_remove = None

        items = [section]

        if not is_first:
            play_next_disabled = len(player.queue) <= 1
            self.btn_next = discord.ui.Button(label="Play Next", style=discord.ButtonStyle.secondary, disabled=play_next_disabled, emoji="<:next:1493501040585347112>")
            self.btn_next.callback = self.play_next
            
            self.btn_remove = discord.ui.Button(label="Remove", style=discord.ButtonStyle.red, emoji="<:remove:1495162872240537690>")
            self.btn_remove.callback = self.remove
            
            items.append(discord.ui.Separator(visible=False))
            items.append(discord.ui.ActionRow(self.btn_next, self.btn_remove))

        container = discord.ui.Container(*items, accent_colour=default_color)
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            return False

        vc = guild.voice_client
        if not vc:
            await send_response(interaction, "No active music session.", error=True, ephemeral=True)
            return False

        if interaction.user.voice and interaction.user.voice.channel == vc.channel:
            return True

        await send_response(interaction, "You must be in the same voice channel as the bot.", error=True, ephemeral=True)
        return False

    async def play_next(self, interaction: discord.Interaction):
        try:
            idx = self.player.queue.index(self.track)
            self.player.queue.pop(idx)
            self.player.queue.insert(0, self.track)
            await send_success_message(interaction, "Track Moved", f"Moved [`{sanitize_title(self.track.title)}`]({track_uri(self.track)}) to play next.")
            
            self.btn_next.disabled = True
            await interaction.message.edit(view=self, allowed_mentions=discord.AllowedMentions.none())
        except ValueError:
            await send_error_embed(interaction, "That track is no longer in the queue.")

    async def remove(self, interaction: discord.Interaction):
        try:
            idx = self.player.queue.index(self.track)
            self.player.queue.pop(idx)
            await interaction.message.delete()
        except ValueError:
            await send_error_embed(interaction, "That track is no longer in the queue.")

class CustomPlayer(DefaultPlayer):
    def __init__(self, guild_id, node):
        super().__init__(guild_id, node)
        self.history: deque[AudioTrack] = deque(maxlen=50)
        self.autoplay: bool = False
        self.channel: Optional[discord.abc.GuildChannel] = None
        self.controller: Optional[discord.Message] = None

    @property
    def recents(self) -> Sequence[AudioTrack]:
        combined = list(self.history) + self.queue[:50]

        if self.current:
            combined.append(self.current)
            
        return combined

    def add_history(self, track: AudioTrack):
        if track.extra.pop('_skip_history', False):
            return
            
        for existing in [t for t in self.history if t.identifier == track.identifier]:
            self.history.remove(existing)

        self.history.append(track)

    def is_duplicate(self, track: AudioTrack) -> bool:
        if not track.identifier:
            return False
            
        return any(track.identifier == t.identifier for t in self.recents)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'lavalink'):
            bot.lavalink = lavalink.Client(bot.user.id, player=CustomPlayer)

            for identifier, config in nodes.items():
                bot.lavalink.add_node(
                    host=config["host"], 
                    port=config["port"], 
                    password=config["password"], 
                    region='us', 
                    name=config.get("identifier", identifier), 
                    ssl=config.get("secure", False)
                )

        self.bot.lavalink = cast(lavalink.Client, self.bot.lavalink)
        self.bot.lavalink.add_event_hooks(self)
        self.url_rx = re.compile(r'https?://(?:www\.)?.+')
        self.deezer_rx = re.compile(r'https?://(?:www\.)?deezer\.com/(?:[a-zA-Z]+/)?track/[0-9]+')
        self.spotify_rx = re.compile(r'https?://(?:open\.)?spotify\.com/track/[a-zA-Z0-9]+')
        self.youtube_rx = re.compile(r'https?://(?:(?:www\.)?youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+')
        self.saavn_rx = re.compile(r'https?://(?:www\.)?jiosaavn\.com/song/.+')
        self.check_247.start()

    def cog_unload(self):
        self.check_247.cancel()

        if self.bot.lavalink:
            self.bot.lavalink._event_hooks.clear()

    def get_player(self, guild_id: int) -> Optional[CustomPlayer]:
        
        if not self.bot.lavalink:
            return None
        
        return self.bot.lavalink.player_manager.get(guild_id)

    @tasks.loop(minutes=5)
    async def check_247(self):
        await self.bot.wait_until_ready()
        player_cog = self.bot.get_cog("MusicControls")

        if not player_cog:
            return

        for guild_id, channel_id in list(player_cog.voice_247.items()):
            try:
                guild = self.bot.get_guild(guild_id)
                if not guild: 
                    continue
                
                channel = guild.get_channel(channel_id)
                if not channel: 
                    continue
                
                vc = guild.voice_client
                
                if not vc:
                    try:
                        perms = channel.permissions_for(guild.me)
                        if not perms.connect or not perms.speak:
                            continue
                            
                        await channel.connect(cls=LavalinkVoiceClient, self_deaf=True)
                        player = self.bot.lavalink.player_manager.get(guild_id)

                        if player:
                            await update_vc_status(player, self.bot)

                    except:
                        pass
            except:
                pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        vc = member.guild.voice_client
        if not vc:
            return

        voice_channel = vc.channel
        if not voice_channel:
            return

        if before.channel != voice_channel:
            return

        if len([m for m in voice_channel.members if not m.bot]) == 0:
            player_cog = self.bot.get_cog("MusicControls")
            is_247 = player_cog and player_cog.voice_247.get(member.guild.id) == voice_channel.id
            player = self.get_player(member.guild.id)

            if player:
                was_playing = player.is_playing or len(player.queue) > 0
                player.autoplay = False
                await player.stop()
                player.queue.clear()
                await delete_controller(player)
                await update_vc_status(player, self.bot)
            
                if player.channel and was_playing:
                    variants = [
                        {
                            "title": "All By Myself!",
                            "desc": "Everyone left the voice channel, so I stopped the music.",
                            "footer": "-# It's lonely in here... 🥺"
                        },
                        {
                            "title": "The Audience Left!",
                            "desc": "The voice channel is empty! Playback has been halted.",
                            "footer": "-# Come back soon! 👋"
                        },
                        {
                            "title": "Silence Falls!",
                            "desc": "Waiting for someone to join the voice channel before resuming.",
                            "footer": "-# Eerily quiet... 🤫"
                        }
                    ]
                    
                    choice = random.choice(variants)
                    title, desc, footer = choice["title"], choice["desc"], choice["footer"]

                    items = [
                        discord.ui.TextDisplay(content=f"### {title}"),
                        discord.ui.Separator(visible=True),
                        discord.ui.TextDisplay(content=desc),
                        discord.ui.TextDisplay(content=footer)
                    ]

                    if support_url:
                        btn = discord.ui.Button(label="Support Server", emoji="<:dev:1495147599194488873>", url=support_url, style=discord.ButtonStyle.link)
                        items.append(discord.ui.ActionRow(btn))

                    container = discord.ui.Container(*items, accent_colour=None)
                    view = discord.ui.LayoutView()
                    view.add_item(container)
                    
                    await player.channel.send(view=view, allowed_mentions=discord.AllowedMentions.none())

            if not is_247:
                await vc.disconnect(force=True)

    @lavalink.listener(TrackEndEvent)
    async def on_track_end(self, event: TrackEndEvent):
        player = event.player

        if not player:
            return
        
        guild_id = player.guild_id
        await delete_controller(player)

        if event.track:
            player.add_history(event.track)

        await self.process_autoplay(player)
        await update_vc_status(player, self.bot)
        
        player_cog = self.bot.get_cog("MusicControls")
        is_247 = bool(player_cog and guild_id in player_cog.voice_247)

        if not is_247 and not player.is_playing and not player.queue:
            await asyncio.sleep(180)
            is_247 = bool(player_cog and guild_id in player_cog.voice_247)

            if not is_247 and player.is_connected and not player.is_playing and not player.queue:
                guild = self.bot.get_guild(guild_id)
                    
                if guild and guild.voice_client:
                    await guild.voice_client.disconnect(force=True)

    @lavalink.listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        player = event.player

        if not player:
            return
        
        self.bot.dispatch("track_start", player, event.track)
        await update_vc_status(player, self.bot)
        guild = self.bot.get_guild(player.guild_id)
        
        if guild and guild.me and guild.me.voice:
            if isinstance(guild.me.voice.channel, discord.StageChannel):
                await resolve_stage(guild)

        await delete_controller(player)

        try:
            if player.channel:
                view = MusicControls(self.bot, player, track=event.track)
                player.controller = await player.channel.send(view=view, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            pass

    @lavalink.listener(QueueEndEvent)
    async def on_queue_end(self, event: QueueEndEvent):
        player = event.player
        if not player:
            return
        
        await asyncio.sleep(5)
        if player.autoplay and player.history and not player.is_playing and not player.queue:
            return await self.process_autoplay(player)
        
        if player.channel and not player.is_playing and not player.queue:
            variants = [
                {
                    "title": "The Party's On Hold!",
                    "desc": "The current queue has dried up. Toss in more songs via `/play`!",
                    "footer": "-# Keep the vibes going! 🎵"
                },
                {
                    "title": "Out of Tunes?",
                    "desc": "Looks like we're out of music for now. Add your favorites with `/play`.",
                    "footer": "-# Don't let the music fade! 🎧"
                },
                {
                    "title": "Silence Has Arrived!",
                    "desc": "The playlist just ran out. Drop another beat using `/play`!",
                    "footer": "-# Need more melodies? 🎶"
                },
                {
                    "title": "Queue Depleted!",
                    "desc": "We've reached the end of the song list. Queue up the next hit with `/play`!",
                    "footer": "-# Ready for the next track! 🎸"
                },
                {
                    "title": "The Music Stopped... But It Doesn't Have To!",
                    "desc": "It's too quiet in here! Use `/play` to bring back the noise and keep the party alive.",
                    "footer": "-# Play on! 📻"
                },
                {
                    "title": "End of the Road!",
                    "desc": "We've played everything in the queue. Queue up something new with `/play`!",
                    "footer": "-# Let the rhythm flow! ✨"
                },
                {
                    "title": "The DJ is Resting!",
                    "desc": "All tracks have finished playing. Keep the music alive by dropping some more with `/play`.",
                    "footer": "-# What's next? 🎧"
                }
            ]
            
            choice = random.choice(variants)
            title, desc, footer = choice["title"], choice["desc"], choice["footer"]

            items = [
                discord.ui.TextDisplay(content=f"### {title}"),
                discord.ui.Separator(visible=True),
                discord.ui.TextDisplay(content=desc),
                discord.ui.TextDisplay(content=footer)
            ]

            if support_url:
                btn = discord.ui.Button(label="Support Server", emoji="<:dev:1495147599194488873>", url=support_url, style=discord.ButtonStyle.link)
                items.append(discord.ui.ActionRow(btn))

            container = discord.ui.Container(
                *items,
                accent_colour=None
            )

            view = discord.ui.LayoutView()
            view.add_item(container)

            await player.channel.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    async def process_autoplay(self, player):
        if len(player.queue) > 2 or not player.autoplay:
            return

        if not hasattr(player, 'used_autoplay_seeds'):
            player.used_autoplay_seeds = set()

        potential_seeds = itertools.chain([player.current] if player.current else [], reversed(player.history))
        seed = next((s for s in potential_seeds if s.identifier and s.identifier not in player.used_autoplay_seeds), None)
        seed_uri = seed.extra.get('original_uri', seed.uri) if seed else None
        
        if not seed_uri:
            return

        player.used_autoplay_seeds.add(seed.identifier)
        
        match True:
            case _ if self.spotify_rx.match(seed_uri):
                query = f"sprec:{seed.identifier}"
            case _ if self.youtube_rx.match(seed_uri):
                query = f"https://music.youtube.com/watch?v={seed.identifier}&list=RD{seed.identifier}"
            case _ if self.deezer_rx.match(seed_uri):
                query = f"dzrec:track={seed.identifier}"
            case _ if self.saavn_rx.match(seed_uri):
                query = f"jsrec:{seed.identifier}"
            case _ if seed.isrc:
                query = f"sprec:mix:isrc:{seed.isrc}"
            case _:
                query = None
                
        if not query:
            return
            
        try:
            res = await player.node.get_tracks(query)
        except Exception:
            return
            
        if not res or not res.tracks:
            return
            
        valid_tracks = [
            t for t in res.tracks 
            if t.identifier != seed.identifier and not player.is_duplicate(t)
        ]
        
        if not valid_tracks:
            return
            
        for track in random.sample(valid_tracks, min(3, len(valid_tracks))):
            if seed.extra.get('ztunes_id'):
                track = await self.ztunes.register(track)
                
            player.add(track, requester=seed.requester)

        if player.queue and not player.is_playing:
            await player.play()

    async def connect(self, ctx: commands.Context) -> Optional[CustomPlayer]:
        perms = ctx.author.voice.channel.permissions_for(ctx.guild.me)

        if not perms.connect:
            await send_error_embed(ctx, "I don't have Connect permission for that voice channel.")
            raise SilentNotOwner()
            
        if not isinstance(ctx.author.voice.channel, discord.StageChannel) and not perms.speak:
            await send_error_embed(ctx, "I don't have Speak permission in that voice channel.")
            raise SilentNotOwner()

        vc = ctx.guild.voice_client

        if vc and vc.channel == ctx.author.voice.channel:
            player = self.get_player(ctx.guild.id)

            if player:
                player.channel = ctx.channel

            return player
                
        if not vc:
            if ctx.guild.voice_client:
                try:
                    await ctx.guild.voice_client.disconnect(force=True)
                except Exception:
                    pass
                
            try:
                await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient, self_deaf=True)

                if isinstance(ctx.author.voice.channel, discord.StageChannel):
                    await resolve_stage(ctx.guild)

                player = self.get_player(ctx.guild.id)
                await update_vc_status(player, self.bot)
                
                if player:
                    player.channel = ctx.channel

                return player
            
            except (asyncio.CancelledError, asyncio.TimeoutError):
                await send_error_embed(ctx, f"Could not connect to {ctx.author.voice.channel.mention}. Voice connection timed out.")
                raise SilentNotOwner()
            
            except Exception as e:
                await send_error_embed(ctx, f"Failed to connect to {ctx.author.voice.channel.mention} due to an unexpected error.")
                raise SilentNotOwner()

        if isinstance(ctx.author.voice.channel, discord.StageChannel):
            await resolve_stage(ctx.guild)

        player = self.get_player(ctx.guild.id)

        if player:
            player.channel = ctx.channel

        return player
        
    @commands.hybrid_command(name="play", aliases=["p"], description="Plays a song or adds it to the queue.")
    @app_commands.describe(
        query="The song name or URL to play.",
        source="Search source to use (optional)."
    )
    @app_commands.choices(source=[
        app_commands.Choice(name="Spotify", value="spsearch"),
        app_commands.Choice(name="Apple Music", value="amsearch"),
        app_commands.Choice(name="YouTube Music", value="ytmsearch"),
        app_commands.Choice(name="Deezer", value="dzsearch"),
        app_commands.Choice(name="JioSaavn", value="jssearch"),
        app_commands.Choice(name="Gaana", value="gnsearch")
    ])
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def play(self, ctx: commands.Context, *, query: str, source: Optional[str] = None):
        await ctx.defer()
        player = await self.connect(ctx)

        if not player:
            return await send_error_embed(ctx, "Failed to connect to the voice channel.")
        
        try:
            source_cog = self.bot.get_cog("MusicControls")
            
            if source and source_cog:
                await source_cog.db.execute(
                    "INSERT INTO user_source (user_id, source_name) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET source_name = $2",
                    ctx.author.id, source
                )
                if source_cog.redis:
                    await source_cog.redis.set(source_cog.source_key.format(user_id=ctx.author.id), source)

            results = None

            if self.url_rx.match(query):
                results = await player.node.get_tracks(query)

            if not self.url_rx.match(query) and source:
                results = await player.node.get_tracks(f"{source}:{query}")

            if not self.url_rx.match(query) and not source:
                user_source = await source_cog.get_source_config(ctx.author.id) if source_cog else default_source
                results = await player.node.get_tracks(f"{user_source}:{query}")

            if (not results or not results.tracks) and not self.url_rx.match(query):
                results = await player.node.get_tracks(f"ytmsearch:{query}")

        except Exception:
            results = None
        
        if not results or not results.tracks:
            return await send_error_embed(ctx, f"No results found for `{query}` during search.")

        if results.load_type == LoadType.PLAYLIST:
            added_count = len(results.tracks)
            playlist_name = results.playlist_info.name or 'Playlist'

            for track in results.tracks:
                player.add(track, requester=ctx.author.id)

            if not player.is_playing:
                await player.play()

            first_track = results.tracks[0] if results.tracks else None
            thumb_url = (first_track.artwork_url if first_track else None) or self.bot.user.display_avatar.url
            icon = get_source_emoji(first_track.uri if first_track else "")
            playlist_url = query if self.url_rx.match(query) else "https://discord.com"

            section_body = discord.ui.TextDisplay(
                content=(
                    f"**Added to Queue**\n\n"
                    f"{icon} Added **{added_count}** tracks from playlist **[{sanitize_title(playlist_name)}]({playlist_url})**\n"
                    f"-# Requested by {ctx.author.mention} (`{ctx.author.name}`)"
                )
            )
            section = discord.ui.Section(section_body, accessory=discord.ui.Thumbnail(media=thumb_url))
            container = discord.ui.Container(section, accent_colour=default_color)
            view = discord.ui.LayoutView()
            view.add_item(container)
            return await ctx.reply(view=view, allowed_mentions=discord.AllowedMentions.none())
            
        track = results.tracks[0]            
        player.add(track, requester=ctx.author.id)
        is_first = not player.is_playing

        if is_first:
            await player.play()

        thumb_url = track.artwork_url or self.bot.user.display_avatar.url
        icon = get_source_emoji(track.uri)
        author_name = track.author or "Unknown Author"

        section_body = discord.ui.TextDisplay(
            content=(
                f"**Added to Queue**\n\n"
                f"{icon} **[{sanitize_title(track.title)}]({track_uri(track)})** - [{sanitize_title(author_name)}]({track_uri(track)})\n"
                f"Duration: `{format_duration(track.duration, clock=True)}`\n"
                f"-# Requested by {ctx.author.mention} (`{ctx.author.name}`)"
            )
        )
        section = discord.ui.Section(section_body, accessory=discord.ui.Thumbnail(media=thumb_url))
        view = AddedToQueueControls(player, track, section, is_first)
        await ctx.reply(view=view, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="nowplaying", aliases=["nowp"], description="Shows the current playing song.")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nowplaying(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)

        if not player or not player.current:
            return await send_error_embed(ctx, "No active player found in this server.")

        await delete_controller(player)
        
        view = MusicControls(self.bot, player)
        msg = await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())
        player.controller = msg

    @commands.hybrid_command(name="autoplay", aliases=["ap"], description="Toggles autoplay for the server.")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def autoplay(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)
        
        if not player:
            return await send_error_embed(ctx, "No active player found in this server.")

        player.autoplay = not player.autoplay
        await send_success_message(ctx, "Autoplay Toggled", f"Autoplay is now `{'enabled' if player.autoplay else 'disabled'}` for this server.")
        self.bot.loop.create_task(self.process_autoplay(player))

    @commands.hybrid_command(name="history", aliases=["recents"], description="Displays the song history of the server.")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def history(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)
        
        if not player or not player.history:
            return await send_error_embed(ctx, "No playback history available for this server.")
             
        history_list = list(reversed(player.history))
        tracks_per_page = 15
        chunks = [history_list[i:i + tracks_per_page] for i in range(0, len(history_list), tracks_per_page)]
        pages = []
        
        for i, chunk in enumerate(chunks):
            start_index = i * tracks_per_page
            description_lines = []
            for j, track in enumerate(chunk):
                description_lines.append(f"**`{start_index + j + 1:02}.`** [`{sanitize_title(track.title)}`]({track_uri(track)})")
            
            embed = discord.Embed(title=f"Music History [{len(player.history)}]", description="\n".join(description_lines), color=default_color)
            pages.append(embed)
            
        select = HistoryTrackSelect(player, chunks)
        paginator = Paginator(ctx, pages, jump_button=True, page_counter=True, reply=True, extra_items=[select], on_page_change=lambda page, _: select.update_page(page))
        await paginator.start()

    @commands.hybrid_command(name="queue", aliases=["q"], description="Displays the song queue of the server.")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def queue(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)

        if not player or not player.is_connected:
            return await send_error_embed(ctx, "No music system is currently active.")
        
        if not player.queue:
            return await send_error_embed(ctx, "The queue is currently empty for this server.")
        
        queue_list = list(player.queue)
        tracks_per_page = 15
        chunks = [queue_list[i:i + tracks_per_page] for i in range(0, len(queue_list), tracks_per_page)]
        pages = []

        for i, chunk in enumerate(chunks):
            start_index = i * tracks_per_page
            description_lines = []
            for j, track in enumerate(chunk):
                description_lines.append(f"**`{start_index + j + 1:02}.`** [`{sanitize_title(track.title)}`]({track_uri(track)})")

            embed = discord.Embed(title=f"Music Queue [{len(player.queue)}]", description="\n".join(description_lines), color=default_color)
            pages.append(embed)

        select = QueueTrackSelect(player, chunks)
        paginator = Paginator(ctx, pages, jump_button=True, page_counter=True, reply=True, extra_items=[select], on_page_change=lambda page, _: select.update_page(page))
        await paginator.start()

    @commands.hybrid_command(name="lavalink", aliases=["lavastats", "node"], description="View the complete stats of the bot's music system.")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def lavalink_cmd(self, ctx: commands.Context):
        await ctx.defer()

        if not hasattr(self.bot, 'lavalink') or not self.bot.lavalink:
            return await send_error_embed(ctx, "The lavalink music system is not initialized.")

        nodes = self.bot.lavalink.node_manager.nodes
        player_manager = self.bot.lavalink.player_manager
        total_players = len(player_manager.players) if hasattr(player_manager, 'players') else 0
        playing_players = sum(1 for p in player_manager.players.values() if p.is_playing) if total_players > 0 else 0
        connected_nodes = sum(1 for n in nodes if n.available)
        total_nodes = len(nodes)

        items = []
        items.append(
            discord.ui.Section(
                discord.ui.TextDisplay(content=(
                    f"### Lavalink Statistics\n"
                    f"> **__Total Players__ :** `{total_players:,}`\n"
                    f"> **__Playing__ :** `{playing_players:,}`\n"
                    f"> **__Connected Nodes__ :** `{connected_nodes}/{total_nodes}`"
                )),
                accessory=discord.ui.Thumbnail(media=self.bot.user.display_avatar.url)
            )
        )
        items.append(discord.ui.Separator())

        desc_list = []
        for i, node in enumerate(nodes, 1):
            node_name = getattr(node, 'name', None) or getattr(node, '_name', None) or f"Node {i}"
            stats = getattr(node, 'stats', None)
            status_emoji = "<:wccheckmark:1556658412106817567>" if node.available else "<:wccrossmar:1556658451021701167>"
            node_text = f"> **`{node_name}`** → {status_emoji}\n"

            if stats and not getattr(stats, 'is_fake', True):
                node_text += (
                    f"<:space:1556658570198515804><:arrow:1556658266056953899> **Players :** `{stats.playing_players:,}` active / `{stats.players:,}` total\n"
                    f"<:space:1556658570198515804><:arrow:1556658266056953899> **Uptime :** `{format_duration(stats.uptime)}`\n"
                    f"<:space:1556658570198515804><:arrow:1556658266056953899> **CPU :** `{stats.cpu_cores}` Cores (`{stats.system_load:.2%}`)\n"
                    f"<:space:1556658570198515804><:arrow:1556658266056953899> **Memory :** `{format_bytes(stats.memory_used)}` / `{format_bytes(stats.memory_allocated)}`"
                )

                if stats.frames_sent or stats.frames_nulled or stats.frames_deficit:
                    node_text += f"\n<:space:1556658570198515804><:arrow:1556658266056953899> **Frames :** `{stats.frames_sent:,}` sent (`{stats.frames_nulled:,}` nulled)"

            desc_list.append(node_text)

        if desc_list:
            items.append(discord.ui.TextDisplay(content="\n\n".join(desc_list)))

        items.append(discord.ui.Separator())
        items.append(discord.ui.TextDisplay(content=f"-# Requested by {ctx.author.mention} (`{ctx.author.name}`)"))
        container = discord.ui.Container(*items, accent_colour=default_color)
        view = discord.ui.LayoutView()
        view.add_item(container)
        await ctx.reply(view=view, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    await bot.add_cog(Music(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
