from typing import cast

from attrs import define, field
from discord import Intents, VoiceClient
from discord.ext.commands import Bot

from src.modules.music import MusicCog, MusicService
from src.modules.utils import UtilsCog, UtilsService


@define
class DiscordBot(Bot):
    command_prefix: str
    intents: Intents
    music_service: MusicService = field(init=False)
    utils_service: UtilsService = field(init=False)

    def __attrs_post_init__(self) -> None:
        super().__init__(command_prefix=self.command_prefix, intents=self.intents)
        self._setup_services()

    async def on_ready(self) -> None:
        if self.user:
            await self.utils_service.on_ready(
                user=self.user,
                voice_clients=cast(list[VoiceClient], self.voice_clients),
            )

    def _setup_services(self) -> None:
        self.music_service = MusicService()
        self.utils_service = UtilsService()

    async def _setup_cogs(self) -> None:
        await self.add_cog(MusicCog(bot=self, music_service=self.music_service))
        await self.add_cog(UtilsCog(bot=self, utils_service=self.utils_service))
