from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from discord.ext.commands import Cog, Context, command

from ..service.music_service import MusicService

if TYPE_CHECKING:
    from src.bot import DiscordBot


class MusicCog(Cog):
    bot: DiscordBot
    _music_service: MusicService

    def __init__(self, bot: DiscordBot, music_service: MusicService):
        self.bot = bot
        self._music_service = music_service

    @command(name="p", help="Play a song or playlist from YouTube")
    async def play(self, ctx: Context, url: str) -> None:
        asyncio.create_task(
            self._music_service.play(
                ctx=ctx, url=url, voice_clients=self.bot.voice_clients
            )
        )

    @command(name="pl", help="Play from a memory playlist")
    async def play_playlist(self, ctx: Context, playlist_id: int) -> None:
        asyncio.create_task(
            self._music_service.play_from_memory_playlist(
                ctx=ctx, playlist_id=playlist_id, voice_clients=self.bot.voice_clients
            )
        )

    @command(name="pl-c", help="Create a new empty playlist")
    async def create_playlist(self, ctx: Context, name: str):
        asyncio.create_task(
            self._music_service._memory_playlist_handler.create_playlist(
                ctx=ctx, name=name
            )
        )

    @command(name="pl-a", help="Add a url to a playlist")
    async def add_to_playlist(self, ctx: Context, playlist_id: int, url: str):
        asyncio.create_task(
            self._music_service._memory_playlist_handler.add_to_playlist(
                ctx=ctx, playlist_id=playlist_id, url=url
            )
        )

    @command(name="pl-l", help="Show all playlists")
    async def show_playlists(self, ctx: Context):
        asyncio.create_task(
            self._music_service._memory_playlist_handler.show_playlists(ctx=ctx)
        )

    @command(name="pl-s", help="Show all playlists")
    async def show_playlist_content(self, ctx: Context, playlist_id: int):
        asyncio.create_task(
            self._music_service._memory_playlist_handler.show_playlist_content(
                ctx=ctx, playlist_id=playlist_id
            )
        )

    @command(name="pl-r", help="Remove a url from a playlist")
    async def remove_from_playlist(self, ctx: Context, playlist_id: int, track_id: int):
        asyncio.create_task(
            self._music_service._memory_playlist_handler.remove_from_playlist(
                ctx=ctx, playlist_id=playlist_id, track_id=track_id
            )
        )

    @command(name="s", help="Skip the currently playing song")
    async def skip(self, ctx: Context) -> None:
        asyncio.create_task(
            self._music_service.skip(ctx=ctx, voice_clients=self.bot.voice_clients)  # type: ignore[arg-type]
        )

    @command(name="sa", help="Skip all")
    async def skip_all(self, ctx: Context) -> None:
        asyncio.create_task(
            self._music_service.skip_all(ctx=ctx, voice_clients=self.bot.voice_clients)  # type: ignore[arg-type]
        )

    @command(name="mix", help="Shuffle playlist")
    async def mix(self, ctx: Context) -> None:
        asyncio.create_task(self._music_service.mix_playlist())

    @command(name="q", help="Show the current music queue")
    async def show_queue(self, ctx: Context) -> None:
        asyncio.create_task(self._music_service.show_queue(ctx=ctx))
