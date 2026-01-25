# cogs/farkle.py
import random
from collections import Counter
import discord
from discord.ext import commands
import asyncio

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

class Farkle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_game = None

    @commands.command()
    async def rzut(self, ctx, opponent: discord.Member = None):
        global active_game  # jeśli chcesz zachować global – możesz, ale lepiej self.active_game
        if self.active_game is not None:
            await ctx.send("Gra już trwa! Użyj `8skończ`.")
            return
        self.active_game = ctx.channel.id
        await ctx.send("🎲 Start gry z botem!")
        player1 = ctx.author
        vs_bot = True

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
                    reaction, _ = await self.bot.wait_for('reaction_add', timeout=180, check=check)
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
            self.active_game = None
            return
        p1_total = 0
        p2_total = 0

        async def send_game_state():
            if not self.active_game: return
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
            while self.active_game:
                roll_results = [roll_single_die() for _ in range(remaining_dice)]
                dice_values = [v for v, _ in roll_results]
                if not has_scoring_combo(dice_values):
                    if self.active_game:
                        await ctx.send(f"💀 **FARKLE od razu!** {player1.mention} – brak punktujących kostek w rzucie.")
                    return
                # ... reszta player_turn (dice_parts, embed, reakcje, obsługa kept, calculate_points itd.)
                # wklej tutaj całą swoją oryginalną logikę z player_turn – to jest długie, więc pomijam kopiowanie wszystkiego
                # po prostu skopiuj z Twojego starego main.py fragment od "# Rzut" do końca player_turn

        async def bot_turn():
            # ... wklej całą funkcję bot_turn z Twojego kodu

        await send_game_state()
        while self.active_game and p1_total < target_points and p2_total < target_points:
            await player_turn()
            if not self.active_game or p1_total >= target_points:
                break
            await bot_turn()
            if not self.active_game or p2_total >= target_points:
                break
            await send_game_state()
        if self.active_game:
            winner = player1 if p1_total >= target_points else "Bot"
            await ctx.send(embed=discord.Embed(title="🏆 KONIEC!", description=f"**Wygrywa {winner}!**\n{player1.display_name}: {p1_total} pkt\nBot: {p2_total} pkt", color=0xffd700))
        self.active_game = None

    @commands.command(aliases=['stop'])
    async def skończ(self, ctx):
        if self.active_game == ctx.channel.id:
            self.active_game = None
            await ctx.send("Gra przerwana.")
        else:
            await ctx.send("Brak gry.")

async def setup(bot):
    await bot.add_cog(Farkle(bot))
