# cogs/farkle.py
import random
from collections import Counter
import discord
from discord.ext import commands

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
        # ← Tu w przyszłości wkleisz całą swoją oryginalną logikę gry (choose_target, player_turn itd.)
        # Na razie testowa wiadomość, żeby bot nie crashował
        await ctx.send("🎲 Komenda rzut działa! (logika gry będzie dodana później)")

    @commands.command(aliases=['stop'])
    async def skończ(self, ctx):
        if self.active_game == ctx.channel.id:
            self.active_game = None
            await ctx.send("Gra przerwana.")
        else:
            await ctx.send("Brak gry.")

async def setup(bot):
    await bot.add_cog(Farkle(bot))
