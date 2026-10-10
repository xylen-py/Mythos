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

from discord.ext          import commands
import random
import asyncio
from typing               import cast, Optional

import asyncpg
import redis.asyncio      as aioredis
from lavalink             import DefaultPlayer

from config               import default_source
from utils.parse_duration import parse_duration
from utils.success_send   import send_success_message
from utils.send_errors    import send_error_embed
from utils.bl_ignore      import bl_ignore_check
from cogs.music           import requires_voice, sanitize_title, track_uri

class MusicControls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = cast(asyncpg.Pool, self.bot.db)
        self.redis = cast(aioredis.Redis, self.bot.redis)
        self.source_key = "usersource:{user_id}"
        self.voice_247 = {}
        self.bot.loop.create_task(self.connect_db())

    async def connect_db(self):
        await self.setup_db()
        await self.warm_cache()

    async def setup_db(self):
        await self.db.execute("CREATE TABLE IF NOT EXISTS user_source (user_id BIGINT PRIMARY KEY, source_name TEXT NOT NULL)")
        await self.db.execute("CREATE TABLE IF NOT EXISTS voice_247 (guild_id BIGINT PRIMARY KEY, channel_id BIGINT NOT NULL)")

    async def warm_cache(self):
        self.voice_247.clear()
        voice_rows = await self.db.fetch("SELECT guild_id, channel_id FROM voice_247")

        shard_ids = self.bot.shard_ids or range(self.bot.shard_count or 1)

        for row in voice_rows:
            guild_id = row['guild_id']
            
            if (guild_id >> 22) % (self.bot.shard_count or 1) in shard_ids:
                self.voice_247[guild_id] = row['channel_id']
        
        if 0 not in shard_ids:
            return

        pipe = self.redis.pipeline()
        source_rows = await self.db.fetch("SELECT user_id, source_name FROM user_source")

        for row in source_rows:
            pipe.set(self.source_key.format(user_id=row['user_id']), row['source_name'])

        await pipe.execute()

    async def get_source_config(self, user_id: int) -> str:
        data = await self.redis.get(self.source_key.format(user_id=user_id))

        if data:
            return data.decode() if isinstance(data, bytes) else data

        row = await self.db.fetchrow("SELECT source_name FROM user_source WHERE user_id = $1", user_id)

        if row:
            source_name = row['source_name']
            await self.redis.set(self.source_key.format(user_id=user_id), source_name)
            return source_name

        await self.redis.set(self.source_key.format(user_id=user_id), default_source)
        return default_source

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if channel.guild.id not in self.voice_247 or self.voice_247[channel.guild.id] != channel.id:
            return

        del self.voice_247[channel.guild.id]
        await self.db.execute("DELETE FROM voice_247 WHERE guild_id = $1", channel.guild.id)

    def get_player(self, guild_id: int) -> Optional[DefaultPlayer]:

        if not self.bot.lavalink:
            return None

        return self.bot.lavalink.player_manager.get(guild_id)

    @commands.hybrid_command(name="join", description="Connects the bot to your current voice channel")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def join(self, ctx: commands.Context):
        music = self.bot.get_cog('Music')

        if not music:
            return await send_error_embed(ctx, "Music cog not available or not loaded.")

        player = await music.connect(ctx)

        if player:
            return await send_success_message(ctx, "Channel joined", f"Successfully joined vc {ctx.author.voice.channel.mention}")

        await send_error_embed(ctx, f"Failed to join the voice channel {ctx.author.voice.channel.mention}.")

    @commands.hybrid_command(name="leave", aliases=["dc", "disconnect"], description="Disconnects the bot from the voice channel")
    @commands.guild_only()
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def leave(self, ctx: commands.Context):
        if not ctx.guild.voice_client:
            return await send_error_embed(ctx, "I am not connected to a voice channel.")

        if not ctx.author.voice:
            return await send_error_embed(ctx, "You are not connected to a voice channel.")

        if ctx.author.voice.channel != ctx.guild.voice_client.channel:
            return await send_error_embed(ctx, "You are not in the same voice channel as the bot.")

        if self.voice_247.get(ctx.guild.id) == ctx.guild.voice_client.channel.id:
            return await send_error_embed(ctx, "I cannot leave a designated 24/7 voice channel.")

        player = self.get_player(ctx.guild.id)

        if player:
            await player.stop()
            player.queue.clear()

        await ctx.guild.voice_client.disconnect(force=True)
        await send_success_message(ctx, "Channel left", "Successfully left the voice channel.")

    @commands.hybrid_command(name="forcefix", aliases=["rejoin"], description="Disconnects and reconnects the bot to fix audio issues")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def forcefix(self, ctx: commands.Context):
        music = self.bot.get_cog('Music')

        if not music:
            return await send_error_embed(ctx, "Music cog not available or not loaded.")

        if ctx.guild.voice_client:
            player = self.get_player(ctx.guild.id)

            if player:
                await player.stop()

            await ctx.guild.voice_client.disconnect(force=True)

        await asyncio.sleep(1)
        new_player = await music.connect(ctx)

        if new_player:
            return await send_success_message(ctx, "Force fixed", "Successfully reconnected to the voice channel.")

        return await send_error_embed(ctx, "Failed to reconnect to the voice channel.")

    @commands.hybrid_command(name="pause", aliases=["pa"], description="Pauses the currently playing track")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def pause(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)

        if not player or not player.is_playing or player.paused:
            return await send_error_embed(ctx, "No music is currently playing to pause.")

        await player.set_pause(True)
        await send_success_message(ctx, "Player paused", "The music player has been paused.")

    @commands.hybrid_command(name="resume", aliases=["re"], description="Resumes the paused track")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def resume(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)

        if not player or not player.paused:
            return await send_error_embed(ctx, "No music is currently paused to resume.")

        await player.set_pause(False)
        await send_success_message(ctx, "Player resumed", "The music player has been resumed.")

    @commands.hybrid_command(name="volume", aliases=["vol", "v"], description="Sets the player volume (0 to 200)")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def volume(self, ctx: commands.Context, volume: int):
        player = self.get_player(ctx.guild.id)

        if not player:
            return await send_error_embed(ctx, "No music system is currently active.")

        if not (0 <= volume <= 200):
            return await send_error_embed(ctx, f"Volume must be a number between `0` and `200`.")

        await player.set_volume(volume)
        await send_success_message(ctx, "Volume Set", f"Player volume is set to `{volume}/200` now.")

    @commands.hybrid_command(name="replay", description="Replays the current track from the beginning")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def replay(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)

        if not player or not player.current:
            return await send_error_embed(ctx, "No music is currently playing to replay.")

        await player.seek(0)
        await send_success_message(ctx, "Track replayed", "The current track has been replayed.")

    @commands.hybrid_command(name="seek", aliases=["sk"], description="Jumps to a specific time by percentage (0 to 100)")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def seek(self, ctx: commands.Context, percentage: int):
        player = self.get_player(ctx.guild.id)

        if not player or not player.current:
            return await send_error_embed(ctx, "No music is currently playing to seek.")

        if not (0 <= percentage <= 100):
            return await send_error_embed(ctx, "Invalid percentage. Please use a value between 0 and 100.")

        await player.seek(int(percentage * player.current.duration / 100))
        await send_success_message(ctx, "Player seeked", f"Jumped to `{percentage}%` in the current track.")

    @commands.hybrid_command(name="forward", aliases=["ff"], description="Fast-forwards the current track")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def forward(self, ctx: commands.Context, position: str):
        player = self.get_player(ctx.guild.id)

        if not player or not player.current:
            return await send_error_embed(ctx, "No music is currently playing to fast-forward.")

        parsed_time = parse_duration(position)

        if parsed_time is None:
            return await send_error_embed(ctx, "Invalid duration provided. Please use format like 5s, 10s, 1m")

        if parsed_time.total_seconds() < 0 or parsed_time.total_seconds() * 1000 > (player.current.duration - player.position):
            return await send_error_embed(ctx, "Invalid duration. Please use valid time until the end of the track.")

        new_position = player.position + parsed_time.total_seconds() * 1000
        await player.seek(int(new_position))
        await send_success_message(ctx, "Track fast-forwarded", f"Fast-forwarded the current track by `{position}`.")

    @commands.hybrid_command(name="rewind", aliases=["rw"], description="Rewinds the current track")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def rewind(self, ctx: commands.Context, position: str):
        player = self.get_player(ctx.guild.id)

        if not player or not player.current:
            return await send_error_embed(ctx, "No music is currently playing to rewind.")

        parsed_time = parse_duration(position)

        if parsed_time is None:
            return await send_error_embed(ctx, "Invalid duration provided. Please use format like 5s, 10s, 1m")

        if parsed_time.total_seconds() < 0 or parsed_time.total_seconds() * 1000 > player.position:
            return await send_error_embed(ctx, "Invalid duration. Please use valid time until the current position.")

        new_position = player.position - parsed_time.total_seconds() * 1000
        await player.seek(int(new_position))
        await send_success_message(ctx, "Track rewound", f"Rewound the current track by `{position}`.")

    @commands.hybrid_command(name="loop", aliases=["lp"], description="Toggles looping or sets specific mode (queue & track & off).")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def loop(self, ctx: commands.Context, mode: str = None):
        player = self.get_player(ctx.guild.id)

        if not player or not player.current:
            return await send_error_embed(ctx, "No active player found in this server.")

        if not player.queue and mode in ["queue", "q"]:
            return await send_error_embed(ctx, "The music queue is empty right now.")

        if mode in ["queue", "q"]:
            player.set_loop(player.LOOP_QUEUE)
            return await send_success_message(ctx, "Queue looping", "The music queue has been set to loop.")

        if mode in ["track", "t"]:
            player.set_loop(player.LOOP_SINGLE)
            return await send_success_message(ctx, "Track looping", "The current track has been set to loop.")

        if mode in ["off", "disable"]:
            player.set_loop(player.LOOP_NONE)
            return await send_success_message(ctx, "Loop disabled", "Looping has been disabled for the player.")

        if player.loop in [player.LOOP_QUEUE, player.LOOP_SINGLE]:
            player.set_loop(player.LOOP_NONE)
            return await send_success_message(ctx, "Loop disabled", "Looping has been disabled for the player.")

        player.set_loop(player.LOOP_SINGLE)
        await send_success_message(ctx, "Track looping", "The current track has been set to loop.")

    @commands.hybrid_command(name="247", aliases=["stay"], description="Toggle 24/7 mode (bot stays in voice channel)")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def voice_247_cmd(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)

        if not player:
            return await send_error_embed(ctx, "No active player found in this server.")

        if ctx.guild.id in self.voice_247:
            del self.voice_247[ctx.guild.id]
            await self.db.execute("DELETE FROM voice_247 WHERE guild_id = $1", ctx.guild.id)
            return await send_success_message(ctx, "24/7 Mode", "24/7 mode has been disabled for the player.")

        await self.db.execute(
            "INSERT INTO voice_247 (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET channel_id = EXCLUDED.channel_id",
            ctx.guild.id, ctx.voice_client.channel.id
        )

        self.voice_247[ctx.guild.id] = ctx.voice_client.channel.id
        await send_success_message(ctx, "24/7 Mode", "24/7 mode has been enabled for the player.")

    @commands.hybrid_command(name="shuffle", description="Shuffles the current music queue")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shuffle(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)

        if not player:
            return await send_error_embed(ctx, "No active player found in this server.")

        if not player.queue:
            return await send_error_embed(ctx, "The music queue is empty right now.")

        random.shuffle(player.queue)
        await send_success_message(ctx, "Queue shuffled", "The music queue has been shuffled.")

    @commands.hybrid_command(name="clearqueue", aliases=["cq"], description="Clears all tracks from the queue")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def clearqueue(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)

        if not player or not player.queue:
            return await send_error_embed(ctx, "The music queue is empty right now.")

        player.queue.clear()
        await send_success_message(ctx, "Queue cleared", "All tracks have been removed from the queue.")

    @commands.hybrid_command(name="remove", description="Removes a track from the queue at a specific position")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def remove(self, ctx: commands.Context, position: int):
        player = self.get_player(ctx.guild.id)

        if not player:
            return await send_error_embed(ctx, "No active player found in this server.")

        if not player.queue:
            return await send_error_embed(ctx, "The music queue is empty right now.")

        if 0 <= (position - 1) < len(player.queue):
            track = player.queue.pop(position - 1)
            return await send_success_message(ctx, "Track removed", f"Removed **[{sanitize_title(track.title)}]({track_uri(track)})** from the queue.")

        await send_error_embed(ctx, f"Invalid position, must be between 1 and {len(player.queue)}.")

    @commands.hybrid_command(name="move", description="Moves a track from one position to another in the queue")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def move(self, ctx: commands.Context, position: int, to: int):
        player = self.get_player(ctx.guild.id)

        if not player:
            return await send_error_embed(ctx, "No active player found in this server.")

        if not player.queue:
            return await send_error_embed(ctx, "The music queue is empty right now.")

        if 0 <= (position - 1) < len(player.queue) and 0 <= (to - 1) < len(player.queue):
            track = player.queue.pop(position - 1)
            player.queue.insert(to - 1, track)
            return await send_success_message(ctx, "Track moved", f"Moved **[{sanitize_title(track.title)}]({track_uri(track)})** from position `{position}` to `{to}`.")

        await send_error_embed(ctx, f"Invalid positions, must be between 1 and {len(player.queue)}.")

    @commands.hybrid_command(name="skip", aliases=["s", "next"], description="Skips the current track.")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def skip(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)

        if not player or not player.current:
            return await send_error_embed(ctx, "No music is currently playing to skip.")

        current_song = player.current

        await player.skip()
        await send_success_message(ctx, "Track skipped", f"Successfully skipped track **[{sanitize_title(current_song.title)}]({track_uri(current_song)})**")

    @commands.hybrid_command(name="skipinto", description="Skips to a specific track number in the queue.")
    @commands.guild_only()
    @requires_voice()
    @bl_ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def skipinto(self, ctx: commands.Context, position: int):
        player = self.get_player(ctx.guild.id)

        if not player:
            return await send_error_embed(ctx, "No active player found in this server.")

        if not player.queue:
            return await send_error_embed(ctx, "The music queue is empty right now.")

        target_index = position - 1
        if not (0 <= target_index < len(player.queue)):
            return await send_error_embed(ctx, f"Invalid position, must be between 1 and {len(player.queue)}.")

        del player.queue[:target_index]
        await player.skip()
        await send_success_message(ctx, "Tracks skipped", f"Skipped to track at position `{position}`.")

async def setup(bot):
    await bot.add_cog(MusicControls(bot))

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
