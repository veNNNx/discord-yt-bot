from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, cast

from discord import Embed, VoiceClient
from discord.ext.commands import (
    BadArgument,
    Cog,
    CommandNotFound,
    Context,
    MissingRequiredArgument,
    command,
)

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

    @command(name="h", help="Show help for commands")
    async def help_music(self, ctx: Context):
        embed = Embed(
            title="Help",
            description="List of available commands and how to use them",
            color=0x1DB954,
        )

        embed.add_field(
            name="Play a song",
            value="`!p <url>`",
            inline=False,
        )
        embed.add_field(
            name="Play memory playlist",
            value="`!pl <playlist_id>`",
            inline=False,
        )
        embed.add_field(
            name="Memory playlist controls",
            value=(
                "`!pl-c <name>` — Create a new empty memory playlist\n"
                "`!pl-a <playlist_id> <url>` — Add a YouTube URL to a memory playlist\n"
                "`!pl-l` — List all saved playlists\n"
                "`!pl-s <playlist_id>` — Show all songs in a memory playlist\n"
                "`!pl-r <playlist_id> <track_id>` — Remove a track from a memory playlist"
            ),
            inline=False,
        )
        embed.add_field(
            name="Queue controls",
            value=(
                "`!q` — Show current music queue\n"
                "`!s` — Skip the currently playing song\n"
                "`!sa` — Skip all songs\n"
                "`!mix` — Shuffle the current queue"
            ),
            inline=False,
        )
        embed.add_field(
            name="General bot controls",
            value=("`!l` — Leave the voice channel\n`!r` - Reboot the bot container`",),
            inline=False,
        )

        await ctx.send(embed=embed)

    @command(name="l", help="Leave the voice channel")
    async def leave(self, ctx: Context) -> None:
        if self.bot.music_service._playlist_task:
            self.bot.music_service._playlist_task.cancel()
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

    @Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            cmd = ctx.command
            usage = f"!{cmd.name}"
            for name, param in cmd.params.items():
                if name != "self":  # ignore self/cog
                    if param.default is param.empty:
                        usage += f" <{name}>"
                    else:
                        usage += f" [{name}]"
            await ctx.send(f"Invalid command.\nCorrect usage: `{usage}`")

        elif isinstance(error, BadArgument):
            await ctx.send(
                "Invalid argument type.\nPlease check the correct usage of the command."
            )

        elif isinstance(error, CommandNotFound):
            await ctx.send(
                "Command not found.\nType `!help` to see all available commands."
            )

        else:
            raise error
