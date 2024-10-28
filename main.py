import asyncio
from logging.config import dictConfig

from discord import Intents

from config import DISCORD_BOT_TOKEN
from src.bot import DiscordBot
from src.modules.utils import LOGGING_CONFIG


async def main():
    dictConfig(LOGGING_CONFIG)
    intents = Intents.all()
    discord_bot = DiscordBot(command_prefix="!", intents=intents)
    await discord_bot._setup_cogs()
    await discord_bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
