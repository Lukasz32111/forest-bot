# cogs/music.py
import discord
from discord.ext import commands
import yt_dlp
import asyncio

from config import YTDL_FORMAT_OPTIONS, FFMPEG_OPTIONS

ytdl = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.3):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        if 'entries' in data:
            data = data['entries'][0]
        return cls(discord.FFmpegPCMAudio(data['url'], **FFMPEG_OPTIONS), data=data, volume=0.3)

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
        """Gra jedną piosenkę z YouTube / link / wyszukiwanie"""
        if not ctx.author.voice:
            await ctx.send("Musisz być na kanale głosowym!")
            return

        vc = ctx.guild.voice_client

        # Dołączamy jeśli nie jesteśmy
        if not vc:
            await ctx.invoke(self.bot.get_command('dołącz'))
            await asyncio.sleep(1.5)
            vc = ctx.guild.voice_client

        # Jeśli coś już gra – zatrzymujemy
        if vc.is_playing() or vc.is_paused():
            vc.stop()
            await ctx.send("Zatrzymałem poprzedni utwór – puszczam nowy 🎶")

        try:
            async with ctx.typing():
                player = await YTDLSource.from_url(query, loop=self.bot.loop)
        except Exception as e:
            await ctx.send("Nie udało się znaleźć utworu 😢")
            print(f"Błąd w graj: {e}")
            return

        try:
            vc.play(player)
            await ctx.send(f'🎶 Teraz gra: **{player.title}**')
        except Exception as e:
            await ctx.send(f"Błąd odtwarzania: {e}")
            print(f"Błąd play: {e}")

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
