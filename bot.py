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

from discord.ext import commands
import os
import logging as log
import logging.handlers
import colorlog
import discord
import shutil
import argparse
from datetime import datetime, timezone
from pathlib import Path
import asyncpg
import aiohttp
import redis.asyncio as aioredis
import config
from config import default_prefix, application_owner, token, postgres_dsn, redis_url
from utils.is_owner import OWNER_IDS
from xylogger import console, ConsoleColors

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_RETAIN"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"
os.environ["JISHAKU_HIDE"] = "True"

def setup_external_logging():
    root_logger = log.getLogger()
    root_logger.handlers = []
    root_logger.setLevel(log.INFO)
    
    console_handler = log.StreamHandler()
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s[%(asctime)s] %(levelname)-8s%(reset)s %(purple)s[%(name)s]%(reset)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)
    
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        filename='logs/discord.log',
        encoding='utf-8',
        maxBytes=10 * 1024 * 1024,
        backupCount=3
    )
    file_formatter = log.Formatter(
        fmt='[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(console_handler)
    
    libraries = {
        'discord': log.INFO,
        'discord.http': log.WARNING,
        'discord.gateway': log.INFO,
        'aiohttp': log.WARNING, 
        'asyncio': log.WARNING,
        'lavalink': log.INFO
    }

    for lib_name, level in libraries.items():
        logger = log.getLogger(lib_name)
        logger.setLevel(level)
        logger.propagate = True
        
    return file_handler

handler = setup_external_logging()

def print_centered(lines):
    
    width = shutil.get_terminal_size(fallback=(100, 24)).columns
    if isinstance(lines, str):
        lines = [lines]
        
    for line in lines:
        clean_line = line
        for color in vars(ConsoleColors).values():
            if isinstance(color, str):
                clean_line = clean_line.replace(color, "")
        
        padding = max(0, (width - len(clean_line)) // 2)
        print(" " * padding + line)

class Client(commands.AutoShardedBot):
    def __init__(self):
        intents=discord.Intents.default()
        intents.members = True
        intents.message_content = False
        intents.presences = False
        intents.typing = False
        intents.dm_messages = False
        intents.dm_reactions = False
        intents.dm_typing = False
        intents.auto_moderation = False
        intents.polls = False

        kwargs = {
            "command_prefix": commands.when_mentioned_or(default_prefix),
            "intents": intents,
            "max_messages": 20000,
            "allowed_mentions": discord.AllowedMentions(everyone=False, replied_user=False, roles=False, users=True),
            "owner_id": application_owner,
            "case_insensitive": True,
            "strip_after_prefix": True,
            "shard_count": config.shard_count,
            "chunk_guilds_at_startup": False,
            "heartbeat_timeout": 150.0,
            "status": discord.Status.dnd,
            "activity": discord.Activity(type=discord.ActivityType.listening, name="/help | ♬ Infinity ...")
        }

        if config.shard_ids:
            kwargs["shard_ids"] = config.shard_ids

        super().__init__(**kwargs)
        self.help_command = None
        self.db = None
        self.redis = None
        self.session = None
        self.start_time = None

    async def setup_hook(self):
        os.system('cls' if os.name == 'nt' else 'clear')

        try:
            self.db = await asyncpg.create_pool(dsn=postgres_dsn, ssl="require", min_size=1, max_size=10, statement_cache_size=0)
            console.success("Connected to PostgreSQL (Aiven)")
        except Exception as e:
            self.db = None
            console.error("Failed to connect to PostgreSQL", e)

        try:
            self.redis = await aioredis.from_url(redis_url, decode_responses=True, max_connections=20, socket_timeout=5.0, socket_connect_timeout=5.0, retry_on_timeout=True)
            await self.redis.ping()
            console.success("Connected to Redis")
        except Exception as e:
            self.redis = None
            console.error("Failed to connect to Redis", e)

        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0, ttl_dns_cache=300))
        
        try:
            await self.load_extension("jishaku")
        except Exception as e:
            console.error("Failed to load jishaku", e)
            
        loaded_count = 0
        failed_count = 0

        loaded_extensions = set()

        for path in Path("cogs").rglob("*"):
            if path.suffix not in (".py", ".pyd", ".so") or path.name.startswith("__"): 
                continue
            
            ext = ".".join(list(path.parent.parts) + [path.name.split('.')[0]])

            if ext in loaded_extensions:
                continue

            try:
                await self.load_extension(ext)
                console.success(f"Loaded Cog {ext}")
                loaded_count += 1
                loaded_extensions.add(ext)
            except Exception as e:
                console.error(f"Failed to load Cog {ext}", e)
                failed_count += 1
        
        console.info(f"Cogs Status {ConsoleColors.GREEN}{loaded_count} Loaded{ConsoleColors.RESET} | {ConsoleColors.RED}{failed_count} Failed{ConsoleColors.RESET}")

    def display_ascii_banner(self):
        art_lines = [
            "██████╗     ██████╗       ██╗       ██╗  ██╗    ██╗    ████████╗    ██╗   ██╗",
            "██╔══██╗    ██╔══██╗     ████╗      ╚██╗██╔╝    ██║    ╚══██╔══╝    ╚██╗ ██╔╝",
            "██║══██║    ██████╔╝    ██╔═██╗      ╚███╔╝     ██║       ██║        ╚████╔╝ ",
            "██║  ██║    ██╔══██╗   ██╔╝  ██╗     ██╔██╗     ╚═╝       ██║         ╚██╔╝  ",
            "██████╔╝    ██║  ██║  ██╔╝    ██╗   ██╔╝ ██╗    ██╗       ██║          ██║   ",
            "╚═════╝     ╚═╝  ╚═╝  ╚═╝     ╚═╝   ╚═╝  ╚═╝    ╚═╝       ╚═╝          ╚═╝   ",
            ""
        ]
        
        print("\n")
        for line in art_lines:
            colored_line = f"{ConsoleColors.BOLD}{ConsoleColors.PURPLE}{line}{ConsoleColors.RESET}"
            print_centered(colored_line)
        print("\n")

    async def on_ready(self):
        if not self.start_time:
            self.start_time = datetime.now(timezone.utc)

        self.display_ascii_banner()
        console.section("Bot Ready", start_rgb=(80, 250, 123), end_rgb=(139, 233, 253))
        
        total_servers = len(self.guilds)
        total_users = sum((g.member_count or 0) for g in self.guilds)
        avg_latency = round(self.latency * 1000)
        cluster_shards = list(self.shard_ids) if self.shard_ids else list(range(self.shard_count or 1))
        
        console.success(f"Logged in as {self.user} (ID {self.user.id})")
        console.info(f"Cluster Shards {cluster_shards} ({len(cluster_shards)}/{self.shard_count})")
        console.info(f"Statistics {total_servers} Servers | {total_users} Users")
        console.info(f"Performance Average Latency {avg_latency}ms")

    async def close(self):
        console.info("Shutting down and cleaning up resources...")

        if self.session:
            await self.session.close()

        if self.db:
            await self.db.close()
            
        if self.redis:
            await self.redis.aclose()
            
        await super().close()

    async def on_message_edit(self, before, after):
        if not after.author.bot and before.content != after.content: 
            await self.process_commands(after)

    def is_blacklisted(self, message):
        blacklist_cog = self.get_cog("Blacklist")
        
        if blacklist_cog and message.author.id not in OWNER_IDS:
            if (message.guild and message.guild.id in blacklist_cog.guilds_cache) or message.author.id in blacklist_cog.users_cache:
                return True

        return False

    async def process_commands(self, message):
        if message.author.bot:
            return

        ctx = await self.get_context(message)

        if ctx.command is not None and self.is_blacklisted(message):
            return

        await self.invoke(ctx)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZEON Bot Runner")
    parser.add_argument("--shard-count", type=int, help="Total number of shards for the entire bot")
    parser.add_argument("--shard-ids", type=str, help="Comma separated list of shard IDs for this cluster (e.g. 0,1,2)")
    parser.add_argument("--cluster-id", type=str, help="Custom Cluster ID")
    
    args, _ = parser.parse_known_args()
    
    if args.shard_count is not None:
        config.shard_count = args.shard_count

    if args.shard_ids is not None:
        config.shard_ids = [int(x.strip()) for x in args.shard_ids.split(',')]

    if args.cluster_id is not None:
        os.environ["CLUSTER_ID"] = args.cluster_id

    client = Client()
    client.run(token, log_handler=handler, root_logger=True)

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
