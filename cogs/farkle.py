# cogs/farkle.py
import random
from collections import Counter
import discord
from discord.ext import commands
import asyncio

class Farkle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    @commands.command(aliases=['farkle', 'gra'])
    async def rzut(self, ctx, opponent: discord.Member = None):
        channel_id = ctx.channel.id
        if channel_id in self.games:
            await ctx.send("Na tym kanale trwa już gra! Użyj `8skończ` żeby przerwać.")
            return

        player1 = ctx.author

        if opponent is None:
            # vs BOT
            await ctx.send(f"🎲 **{player1.mention}** zaczyna grę Farkle **z botem**!")
            game = {
                "mode": "vs_bot",
                "player1": player1,
                "player2": None,
                "current_turn": player1,
                "scores": {player1.id: 0, "bot": 0},
                "target": None,
                "channel": ctx.channel
            }
            self.games[channel_id] = game
            await self.choose_target(ctx, game)

        else:
            # PvP
            if opponent == player1:
                return await ctx.send("Nie możesz grać sam ze sobą 😅")
            if opponent.bot:
                return await ctx.send("Nie możesz rzucić wyzwania botowi. Użyj po prostu `8rzut`.")

            challenge_msg = await ctx.send(
                f"🎲 {player1.mention} rzuca wyzwanie w Farkle!\n"
                f"{opponent.mention}, akceptujesz? Reaguj **✅** tak / **❌** nie (60s)"
            )
            await challenge_msg.add_reaction("✅")
            await challenge_msg.add_reaction("❌")

            def check(r, u):
                return u == opponent and str(r.emoji) in ["✅", "❌"] and r.message.id == challenge_msg.id

            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "❌":
                    return await ctx.send(f"{opponent.mention} odmówił. Gra anulowana.")

                starter = random.choice([player1, opponent])
                game = {
                    "mode": "pvp",
                    "player1": player1,
                    "player2": opponent,
                    "current_turn": starter,
                    "scores": {player1.id: 0, opponent.id: 0},
                    "target": None,
                    "channel": ctx.channel
                }
                self.games[channel_id] = game
                await ctx.send(f"{opponent.mention} zaakceptował! **{starter.mention}** zaczyna!")
                await self.choose_target(ctx, game)

            except asyncio.TimeoutError:
                await ctx.send("Czas minął – wyzwanie anulowane.")

    async def choose_target(self, ctx, game):
        embed = discord.Embed(title="🎲 Wybór celu gry", color=0x2b2d31)
        embed.description = "🇦 → 1000 pkt\n🇧 → 2000 pkt\n🇨 → 5000 pkt (klasyczna)\n🇩 → 10000 pkt\n\n❓ = poradnik"
        embed.set_footer(text=f"Reaguj literką • Gracz: {game['current_turn'].display_name}")
        msg = await ctx.send(embed=embed)
        for r in ['🇦', '🇧', '🇨', '🇩', '❓']:
            await msg.add_reaction(r)

        def check(r, u):
            return u == game["current_turn"] and str(r.emoji) in "🇦🇧🇨🇩❓" and r.message.id == msg.id

        while ctx.channel.id in self.games:
            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=180, check=check)
            except asyncio.TimeoutError:
                await ctx.send("Czas minął – gra anulowana.")
                self.games.pop(ctx.channel.id, None)
                return

            if str(reaction.emoji) == '❓':
                await ctx.send(
                    "**Poradnik Farkle**\n\n"
                    "• Pojedyncza 1 → 100 pkt\n"
                    "• Pojedyncza 5 → 50 pkt\n"
                    "• Trójka (lub więcej) → liczba × 100 (trójka 1 = 1000)\n"
                    "• Strit 1-2-3-4-5-6 → 1500 pkt\n\n"
                    "**Możesz wybrać dowolne kości – jeśli nie dadzą punktów → farkle!**"
                )
                continue

            targets = {'🇦': 1000, '🇧': 2000, '🇨': 5000, '🇩': 10000}
            game["target"] = targets[str(reaction.emoji)]
            await ctx.send(f"✅ Cel: **{game['target']}** punktów! Zaczynamy!")
            await self.play_game(ctx, game)
            return

    async def play_game(self, ctx, game):
        await self.show_game_state(ctx, game)

        while ctx.channel.id in self.games:
            current = game["current_turn"]

            if game["mode"] == "vs_bot":
                if current == game["player1"]:
                    await self.player_turn(ctx, game, current)
                    game["current_turn"] = None
                else:
                    await self.bot_turn(ctx, game)
                    game["current_turn"] = game["player1"]
            else:
                await self.player_turn(ctx, game, current)
                game["current_turn"] = game["player2"] if current == game["player1"] else game["player1"]

            if ctx.channel.id not in self.games:
                break

            await self.show_game_state(ctx, game)

            p1_score = game["scores"][game["player1"].id]
            p2_score = game["scores"].get("bot", 0) if game["mode"] == "vs_bot" else game["scores"][game["player2"].id]

            if p1_score >= game["target"] or p2_score >= game["target"]:
                winner = game["player1"] if p1_score >= game["target"] else ( "Bot" if game["mode"] == "vs_bot" else game["player2"] )
                await ctx.send(f"🏆 **{winner.mention if hasattr(winner, 'mention') else winner} wygrywa!**")
                self.games.pop(ctx.channel.id, None)
                return

    async def player_turn(self, ctx, game, player):
        turn_points = 0
        remaining_dice = 6
        turn_num = 1

        while ctx.channel.id in self.games:
            dice = [random.randint(1, 6) for _ in range(remaining_dice)]
            if not self.has_scoring_combo(dice):
                await ctx.send(embed=discord.Embed(title="💀 FARKLE!", description=f"{player.mention} – zero punktujących kombinacji!", color=0xff0000))
                return

            dice_str = " ".join(f"**{d}**" for d in sorted(dice))
            embed = discord.Embed(title=f"🎲 Rzut {turn_num} – {player.display_name}", description=f"Kostki: {dice_str}\n\nPunkty w turze: **{turn_points}**", color=0x2b2d31)
            embed.set_footer(text="Kliknij dowolne cyfry które chcesz zachować • ✅ kontynuuj • ❌ bankuj • 90s")
            msg = await ctx.send(embed=embed)

            # WSZYSTKIE liczby które wypadły – nawet bezużyteczne
            for num in sorted(set(dice)):
                await msg.add_reaction(f"{num}️⃣")
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            kept_counts = Counter()

            def check(r, u):
                return u == player and r.message.id == msg.id and ctx.channel.id in self.games

            decision = None
            while ctx.channel.id in self.games:
                try:
                    reaction, _ = await self.bot.wait_for("reaction_add", timeout=90, check=check)
                except asyncio.TimeoutError:
                    await ctx.send(f"⏰ Czas minął – bankuję **{turn_points}** pkt!")
                    game["scores"][player.id] += turn_points
                    return

                emoji = str(reaction.emoji)
                if emoji in "1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣":
                    num = int(emoji[0])
                    if num in dice:
                        kept_counts[num] += 1
                elif emoji in ["✅", "❌"]:
                    decision = emoji
                    break

            # budujemy listę zachowanych kości
            kept_list = []
            dice_count = Counter(dice)
            for num, clicks in kept_counts.items():
                kept_list.extend([num] * min(clicks, dice_count[num]))

            points, _ = self.calculate_points(kept_list)

            if decision == "✅":
                if points == 0:
                    await ctx.send(embed=discord.Embed(title="💀 FARKLE!", description="Wybrane kości nie dały żadnych punktów!", color=0xff0000))
                    return
                turn_points += points
                remaining_dice -= len(kept_list)
                await ctx.send(f"+**{points}** pkt → razem w turze: **{turn_points}**")
                if remaining_dice == 0:
                    await ctx.send(f"🔥 **HOT DICE!** {player.mention} rzuca znowu 6 kostkami!")
                    remaining_dice = 6
                turn_num += 1

            else:  # bankuj
                game["scores"][player.id] += turn_points
                await ctx.send(f"💰 {player.mention} bankuje **{turn_points}** pkt!")
                return

    async def bot_turn(self, ctx, game):
        turn_points = 0
        remaining_dice = 6
        for _ in range(6):
            dice = [random.randint(1, 6) for _ in range(remaining_dice)]
            if not self.has_scoring_combo(dice):
                await ctx.send("🤖 Bot farklował!")
                return

            # bot wybiera tylko punktujące (żeby nie był głupi)
            scoring = self.get_scoring_nums(dice)
            counts = Counter(dice)
            kept = [num for num in scoring for _ in range(counts[num])]
            points, _ = self.calculate_points(kept)
            turn_points += points
            remaining_dice -= len(kept)

            dice_str = " ".join(f"**{d}**" for d in sorted(dice))
            await ctx.send(embed=discord.Embed(title="🤖 Bot rzuca", description=f"Kostki: {dice_str}\n+{points} → razem: **{turn_points}**", color=0x5865f2))
            await asyncio.sleep(1.8)

            if remaining_dice == 0:
                remaining_dice = 6

            if turn_points >= 600 or (turn_points >= 350 and random.random() < 0.7) or remaining_dice <= 2:
                game["scores"]["bot"] += turn_points
                await ctx.send(f"🤖 Bot bankuje **{turn_points}** pkt!")
                return

        await ctx.send("🤖 Bot za bardzo zaryzykował i farklował!")

    async def show_game_state(self, ctx, game):
        p1 = game["player1"].display_name
        p2 = "Bot" if game["mode"] == "vs_bot" else game["player2"].display_name
        s1 = game["scores"].get(game["player1"].id, 0)
        s2 = game["scores"].get("bot" if game["mode"] == "vs_bot" else game["player2"].id, 0)
        current = "Bot" if game["current_turn"] is None else game["current_turn"].display_name

        embed = discord.Embed(title=f"Farkle • Cel: {game['target']} pkt", color=0x2b2d31)
        embed.add_field(name=p1, value=f"**{s1}** pkt", inline=True)
        embed.add_field(name=p2, value=f"**{s2}** pkt", inline=True)
        embed.add_field(name="Tura", value=current, inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=['stop', 'koniec'])
    async def skończ(self, ctx):
        if ctx.channel.id in self.games:
            del self.games[ctx.channel.id]
            await ctx.send("Gra przerwana.")
        else:
            await ctx.send("Nie ma aktywnej gry.")

    @staticmethod
    def has_scoring_combo(dice):
        if not dice:
            return False
        c = Counter(dice)
        if len(dice) == 6 and sorted(dice) == [1,2,3,4,5,6]:
            return True
        if any(v >= 3 for v in c.values()):
            return True
        return c[1] > 0 or c[5] > 0

    @staticmethod
    def calculate_points(dice):
        if not dice:
            return 0, False
        if len(dice) == 6 and sorted(dice) == [1,2,3,4,5,6]:
            return 1500, True
        c = Counter(dice)
        points = 0
        for num, count in c.items():
            points += (count // 3) * (1000 if num == 1 else num * 100)
        remaining = {num: count % 3 for num, count in c.items()}
        points += remaining.get(1, 0) * 100 + remaining.get(5, 0) * 50
        return points, points > 0

    @staticmethod
    def get_scoring_nums(dice):
        # używane tylko przez bota – gracz widzi wszystko
        c = Counter(dice)
        s = set()
        for num, count in c.items():
            if count >= 3 or num in (1, 5):
                s.add(num)
        return s

async def setup(bot):
    await bot.add_cog(Farkle(bot))
