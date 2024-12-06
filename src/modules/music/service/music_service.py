import asyncio
import logging
from random import shuffle

import discord
from attrs import define, field
from discord import VoiceClient, VoiceProtocol
from discord.ext.commands import Context
from yt_dlp import YoutubeDL  # type: ignore[import-untyped]

from .playlist_handler import PlaylistHandler, Queue


# mypy: disable_error_code="union-attr"
@define
class MusicService:
    _playlist_handler: PlaylistHandler = field(init=False)
    _queue_list: list[Queue] = field(factory=list)
    logger: logging.Logger = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._playlist_handler = PlaylistHandler()

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
            asyncio.create_task(
                self._playlist_handler.get_remaining_urls_from_playlist(
                    url=url, queue_list=self._queue_list, ctx=ctx
                )
            )

        else:
            title = await self._playlist_handler._fetch_title_from_url(url)
            self._queue_list.append(Queue(url=url, title=title))
            await ctx.send(f"Added to queue: {title or 'Unknown title'}")

        if not voice_client.is_playing():
            while not self._queue_list:
                await asyncio.sleep(1)
            asyncio.create_task(self._process_playlist(ctx, voice_client))  # type: ignore[arg-type]

    async def skip(self, ctx: Context, voice_clients: list[VoiceClient]) -> None:
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

    async def _play(
        self,
        ctx: Context,
        url: str,
        voice_client: VoiceClient,
    ) -> None:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "extractor-args": "youtube:player_client=web",
            "audioformat": "mp3",
            "playlistend": 300,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                song = ydl.extract_info(url, download=False)
                audio_url = next(
                    (
                        fmt["url"]
                        for fmt in song["formats"]
                        if fmt.get("acodec") != "none"
                    ),
                    None,
                )

                if audio_url:
                    if not voice_client.is_playing():
                        voice_client.play(
                            discord.FFmpegPCMAudio(
                                audio_url,
                                before_options="-nostdin",
                                options="-vn",
                            )
                        )
                        await ctx.send(f'**Now playing:** {song["title"]}')
                else:
                    await ctx.send(
                        "Unable to extract audio URL for the requested video. This song will be skipped."
                    )

        except Exception as e:
            self.logger.error(f"Error while playing audio: {e}")
            await ctx.send(
                f"An error occurred while trying to play the requested audio: {e}"
            )
