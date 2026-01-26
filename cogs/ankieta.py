# cogs/ankieta.py
import discord
from discord.ext import commands
import asyncio

class Ankieta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ankieta", aliases=["poll", "głosowanie", "sonda"])
    async def ankieta(self, ctx, *, pytanie_i_opcje: str):
        """
        Tworzy ankietę z reakcjami
        8ankieta "Która pizza?" "Pepperoni" "Margherita" "Hawaii" "4 sery" "Wege"
        """
        parts = pytanie_i_opcje.split('"')
        if len(parts) < 3 or len(parts) % 2 == 0:
            return await ctx.send("❌ Zły format! Przykład:\n`8ankieta \"Która pizza?\" \"Pepperoni\" \"Margherita\" \"Hawaii\"`")

        pytanie = parts[1].strip()
        opcje = [opt.strip() for opt in parts[2::2] if opt.strip()]

        if len(opcje) < 2 or len(opcje) > 10:
            return await ctx.send("❌ Musi być 2–10 opcji!")

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        opcje = opcje[:10]

        embed = discord.Embed(
            title=f"📊 {pytanie}",
            color=0x5865f2
        )
        embed.add_field(
            name="Opcje (głosuj reakcją)",
            value="\n".join(f"{emojis[i]} {opcje[i]}" for i in range(len(opcje))),
            inline=False
        )
        embed.set_footer(text=f"Stworzona przez {ctx.author.display_name} • Kliknij ❌ aby zakończyć")

        msg = await ctx.send(embed=embed)

        for emoji in emojis[:len(opcje)]:
            await msg.add_reaction(emoji)
        await msg.add_reaction("❌")

        votes = {emoji: 0 for emoji in emojis[:len(opcje)]}
        voters = {emoji: set() for emoji in emojis[:len(opcje)]}

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=600.0, check=lambda r, u: r.message.id == msg.id and str(r.emoji) in emojis[:len(opcje)] + ["❌"])

                emoji_str = str(reaction.emoji)

                if emoji_str == "❌" and user == ctx.author:
                    embed.set_footer(text=f"Ankieta zakończona przez {ctx.author.display_name}")
                    await msg.edit(embed=embed)
                    break

                if emoji_str in votes and user.id not in voters[emoji_str]:
                    votes[emoji_str] += 1
                    voters[emoji_str].add(user.id)

                    total_votes = sum(votes.values())
                    wyniki = []
                    for i, emoji in enumerate(emojis[:len(opcje)]):
                        procent = round((votes[emoji] / total_votes * 100), 1) if total_votes > 0 else 0
                        wyniki.append(f"{emoji} **{votes[emoji]}** ({procent}%) – {opcje[i]}")

                    embed = discord.Embed(
                        title=f"📊 {pytanie}",
                        description="**Wyniki na żywo** (głosuj reakcją)\n\n" + "\n".join(wyniki),
                        color=0x00ff88
                    )
                    embed.set_footer(text=f"{total_votes} głosów • Stworzona przez {ctx.author.display_name} • ❌ zamknij")
                    await msg.edit(embed=embed)

                await msg.remove_reaction(reaction.emoji, user)

            except asyncio.TimeoutError:
                total_votes = sum(votes.values())
                if total_votes == 0:
                    await msg.edit(content="Ankieta zakończona bez głosów.", embed=None)
                else:
                    max_votes = max(votes.values())
                    winners = [opcje[i] for i, v in enumerate(votes.values()) if v == max_votes]
                    wyniki = []
                    for i, emoji in enumerate(emojis[:len(opcje)]):
                        procent = round((votes[emoji] / total_votes * 100), 1) if total_votes > 0 else 0
                        wyniki.append(f"{emoji} **{votes[emoji]}** ({procent}%) – {opcje[i]}")

                    embed = discord.Embed(
                        title=f"📊 {pytanie} – ZAKOŃCZONA",
                        description="\n".join(wyniki) + f"\n\n**Zwycięzca:** {', '.join(winners)} ({max_votes} głosów)",
                        color=0xffd700
                    )
                    embed.set_footer(text=f"{total_votes} głosów • Ankieta zakończona automatycznie")
                    await msg.edit(embed=embed)
                break
