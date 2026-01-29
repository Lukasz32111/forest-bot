# cogs/farkle.py
import random
from collections import Counter
import discord
from discord.ext import commands
import asyncio

class Farkle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # channel_id -> game dict

    @commands.command(aliases=['farkle', 'gra'])
    async def rzut(self, ctx, opponent: discord.Member = None):
        channel_id = ctx.channel.id

        if channel_id in self.games:
            await ctx.send("Na tym kanale trwa już gra! Użyj `8skończ` żeby przerwać.")
            return

        player1 = ctx.author

        if opponent is None:
            # ── vs BOT ────────────────────────────────────────
            await ctx.send(f"🎲 **{player1.mention}** zaczyna grę Farkle **z botem**!")
            game = {
                "mode": "vs_bot",
                "player1": player1,
                "player2": None,
                "current_turn": player1,
                "scores": {player1.id: 0, "bot": 0},
                "target": None,
                "channel": ctx.channel,
                "state": "choosing_target"
            }
            self.games[channel_id] = game
            await self.choose_target(ctx, game)

        else:
            # ── PvP ───────────────────────────────────────────
            if opponent == player1:
                return await ctx.send("Nie możesz grać sam ze sobą 😅")
            if opponent.bot:
                return await ctx.send("Nie możesz rzucić wyzwania botowi. Użyj po prostu `8rzut`.")

            challenge_msg = await ctx.send(
                f"🎲 {player1.mention} rzuca wyzwanie w Farkle!\n"
                f"{opponent.mention}, akceptujesz? Reaguj **✅** tak / **❌** nie\n"
                "Masz 60 sekund."
            )
            await challenge_msg.add_reaction("✅")
            await challenge_msg.add_reaction("❌")

            def check(r, u):
                return u == opponent and str(r.emoji) in ["✅", "❌"] and r.message.id == challenge_msg.id

            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "❌":
                    await ctx.send(f"{opponent.mention} odmówił. Gra anulowana.")
                    return

                await ctx.send(f"{opponent.mention} zaakceptował! Zaczynamy 1v1 🎲")

                starter = random.choice([player1, opponent])
                game = {
                    "mode": "pvp",
                    "player1": player1,
                    "player2": opponent,
                    "current_turn": starter,
                    "scores": {player1.id: 0, opponent.id: 0},
                    "target": None,
                    "channel": ctx.channel,
                    "state": "choosing_target"
                }
                self.games[channel_id] = game
                await ctx.send(f"Pierwszy rzuca: **{starter.mention}**!")
                await self.choose_target(ctx, game)

            except asyncio.TimeoutError:
                await ctx.send("Czas na akceptację minął. Gra anulowana.")

    async def choose_target(self, ctx, game):
        if ctx.channel.id not in self.games:
            return
        embed = discord.Embed(
            title="🎲 Wybór celu gry",
            description="🇦 → 1000 pkt\n🇧 → 2000 pkt\n🇨 → 5000 pkt (klasyczna)\n🇩 → 10000 pkt\n\n❓ = poradnik",
            color=0x2b2d31
        )
        embed.set_footer(text=f"Reaguj wybraną literką | Gracz: {game['current_turn'].display_name}")
        msg = await ctx.send(embed=embed)
        for r in ['🇦', '🇧', '🇨', '🇩', '❓']:
            await msg.add_reaction(r)

        def check(r, u):
            return u == game["current_turn"] and str(r.emoji) in ['🇦','🇧','🇨','🇩','❓'] and r.message.id == msg.id

        while ctx.channel.id in self.games:
            try:
                reaction, _ = await self.bot.wait_for('reaction_add', timeout=180, check=check)
            except asyncio.TimeoutError:
                await ctx.send("Czas minął – gra anulowana.")
                self.games.pop(ctx.channel.id, None)
                return

            emoji = str(reaction.emoji)
            if emoji == '❓':
                poradnik = (
                    "**📜 Poradnik Farkle**\n\n"
                    "• 1 = 100 pkt\n"
                    "• 5 = 50 pkt\n"
                    "• Trójka takich samych = liczba × 100 (trójka 1 = 1000)\n"
                    "• Strit 1-6 = 1500 pkt\n"
                    "**Hot Dice** – zużyjesz wszystkie kostki → rzucasz 6 nowych!\n"
                    "**Farkle** – zero punktów w rzucie → tracisz punkty tury!\n"
                    "Możesz zachować tylko punktujące kombinacje!"
                )
                await ctx.send(poradnik)
                continue

            options = {'🇦': 1000, '🇧': 2000, '🇨': 5000, '🇩': 10000}
            if emoji in options:
                game["target"] = options[emoji]
                await ctx.send(f"✅ Cel gry: **{game['target']}** punktów! Zaczynamy!")
                game["state"] = "playing"
                await self.play_game(ctx, game)
                return

    async def play_game(self, ctx, game):
        while ctx.channel.id in self.games:
            current = game["current_turn"]
            await self.show_game_state(ctx, game)
            if game["mode"] == "vs_bot" and current is None:  # bot turn
                await self.bot_turn(ctx, game)
            else:
                await self.player_turn(ctx, game, current)

            if ctx.channel.id not in self.games:
                break

            # sprawdzamy zwycięzcę
            p1_score = game["scores"].get(game["player1"].id, 0)
            p2_score = game["scores"].get("bot" if game["mode"] == "vs_bot" else game["player2"].id, 0)

            if p1_score >= game["target"] or p2_score >= game["target"]:
                winner = game["player1"] if p1_score >= game["target"] else ("Bot" if game["mode"] == "vs_bot" else game["player2"])
                embed = discord.Embed(
                    title="🏆 KONIEC GRY!",
                    description=f"**Wygrywa {winner if isinstance(winner, str) else winner.mention}!**\n\n"
                                f"{game['player1'].display_name}: **{p1_score}** pkt\n"
                                f"{'Bot' if game['mode']=='vs_bot' else game['player2'].display_name}: **{p2_score}** pkt",
                    color=0xffd700
                )
                await ctx.send(embed=embed)
                self.games.pop(ctx.channel.id, None)
                return

            # następna tura
            if game["mode"] == "vs_bot":
                game["current_turn"] = None if current == game["player1"] else game["player1"]
            else:
                game["current_turn"] = game["player2"] if current == game["player1"] else game["player1"]

    async def player_turn(self, ctx, game, player):
        if ctx.channel.id not in self.games:
            return
        turn_points = 0
        remaining_dice = 6
        turn_num = 1

        while ctx.channel.id in self.games:
            dice = [random.randint(1, 6) for _ in range(remaining_dice)]
            if not self.has_scoring_combo(dice):
                await ctx.send(embed=discord.Embed(
                    title="💀 FARKLE!",
                    description=f"{player.mention} – brak punktujących kombinacji!",
                    color=0xff0000
                ))
                return

            dice_str = " ".join(f"**{d}**" for d in sorted(dice))
            embed = discord.Embed(
                title=f"🎲 Rzut {turn_num} – {player.display_name}",
                description=f"Kostki: {dice_str}\n\n**Punkty w turze:** {turn_points}",
                color=0x2b2d31
            )
            embed.set_footer(text="Kliknij cyfrę aby zachować (tylko punktujące!) | ✅ kontynuuj | ❌ bankuj | 90s")
            msg = await ctx.send(embed=embed)

            scoring_nums = self.get_scoring_nums(dice)
            for d in scoring_nums:
                await msg.add_reaction(f"{d}️⃣")
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            kept = set()
            def check(r, u):
                return u == player and r.message.id == msg.id and ctx.channel.id in self.games

            reacted_emoji = None
            while ctx.channel.id in self.games:
                try:
                    reaction, _ = await self.bot.wait_for("reaction_add", timeout=90, check=check)
                except asyncio.TimeoutError:
                    if ctx.channel.id in self.games:
                        await ctx.send(f"⏰ Czas minął – bankuję **{turn_points}** pkt dla {player.mention}")
                        game["scores"][player.id] += turn_points
                    return

                reacted_emoji = str(reaction.emoji)
                if reacted_emoji[0].isdigit():
                    num = int(reacted_emoji[0])
                    if num in scoring_nums:
                        kept.add(num)
                if reacted_emoji in ["✅", "❌"]:
                    break

            if ctx.channel.id not in self.games:
                return

            kept_list = []
            counts = Counter(dice)
            for num in kept:
                kept_list.extend([num] * counts[num])  # zachowujemy wszystkie wystąpienia wybranego numeru

            points, has_points = self.calculate_points(kept_list)

            if not has_points or points == 0:
                await ctx.send(embed=discord.Embed(title="💀 FARKLE!", description="Wybrana kombinacja nic nie daje!", color=0xff0000))
                return

            if reacted_emoji == "✅":
                turn_points += points
                remaining_dice -= len(kept_list)
                await ctx.send(f"+**{points}** pkt → razem w turze: **{turn_points}**")
                if remaining_dice == 0:
                    await ctx.send(f"🔥 **HOT DICE!** {player.mention} rzuca znowu 6 kostkami!")
                    remaining_dice = 6
                turn_num += 1
            else:  # ❌ bankuj
                turn_points += points  # dodajemy ostatnie punkty przed bankowaniem
                game["scores"][player.id] += turn_points
                await ctx.send(f"Bankujesz **{turn_points}** pkt!")
                return

    async def bot_turn(self, ctx, game):
        if ctx.channel.id not in self.games:
            return
        turn_points = 0
        remaining_dice = 6
        turn_num = 1

        for _ in range(5):  # max 5 rzutów bota
            if ctx.channel.id not in self.games:
                return

            dice = [random.randint(1, 6) for _ in range(remaining_dice)]
            if not self.has_scoring_combo(dice):
                await ctx.send("🤖 Bot farklował! 😞")
                return

            scoring_nums = self.get_scoring_nums(dice)
            counts = Counter(dice)

            kept = []
            for num in scoring_nums:
                if random.random() < 0.8:  # bot czasem nie bierze wszystkiego
                    kept.extend([num] * counts[num])

            points, _ = self.calculate_points(kept)
            if points == 0:
                await ctx.send("🤖 Bot farklował! 😞")
                return

            turn_points += points
            remaining_dice -= len(kept)

            dice_str = " ".join(f"**{d}**" for d in sorted(dice))
            await ctx.send(embed=discord.Embed(
                title=f"🤖 Bot – rzut {turn_num}",
                description=f"Kostki: {dice_str}\n+**{points}** pkt → razem: **{turn_points}**",
                color=0x5865f2
            ))

            await asyncio.sleep(random.uniform(1.0, 2.5))

            if remaining_dice == 0:
                remaining_dice = 6

            # decyzja o bankowaniu
            bank_chance = 0.3 if turn_points < 300 else 0.6 if turn_points < 600 else 0.9
            if random.random() < bank_chance or remaining_dice <= 2:
                game["scores"]["bot"] += turn_points
                await ctx.send(f"🤖 Bankuje **{turn_points}** pkt!")
                return

            turn_num += 1

        # jeśli zbyt długo
        await ctx.send("🤖 Bot za bardzo zaryzykował i farklował!")

    async def show_game_state(self, ctx, game):
        if ctx.channel.id not in self.games:
            return
        p1 = game["player1"].display_name
        p2 = "Bot" if game["mode"] == "vs_bot" else game["player2"].display_name
        s1 = game["scores"].get(game["player1"].id, 0)
        s2 = game["scores"].get("bot" if game["mode"] == "vs_bot" else game["player2"].id, 0)

        embed = discord.Embed(title=f"Farkle • Cel: {game['target']} pkt", color=0x2b2d31)
        embed.add_field(name=p1, value=f"**{s1}** pkt", inline=True)
        embed.add_field(name=p2, value=f"**{s2}** pkt", inline=True)
        current_name = "Bot" if game["current_turn"] is None else game["current_turn"].display_name
        embed.add_field(name="Aktualna tura", value=current_name, inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=['stop', 'koniec'])
    async def skończ(self, ctx):
        if ctx.channel.id in self.games:
            del self.games[ctx.channel.id]
            await ctx.send("Gra przerwana.")
        else:
            await ctx.send("Nie ma żadnej gry na tym kanale.")

    @staticmethod
    def has_scoring_combo(dice):
        if len(dice) == 0:
            return False
        counts = Counter(dice)
        if len(dice) == 6 and sorted(dice) == [1,2,3,4,5,6]:
            return True
        if any(c >= 3 for c in counts.values()):
            return True
        return counts[1] > 0 or counts[5] > 0

    @staticmethod
    def calculate_points(dice):
        if not dice:
            return 0, False
        if len(dice) == 6 and sorted(dice) == [1,2,3,4,5,6]:
            return 1500, True
        counts = Counter(dice)
        points = 0
        used = Counter()
        for num, count in counts.items():
            triples = count // 3
            if triples > 0:
                points += triples * (1000 if num == 1 else num * 100)
                used[num] += triples * 3
        remaining = {num: count - used[num] for num, count in counts.items()}
        points += remaining.get(1, 0) * 100
        points += remaining.get(5, 0) * 50
        return points, points > 0

    @staticmethod
    def get_scoring_nums(dice):
        counts = Counter(dice)
        scoring = set()
        if len(dice) == 6 and sorted(dice) == [1,2,3,4,5,6]:
            return set(range(1,7))  # cały strit
        for num, c in counts.items():
            if c >= 3 or num in (1,5):
                scoring.add(num)
        return scoring

async def setup(bot):
    await bot.add_cog(Farkle(bot))
