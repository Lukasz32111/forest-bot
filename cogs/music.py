# cogs/music.py
import discord
from discord.ext import commands
import yt_dlp
import asyncio
import random
from collections import deque
from config import YTDL_FORMAT_OPTIONS, FFMPEG_OPTIONS, MAX_HISTORY

# Używamy YT-DLP z config – nie definiujemy ponownie!
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
        self.queue = {}
        self.history = {}

    async def play_next(self, ctx):
        vc = ctx.guild.voice_client
        if not vc or not vc.is_connected():
            return

        if ctx.guild.id in self.queue and self.queue[ctx.guild.id]:
            next_song = self.queue[ctx.guild.id].popleft()
            try:
                player = await YTDLSource.from_url(next_song['url'], loop=self.bot.loop)
                vc.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next_after(ctx), self.bot.loop))
                await ctx.send(f'🎶 Teraz gra: **{next_song["title"]}**')
            except Exception as e:
                print(f"Błąd przy odtwarzaniu: {e}")
                await self.play_next(ctx)  # spróbuj następną jeśli błąd
        else:
            await ctx.send("Koniec kolejki! 🎶")

    async def play_next_after(self, ctx):
        if ctx.guild.id in self.queue and self.queue[ctx.guild.id]:
            current = self.queue[ctx.guild.id].popleft()
            if ctx.guild.id not in self.history:
                self.history[ctx.guild.id] = deque(maxlen=MAX_HISTORY)
            self.history[ctx.guild.id].append(current)
        await self.play_next(ctx)

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
            self.history.pop(ctx.guild.id, None)
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
            await ctx.send("Nie udało się znaleźć lub dodać utworu 😢")
            print(f"Błąd w graj: {e}")
            return

        # Dodajemy do kolejki
        self.queue[ctx.guild.id].append({"title": player.title, "url": query})

        # Jeśli nic nie gra i nie jest w pauzie → startujemy od razu
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
    async def poprzedni(self, ctx):
        if ctx.guild.id not in self.history or not self.history[ctx.guild.id]:
            await ctx.send("Brak poprzedniego utworu w historii!")
            return
        if not ctx.guild.voice_client:
            await ctx.invoke(self.bot.get_command('dołącz'))
        prev_song = self.history[ctx.guild.id].pop()
        if ctx.guild.id not in self.queue:
            self.queue[ctx.guild.id] = deque()
        self.queue[ctx.guild.id].appendleft(prev_song)
        ctx.guild.voice_client.stop()
        await ctx.send(f"⏮ Wracam do: **{prev_song['title']}**")

    @commands.command()
    async def kolejka(self, ctx):
        if ctx.guild.id not in self.queue or not self.queue[ctx.guild.id]:
            await ctx.send("Kolejka jest pusta! Dodaj utwory komendą `8graj <nazwa/link>`")
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
            self.history.pop(ctx.guild.id, None)
            ctx.guild.voice_client.stop()
            await ctx.send("Zakończyłem puszczać muzykę ⏹ Kolejka wyczyszczona.")
        else:
            await ctx.send("Nie jestem na kanale!")

    @commands.command()
    async def podobne(self, ctx):
        if ctx.guild.voice_client and (ctx.guild.voice_client.is_playing() or ctx.guild.voice_client.is_paused()):
            await ctx.send("Aktualnie coś gra! Użyj `8skip` lub poczekaj do końca, żeby puścić podobne.")
            return
        if ctx.guild.id not in self.history or not self.history[ctx.guild.id]:
            await ctx.send("Nie mam historii odtwarzania – puść najpierw jakąś piosenkę komendą `8graj`!")
            return
        last_song_url = self.history[ctx.guild.id][-1]['url']
        await ctx.send("Szukam czegoś podobnego... 🎵")
        if not ctx.guild.voice_client:
            await ctx.invoke(self.bot.get_command('dołącz'))
            await asyncio.sleep(1.5)
        try:
            info = await self.bot.loop.run_in_executor(None, lambda: ytdl.extract_info(last_song_url, download=False))
            original_title = info.get('title', 'Nieznany tytuł')
            artist = info.get('artist') or info.get('uploader') or info.get('channel') or "Nieznany artysta"
            await ctx.send(f"Ostatni utwór: **{original_title}** – {artist}\nSzukam czegoś podobnego... 🔍")
            search_queries = [
                f"{artist} similar songs",
                f"songs like {original_title} by {artist}",
                f"{artist} best songs",
                f"{artist} radio",
                f"music like {artist}",
                f"{original_title} cover or remix"
            ]
            search_query = random.choice(search_queries)
            async with ctx.typing():
                search_opts = YTDL_FORMAT_OPTIONS.copy()
                search_opts['extract_flat'] = True
                search_opts['playlistend'] = 15
                search_ytdl = yt_dlp.YoutubeDL(search_opts)
                search_info = await self.bot.loop.run_in_executor(None, lambda: search_ytdl.extract_info(f"ytsearch15:{search_query}", download=False))
                if 'entries' in search_info and search_info['entries']:
                    similar_entries = search_info['entries'][4:] or search_info['entries'][1:]
                    chosen = random.choice(similar_entries)
                    video_url = chosen.get('url')
                    final_url = video_url if video_url.startswith('https://') else f"https://www.youtube.com/watch?v={video_url}"
                    player = await YTDLSource.from_url(final_url, loop=self.bot.loop)
                    if ctx.guild.id not in self.queue:
                        self.queue[ctx.guild.id] = deque()
                    self.queue[ctx.guild.id].append({"title": player.title, "url": final_url})
                    await self.play_next(ctx)
                    await ctx.send(f"Puszczam podobny utwór: **{player.title}**")
                else:
                    await ctx.send("Nie znalazłem podobnych piosenek 😢")
        except Exception as e:
            await ctx.send("Nie udało się znaleźć podobnej piosenki 😢")
            print(f"Błąd w podobne: {e}")

async def setup(bot):
    await bot.add_cog(Music(bot))
