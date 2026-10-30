from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING

import discord
from discord import ButtonStyle, Embed, Interaction, ui

if TYPE_CHECKING:
    from .music_service import MusicService

_YT_ID = re.compile(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})")
_QUEUE_PREVIEW = 5


class SkipModal(ui.Modal, title="Skip songs"):
    count = ui.TextInput(label="How many songs to skip?", default="2", max_length=3)

    def __init__(self, service: MusicService):
        super().__init__()
        self._service = service

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            n = int(str(self.count))
        except ValueError:
            n = 0
        if n < 1:
            await interaction.response.send_message(
                "Please enter a number of at least 1.", ephemeral=True
            )
            return
        await interaction.response.defer()
        await self._service.skip_songs(interaction.guild, n, interaction.user)


class PlayerView(ui.View):
    def __init__(self, service: MusicService, paused: bool = False):
        super().__init__(timeout=None)
        self._service = service
        self.pause_button.label = "Resume" if paused else "Pause"
        self.pause_button.emoji = "▶️" if paused else "⏸️"

    async def interaction_check(self, interaction: Interaction) -> bool:
        voice_client = interaction.guild.voice_client if interaction.guild else None
        user_voice = getattr(interaction.user, "voice", None)
        if (
            voice_client is None
            or user_voice is None
            or user_voice.channel != voice_client.channel
        ):
            await interaction.response.send_message(
                "Join the bot's voice channel to use these controls.", ephemeral=True
            )
            return False
        return True

    @ui.button(label="Pause", emoji="⏸️", style=ButtonStyle.secondary)
    async def pause_button(self, interaction: Interaction, button: ui.Button) -> None:
        await interaction.response.defer()
        await self._service.toggle_pause(interaction.guild)

    @ui.button(label="Skip", emoji="➡️", style=ButtonStyle.secondary)
    async def skip_button(self, interaction: Interaction, button: ui.Button) -> None:
        await interaction.response.defer()
        await self._service.skip_songs(interaction.guild, 1, interaction.user)

    @ui.button(label="Skip N", emoji="⏩", style=ButtonStyle.secondary)
    async def skip_n_button(self, interaction: Interaction, button: ui.Button) -> None:
        await interaction.response.send_modal(SkipModal(self._service))

    @ui.button(label="Mix", emoji="🔀", style=ButtonStyle.secondary)
    async def mix_button(self, interaction: Interaction, button: ui.Button) -> None:
        await interaction.response.defer()
        await self._service.mix_and_refresh()

    @ui.button(label="Queue", emoji="📜", style=ButtonStyle.secondary)
    async def queue_button(self, interaction: Interaction, button: ui.Button) -> None:
        queue = self._service._queue_list
        if not queue:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return
        lines = [f"{i + 1}. {s.title}" for i, s in enumerate(queue)]
        text = "**Current Queue:**\n" + "\n".join(lines)
        if len(text) > 1900:
            text = text[:1900].rsplit("\n", 1)[0] + f"\n… ({len(queue)} songs total)"
        await interaction.response.send_message(text, ephemeral=True)


class PlayerPanel:
    """A single 'now playing' message with controls, kept at the bottom of the channel."""

    def __init__(self, service: MusicService):
        self._service = service
        self._message: discord.Message | None = None
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _build(self, channel, status: str | None) -> tuple[Embed, ui.View | None]:
        service = self._service
        song = service._current_song
        queue = service._queue_list
        voice_client = channel.guild.voice_client
        paused = bool(voice_client and voice_client.is_paused())
        active = bool(song or queue)

        if not active:
            embed = Embed(
                title="⏹️ Nothing is playing",
                description=status or "Use `!p <url>` to add a song.",
                color=0x747F8D,
            )
            return embed, None

        if song:
            embed = Embed(
                title=f"{'⏸️' if paused else '🎵'} {song.title}",
                url=song.url,
                color=0xF1C40F if paused else 0x1DB954,
            )
            match = _YT_ID.search(song.url)
            if match:
                embed.set_thumbnail(
                    url=f"https://i.ytimg.com/vi/{match.group(1)}/hqdefault.jpg"
                )
            embed.set_author(name="Paused" if paused else "Now playing")
        else:
            embed = Embed(title="⏳ Loading next song…", color=0x3498DB)

        if status:
            embed.description = status
        if queue:
            preview = "\n".join(
                f"{i + 1}. {s.title}" for i, s in enumerate(queue[:_QUEUE_PREVIEW])
            )
            more = len(queue) - _QUEUE_PREVIEW
            if more > 0:
                preview += f"\n… and {more} more"
            embed.add_field(name=f"Up next ({len(queue)})", value=preview[:1024])
        return embed, PlayerView(service, paused=paused)

    async def update(self, channel, status: str | None = None) -> None:
        async with self._lock:
            try:
                embed, view = self._build(channel, status)
                msg = self._message
                if msg is not None and msg.channel.id == channel.id:
                    if channel.last_message_id == msg.id:
                        await msg.edit(embed=embed, view=view)
                        return
                    await self._delete(msg)
                elif msg is not None:
                    await self._delete(msg)
                self._message = await channel.send(embed=embed, view=view)
            except Exception as e:
                self.logger.warning(f"Failed to update player panel: {e}")
                self._message = None

    async def _delete(self, msg: discord.Message) -> None:
        try:
            await msg.delete()
        except Exception:
            pass
        self._message = None
