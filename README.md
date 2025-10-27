# Discord YouTube Music Bot

A feature-rich **Discord bot** for streaming and managing **YouTube music** directly in your voice channels.  
Deployed via **Portainer**, this bot provides a simple and powerful way to play, organize, and control music through Discord commands.

## Key Features

### Music Playback
- **`!p <url>`** - Play a song or YouTube playlist.  
  The bot automatically joins your voice channel and streams high-quality audio.  
- **`!q`** - Show the current playback queue.  
- **`!s`** - Skip the currently playing song.  
- **`!sa`** - Skip all songs and clear the queue.  
- **`!mix`** - Shuffle the entire playlist order for a new listening experience.  

### Memory Playlists
Create and manage persistent playlists that you can play later.

- **`!pl-c <name>`** - Create a new empty playlist with selected name.  
- **`!pl-d <playlist_id>`** - Delete the playlist.  
- **`!pl-a <playlist_id> <url>`** - Add a YouTube URL to a saved playlist.  
- **`!pl-r <playlist_id> <track_id>`** - Remove a song from a playlist.  
- **`!pl-l`** - List all available memory playlists.  
- **`!pl-s <playlist_id>`** - List all songs in selected playlist.  
- **`!pl <playlist_id>`** - Play an existing memory playlist directly in your voice channel.  

Playlists are stored in memory and can easily be accessed again.


### Utility Commands
- **`!h`** — Display help for all available commands.  
- **`!l`** — Leave the current voice channel.  
- **`!r`** — Reboot the bot service (if hosted in docker container).  


## Under the Hood

This bot is powered by a clean, modular architecture:

- **`MusicService`** – handles playback, queue management, and background prefetching for smooth transitions between songs.  
- **`YtPlaylistHandler`** – fetches and parses YouTube playlists.  
- **`MemoryPlaylistHandler`** – manages in-memory playlists.  
- **`MusicCog`** and **`UtilsCog`** – expose commands for user interaction.

💡 The bot **prefetches the next song** while the current one is playing, minimizing any silence between tracks.

# Deployment

## Prerequirements
* Create bot with proper access rights in discord developer platform.

* Create `YouTube Data API v3` token in `Google Developers Console`.
* Create file `config.py` with proper tokens.
```bash
DISCORD_BOT_TOKEN = "........"
YOUTUBE_API_KEY = "............"
```


## Setup docker image on server
* Drop all files or clone repository on server (create config.py and add tokens)
* Change permissions `chmod +x install_requirements.sh`
* Change permissions `chmod +x  src/modules/utils/scripts/restart.sh`
* Setup proper volume on server for static folder for in-memory playlists
* Create Docker Image using content of `Dockerfile` and files from repository.
* Create Custom Template in portainer using `portainer_template.txt`.
* Deploy the stack.

# TBD
## Skip to selected song in queue

