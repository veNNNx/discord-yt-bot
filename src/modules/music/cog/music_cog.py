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
