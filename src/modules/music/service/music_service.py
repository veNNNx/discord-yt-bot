import asyncio
import logging

import discord
import yt_dlp as youtube_dl
from attrs import define, field
from discord import VoiceClient, VoiceProtocol
from discord import utils as discord_utils
from discord.ext.commands import Context

from .playlist_handler import PlaylistHandler, Queue


@define
class MusicService:
    _playlist_handler: PlaylistHandler = field(init=False)
    _queue_list: list[Queue] = []
    logger: logging.Logger = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._playlist_handler = PlaylistHandler()

    async def play(
        self,
        ctx: Context,
        url: str,
        voice_clients: list[VoiceClient] | list[VoiceProtocol],
    ) -> None:
        self.logger.info(f"{ctx.author} requested to play URL: {url}")

        if "list=" in url:
            self.logger.info("Gathering playlist")
            await self._playlist_handler.get_remaining_urls_from_playlist(
                url=url, queue_list=self._queue_list
            )

        await asyncio.sleep(10)  # Potrzebne na zbieranie piosenek z playlisty, jeśli są

        if self._queue_list:
            first_song = self._queue_list.pop(0)
            now_playing_url = first_song.url
        else:
            await ctx.send("No songs found in the playlist.")
            return

        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to play music.")
            return

        channel = ctx.author.voice.channel

        if not voice_channel:
            await channel.connect()
            voice_channel = discord_utils.get(voice_clients, guild=ctx.guild)

        await self._play(ctx=ctx, url=now_playing_url, voice_channel=voice_channel)

    async def _play(
        self,
        ctx: Context,
        url: str,
        voice_channel: VoiceClient,
    ) -> None:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "extractor-args": "youtube:player_client=web",
            "audioformat": "mp3",
            "playlistend": 300,
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
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
                    if not voice_channel.is_playing():
                        voice_channel.play(
                            discord.FFmpegPCMAudio(
                                audio_url,
                                before_options="-nostdin",
                                options="-vn",
                            ),
                            after=lambda e: asyncio.run_coroutine_threadsafe(
                                self._after_play(ctx, voice_channel),
                                asyncio.get_event_loop(),
                            ),
                        )
                        await ctx.send(f'Now playing: {song["title"]}')
                else:
                    await ctx.send(
                        "Unable to extract audio URL for the requested video. This song will be skipped."
                    )

        except Exception as e:
            self.logger.error(f"Error while playing audio: {e}")
            await ctx.send(
                f"An error occurred while trying to play the requested audio: {e}"
            )

    async def _after_play(self, ctx: Context, voice_channel: VoiceClient) -> None:
        # To jest wywoływane po zakończeniu odtwarzania aktualnej piosenki
        if self._queue_list:
            await self._play_next(ctx, voice_channel)
        else:
            await ctx.send("Queue is empty. Disconnecting.")
            await voice_channel.disconnect()

    async def _play_next(self, ctx: Context, voice_channel: VoiceClient) -> None:
        if not voice_channel.is_connected():
            await ctx.send("Reconnecting to the voice channel.")
            await voice_channel.connect(
                reconnect=True, timeout=60
            )  # Upewnij się, że timeout jest podany

        if not self._queue_list:
            await ctx.send("Queue is empty. Disconnecting.")
            await voice_channel.disconnect()
            return

        next_song = self._queue_list.pop(0)

        if next_song:
            if voice_channel.is_playing():
                await ctx.send(
                    "Already playing audio, waiting for current track to finish..."
                )
                return  # Nie próbuj ponownie odtwarzać, jeśli już odtwarza

            def after_callback(e):
                # To jest wywoływane po zakończeniu odtwarzania
                if e:
                    asyncio.run_coroutine_threadsafe(
                        self._handle_playback_error(e, ctx, voice_channel),
                        asyncio.get_event_loop(),
                    )
                else:
                    asyncio.run_coroutine_threadsafe(
                        self._play_next(ctx, voice_channel),
                        asyncio.get_event_loop(),
                    )

            try:
                voice_channel.play(
                    discord.FFmpegPCMAudio(
                        next_song.url,
                        before_options="-nostdin",
                        options="-vn",
                    ),
                    after=after_callback,
                )
                await ctx.send(f"Now playing: {next_song.title}")
            except Exception as e:
                self.logger.error(f"Error playing audio: {e}")
                await ctx.send(f"Error while trying to play: {e}")
        else:
            await ctx.send("No songs left in the queue.")
            await voice_channel.disconnect()

    async def _handle_playback_error(
        self, error, ctx: Context, voice_channel: VoiceClient
    ) -> None:
        self.logger.error(f"Playback error: {error}")
        await ctx.send("An error occurred during playback. Skipping to the next song.")
        await self._play_next(ctx=ctx, voice_channel=voice_channel)
