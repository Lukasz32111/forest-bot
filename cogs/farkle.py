# cogs/farkle.py
import random
from collections import Counter
import discord
from discord.ext import commands
import asyncio

class Farkle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_game = None

    @commands.command()
    async def rzut(self, ctx, opponent: discord.Member = None):
        if self.active_game is not None:
            await ctx.send("Gra już trwa! Użyj `8skończ`.")
            return
        self.active_game = ctx.channel.id
        await ctx.send("🎲 Start gry z botem!")
        player1 = ctx.author

        async def choose_target():
            nonlocal target_points
            embed = discord.Embed(
                title="🎲 Wybór celu gry",
                description="🇦 → 1000 pkt\n🇧 → 2000 pkt\n🇨 → 5000 pkt (klasyczna)\n🇩 → 10000 pkt\n\n❓ = poradnik",
                color=0x2b2d31
            )
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
            if not self.active_game:
                return
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
                # Rzut kostkami – zwykłe 1-6
                dice_values = [random.randint(1, 6) for _ in range(remaining_dice)]

                if not has_scoring_combo(dice_values):
                    if self.active_game:
                        embed = discord.Embed(
                            title="💀 FARKLE!",
                            description=f"{player1.mention} – brak punktujących kombinacji w rzucie.",
                            color=0xff0000
                        )
                        await ctx.send(embed=embed)
                    return

                # Czytelne wyświetlanie kostek
                dice_display = " ".join([f"**{v}**" for v in dice_values])
                embed = discord.Embed(
                    title=f"Rzut {turn_num} – {player1.display_name}",
                    description=f"Kostki: {dice_display}\n\n"
                                f"**Pozostało kostek:** {remaining_dice}   "
                                f"**Punkty w tej turze:** {points_this_turn}",
                    color=0x2b2d31
                )
                embed.set_footer(text="Kliknij cyfrę aby zachować | ✅ kontynuuj | ❌ bankuj | ⏰ automat po 90 s")
                msg = await ctx.send(embed=embed)

                for d in set(dice_values):
                    await msg.add_reaction(f'{d}️⃣')
                await msg.add_reaction('✅')
                await msg.add_reaction('❌')

                kept = set()
                def check(r, u):
                    return u == player1 and r.message.id == msg.id and self.active_game

                reacted_emoji = None
                while self.active_game:
                    try:
                        reaction, _ = await self.bot.wait_for('reaction_add', timeout=90, check=check)
                    except asyncio.TimeoutError:
                        if self.active_game:
                            embed = discord.Embed(
                                title="⏰ Czas minął",
                                description=f"Automatycznie bankuję **{points_this_turn}** punktów.",
                                color=0x5865f2
                            )
                            await ctx.send(embed=embed)
                            p1_total += points_this_turn
                        return

                    reacted_emoji = str(reaction.emoji)

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
                        embed = discord.Embed(
                            title="💀 FARKLE!",
                            description=f"{player1.mention} – wybrana kombinacja nie daje punktów.",
                            color=0xff0000
                        )
                        await ctx.send(embed=embed)
                        return

                    points_this_turn += turn_points
                    remaining_dice -= len(kept_list)

                    color = 0x00ff00 if turn_points > 300 else 0x2b2d31
                    embed = discord.Embed(
                        title=f"+{turn_points} punktów!",
                        description=f"**Razem w turze:** {points_this_turn}",
                        color=color
                    )
                    await ctx.send(embed=embed)

                    if remaining_dice == 0:
                        await ctx.send("🔥 **HOT DICE!** Rzucasz znowu 6 kostkami!")
                        remaining_dice = 6

                    turn_num += 1

                else:  # ❌ lub timeout
                    if has_points:
                        points_this_turn += turn_points

                    if points_this_turn == 0:
                        embed = discord.Embed(
                            title="💀 FARKLE!",
                            description=f"{player1.mention} – nie zachowałeś nic punktującego.",
                            color=0xff0000
                        )
                        await ctx.send(embed=embed)
                        return

                    embed = discord.Embed(
                        title="Bankujesz punkty",
                        description=f"**{points_this_turn}** punktów dodane do konta!",
                        color=0x00aa00
                    )
                    await ctx.send(embed=embed)
                    p1_total += points_this_turn
                    return

        async def bot_turn():
            nonlocal p2_total
            points_this_turn = 0
            remaining_dice = 6
            for _ in range(3):
                if not self.active_game:
                    return
                dice_values = [random.randint(1, 6) for _ in range(remaining_dice)]
                if not has_scoring_combo(dice_values):
                    await ctx.send("🤖 Bot – Farkle!")
                    return
                counts = Counter(dice_values)
                kept = set()
                for num in range(6, 0, -1):
                    if counts[num] >= 3 or (num in [1, 5] and counts[num] > 0):
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
            embed = discord.Embed(
                title="🏆 KONIEC GRY!",
                description=f"**Wygrywa {winner}!**\n\n{player1.display_name}: **{p1_total}** pkt\nBot: **{p2_total}** pkt",
                color=0xffd700
            )
            await ctx.send(embed=embed)
        self.active_game = None

    @commands.command(aliases=['stop'])
    async def skończ(self, ctx):
        if self.active_game == ctx.channel.id:
            self.active_game = None
            await ctx.send("Gra przerwana.")
        else:
            await ctx.send("Brak gry.")

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

async def setup(bot):
    await bot.add_cog(Farkle(bot))
