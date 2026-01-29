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

        while True:
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
            if game["mode"] == "vs_bot" and current is None:  # bot turn
                await self.bot_turn(ctx, game)
            else:
                await self.player_turn(ctx, game, current)

            if not ctx.channel.id in self.games:
                break

            # sprawdzamy zwycięzcę
            p1_score = game["scores"].get(game["player1"].id, 0)
            p2_score = game["scores"].get("bot" if game["mode"] == "vs_bot" else game["player2"].id, 0)

            if p1_score >= game["target"]:
                winner = game["player1"]
            elif p2_score >= game["target"]:
                winner = "Bot" if game["mode"] == "vs_bot" else game["player2"]
            else:
                # następna tura
                if game["mode"] == "pvp":
                    game["current_turn"] = game["player2"] if game["current_turn"] == game["player1"] else game["player1"]
                continue

            # koniec gry
            embed = discord.Embed(
                title="🏆 KONIEC GRY!",
                description=f"**Wygrywa {winner.mention if isinstance(winner, discord.Member) else winner}!**\n\n"
                            f"{game['player1'].display_name}: **{p1_score}** pkt\n"
                            f"{'Bot' if game['mode']=='vs_bot' else game['player2'].display_name}: **{p2_score}** pkt",
                color=0xffd700
            )
            await ctx.send(embed=embed)
            self.games.pop(ctx.channel.id, None)
            break

        await self.show_game_state(ctx, game)

    async def player_turn(self, ctx, game, player):
        turn_points = 0
        remaining_dice = 6

        while True:
            if remaining_dice == 0:
                remaining_dice = 6
                await ctx.send(f"🔥 **HOT DICE!** {player.mention} rzuca znowu 6 kostkami!")

            dice = [random.randint(1, 6) for _ in range(remaining_dice)]
            if not self.has_scoring_combo(dice):
                await ctx.send(embed=discord.Embed(
                    title="💀 FARKLE!",
                    description=f"{player.mention} – brak punktujących kombinacji!",
                    color=0xff0000
                ))
                return

            dice_str = " ".join(f"**{d}**" for d in dice)
            embed = discord.Embed(
                title=f"🎲 Tura {player.display_name} – {remaining_dice} kostek",
                description=f"Kostki: {dice_str}\n\n**Punkty w turze:** {turn_points}",
                color=0x2b2d31
            )
            embed.set_footer(text="Kliknij cyfrę aby zachować | ✅ kontynuuj | ❌ bankuj | 90s na decyzję")
            msg = await ctx.send(embed=embed)

            for d in set(dice):
                await msg.add_reaction(f"{d}️⃣")
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            kept = set()
            def check(r, u):
                return u == player and r.message.id == msg.id

            while True:
                try:
                    reaction, _ = await self.bot.wait_for("reaction_add", timeout=90, check=check)
                except asyncio.TimeoutError:
                    await ctx.send(f"⏰ Czas minął – bankuję **{turn_points}** pkt dla {player.mention}")
                    game["scores"][player.id] += turn_points
                    return

                emoji = str(reaction.emoji)
                if emoji[0].isdigit():
                    num = int(emoji[0])
                    if num in dice:
                        kept.add(num)
                if emoji in ["✅", "❌"]:
                    break

            kept_list = [d for d in dice if d in kept]
            points, has_points = self.calculate_points(kept_list)

            if emoji == "✅":
                if not has_points:
                    await ctx.send(embed=discord.Embed(title="💀 FARKLE!", description="Wybrana kombinacja nic nie daje!", color=0xff0000))
                    return
                turn_points += points
                remaining_dice -= len(kept_list)
                await ctx.send(f"+**{points}** pkt → razem w turze: **{turn_points}**")
            else:  # ❌ bankuj
                if turn_points == 0:
                    await ctx.send(embed=discord.Embed(title="💀 FARKLE!", description="Nie zachowałeś nic punktującego!", color=0xff0000))
                    return
                game["scores"][player.id] += turn_points
                await ctx.send(f"Bankujesz **{turn_points}** pkt!")
                return

    async def bot_turn(self, ctx, game):
        turn_points = 0
        remaining_dice = 6

        for _ in range(5):  # max 5 rzutów bota
            if remaining_dice == 0:
                remaining_dice = 6

            dice = [random.randint(1, 6) for _ in range(remaining_dice)]
            if not self.has_scoring_combo(dice):
                await ctx.send("🤖 Bot farklował! 😞")
                return

            counts = Counter(dice)
            kept = []
            for num, cnt in counts.items():
                if cnt >= 3:
                    kept.extend([num] * cnt)
                elif num in (1, 5) and cnt > 0:
                    if random.random() < 0.7:  # bot czasem pomija pojedyncze
                        kept.extend([num] * cnt)

            points, _ = self.calculate_points(kept)
            turn_points += points
            remaining_dice -= len(kept)

            dice_str = " ".join(f"**{d}**" for d in dice)
            await ctx.send(embed=discord.Embed(
                title="🤖 Bot rzuca",
                description=f"Kostki: {dice_str}\n+**{points}** pkt → razem: **{turn_points}**",
                color=0x5865f2
            ))

            await asyncio.sleep(random.uniform(1.0, 2.5))

            # decyzja o bankowaniu
            if turn_points > 500 or remaining_dice <= 2 or random.random() < 0.4:
                game["scores"]["bot"] += turn_points
                await ctx.send(f"🤖 Bankuje **{turn_points}** pkt!")
                return

        # jeśli dotarł tu – farkle z powodu zbyt ryzykownego grania
        await ctx.send("🤖 Bot za bardzo zaryzykował i farklował!")
        return

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
        embed.add_field(name="Aktualna tura", value=game["current_turn"].mention if game["current_turn"] else "Bot", inline=False)
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
        counts = Counter(dice)
        if sorted(dice) == [1,2,3,4,5,6]:
            return True
        if any(v >= 3 for v in counts.values()):
            return True
        return counts[1] > 0 or counts[5] > 0

    @staticmethod
    def calculate_points(dice):
        if sorted(dice) == [1,2,3,4,5,6]:
            return 1500, True
        counts = Counter(dice)
        points = 0
        for num in range(1, 7):
            c = counts[num]
            if c >= 3:
                points += (1000 if num == 1 else num * 100) * (c // 3)
                c %= 3
            points += c * (100 if num == 1 else 50 if num == 5 else 0)
        return points, points > 0

async def setup(bot):
    await bot.add_cog(Farkle(bot))
