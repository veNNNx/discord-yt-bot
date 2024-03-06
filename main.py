import discord
import yt_dlp as youtube_dl
from discord.ext import commands, tasks

from config import DISCORD_BOT_TOKEN, YOUTUBE_API_KEY

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

queue = []
queue_names = []


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    check_inactivity.start()


@tasks.loop(minutes=5)
async def check_inactivity():
    voice_channel = discord.utils.get(bot.voice_clients)

    if voice_channel and not voice_channel.is_playing():
        await voice_channel.disconnect()
        print("Bot disconnected due to inactivity")


@bot.command(name="p", help="Play a song from YouTube")
async def play(ctx, url):
    channel = ctx.author.voice.channel
    voice_channel = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice_channel:
        await channel.connect()
        voice_channel = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    with youtube_dl.YoutubeDL({"key": YOUTUBE_API_KEY}) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_format = next(
            (fmt for fmt in info["formats"] if fmt.get("acodec") == "opus"),
            None,
        )

        if audio_format:
            audio_url = audio_format["url"]
            queue.append(audio_url)
            queue_names.append(info["title"])
            if not voice_channel.is_playing():
                play_next(ctx, voice_channel)
                await ctx.send(f'Playing: {info["title"]}')
            else:
                await ctx.send(
                    f'Added to the queue as {len(queue)} in row: {info["title"]}'
                )


@bot.command(name="s", help="Skip the currently playing song")
async def skip(ctx):
    voice_channel = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_channel and voice_channel.is_playing():
        voice_channel.stop()
        if queue:
            play_next(ctx, voice_channel)
        else:
            await ctx.send("Song skipped. Queue is empty.")
    else:
        await ctx.send("No song is currently playing to skip.")
        voice_channel.disconnect()


@bot.command(name="l", help="Leave the voice channel")
async def leave(ctx):
    voice_channel = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_channel.is_connected():
        await voice_channel.disconnect()


@bot.command(name="q", help="Show the current music queue")
async def show_queue(ctx):
    if not queue:
        await ctx.send("The queue is empty.")
        return
    queue_list = "\n".join(q for q in queue_names)
    await ctx.send(f"Current queue:\n{queue_list}")


def get_title_from_url(url):
    with youtube_dl.YoutubeDL() as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("title", "Unknown Title")


def play_next(ctx, voice_channel):
    if not voice_channel.is_playing() and queue:
        next_song = queue.pop(0)
        queue_names.pop(0)
        voice_channel.play(
            discord.FFmpegPCMAudio(
                next_song,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn",
            ),
            after=lambda e: play_next(ctx, voice_channel),
        )
        ctx.send(f"Now playing: {next_song}")
    else:
        voice_channel.disconnect()


bot.run(DISCORD_BOT_TOKEN)
