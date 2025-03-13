from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, cast
from pathlib import Path
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

    @command(name="r", help="Reboot the bot")
    async def reboot(self, ctx: Context) -> None:
        await ctx.send("Restarting")
        await self._utils_service.leave(
            ctx=ctx, voice_clients=cast(list[VoiceClient], self.bot.voice_clients)
        )
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "restart.sh"
        subprocess.Popen([script_path], shell=True)
