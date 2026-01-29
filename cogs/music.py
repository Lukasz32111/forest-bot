# cogs/music.py
import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque

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
        self.queue = {}  # guild_id -> deque piosenek

    async def play_next(self, ctx):
        vc = ctx.guild.voice_client
        if not vc or not vc.is_connected():
            return

        if ctx.guild.id not in self.queue or not self.queue[ctx.guild.id]:
            await ctx.send("Koniec kolejki! 🎶")
            return

        # Bierzemy i USUWAMY pierwszą piosenkę z kolejki
        next_song = self.queue[ctx.guild.id].popleft()

        try:
            player = await YTDLSource.from_url(next_song['url'], loop=self.bot.loop)
            vc.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
            await ctx.send(f'🎶 Teraz gra: **{next_song["title"]}**')
        except Exception as e:
            print(f"Błąd odtwarzania: {e}")
            await ctx.send(f"Błąd odtwarzania: {e}")
            await self.play_next(ctx)  # próbuj następną

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
            self.queue.pop(ctx.guild.id, None)
            await ctx.guild.voice_client.disconnect()
            await ctx.send("Opuszczam kanał głosowy 👋")
        else:
            await ctx.send("Nie jestem na żadnym kanale!")

    @commands.command()
    async def graj(self, ctx, *, query):
        """Gra piosenkę z YouTube / link / wyszukiwanie"""
        if not ctx.author.voice:
            await ctx.send("Musisz być na kanale głosowym!")
            return

        # Dołączamy jeśli nie jesteśmy podłączeni
        if not ctx.guild.voice_client:
            await ctx.invoke(self.bot.get_command('dołącz'))
            await asyncio.sleep(1.5)

        vc = ctx.guild.voice_client

        if ctx.guild.id not in self.queue:
            self.queue[ctx.guild.id] = deque()

        try:
            async with ctx.typing():
                player = await YTDLSource.from_url(query, loop=self.bot.loop)
        except Exception as e:
            await ctx.send("Nie udało się znaleźć utworu 😢")
            print(f"Błąd w graj: {e}")
            return

        # Dodajemy do kolejki
        self.queue[ctx.guild.id].append({"title": player.title, "url": query})

        # Jeśli nic nie gra → startujemy natychmiast
        if not vc.is_playing() and not vc.is_paused():
            await self.play_next(ctx)
        else:
            position = len(self.queue[ctx.guild.id])
            await ctx.send(f'✅ Dodano do kolejki: **{player.title}** (pozycja {position})')

    @commands.command()
    async def skip(self, ctx):
        if not ctx.guild.voice_client or not ctx.guild.voice_client.is_playing():
            await ctx.send("Nic nie odtwarzam!")
            return
        ctx.guild.voice_client.stop()
        await ctx.send("⏭ Przeskoczono do następnego utworu!")

    @commands.command()
    async def kolejka(self, ctx):
        if ctx.guild.id not in self.queue or not self.queue[ctx.guild.id]:
            await ctx.send("Kolejka jest pusta!")
            return
        entries = list(self.queue[ctx.guild.id])
        message = "**Aktualna kolejka:**\n"
        for i, song in enumerate(entries, 1):
            message += f"{i}. **{song['title']}**\n"
            if len(message) > 1800:
                message += "... i więcej"
                break
        await ctx.send(message)

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
        if ctx.guild.voice_client:
            self.queue.pop(ctx.guild.id, None)
            ctx.guild.voice_client.stop()
            await ctx.send("Zakończyłem puszczać muzykę ⏹ Kolejka wyczyszczona.")
        else:
            await ctx.send("Nie jestem na kanale!")

async def setup(bot):
    await bot.add_cog(Music(bot))
