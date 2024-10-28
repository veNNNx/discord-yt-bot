# mypy: disable_error_code="attr-defined"
import logging

from attrs import define, field
from discord import ClientUser, VoiceClient, VoiceProtocol
from discord import utils as discord_utils
from discord.ext import commands, tasks


@define
class UtilsService:
    logger: logging.Logger = field(init=False)
    check_inactivity: tasks.Loop = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.check_inactivity = self._create_check_inactivity_loop()

    def _create_check_inactivity_loop(self):
        @tasks.loop(minutes=5)
        async def loop(voice_clients: list[VoiceClient] | list[VoiceProtocol]) -> None:
            for voice_channel in voice_clients:
                if not voice_channel.is_playing():
                    self.logger.debug(
                        f"Bot disconnected from {voice_channel.channel.name} due to inactivity"
                    )
                    await voice_channel.disconnect(force=True)

        return loop

    async def on_ready(
        self,
        user: ClientUser,
        voice_clients: list[VoiceClient] | list[VoiceProtocol],
    ) -> None:
        self.logger.debug(f"Logged in as {user.name} ({user.id})")
        self.check_inactivity.start(voice_clients=voice_clients)

    @staticmethod
    async def leave(
        ctx: commands.Context,
        voice_clients: list[VoiceClient] | list[VoiceProtocol],
    ) -> None:
        voice_channel = discord_utils.get(voice_clients, guild=ctx.guild)
        if voice_channel and voice_channel.is_connected():
            await voice_channel.disconnect(force=True)
