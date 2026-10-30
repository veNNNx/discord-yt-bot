import asyncio
import logging
import os
from random import shuffle
from urllib.parse import urlparse

import discord
from attrs import define, field
from discord import VoiceClient, VoiceProtocol
from discord.ext.commands import Context
from yt_dlp import YoutubeDL  # type: ignore[import-untyped]

from .memory_playlist_handler import MemoryPlaylistHandler
from .yt_playlist_handler import Queue, YtPlaylistHandler


# mypy: disable_error_code="union-attr"
@define
class MusicService:
    _yt_playlist_handler: YtPlaylistHandler = field(init=False)
    _memory_playlist_handler: MemoryPlaylistHandler = field(init=False)
    _queue_list: list[Queue] = field(factory=list)
    _playlist_task: asyncio.Task | None = None
    _player_task: asyncio.Task | None = field(init=False, default=None)
    _current_song: Queue | None = field(init=False, default=None)
    _downloads: dict[str, asyncio.Task] = field(init=False, factory=dict)
    _downloads_dir = "./downloads"
    logger: logging.Logger = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._yt_playlist_handler = YtPlaylistHandler()
        self._memory_playlist_handler = MemoryPlaylistHandler()

    async def play(
        self,
        ctx: Context,
        url: str,
        voice_clients: list[VoiceClient | VoiceProtocol],
    ) -> None:
        self.logger.info(f"{ctx.author} requested to play URL: {url}")
        if not await self._is_valid_url(url):
            await ctx.send(f"Not a valid URL: '{url}'. Skipping.")
            self.logger.warning(f"Invalid URL provided: {url}")
            return

        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to play music.")
            return

        channel = ctx.author.voice.channel
        voice_client = await self._ensure_voice_client(ctx, channel)

        if "list=" in url:
            self.logger.info("Gathering playlist")
            self._playlist_task = asyncio.create_task(
                self._yt_playlist_handler.get_remaining_urls_from_playlist(
                    url=url, queue_list=self._queue_list, ctx=ctx
                )
            )

        else:
            title = await self._yt_playlist_handler._fetch_title_from_url(url)
            title = title if title else "Unknown title"
            self._queue_list.append(Queue(url=url, title=title))
            await ctx.send(f"Added to queue: {title}")

        self._ensure_player(ctx, voice_client)

    async def _ensure_voice_client(self, ctx: Context, channel) -> VoiceClient:
        voice_client = ctx.guild.voice_client
        if voice_client is not None and not voice_client.is_connected():
            try:
                await voice_client.disconnect(force=True)
            except Exception as e:
                self.logger.warning(f"Failed to drop stale voice client: {e}")
            voice_client = None
        if voice_client is None:
            return await channel.connect()
        return voice_client

    def _ensure_player(self, ctx: Context, voice_client: VoiceClient) -> None:
        if self._player_task is None or self._player_task.done():
            self._player_task = asyncio.create_task(
                self._player_loop(ctx, voice_client.channel)
            )

    def is_busy(self) -> bool:
        return bool(
            self._queue_list
            or self._current_song
            or (self._player_task and not self._player_task.done())
        )

    async def play_from_memory_playlist(
        self,
        ctx: Context,
        playlist_id: int,
        voice_clients: list[VoiceClient | VoiceProtocol],
    ) -> None:
        playlist = await self._memory_playlist_handler.get_playlist_by_id(
            playlist_id=playlist_id
        )
        if not playlist:
            await ctx.send(f"Playlist with ID {playlist_id} not found.")
            return

        self.logger.info(
            f"{ctx.author} requested to play playlist ID: {playlist_id}, title: {playlist.get('title')}"
        )

        if not playlist["data"]:
            await ctx.send("Playlist is empty.")
            return

        await ctx.send(
            f"Playing memory playlist '{playlist['title']}' ({len(playlist['data'])} songs)..."
        )
        for item in playlist["data"]:
            url = item["url"]
            await self.play(ctx, url, voice_clients)

    async def skip(
        self, ctx: Context, voice_clients: list[VoiceClient], count: int = 1
    ) -> None:
        self.logger.info(f"Skipping {count}")
        if count < 1:
            await ctx.send("Number of songs to skip must be at least 1.")
            return
        voice_client = ctx.guild.voice_client
        if not voice_client or not (
            voice_client.is_playing() or voice_client.is_paused()
        ):
            await ctx.send("No song is currently playing.")
            return
        titles = [self._current_song.title if self._current_song else "current song"]
        removed = self._queue_list[: count - 1]
        del self._queue_list[: count - 1]
        titles.extend(song.title for song in removed)
        listing = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(titles))
        await ctx.send(
            f"**Skipped {len(titles)} song(s)** (requested by {ctx.author.display_name}):\n{listing}"
        )
        voice_client.stop()

    async def skip_all(self, ctx: Context, voice_clients: list[VoiceClient]) -> None:
        voice_client = ctx.guild.voice_client
        playing = bool(
            voice_client and (voice_client.is_playing() or voice_client.is_paused())
        )
        if not self._queue_list and not playing:
            await ctx.send("No song is currently playing.")
            return
        await self.clear_queue()
        await ctx.send(f"**Queue cleared** Skipping all songs.")
        if playing:
            voice_client.stop()

    async def show_queue(self, ctx: Context) -> None:
        if not self._queue_list:
            await ctx.send("Queue is empty.")
            return

        queue_display = "\n".join(
            f"{idx + 1}. {song.title}" for idx, song in enumerate(self._queue_list)
        )
        try:
            await ctx.send(f"**Current Queue:**\n{queue_display}")
        except Exception:
            await ctx.send(
                f"**Current Queue is too big to show titles,length:** {len(self._queue_list)}"
            )

    async def clear_queue(self) -> None:
        if self._playlist_task and not self._playlist_task.done():
            self._playlist_task.cancel()
        self._queue_list.clear()

    async def hard_reset(self, guild) -> None:
        """Stop everything: playlist gathering, player loop, playback, downloads."""
        await self.clear_queue()
        for task in (self._player_task, *self._downloads.values()):
            if task and not task.done():
                task.cancel()
        self._player_task = None
        self._downloads.clear()
        self._current_song = None
        voice_client = guild.voice_client if guild else None
        if voice_client:
            try:
                voice_client.stop()
                await voice_client.disconnect(force=True)
            except Exception as e:
                self.logger.warning(f"Error during hard reset: {e}")

    async def mix_playlist(self) -> None:
        shuffle(self._queue_list)

    async def _player_loop(self, ctx: Context, channel) -> None:
        """Single consumer of the queue; the only place that plays songs."""
        try:
            while True:
                if not self._queue_list:
                    if self._playlist_task and not self._playlist_task.done():
                        await asyncio.sleep(1)
                        continue
                    break

                song = self._queue_list.pop(0)
                self._current_song = song

                voice_client = await self._get_connected_client(ctx, channel)
                if voice_client is None:
                    await ctx.send(
                        f"**Skipped:** {song.title} (reason: could not connect to the voice channel)"
                    )
                    self._queue_list.clear()
                    break

                asyncio.create_task(self._prefetch_next_song())
                await self._play(ctx=ctx, song=song, voice_client=voice_client)
                self._current_song = None
        finally:
            self._current_song = None

    async def _get_connected_client(self, ctx: Context, channel) -> VoiceClient | None:
        for attempt in range(3):
            voice_client = ctx.guild.voice_client
            if voice_client is not None and voice_client.is_connected():
                return voice_client
            try:
                if voice_client is not None:
                    await voice_client.disconnect(force=True)
                return await channel.connect()
            except Exception as e:
                self.logger.warning(
                    f"Voice reconnect attempt {attempt + 1} failed: {e}"
                )
                await asyncio.sleep(2)
        return None

    async def _is_valid_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc])
        except Exception:
            return False

    async def _prefetch_next_song(self) -> None:
        if not self._queue_list:
            return

        next_song = self._queue_list[0]

        try:
            await self._download_audio_file(next_song.url)
            self.logger.info(f"Prefetched next song: {next_song.title}")
        except Exception as e:
            self.logger.warning(f"Prefetch failed for {next_song.url}: {e}")

    async def _download_audio_file(self, url: str) -> tuple[str, str]:
        """Download in a worker thread; concurrent requests for a URL share one task."""
        task = self._downloads.get(url)
        if task is None or task.done():
            task = asyncio.create_task(asyncio.to_thread(self._download_blocking, url))
            self._downloads[url] = task
            task.add_done_callback(lambda _t, u=url: self._downloads.pop(u, None))
        return await asyncio.shield(task)

    def _download_blocking(self, url: str) -> tuple[str, str]:
        os.makedirs(self._downloads_dir, exist_ok=True)

        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "noplaylist": True,
            "outtmpl": os.path.join(self._downloads_dir, "%(title)s.%(ext)s"),
            "extractor_args": {"youtube": {"player_client": ["android"]}},
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                file_path = ydl.prepare_filename(info)
                title = info.get("title", "Unknown Title")

                if os.path.exists(file_path):
                    self.logger.debug(f"Using cached file: {file_path}")
                    return file_path, title

                self.logger.info(f"Downloading {title} ...")
                ydl.download([url])

                if not os.path.exists(file_path):
                    raise FileNotFoundError(
                        f"File not found after download: {file_path}"
                    )

                return file_path, title

        except Exception as e:
            self.logger.error(f"Error downloading {url}: {e}")
            raise

    async def _play(
        self,
        ctx: Context,
        song: Queue,
        voice_client: VoiceClient,
    ) -> None:
        try:
            file_path, title = await self._download_audio_file(song.url)
        except Exception as e:
            self.logger.error(f"Error while downloading {song.url}: {e}")
            await ctx.send(f"**Skipped:** {song.title} (reason: download failed: {e})")
            return

        if not voice_client.is_connected():
            voice_client = await self._get_connected_client(ctx, voice_client.channel)
            if voice_client is None:
                await ctx.send(
                    f"**Skipped:** {song.title} (reason: lost connection to the voice channel)"
                )
                return

        loop = asyncio.get_running_loop()
        finished: asyncio.Future = loop.create_future()

        def _after_playing(error):
            loop.call_soon_threadsafe(
                lambda: finished.done() or finished.set_result(error)
            )

        try:
            source = discord.FFmpegPCMAudio(
                file_path, before_options="-nostdin", options="-vn"
            )
            voice_client.play(source, after=_after_playing)
            await ctx.send(f"**Now playing:** {title}")
            error = await finished
            if error:
                await ctx.send(f"Error while playing {title}: {error}")
        except discord.ClientException as e:
            self.logger.error(f"Error while playing {song.url}: {e}")
            await ctx.send(f"**Skipped:** {song.title} (reason: {e})")
        finally:
            if voice_client.is_playing():
                voice_client.stop()
            upcoming = {s.url for s in self._queue_list}
            if song.url not in upcoming:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        self.logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove file {file_path}: {e}")
