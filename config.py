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

import json
import sys
import discord

CONFIG_FILE = "data/config.json"

try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    sys.exit(1)
except json.JSONDecodeError:
    sys.exit(1)

token = data["bot_settings"].get("token")
default_prefix = data["bot_settings"].get("prefix", ".")
default_color = discord.Color.from_str(data["bot_settings"].get("default_color", "#333537"))
application_owner = data["bot_settings"].get("application_owner", 0)
startup_settings = data["bot_settings"].get("startup_settings", {})
shard_count = startup_settings.get("shard_count", 10)
shard_ids = startup_settings.get("shard_ids", None)

database_config = data.get("database", {})
postgres_dsn = database_config.get("postgres_dsn", "")
redis_url = database_config.get("redis_url", "")

links = data.get("links", {})
support_url = links.get("support_server", "")
website = links.get("website", "")
support_server_id = links.get("support_server_id", 0)
support_server_name = links.get("support_server_name", "Support Server")

music = data.get("music_settings", {})
nodes = music.get("nodes", {})
default_source = music.get("default_source", "spsearch")
source_emojis = music.get("source_emojis", {})

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
