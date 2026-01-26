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
        Przykład: 8ankieta "Która pizza?" "Pepperoni" "Margherita" "Hawaje"
        """
        # Normalizujemy polskie cudzysłowy → zwykłe
        tekst = pytanie_i_opcje.replace('“', '"').replace('”', '"').replace('„', '"').replace('”', '"').strip()

        # Rozdzielamy po cudzysłowach, usuwamy puste elementy
        części = [p.strip() for p in tekst.split('"') if p.strip()]

        if len(części) < 3 or len(części) % 2 == 0:
            return await ctx.send(
                "❌ Zły format!\n\n"
                "Poprawnie:\n"
                '`8ankieta "Pytanie?" "Opcja 1" "Opcja 2" "Opcja 3"`\n\n'
                "Pytanie musi być w pierwszych cudzysłowach, każda opcja w osobnych."
            )

        pytanie = części[0]
        opcje = części[1:]

        if len(opcje) < 2 or len(opcje) > 10:
            return await ctx.send("❌ Ankieta musi mieć od 2 do 10 opcji!")

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
                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    timeout=600.0,
                    check=lambda r, u: r.message.id == msg.id and str(r.emoji) in emojis[:len(opcje)] + ["❌"]
                )

                emoji_str = str(reaction.emoji)

                if emoji_str == "❌" and user == ctx.author:
                    embed.set_footer(text=f"Ankieta zakończona przez {ctx.author.display_name}")
                    await msg.edit(embed=embed)
                    break

                if emoji_str in votes and user.id not in voters[emoji_str]:
                    votes[emoji_str] += 1
                    voters[emoji_str].add(user.id)

                    total = sum(votes.values())
                    linie = []
                    for i, em in enumerate(emojis[:len(opcje)]):
                        proc = round(votes[em] / total * 100, 1) if total > 0 else 0
                        linie.append(f"{em} **{votes[em]}** ({proc}%) – {opcje[i]}")

                    embed = discord.Embed(
                        title=f"📊 {pytanie}",
                        description="**Wyniki na żywo**\n\n" + "\n".join(linie),
                        color=0x00ff88
                    )
                    embed.set_footer(text=f"{total} głosów • Stworzona przez {ctx.author.display_name} • ❌ zamknij")
                    await msg.edit(embed=embed)

                await msg.remove_reaction(reaction.emoji, user)

            except asyncio.TimeoutError:
                total = sum(votes.values())
                if total == 0:
                    await msg.edit(content="Ankieta zakończona bez głosów.", embed=None)
                else:
                    max_v = max(votes.values())
                    zwycięzcy = [opcje[i] for i, v in enumerate(votes.values()) if v == max_v]
                    linie = []
                    for i, em in enumerate(emojis[:len(opcje)]):
                        proc = round(votes[em] / total * 100, 1) if total > 0 else 0
                        linie.append(f"{em} **{votes[em]}** ({proc}%) – {opcje[i]}")

                    embed = discord.Embed(
                        title=f"📊 {pytanie} – ZAKOŃCZONA",
                        description="\n".join(linie) + f"\n\n**Zwycięzca:** {', '.join(zwycięzcy)} ({max_v} głosów)",
                        color=0xffd700
                    )
                    embed.set_footer(text=f"{total} głosów • Ankieta zakończona automatycznie")
                    await msg.edit(embed=embed)
                break

async def setup(bot):
    await bot.add_cog(Ankieta(bot))
