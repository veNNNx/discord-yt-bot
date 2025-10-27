from attrs import define, field
from discord import Intents
from discord.ext.commands import Bot

from src.modules.music import MusicCog, MusicService
from src.modules.utils import CleanupService, UtilsCog, UtilsService


@define
class DiscordBot(Bot):
    command_prefix: str
    intents: Intents
    music_service: MusicService = field(init=False)
    utils_service: UtilsService = field(init=False)
    cleanup_service: CleanupService = field(init=False)

    def __attrs_post_init__(self) -> None:
        super().__init__(command_prefix=self.command_prefix, intents=self.intents)
        self._setup_services()

    def _setup_services(self) -> None:
        self.music_service = MusicService()
        self.utils_service = UtilsService()
        self.cleanup_service = CleanupService()

    async def _setup_cogs(self) -> None:
        await self.add_cog(MusicCog(bot=self, music_service=self.music_service))
        await self.add_cog(UtilsCog(bot=self, utils_service=self.utils_service))

    async def on_ready(self) -> None:
        if self.user:
            await self.utils_service.on_ready(user=self.user)
        self.loop.create_task(self.cleanup_service.run())

    async def clear_music_queue(self) -> None:
        await self.music_service.clear_queue()
