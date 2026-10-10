<div align="center">

# <img src="assets/mythos.webp" width="45" align="top"> Mythos

A feature-rich, high-performance Discord music bot built with [discord.py](https://github.com/Rapptz/discord.py) and [Lavalink](https://github.com/lavalink-devs/Lavalink).

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![discord.py](https://img.shields.io/badge/discord.py-2.0+-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://github.com/Rapptz/discord.py)
[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Discord Support](https://img.shields.io/discord/1270760786817450086?color=5865F2&label=Support%20Server&logo=discord&logoColor=white&style=for-the-badge)](https://discord.gg/HwHD8a5QXa)

</div>

---

<div align="center">
  <img src="assets/banner.jpg" alt="Mythos Banner">
</div>

## Features

### Core Audio Engine
- **Extensive Platform Support**: Seamless playback from Spotify, YouTube, Apple Music, SoundCloud, Deezer, JioSaavn, Gaana, Amazon Music, and Pandora.
- **Intelligent Native Autoplay**: Employs advanced native algorithms (Spotify Recommendations, YouTube Music Mixes, Deezer Track Recommendations, and exact ISRC matching) to perfectly curate infinite listening sessions without relying on poor-quality third-party fallbacks.
- **Studio-Grade DSP Filters**: Apply real-time digital signal processing effects including Bassboost, Nightcore, Vaporwave, 8D Audio, Karaoke, Tremolo, and Vibrato without latency penalties.

### User Experience
- **Dynamic Interactive Controller**: A fully functional, responsive button-based player interface allowing intuitive control over playback, skipping, shuffling, looping, and volume manipulation.
- **Precision Synced Lyrics**: Real-time lyrics fetching engine that synchronizes perfectly with the audio timestamp, providing an immersive sing-along experience.
- **Hybrid Command Architecture**: 100% compatibility across both traditional text-based prefix commands and modern Discord slash commands for ultimate user accessibility.
- **Persistent Global AFK System**: A robust cross-server AFK tracking system that alerts users instantly when a tagged member is currently away.

### Moderation & Infrastructure
- **Granular Access Control (Nexus System)**: Absolute administrative control featuring comprehensive blacklist and ignore mechanics targeting specific users, roles, channels, or entire guilds.
- **Application-Owned Emojis**: Includes a fully automated `migrate.py` utility that scrapes, downloads, and migrates custom emojis directly to your bot's application scope, bypassing server-based emoji slots.
- **Enterprise-Grade Scaling**: Built-in AutoSharding support backed by Redis caching and PostgreSQL persistent storage, designed from the ground up to efficiently handle thousands of concurrent voice connections.

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

### Lavalink Server Setup & Configuration

Mythos requires a highly customized Lavalink v4+ instance with specific plugins (LavaSrc, SkyBot, SponsorBlock, LavaLyrics, LavaSearch, and SlugYZeon) to function correctly. A pre-configured `application.yml` is provided in the `lavalink/` directory.

#### Step 1: Server Installation
1. Install **Java 17** or newer on your host machine.
2. Download the latest `Lavalink.jar` (v4.0.0 or higher) from the official [Lavalink releases](https://github.com/lavalink-devs/Lavalink/releases).
3. Create a folder named `lavalink` and place the downloaded `Lavalink.jar` inside it.
4. Copy the provided `lavalink/application.yml` from this repository into your new `lavalink` folder next to the JAR file.

#### Step 2: Configuring Tokens
To enable playback and searching across premium platforms, you must provide valid credentials in your `application.yml` file. Open `lavalink/application.yml` and replace the placeholder strings with your actual data:

| Service | Required Fields | Acquisition Method |
|---------|----------------|-------------------|
| **YouTube** | `pot.token`<br>`pot.visitorData`<br>`oauth.refreshToken` | Obtain PoT tokens by inspecting network requests (specifically `player` requests) on YouTube Music. Use a Lavalink OAuth generator for the refresh token. |
| **Spotify** | `spDc` | Log into Spotify in an incognito window, open Developer Tools (F12) -> Application -> Cookies, and copy the value of `sp_dc`. |
| **Deezer** | `arl`<br>`masterDecryptionKey` | Extract the `arl` cookie from Deezer via browser Developer Tools. The master decryption key can be found in public audio engineering or Lavalink forums. |
| **Apple Music**| `mediaAPIToken` | Inspect network requests on the Apple Music Web Player (listen.apple.com) and locate the JWT token in the request headers. |
| **JioSaavn** | `secretKey` | Required for decrypting JioSaavn media streams. Replace the placeholder with the appropriate DES encryption key. |

#### Step 3: Running the Server
Once your tokens are configured, start the Lavalink server:
```bash
java -jar Lavalink.jar
```
Lavalink will automatically download the required plugins specified in the `application.yml` on its first startup. Ensure the node details (Host, Port, and Password) in your `data/config.json` match the values defined in your `application.yml`.
## Support

Need help setting up the bot or want to stay updated on the latest features? Join the official Mythos support server!

<div align="center">
  <a href="https://discord.gg/HwHD8a5QXa">
    <img src="https://discordapp.com/api/guilds/1270760786817450086/widget.png?style=banner2" alt="Discord Server Widget">
  </a>
</div>

## License

This project is licensed under the **GPL-3.0 License** — see the [LICENSE](LICENSE) file for details. This means if you modify and distribute this code, you must open-source your modifications and provide proper credit to `xylen-py`.
