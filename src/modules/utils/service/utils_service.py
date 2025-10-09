# mypy: disable_error_code="attr-defined"
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from attrs import define, field
from discord import ClientUser, VoiceClient, VoiceProtocol
from discord import utils as discord_utils
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from src.bot import DiscordBot


@define
class UtilsService:
    logger: logging.Logger = field(init=False)
    check_inactivity: tasks.Loop = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _create_check_inactivity_loop(self, bot: DiscordBot):
        @tasks.loop(minutes=5)
        async def loop():
            voice_clients = [vc for vc in bot.voice_clients if not vc.is_playing()]
            for voice_channel in voice_clients:
                self.logger.debug(
                    f"Bot disconnected from {voice_channel.channel.name} due to inactivity"
                )
                await voice_channel.disconnect(force=True)

        return loop

    def start_check_inactivity(self, bot: DiscordBot):
        self.check_inactivity = self._create_check_inactivity_loop(bot)
        if not self.check_inactivity.is_running():
            self.check_inactivity.start()

    async def on_ready(self, user: ClientUser) -> None:
        self.logger.debug(f"Logged in as {user.name} ({user.id})")

    async def leave(
        self,
        ctx: commands.Context,
        voice_clients: list[VoiceClient] | list[VoiceProtocol],
    ) -> None:
        self.logger.info("Bot disconnecting...")
        voice_channel = discord_utils.get(voice_clients, guild=ctx.guild)
        if voice_channel and voice_channel.is_connected():
            await voice_channel.disconnect(force=True)
