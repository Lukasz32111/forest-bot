# main.py
import discord
from discord.ext import commands
import os
import logging
import asyncio
import shutil

# wyciszenie logów discord
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.client').setLevel(logging.ERROR)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)

from config import PREFIX, INTENTS

bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)

@bot.event
async def on_ready():
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    
    print("══════════════════════════════════════════════════════════════════════")
    print(" BOT URUCHOMIONY POMYŚLNIE")
    print("══════════════════════════════════════════════════════════════════════")
    print(f" Bot: {bot.user}")
    print(f" Serwery: {len(bot.guilds)}")
    print(f" Prefix: {PREFIX}")
    print(f" FFmpeg: {'znaleziony ✓' if ffmpeg_ok else 'BRAK ✗ – muzyka nie będzie działać!'}")
    
    # ────────────── DIAGNOSTYKA ──────────────
    print("\nZaładowane komendy (powinno być min. 1–2):")
    cmd_names = [c.name for c in bot.commands]
    print(", ".join(sorted(cmd_names)) if cmd_names else "ŻADNA KOMENDA NIE ZOSTAŁA ZAREJESTROWANA")
    
    if "pomoc" in cmd_names:
        print("→ KOMENDA 'pomoc' JEST ZAREJESTROWANA ✓")
    else:
        print("→ KOMENDA 'pomoc' NIE JEST ZAREJESTROWANA !!!")
    
    if "testpomoc" in cmd_names:
        print("→ KOMENDA 'testpomoc' JEST ZAREJESTROWANA ✓")
    else:
        print("→ KOMENDA 'testpomoc' NIE JEST ZAREJESTROWANA !!!")
    # ──────────────────────────────────────────
    
    print("══════════════════════════════════════════════════════════════════════")
    print("Gotowy! Testuj komendy 8rzut i 8graj")

async def load_cogs():
    await bot.load_extension("cogs.farkle")
    await bot.load_extension("cogs.music")
    await bot.load_extension("cogs.pomoc")
    await bot.load_extension("cogs.meme")
    await bot.load_extension("cogs.moderacja")
    await bot.load_extension("cogs.warn")
    await bot.load_extension("cogs.ankieta")
    await bot.load_extension("cogs.ticket")
    print("Cogi załadowane pomyślnie")

@bot.event
async def setup_hook():
    await load_cogs()

async def main():
    token = os.getenv("TOKEN")
    if not token:
        print("BŁĄD: Nie znaleziono zmiennej środowiskowej TOKEN! Dodaj ją w Variables na Railway.")
        return
    await bot.start(token)

@bot.event
async def on_command_error(ctx, error):
    """Globalny handler błędów komend – ładne komunikaty zamiast crashy"""
    if isinstance(error, commands.CommandNotFound):
        return  # ignorujemy nieistniejące komendy

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"❌ Brak wymaganego argumentu!\n"
            f"Użyj: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`"
        )

    elif isinstance(error, commands.BadArgument):
        await ctx.send(
            f"❌ Nieprawidłowy argument!\n"
            f"Sprawdź format komendy: `{ctx.prefix}{ctx.command.name}`\n"
            f"Przykład: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`"
        )

    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"⏳ Spokojnie! Komenda dostępna za **{error.retry_after:.1f} sekund**."
        )

    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Nie masz uprawnień do tej komendy.")

    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(
            "❌ Bot nie ma wymaganych uprawnień (np. Manage Messages, Manage Channels).\n"
            "Poproś admina serwera o nadanie botowi roli z odpowiednimi permisjami."
        )

    elif isinstance(error, commands.CommandInvokeError):
        # Błędy wewnętrzne – np. exception w kodzie komendy
        print(f"Błąd w komendzie {ctx.command}: {error.original}")
        await ctx.send(
            "❌ Coś poszło nie tak po stronie bota...\n"
            f"({type(error.original).__name__})\n"
            "Zgłoś to twórcy – sprawdzę co się stało."
        )

    else:
        # Wszystkie inne nieobsłużone błędy
        print(f"Nieobsłużony błąd w komendzie {ctx.command}: {error}")
        await ctx.send(
            f"❌ Nieznany błąd: `{type(error).__name__}`\n"
            "Coś poszło nie tak – zgłoś to twórcy bota."
        )

if __name__ == "__main__":
    asyncio.run(main())










