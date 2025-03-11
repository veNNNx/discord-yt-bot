from __future__ import annotations

from typing import TYPE_CHECKING, cast

from discord import VoiceClient
from discord.ext.commands import Cog, Context, command

from ..service.utils_service import UtilsService

if TYPE_CHECKING:
    from src.bot import DiscordBot


class UtilsCog(Cog):
    _utils_service: UtilsService
    bot: DiscordBot

    def __init__(self, bot: DiscordBot, utils_service: UtilsService):
        self.bot = bot
        self._utils_service = utils_service
        self._utils_service.start_check_inactivity(bot=self.bot)

    @command(name="l", help="Leave the voice channel")
    async def leave(self, ctx: Context) -> None:
        await self.bot.clear_music_queue()
        await self._utils_service.leave(
            ctx=ctx, voice_clients=cast(list[VoiceClient], self.bot.voice_clients)
        )
