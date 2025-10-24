import asyncio
import logging
import os
from random import shuffle

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

        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to play music.")
            return

        channel = ctx.author.voice.channel
        voice_client = discord.utils.get(voice_clients, guild=ctx.guild)
        if not voice_client:
            voice_client = await channel.connect()

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

        if not voice_client.is_playing():
            while not self._queue_list:
                await asyncio.sleep(1)
            asyncio.create_task(self._process_playlist(ctx, voice_client))  # type: ignore[arg-type]

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

    async def skip(self, ctx: Context, voice_clients: list[VoiceClient]) -> None:
        self.logger.info("Skipping")
        voice_client = discord.utils.get(voice_clients, guild=ctx.guild)
        if self._queue_list:
            voice_client.stop()
            asyncio.create_task(self._process_playlist(ctx, voice_client))  # type: ignore[arg-type]
        elif not voice_client or not voice_client.is_playing():
            await ctx.send("No song is currently playing.")
            return

    async def skip_all(self, ctx: Context, voice_clients: list[VoiceClient]) -> None:
        voice_client = discord.utils.get(voice_clients, guild=ctx.guild)
        if self._queue_list:
            voice_client.stop()
            await ctx.send("**Queue cleared.**")
            await self.clear_queue()
            asyncio.create_task(self._process_playlist(ctx, voice_client))  # type: ignore[arg-type]
        elif not voice_client or not voice_client.is_playing():
            await ctx.send("No song is currently playing.")
            return

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
        self._queue_list = []

    async def mix_playlist(self) -> None:
        shuffle(self._queue_list)

    async def _process_playlist(self, ctx: Context, voice_client: VoiceClient) -> None:
        while self._queue_list:
            if not voice_client.is_playing():
                next_song = self._queue_list[0]
                await self._play(ctx=ctx, url=next_song.url, voice_client=voice_client)
                del self._queue_list[0]
            await asyncio.sleep(2)

    # async def _play(
    #     self,
    #     ctx: Context,
    #     url: str,
    #     voice_client: VoiceClient,
    # ) -> None:
    #     def after_playing(error):
    #         if error:
    #             asyncio.run_coroutine_threadsafe(
    #                 ctx.send(f"Stream interrupted for: {song['title']} — retrying..."),
    #                 ctx.bot.loop,
    #             )
    #             asyncio.run_coroutine_threadsafe(
    #                 self._play(ctx, url, voice_client), ctx.bot.loop
    #             )
    #         else:
    #             asyncio.run_coroutine_threadsafe(
    #                 ctx.send(f"Finished playing: {song['title']}"), ctx.bot.loop
    #             )

    #     ydl_opts = {
    #         "format": "251/bestaudio/best",
    #         "quiet": True,
    #         "noplaylist": True,
    #         "extractor_args": {"youtube": {"player_client": ["android"]}},
    #         "downloader_args": {
    #             "ffmpeg_i": [
    #                 "-reconnect",
    #                 "1",
    #                 "-reconnect_streamed",
    #                 "1",
    #                 "-reconnect_delay_max",
    #                 "5",
    #                 "-err_detect",
    #                 "ignore_err",
    #                 "-timeout",
    #                 "5000000",
    #             ]
    #         },
    #     }

    #     ffmpeg_before_opts = (
    #         "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "
    #         "-reconnect_at_eof 1 -err_detect ignore_err -timeout 5000000 -nostdin"
    #     )

    #     try:
    #         with YoutubeDL(ydl_opts) as ydl:
    #             song = ydl.extract_info(url, download=False)
    #             audio_url = next(
    #                 (
    #                     fmt["url"]
    #                     for fmt in song["formats"]
    #                     if fmt.get("acodec") != "none"
    #                 ),
    #                 None,
    #             )
    #             if audio_url:
    #                 if not voice_client.is_playing():
    #                     voice_client.play(
    #                         discord.FFmpegPCMAudio(
    #                             audio_url,
    #                             # before_options="-nostdin",
    #                             before_options=ffmpeg_before_opts,
    #                             options="-vn",
    #                         ),
    #                         after=after_playing,
    #                     )
    #                     await ctx.send(f"**Now playing:** {song['title']}")
    #             else:
    #                 await ctx.send(
    #                     f"Unable to extract audio URL for the requested video. This song will be skipped. {song['title']}"
    #                 )

    #     except Exception as e:
    #         self.logger.error(f"Error while playing audio: {e}")
    #         await ctx.send(
    #             f"An error occurred while trying to play the requested audio: {e}"
    #         )
    async def _play(
        self,
        ctx: Context,
        url: str,
        voice_client: VoiceClient,
    ) -> None:
        downloads_dir = "./downloads"
        os.makedirs(downloads_dir, exist_ok=True)

        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "noplaylist": True,
            "outtmpl": os.path.join(downloads_dir, "%(title)s.%(ext)s"),
            "extractor_args": {"youtube": {"player_client": ["android"]}},
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                title = info.get("title", "Unknown Title")

            if not os.path.exists(file_path):
                await ctx.send(f"Failed to download: {title}")
                return

            async def after_playing_wrapper(error):
                try:
                    if error:
                        await ctx.send(f"Error while playing {title}: {error}")
                finally:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            self.logger.info(f"Deleted file: {file_path}")
                    except Exception as e:
                        self.logger.warning(f"Failed to remove file {file_path}: {e}")

                    if self._queue_list:
                        asyncio.create_task(self._process_playlist(ctx, voice_client))

            def _after_playing(error):
                asyncio.run_coroutine_threadsafe(
                    after_playing_wrapper(error),
                    ctx.bot.loop,
                )

            if not voice_client.is_playing():
                source = discord.FFmpegPCMAudio(
                    file_path,
                    before_options="-nostdin",
                    options="-vn",
                )
                voice_client.play(source, after=_after_playing)
                await ctx.send(f"**Now playing:** {title}")

        except Exception as e:
            await ctx.send(f"Failed to download or play: {e}")
            self.logger.error(f"Error while playing {url}: {e}")
