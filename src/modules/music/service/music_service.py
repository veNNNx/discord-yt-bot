import asyncio
import logging

import discord
import yt_dlp as youtube_dl
from attrs import define, field
from discord import VoiceClient
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

    async def play(self, ctx: Context, url: str) -> None:
        self.logger.info(f"{ctx.author} requested to play URL: {url}")

        if "list=" in url:
            self.logger.info("Gathering playlist")
            asyncio.create_task(
                self._playlist_handler.get_remaining_urls_from_playlist(
                    url=url, queue_list=self._queue_list
                )
            )
            await asyncio.sleep(6)
        else:
            song_title = await self._get_song_title(url)
            if song_title:
                self._queue_list.append(Queue(url=url, title=song_title))
                self.logger.info(f"Added song to queue: {song_title}")
                if len(self._queue_list) > 0:
                    await self._connect_and_play(ctx)

        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to play music.")
            return

        voice_channel = discord_utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        channel = ctx.author.voice.channel

        if not voice_channel:
            voice_channel = await channel.connect()
        else:
            await voice_channel.move_to(channel)

        await self._play(ctx=ctx, voice_channel=voice_channel)

    async def _play(self, ctx: Context, voice_channel: VoiceClient) -> None:
        if not self._queue_list:
            await ctx.send("Queue is empty.")
            self.logger.info("Queue is empty")
            await voice_channel.disconnect()
            return

        url = self._queue_list.pop(0).url
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "extractor-args": "youtube:player_client=web",
            "audioformat": "mp3",
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

    async def _after_play(self, ctx: Context, voice_channel: VoiceClient) -> None:
        if self._queue_list:
            await self._play(ctx, voice_channel)
        else:
            await ctx.send("Queue is empty. Disconnecting.")
            await voice_channel.disconnect()

    async def skip(self, ctx: Context) -> None:
        voice_channel = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if voice_channel and voice_channel.is_playing():
            voice_channel.stop()
            if self._queue_list:
                await self._play(ctx, voice_channel)
            else:
                await ctx.send("No more songs in the queue.")

    async def show_queue(self, ctx: Context) -> None:
        if not self._queue_list:
            await ctx.send("Queue is empty.")
        else:
            queue_str = "\n".join(
                f"{idx + 1}. {song.title}" for idx, song in enumerate(self._queue_list)
            )
            await ctx.send(f"Current queue:\n{queue_str}")

    async def clear_queue(self, ctx: Context) -> None:
        if not self._queue_list:
            await ctx.send("Queue is empty.")
        else:
            self._queue_list.clear()
            await ctx.send("Queue cleared")

    async def _connect_and_play(self, ctx: Context) -> None:
        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to play music.")
            return

        voice_channel = discord_utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        channel = ctx.author.voice.channel

        if not voice_channel:
            voice_channel = await channel.connect()

        await self._play(ctx=ctx, voice_channel=voice_channel)

    async def _get_song_title(self, url: str) -> str:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "extractor-args": "youtube:player_client=web",
        }
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                song_info = ydl.extract_info(url, download=False)
                return song_info.get("title", "Unknown Title")
        except Exception as e:
            self.logger.error(f"Error retrieving song title: {e}")
            return None
