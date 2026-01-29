# cogs/music.py – WERSJA Z PYTUBE + TYLKO BEZPOŚREDNI LINK
import discord
from discord.ext import commands
from pytube import YouTube
import asyncio
import traceback

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
            print(f"[MUSIC] Pobieram link: {url}")
            yt = await loop.run_in_executor(None, lambda: YouTube(url))
            stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if not stream:
                raise ValueError("Brak strumienia audio")
            print(f"[MUSIC] Stream URL: {stream.url[:100]}...")
            return cls(discord.FFmpegPCMAudio(stream.url, **FFMPEG_OPTIONS), data={'title': yt.title, 'url': stream.url}, volume=0.3)
        except Exception as e:
            print(f"[MUSIC] Błąd pytube: {str(e)}")
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
    async def graj(self, ctx, *, url):
        """Gra piosenkę – podaj **bezpośredni link** YouTube!"""
        print(f"[MUSIC] Komenda graj uruchomiona z: {url}")
        if not ctx.author.voice:
            await ctx.send("Musisz być na kanale głosowym!")
            return

        vc = ctx.guild.voice_client

        if not vc:
            await ctx.invoke(self.bot.get_command('dołącz'))
            await asyncio.sleep(2)
            vc = ctx.guild.voice_client
            if not vc:
                await ctx.send("Nie udało się dołączyć do kanału.")
                return

        if vc.is_playing() or vc.is_paused():
            vc.stop()
            await ctx.send("Zatrzymałem poprzedni utwór – puszczam nowy 🎶")

        # Wymagamy bezpośredniego linku YouTube
        if not (url.startswith("https://www.youtube.com/") or url.startswith("https://youtu.be/")):
            await ctx.send(
                "❌ Podaj **bezpośredni link** do filmu YouTube!\n\n"
                "Przykład:\n"
                "`8graj https://www.youtube.com/watch?v=dQw4w9WgXcQ`\n\n"
                "Wyszukiwanie tekstowe (np. 'Hymn Polski') nie działa – YouTube blokuje boty."
            )
            return

        try:
            async with ctx.typing():
                print("[MUSIC] Pobieram utwór...")
                player = await YTDLSource.from_url(url, loop=self.bot.loop)
                print("[MUSIC] Utwór pobrany")
        except Exception as e:
            await ctx.send(f"Błąd pobierania: {str(e)}\nSpróbuj inny link.")
            print(f"[MUSIC] Pełny błąd pobierania:\n{traceback.format_exc()}")
            return

        try:
            vc.play(player)
            await ctx.send(f'🎶 Teraz gra: **{player.title}**')
            print("[MUSIC] vc.play wywołane – powinno być słychać")
        except Exception as e:
            await ctx.send(f"Błąd odtwarzania: {str(e)}")
            print(f"[MUSIC] Pełny błąd play:\n{traceback.format_exc()}")

    @commands.command()
    async def skip(self, ctx):
        vc = ctx.guild.voice_client
        if not vc or not vc.is_playing():
            await ctx.send("Nic nie odtwarzam!")
            return
        vc.stop()
        await ctx.send("⏭ Przeskoczono!")

    @commands.command()
    async def pauza(self, ctx):
        vc = ctx.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("Pauza ⏸")
        else:
            await ctx.send("Nic nie odtwarzam lub już w pauzie!")

    @commands.command()
    async def wznów(self, ctx):
        vc = ctx.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("Wznawiam ▶")
        else:
            await ctx.send("Nie jestem w pauzie!")

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
