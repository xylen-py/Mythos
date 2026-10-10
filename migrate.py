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

import re
import json
import asyncio
import logging
import discord
import logging
from pathlib import Path
from typing import Set, Dict, Tuple

import aiohttp
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

EMOJI_REGEX = re.compile(r'<(a?):([a-zA-Z0-9_]+):([0-9]+)>')
TARGET_EXTENSIONS = {'.py', '.json'}
IGNORED_DIRS = {'.git', 'venv', '__pycache__', 'env'}

def get_target_files(base_path: Path) -> list[Path]:
    return [
        file for file in base_path.rglob("*")
        if file.is_file() 
        and file.suffix in TARGET_EXTENSIONS 
        and not any(ignored in file.parts for ignored in IGNORED_DIRS)
    ]

def extract_emojis(files: list[Path]) -> Set[Tuple[str, str, str]]:
    emojis = set()
    for file in files:
        try:
            content = file.read_text(encoding='utf-8')
            emojis.update(EMOJI_REGEX.findall(content))
        except Exception as e:
            logger.error(f"Failed reading {file}: {e}")
    return emojis

def update_files(files: list[Path], replacements: Dict[str, str]) -> None:
    for file in files:
        try:
            content = file.read_text(encoding='utf-8')
            new_content = content
            for old_emoji, new_emoji in replacements.items():
                new_content = new_content.replace(old_emoji, new_emoji)
            
            if new_content != content:
                file.write_text(new_content, encoding='utf-8')
                logger.info(f"Updated file: {file}")
        except Exception as e:
            logger.error(f"Failed updating {file}: {e}")

async def fetch_emoji_image(session: aiohttp.ClientSession, emoji_id: str, is_animated: str) -> bytes | None:
    ext = "gif" if is_animated == "a" else "png"
    url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
    
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
            logger.warning(f"Download failed for {emoji_id}: HTTP {resp.status}")
    except Exception as e:
        logger.error(f"Request failed for {emoji_id}: {e}")
    return None

async def migrate(bot: commands.Bot) -> None:
    try:
        existing = await bot.fetch_application_emojis()
        existing_names = {e.name: e for e in existing}
        existing_ids = {e.id for e in existing}
        logger.info(f"Loaded {len(existing)} existing application emojis.")
    except Exception as e:
        logger.error(f"Failed to fetch application emojis: {e}")
        existing_names = {}
        existing_ids = set()

    files = get_target_files(Path("."))
    all_emojis = extract_emojis(files)
    logger.info(f"Found {len(all_emojis)} unique custom emojis in codebase.")
    
    replacements: Dict[str, str] = {}
    
    async with aiohttp.ClientSession() as session:
        for is_animated, name, emoji_id in all_emojis:
            old_format = f"<{is_animated}:{name}:{emoji_id}>"
            
            if int(emoji_id) in existing_ids:
                continue
                
            if name in existing_names:
                new_e = existing_names[name]
                replacements[old_format] = f"<{is_animated}:{new_e.name}:{new_e.id}>"
                logger.info(f"Mapped existing emoji: {name}")
                continue

            image_bytes = await fetch_emoji_image(session, emoji_id, is_animated)
            if not image_bytes:
                continue

            safe_name = name if len(name) >= 2 else f"{name}_"
            
            try:
                logger.info(f"Uploading new application emoji: {safe_name}")
                new_emoji = await bot.create_application_emoji(name=safe_name, image=image_bytes)
                
                replacements[old_format] = f"<{is_animated}:{new_emoji.name}:{new_emoji.id}>"
                existing_names[safe_name] = new_emoji
                existing_ids.add(new_emoji.id)
                
                await asyncio.sleep(2.5)
            except Exception as e:
                logger.error(f"Upload failed for {safe_name}: {e}")

    if replacements:
        logger.info(f"Applying {len(replacements)} replacements across files...")
        update_files(files, replacements)
    
    logger.info("Migration complete!")

def get_token():
    try:
        import json
        with open("data/config.json", "r") as f:
            data = json.load(f)
            return data["bot_settings"]["token"]
    except Exception:
        return None

async def main():
    token = get_token()
    if not token:
        logger.error("Could not find token in data/config.json")
        return

    bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
    
    @bot.event
    async def on_ready():
        logger.info(f"Logged in as {bot.user}")
        await migrate(bot)
        logger.info("Done! Closing bot.")
        await bot.close()

    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
