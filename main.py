# main.py
import discord
from discord.ext import commands
import os
import logging
import asyncio
import shutil

logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.client').setLevel(logging.ERROR)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)

from config import PREFIX, INTENTS

bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)

@bot.event
async def on_ready():
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    print("══════════════════════════════════════════════════════════════════════")
    print("                BOT URUCHOMIONY POMYŚLNIE")
    print("══════════════════════════════════════════════════════════════════════")
    print(f"  Bot: {bot.user} | Serwery: {len(bot.guilds)} | Prefix: {PREFIX}")
    print(f"  FFmpeg: {'OK ✓' if ffmpeg_ok else 'BRAK ✗'}")
    print("  Załadowane cogi: farkle, music")
    print("══════════════════════════════════════════════════════════════════════")

async def load_cogs():
    await bot.load_extension("cogs.farkle")
    await bot.load_extension("cogs.music")

@bot.event
async def setup_hook():
    await load_cogs()

async def main():
    token = os.getenv("TOKEN")
    if not token:
        print("Brak TOKEN!")
        return
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
