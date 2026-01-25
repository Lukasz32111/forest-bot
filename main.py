import discord
from discord.ext import commands
import random
import yt_dlp
import asyncio
import json
import os
import shutil
from collections import deque
from collections import Counter
import logging  # Dodaj to
logging.getLogger('discord.client').setLevel(logging.ERROR)  # I to

# Ręczne znalezienie i ustawienie ścieżki do ffmpeg
ffmpeg_path = shutil.which("ffmpeg")
if ffmpeg_path:
    discord.FFmpegPCMAudio.executable = ffmpeg_path
    print(f"FFmpeg znaleziony w ścieżce: {ffmpeg_path}")
else:
    print("FFmpeg NIE znaleziony! Muzyka nie będzie działać.")

# Self-role – zapis paneli
selfroles = {}
SELFROLES_FILE = 'selfroles.json'

try:
    with open(SELFROLES_FILE, 'r', encoding='utf-8') as f:
        selfroles = json.load(f)
except FileNotFoundError:
    selfroles = {}

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.reactions = True
intents.guild_reactions = True
intents.members = True

bot = commands.Bot(command_prefix='8', intents=intents)

# === KONFIGURACJA MUZYKI ===
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'cookiefile': 'cookies.txt',
}
ffmpeg_options = {
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

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
        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data, volume=0.3)

# === GLOBALNE ZMIENNE ===
queue = {}
history = {}
MAX_HISTORY = 10
active_game = None

# === SYSTEM SPECJALNYCH KOŚCI ===
SZANSA_NA_SPECJALNA_KOSC = 0.50

OPISY_KOSCI = {
    "Kość parzysta": "Silnie dociążona na liczby parzyste (2, 4, 6).",
    "Kość nieparzysta": "Silnie dociążona na liczby nieparzyste (1, 3, 5).",
    "Szczęśliwa kość do gry": "Czasem dodaje +1 do wyniku.",
    "Szczęśliwa kość": "Częściej wypada 1.",
    "Kość Niebiańskiego Królestwa": "Rzadko daje potężną 6.",
    "Kość Lu (Fragle I)": "Demoniczna – 38% na 6.",
    "Kość Ci (Fragle II)": "43% na 6.",
    "Kość Fer (Fragle III)": "Najlepsza – 48% na 6! 🌟",
    "Kość rozbierająca": "Lubi 1 i 6.",
    "Niepopularna kość": "Często niskie liczby.",
    "Stronnicza kość": "Dociążona na 1, 2 i 6.",
    "Kość pecha": "Unika 1 i 6.",
    "Kurcząca się kość": "Bardzo lubi 1 i 6.",
    "Kość Świętej Trójcy": "Częściej wypada 3.",
}

DICE_POOL = [
    ("Kość parzysta", lambda: random.choices([1,2,3,4,5,6], weights=[5,25,5,25,5,25])[0], 20),
    ("Kość nieparzysta", lambda: random.choices([1,2,3,4,5,6], weights=[25,5,25,5,25,5])[0], 18),
    ("Szczęśliwa kość do gry", lambda: min(6, random.randint(1,6) + (1 if random.random() < 0.25 else 0)), 12),
    ("Szczęśliwa kość", lambda: 1 if random.random() < 0.35 else random.randint(1,6), 15),
    ("Kość Niebiańskiego Królestwa", lambda: 6 if random.random() < 0.15 else random.randint(1,6), 8),
    ("Kość Lu (Fragle I)", lambda: 6 if random.random() < 0.38 else random.randint(1,6), 14),
    ("Kość Ci (Fragle II)", lambda: 6 if random.random() < 0.43 else random.randint(1,6), 10),
    ("Kość Fer (Fragle III)", lambda: 6 if random.random() < 0.48 else random.randint(1,6), 5),
    ("Kość rozbierająca", lambda: random.choices([1,2,3,4,5,6], weights=[22,8,8,8,8,22])[0], 12),
    ("Niepopularna kość", lambda: random.choices([1,2,3,4,5,6], weights=[12,18,30,18,12,10])[0], 22),
    ("Stronnicza kość", lambda: random.choices([1,2,3,4,5,6], weights=[20,30,8,8,8,16])[0], 16),
    ("Kość pecha", lambda: random.choices([1,2,3,4,5,6], weights=[3,28,25,25,22,2])[0], 20),
    ("Kurcząca się kość", lambda: random.choices([1,2,3,4,5,6], weights=[20,10,10,10,10,20])[0], 10),
    ("Kość Świętej Trójcy", lambda: 3 if random.random() < 0.28 else random.randint(1,6), 13),
]

def roll_single_die():
    if random.random() < SZANSA_NA_SPECJALNA_KOSC:
        names, funcs, weights = zip(*DICE_POOL)
        idx = random.choices(range(len(names)), weights=weights)[0]
        return funcs[idx](), names[idx]
    return random.randint(1, 6), None

def has_scoring_combo(dice):
    counts = Counter(dice)
    if len(dice) == 6 and sorted(dice) == [1,2,3,4,5,6]:
        return True
    if any(c >= 3 for c in counts.values()):
        return True
    return counts[1] > 0 or counts[5] > 0

def calculate_points(dice):
    if len(dice) == 6 and sorted(dice) == [1,2,3,4,5,6]:
        return 1500, True
    counts = Counter(dice)
    points = 0
    remaining = counts.copy()
    for num in range(1,7):
        count = remaining[num]
        if count >= 3:
            mult = 1000 if num == 1 else num * 100
            points += mult * (count // 3)
            remaining[num] %= 3
    points += remaining[1] * 100
    points += remaining[5] * 50
    return points, points > 0

@bot.command()
async def rzut(ctx, opponent: discord.Member = None):
    global active_game
    if active_game is not None:
        await ctx.send("Gra już trwa! Użyj `8skończ`.")
        return
    active_game = ctx.channel.id

    await ctx.send("🎲 Start gry z botem!")
    player1 = ctx.author
    vs_bot = True

    # Wybór celu z poradnikiem
    async def choose_target():
        nonlocal target_points
        embed = discord.Embed(title="🎲 Wybór celu gry", description="🇦 → 1000 pkt\n🇧 → 2000 pkt\n🇨 → 5000 pkt (klasyczna)\n🇩 → 10000 pkt\n\n❓ = poradnik", color=0x2b2d31)
        embed.set_footer(text="Reaguj wybraną literką")
        msg = await ctx.send(embed=embed)
        for r in ['🇦', '🇧', '🇨', '🇩', '❓']:
            await msg.add_reaction(r)
        options = {'🇦': 1000, '🇧': 2000, '🇨': 5000, '🇩': 10000}
        def check(r, u):
            return u == player1 and r.message.id == msg.id
        while True:
            try:
                reaction, _ = await bot.wait_for('reaction_add', timeout=180, check=check)
            except asyncio.TimeoutError:
                await ctx.send("Czas minął – anuluję grę.")
                return False
            emoji = str(reaction.emoji)
            if emoji == '❓':
                poradnik = (
                    "**📜 Poradnik Farkle**\n\n"
                    "• Pojedyncza **1** = 100 pkt\n"
                    "• Pojedyncza **5** = 50 pkt\n"
                    "• Trójka (lub więcej) identycznych = wartość × 100 (trójka 1 = 1000 pkt)\n"
                    "• Strit 1-2-3-4-5-6 = 1500 pkt\n\n"
                    "**Hot Dice** – wykorzystasz wszystkie 6 kostek → nowy rzut 6 kostkami!\n"
                    "**Farkle** – brak punktujących kombinacji → tracisz punkty z całej tury!\n\n"
                    "Powodzenia! 🎲"
                )
                await ctx.send(poradnik)
                continue
            if emoji in options:
                target_points = options[emoji]
                await ctx.send(f"✅ Cel gry: **{target_points}** punktów! Start!")
                return True
        return False

    target_points = 0
    if not await choose_target():
        active_game = None
        return

    p1_total = 0
    p2_total = 0

    async def send_game_state():
        if not active_game: return
        embed = discord.Embed(title=f"🎲 Farkle • Cel: {target_points} pkt", color=0x2b2d31)
        embed.add_field(name=f"👤 {player1.display_name}", value=f"**{p1_total}** pkt", inline=True)
        embed.add_field(name="🤖 Bot", value=f"**{p2_total}** pkt", inline=True)
        embed.add_field(name="🕹 Tura", value=player1.display_name, inline=False)
        await ctx.send(embed=embed)

    async def player_turn():
        nonlocal p1_total
        points_this_turn = 0
        remaining_dice = 6
        turn_num = 1

        while active_game:
            # Rzut
            roll_results = [roll_single_die() for _ in range(remaining_dice)]
            dice_values = [v for v, _ in roll_results]

            if not has_scoring_combo(dice_values):
                if active_game:
                    await ctx.send(f"💀 **FARKLE od razu!** {player1.mention} – brak punktujących kostek w rzucie.")
                return

            # Estetyczny wiersz kostek
            dice_parts = []
            special_present = False

            for value, name in roll_results:
                if name:
                    special_present = True
                    if "Fragle" in name or "Lu" in name or "Ci" in name or "Fer" in name:
                        icon = "🔴"
                    elif "Szczęśliwa" in name or "Niebiańskiego" in name or "Kurcząca" in name:
                        icon = "🟢"
                    elif "pecha" in name or "Niepopularna" in name:
                        icon = "⚫"
                    else:
                        icon = "🟡"

                    rarity = " 🌟" if "Fer" in name else ""
                    dice_parts.append(f"{icon}`{name}{rarity}`\n{value}️⃣")
                else:
                    dice_parts.append(f"{value}️⃣")

            dice_row = "  ".join(dice_parts)

            embed = discord.Embed(
                title=f"🎲 {player1.display_name} – Rzut {turn_num}",
                description=f"{dice_row}\n\n"
                            f"**Pozostało kostek:** {remaining_dice}  **Punkty w turze:** {points_this_turn}",
                color=0x2b2d31
            )
            embed.set_footer(text="Kliknij numer → zachowaj | ✅ kontynuuj | ❌ bankuj | ℹ️ opis specjalnych")
            msg = await ctx.send(embed=embed)

            for d in set(dice_values):
                await msg.add_reaction(f'{d}️⃣')
            await msg.add_reaction('✅')
            await msg.add_reaction('❌')
            if special_present:
                await msg.add_reaction('ℹ️')

            # Obsługa reakcji
            kept = set()
            def check(r, u):
                return u == player1 and r.message.id == msg.id and active_game

            reacted_emoji = None
            while active_game:
                try:
                    reaction, _ = await bot.wait_for('reaction_add', timeout=90, check=check)
                except asyncio.TimeoutError:
                    if active_game:
                        await ctx.send(f"⏰ Timeout – bankuję {points_this_turn} pkt.")
                        p1_total += points_this_turn
                    return

                reacted_emoji = str(reaction.emoji)

                # NOWA OBSŁUGA ℹ️ – WSZYSTKIE specjalne kości z rzutu
                if reacted_emoji == 'ℹ️' and special_present:
                    special_count = Counter([n for _, n in roll_results if n])
                    info_lines = []
                    for name, count in special_count.items():
                        opis = OPISY_KOSCI.get(name, "Specjalna kość bez opisu.")
                        count_str = f" (x{count})" if count > 1 else ""
                        info_lines.append(f"**{name}{count_str}**\n{opis}")

                    info_embed = discord.Embed(
                        title="ℹ️ Specjalne kości z tego rzutu",
                        description="\n\n".join(info_lines),
                        color=0x2b2d31
                    )
                    await ctx.send(embed=info_embed, delete_after=30)
                    continue

                if reacted_emoji[0].isdigit():
                    num = int(reacted_emoji[0])
                    if num in dice_values:
                        kept.add(num)
                if reacted_emoji in ['✅', '❌']:
                    break

            kept_list = [d for d in dice_values if d in kept]
            turn_points, has_points = calculate_points(kept_list)

            if reacted_emoji == '✅':
                if not has_points:
                    if active_game:
                        await ctx.send(f"💀 **FARKLE!** {player1.mention}")
                    return
                points_this_turn += turn_points
                remaining_dice -= len(kept_list)
                if active_game:
                    await ctx.send(f"✅ +**{turn_points}** pkt → razem: **{points_this_turn}**")
                if remaining_dice == 0:
                    await ctx.send("🔥 **HOT DICE!** Nowe 6 kostek!")
                    remaining_dice = 6
                turn_num += 1
            else:
                if has_points:
                    points_this_turn += turn_points
                if points_this_turn == 0:
                    await ctx.send(f"💀 **FARKLE!** {player1.mention}")
                    return
                await ctx.send(f"✅ Bankujesz **{points_this_turn}** pkt!")
                p1_total += points_this_turn
                return

    async def bot_turn():
        nonlocal p2_total
        points_this_turn = 0
        remaining_dice = 6
        for _ in range(3):
            if not active_game: return
            roll_results = [roll_single_die() for _ in range(remaining_dice)]
            dice_values = [v for v, _ in roll_results]
            if not has_scoring_combo(dice_values):
                await ctx.send("🤖 Bot – Farkle!")
                return
            counts = Counter(dice_values)
            kept = set()
            for num in range(6,0,-1):
                if counts[num] >= 3 or (num in [1,5] and counts[num] > 0):
                    kept.add(num)
            kept_list = [d for d in dice_values if d in kept]
            turn_points, _ = calculate_points(kept_list)
            points_this_turn += turn_points
            remaining_dice -= len(kept_list)
            if remaining_dice == 0:
                remaining_dice = 6
            if points_this_turn >= 700 or random.random() < 0.3:
                break
        p2_total += points_this_turn
        await ctx.send(f"🤖 Bot bankuje **{points_this_turn}** pkt! Razem: **{p2_total}**")

    await send_game_state()

    while active_game and p1_total < target_points and p2_total < target_points:
        await player_turn()
        if not active_game or p1_total >= target_points:
            break
        await bot_turn()
        if not active_game or p2_total >= target_points:
            break
        await send_game_state()

    if active_game:
        winner = player1 if p1_total >= target_points else "Bot"
        await ctx.send(embed=discord.Embed(title="🏆 KONIEC!", description=f"**Wygrywa {winner}!**\n{player1.display_name}: {p1_total} pkt\nBot: {p2_total} pkt", color=0xffd700))

    active_game = None

@bot.command(aliases=['stop'])
async def skończ(ctx):
    global active_game
    if active_game == ctx.channel.id:
        active_game = None
        await ctx.send("Gra przerwana.")
    else:
        await ctx.send("Brak gry.")
        
# === KOMENDY MUZYCZNE Z KOLEJKĄ ===
async def play_next(ctx):
    vc = ctx.guild.voice_client
    if not vc or not vc.is_connected():
        return

    if ctx.guild.id in queue and queue[ctx.guild.id]:
        next_song = queue[ctx.guild.id][0]
        try:
            player = await YTDLSource.from_url(next_song['url'], loop=bot.loop)
            vc.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next_after(ctx), bot.loop))
            await ctx.send(f'🎶 Teraz gra: **{next_song["title"]}**')
        except Exception as e:
            print(f"Błąd przy odtwarzaniu: {e}")
            queue[ctx.guild.id].popleft()
            await play_next(ctx)
    else:
        await ctx.send("Koniec kolejki! 🎶")

async def play_next_after(ctx):
    if ctx.guild.id in queue and queue[ctx.guild.id]:
        current = queue[ctx.guild.id].popleft()
        if ctx.guild.id not in history:
            history[ctx.guild.id] = deque(maxlen=MAX_HISTORY)
        history[ctx.guild.id].append(current)
    await play_next(ctx)

@bot.command()
async def dołącz(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"Dołączyłem do {channel.name} 🎵")
    else:
        await ctx.send("Musisz być na kanale głosowym!")

@bot.command()
async def opuść(ctx):
    if ctx.guild.voice_client:
        queue.pop(ctx.guild.id, None)
        history.pop(ctx.guild.id, None)
        await ctx.guild.voice_client.disconnect()
        await ctx.send("Opuszczam kanał głosowy 👋")
    else:
        await ctx.send("Nie jestem na żadnym kanale!")

@bot.command()
async def graj(ctx, *, query):
    if not ctx.author.voice:
        await ctx.send("Musisz być na kanale głosowym!")
        return

    if not ctx.guild.voice_client:
        await ctx.invoke(bot.get_command('dołącz'))
        await asyncio.sleep(1.5)

    try:
        async with ctx.typing():
            player = await YTDLSource.from_url(query, loop=bot.loop)

        if ctx.guild.id not in queue:
            queue[ctx.guild.id] = deque()

        queue[ctx.guild.id].append({"title": player.title, "url": query})

        if not ctx.guild.voice_client.is_playing() and not ctx.guild.voice_client.is_paused():
            await play_next(ctx)
        else:
            await ctx.send(f'✅ Dodano do kolejki: **{player.title}** (pozycja {len(queue[ctx.guild.id])})')
    except Exception as e:
        await ctx.send("Nie udało się dodać utworu 😢")
        print(f"Błąd w graj: {e}")

@bot.command()
async def skip(ctx):
    if not ctx.guild.voice_client or not ctx.guild.voice_client.is_playing():
        await ctx.send("Nic nie odtwarzam!")
        return
    ctx.guild.voice_client.stop()
    await ctx.send("⏭ Przeskoczono do następnego utworu!")

@bot.command()
async def poprzedni(ctx):
    if ctx.guild.id not in history or not history[ctx.guild.id]:
        await ctx.send("Brak poprzedniego utworu w historii!")
        return

    if not ctx.guild.voice_client:
        await ctx.invoke(bot.get_command('dołącz'))

    prev_song = history[ctx.guild.id].pop()
    if ctx.guild.id not in queue:
        queue[ctx.guild.id] = deque()
    queue[ctx.guild.id].appendleft(prev_song)
    ctx.guild.voice_client.stop()
    await ctx.send(f"⏮ Wracam do: **{prev_song['title']}**")

@bot.command()
async def kolejka(ctx):
    if ctx.guild.id not in queue or not queue[ctx.guild.id]:
        await ctx.send("Kolejka jest pusta! Dodaj utwory komendą `8graj <nazwa/link>`")
        return

    entries = list(queue[ctx.guild.id])
    message = "**Aktualna kolejka:**\n"
    for i, song in enumerate(entries, 1):
        message += f"{i}. **{song['title']}**\n"
        if len(message) > 1800:
            message += "... i więcej"
            break
    await ctx.send(message)

@bot.command()
async def pauza(ctx):
    vc = ctx.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("Pauza ⏸")
    else:
        await ctx.send("Nic nie odtwarzam lub już w pauzie!")

@bot.command()
async def wznów(ctx):
    vc = ctx.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("Wznawiam ▶")
    else:
        await ctx.send("Nie jestem w pauzie!")

@bot.command()
async def zakończ(ctx):
    if ctx.guild.voice_client:
        queue.pop(ctx.guild.id, None)
        history.pop(ctx.guild.id, None)
        ctx.guild.voice_client.stop()
        await ctx.send("Zakończyłem puszczać muzykę ⏹ Kolejka wyczyszczona.")
    else:
        await ctx.send("Nie jestem na kanale!")

# === KOMENDA PODOBNA PIOSENKA ===
@bot.command()
async def podobne(ctx):
    if ctx.guild.voice_client and (ctx.guild.voice_client.is_playing() or ctx.guild.voice_client.is_paused()):
        await ctx.send("Aktualnie coś gra! Użyj `8skip` lub poczekaj do końca, żeby puścić podobne.")
        return

    if ctx.guild.id not in history or not history[ctx.guild.id]:
        await ctx.send("Nie mam historii odtwarzania – puść najpierw jakąś piosenkę komendą `8graj`!")
        return

    last_song_url = history[ctx.guild.id][-1]['url']
    await ctx.send("Szukam czegoś podobnego... 🎵")

    if not ctx.guild.voice_client:
        await ctx.invoke(bot.get_command('dołącz'))
        await asyncio.sleep(1.5)

    try:
        info = await bot.loop.run_in_executor(None, lambda: ytdl.extract_info(last_song_url, download=False))
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
            search_opts = ytdl_format_options.copy()
            search_opts['extract_flat'] = True
            search_opts['playlistend'] = 15
            search_ytdl = yt_dlp.YoutubeDL(search_opts)
            search_info = await bot.loop.run_in_executor(None, lambda: search_ytdl.extract_info(f"ytsearch15:{search_query}", download=False))

            if 'entries' in search_info and search_info['entries']:
                similar_entries = search_info['entries'][4:] or search_info['entries'][1:]
                chosen = random.choice(similar_entries)
                video_url = chosen.get('url')
                final_url = video_url if video_url.startswith('https://') else f"https://www.youtube.com/watch?v={video_url}"
                player = await YTDLSource.from_url(final_url, loop=bot.loop)

                if ctx.guild.id not in queue:
                    queue[ctx.guild.id] = deque()

                queue[ctx.guild.id].append({"title": player.title, "url": final_url})
                await play_next(ctx)
                await ctx.send(f"Puszczam podobny utwór: **{player.title}**")
            else:
                await ctx.send("Nie znalazłem podobnych piosenek 😢")
    except Exception as e:
        await ctx.send("Nie udało się znaleźć podobnej piosenki 😢")
        print(f"Błąd w podobne: {e}")

@bot.event
async def on_ready():
    print("═" * 70)
    print(" " * 20 + "=== BOT URUCHOMIONY POMYŚLNIE ===")
    print("═" * 70)
    
    now = discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"  Aktualny czas UTC:       {now}")
    print(f"  Nazwa bota:              {bot.user}")
    print(f"  ID bota:                 {bot.user.id}")
    print(f"  Liczba serwerów:         {len(bot.guilds)}")
    
    total_members = sum(g.member_count or 0 for g in bot.guilds)
    print(f"  Szacowana liczba użytkowników: ~{total_members}")
    
    print(f"  Prefix komend:           {bot.command_prefix}")
    
    # Sprawdzenie FFmpeg – kluczowe dla muzyki
    ffmpeg_status = "znaleziony ✓" if shutil.which("ffmpeg") else "BRAK ✗ – muzyka nie będzie działać!"
    print(f"  FFmpeg:                  {ffmpeg_status}")
    
    # Sprawdzenie najważniejszych intents
    intents_status = []
    if not intents.message_content:
        intents_status.append("BRAK message_content ✗")
    if not intents.voice_states:
        intents_status.append("BRAK voice_states ✗")
    if not intents.members:
        intents_status.append("BRAK members ✗")
    if not intents.reactions:
        intents_status.append("BRAK reactions ✗")
    
    if intents_status:
        print("  Intents – problemy:      " + ", ".join(intents_status))
    else:
        print("  Intents kluczowe:        wszystkie włączone ✓")
    
    print("\n" + "═" * 70)
    print("Dostępne / sprawdzone funkcje:")
    print("")
    print("  ✓ Gra Farkle (z botem)              →  8rzut   /  8skończ")
    print(f"  {'✓' if 'znaleziony' in ffmpeg_status else '✗'}  Odtwarzanie muzyki z YouTube     →  8graj   /  8skip   /  8pauza /  8wznów")
    print("  ✓ Zarządzanie kolejką               →  8kolejka /  8poprzedni /  8zakończ")
    print("  ✓ Sugestie podobnych utworów        →  8podobne")
    print("  ✓ Reakcje, embedy, timeouty         → używane w grze Farkle i interakcjach")
    print("")
    print("Bot jest gotowy do użycia!")
    print("Jeśli widzisz ten komunikat → podstawowe funkcje powinny działać.")
    print("═" * 70)

# === URUCHOMIENIE ===
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    print("BŁĄD: Nie znaleziono zmiennej środowiskowej TOKEN! Dodaj ją w Variables na Railway.")
else:
    bot.run(TOKEN)

