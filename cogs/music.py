# cogs/music.py – TESTOWA WERSJA BEZ KOLEJKI, TYLKO JEDNA PIOSENKA
import discord
from discord.ext import commands
from pytube import YouTube
import asyncio
import traceback  # do lepszych logów błędów

from config import FFMPEG_OPTIONS

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.3):
        super().__init__(source, volume)
        self.data = data
        self.title = data['title']
        self.url = data['url']

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        try:
            yt = await loop.run_in_executor(None, lambda: YouTube(url))
            stream = yt.streams.filter(only_audio=True).first()
            if not stream:
                raise ValueError("Nie znaleziono strumienia audio")
            print(f"[MUSIC] Pobrano stream: {stream.url}")
            return cls(discord.FFmpegPCMAudio(stream.url, **FFMPEG_OPTIONS), data={'title': yt.title, 'url': stream.url}, volume=0.3)
        except Exception as e:
            print(f"[MUSIC] Błąd w pytube.from_url: {str(e)}")
            raise e

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def dołącz(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if ctx.guild.voice_client:
                await ctx.guild.voice_client.move_to(channel)
            else:
                await channel.connect()
            await ctx.send(f"Dołączyłem do {channel.name} 🎵")
        else:
            await ctx.send("Musisz być na kanale głosowym!")

    @commands.command()
    async def opuść(self, ctx):
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()
            await ctx.send("Opuszczam kanał głosowy 👋")
        else:
            await ctx.send("Nie jestem na żadnym kanale!")

    @commands.command()
    async def graj(self, ctx, *, query):
        """Gra jedną piosenkę z YouTube"""
        print(f"[MUSIC] Komenda graj uruchomiona: {query}")
        if not ctx.author.voice:
            await ctx.send("Musisz być na kanale głosowym!")
            return

        vc = ctx.guild.voice_client

        if not vc:
            await ctx.invoke(self.bot.get_command('dołącz'))
            await asyncio.sleep(2)  # więcej czasu na połączenie
            vc = ctx.guild.voice_client
            if not vc:
                await ctx.send("Nie udało się dołączyć do kanału – spróbuj ponownie.")
                return

        # Zatrzymujemy poprzedni utwór jeśli gra
        if vc.is_playing() or vc.is_paused():
            vc.stop()
            await ctx.send("Zatrzymałem poprzedni utwór – puszczam nowy 🎶")

        try:
            async with ctx.typing():
                print("[MUSIC] Szukam i pobieram utwór...")
                player = await YTDLSource.from_url(query, loop=self.bot.loop)
                print("[MUSIC] Utwór pobrany, puszczam...")
        except Exception as e:
            error_msg = f"Błąd pobierania utworu: {str(e)}\nSprawdź konsolę lub link."
            await ctx.send(error_msg)
            print(f"[MUSIC] Pełny błąd: {traceback.format_exc()}")
            return

        try:
            vc.play(player)
            await ctx.send(f'🎶 Teraz gra: **{player.title}**')
            print("[MUSIC] vc.play wywołane – powinno być słychać")
        except Exception as e:
            await ctx.send(f"Błąd odtwarzania: {str(e)}")
            print(f"[MUSIC] Błąd play: {traceback.format_exc()}")

    @commands.command()
    async def skip(self, ctx):
        vc = ctx.guild.voice_client
        if not vc or not vc.is_playing():
            await ctx.send("Nic nie odtwarzam!")
            return
        vc.stop()
        await ctx.send("⏭ Przeskoczono!")

    @commands.command()
    async def zakończ(self, ctx):
        vc = ctx.guild.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
            await ctx.send("Zakończyłem puszczać muzykę ⏹")
        else:
            await ctx.send("Nie jestem na kanale!")

async def setup(bot):
    await bot.add_cog(Music(bot))
