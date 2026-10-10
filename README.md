<div align="center">

# Mythos

A feature-rich, high-performance Discord music bot built with [discord.py](https://github.com/Rapptz/discord.py) and [Lavalink](https://github.com/lavalink-devs/Lavalink).

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![discord.py](https://img.shields.io/badge/discord.py-2.0+-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://github.com/Rapptz/discord.py)
[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

</div>

---

## Features

- **Multi-Source Music** — Spotify, YouTube, Apple Music, SoundCloud, Deezer, JioSaavn, Gaana, Amazon Music, Pandora
- **Smart Autoplay** — Automatically queues related tracks natively matching platform algorithms (Spotify Recommendations, YouTube Music Mixes, Deezer Track Recommendations, and smart ISRC-based matching) for perfectly curated listening sessions.
- **Audio Filters** — Bassboost, nightcore, vaporwave, 8D, karaoke, tremolo, vibrato, and more
- **Synced Lyrics** — Real-time lyrics display with timestamp syncing
- **Player Controls** — Interactive controller with buttons for play/pause, skip, shuffle, loop, and volume
- **AFK System** — Set AFK status with mention tracking across servers
- **Blacklist & Ignore** — Granular control over users, servers, channels, and roles
- **Sharding** — Built-in auto-sharding support for scaling across thousands of servers
- **Hybrid Commands** — All commands work as both slash commands and text commands
- **Application Emojis** — Emoji migration utility to move all custom emojis to application-owned emojis

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | [discord.py](https://github.com/Rapptz/discord.py) (AutoShardedBot) |
| Audio | [Lavalink](https://github.com/lavalink-devs/Lavalink) via [lavalink.py](https://github.com/Devoxin/Lavalink.py) |
| Database | PostgreSQL ([Aiven](https://aiven.io/)) |
| Cache | Redis ([Redis Cloud](https://redis.io/cloud/)) |

## Project Structure

```
mythos/
├── bot.py                  # Bot entry point and core setup
├── config.py               # Configuration loader
├── migrate.py              # Application emoji migration utility
├── requirements.txt        # Python dependencies
├── data/
│   └── config.json         # Bot configuration (credentials, nodes, etc.)
├── cogs/
│   ├── music.py            # Core music commands (play, skip, queue, etc.)
│   ├── player.py           # Player controller and now-playing UI
│   ├── filters.py          # Audio filter commands
│   ├── lyrics.py           # Lyrics fetching and display
│   ├── events/
│   │   ├── advertise.py    # Bot promotion in empty voice channels
│   │   ├── errors.py       # Global error handler
│   │   └── mention.py      # Bot mention response
│   └── nexus/
│       ├── afk.py          # AFK system
│       ├── blacklist.py    # User/server blacklisting
│       ├── ignore.py       # Channel/role ignore system
│       ├── info.py         # Bot information commands
│       ├── invite.py       # Invite link command
│       ├── owner.py        # Owner-only commands
│       ├── pfp.py          # Avatar/banner commands
│       └── stats.py        # Bot statistics
├── music/
│   ├── __init__.py         # Music module exports
│   ├── lavalink_client.py  # Custom Lavalink client wrapper
│   ├── status.py           # Voice channel status management
│   └── voice.py            # Voice connection handler
└── utils/
    ├── bl_ignore.py        # Blacklist/ignore check decorator
    ├── blacklist_check.py  # Blacklist query helpers
    ├── is_owner.py         # Owner check utility
    ├── paginators.py       # Paginated embed views
    ├── parse_duration.py   # Duration string parser
    ├── send_errors.py      # Error embed builder
    ├── subcmds.py          # Subcommand help formatter
    └── success_send.py     # Success embed builder
```

## Setup

### Prerequisites

- **Python 3.11+**
- **PostgreSQL** database (e.g., [Aiven Free Tier](https://aiven.io/))
- **Redis** instance (e.g., [Redis Cloud Free Tier](https://redis.io/cloud/))
- **Lavalink** server ([setup guide](https://lavalink.dev/getting-started/))
- A **Discord Bot** application ([Discord Developer Portal](https://discord.com/developers/applications))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/xylen-py/mythos.git
   cd mythos
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot**
   ```bash
   cp data/config.example.json data/config.json
   ```
   Edit `data/config.json` with your credentials:
   - Bot token from the [Developer Portal](https://discord.com/developers/applications)
   - PostgreSQL connection string
   - Redis connection URL
   - Lavalink node details

4. **Run the bot**
   ```bash
   python bot.py
   ```

### Emoji Migration

To migrate all custom emojis used in the codebase to your bot's application emojis:

```bash
python migrate.py
```

This will scan every `.py` and `.json` file, download each referenced emoji, upload it as an application emoji, and update all files with the new IDs.

## Configuration

All configuration lives in `data/config.json`. See [`data/config.example.json`](data/config.example.json) for the full template.

| Key | Description |
|-----|-------------|
| `bot_settings.token` | Your Discord bot token |
| `bot_settings.prefix` | Text command prefix |
| `bot_settings.application_owner` | Your Discord user ID |
| `bot_settings.startup_settings.shard_count` | Number of shards |
| `database.postgres_dsn` | PostgreSQL connection string |
| `database.redis_url` | Redis connection URL |
| `music_settings.nodes` | Lavalink node configurations |
| `music_settings.default_source` | Default music search source |
| `links.support_server` | Support server invite URL |

### Lavalink Configuration (`lavalink/application.yml`)

Mythos relies on a highly customized Lavalink server with several plugins (LavaSrc, SkyBot, SponsorBlock, LavaLyrics, etc.). To enable playback from premium sources, you **must** configure your `lavalink/application.yml` file with the appropriate tokens:

| Service | Configuration Required | How to obtain |
|---------|------------------------|---------------|
| **YouTube** | `pot.token`, `pot.visitorData`, `oauth.refreshToken` | Extract from your browser's network tab while logged into YouTube. |
| **Spotify** | `spDc` cookie | Grab the `sp_dc` cookie from your browser after logging into Spotify. |
| **Deezer** | `arl`, `masterDecryptionKey` | Get the `arl` cookie from your browser. The decryption key can be found online. |
| **Apple Music** | `mediaAPIToken` | Extract the JWT token from the Apple Music web player's network requests. |
| **JioSaavn** | `secretKey` | Required for JioSaavn decryption. |

Ensure you replace the placeholder values (like `your_spotify_spdc_cookie_here`) in your `lavalink/application.yml` before starting your Lavalink server.

## License

This project is licensed under the **GPL-3.0 License** — see the [LICENSE](LICENSE) file for details. This means if you modify and distribute this code, you must open-source your modifications and provide proper credit to `xylen-py`.
