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
        Przykład:
        8ankieta "Która pizza?" "Pepperoni" "Margherita" "Hawaje" "4 sery"
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
        voters = {emoji: set() for emoji in emojis[:len(opcje)]}  # kto zagłosował na daną opcję
        voted_users = set()  # kto w ogóle zagłosował
        show_voters_reaction_added = False

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    timeout=600.0,
                    check=lambda r, u: r.message.id == msg.id and not u.bot
                )

                emoji_str = str(reaction.emoji)

                # Zamknięcie ankiety przez twórcę
                if emoji_str == "❌" and user == ctx.author:
                    embed.set_footer(text=f"Ankieta zakończona przez {ctx.author.display_name}")
                    await msg.edit(embed=embed)
                    break

                # Pokazanie kto głosował (w DM z pełną nazwą opcji)
                if emoji_str == "👥":
                    if voted_users:
                        lista = []
                        for em, usr_set in voters.items():
                            if usr_set:
                                # Znajdujemy indeks opcji dla tego emoji
                                idx = emojis.index(em)
                                opcja_nazwa = opcje[idx]
                                lista.append(f"{em} ({opcja_nazwa}) → {', '.join([f'<@{u}>' for u in usr_set])}")
                        if lista:
                            lista_txt = "\n".join(lista)
                            await user.send(f"**Głosy w ankiecie:** {pytanie}\n\n{lista_txt}")
                        else:
                            await user.send("Nikt jeszcze nie zagłosował.")
                    else:
                        await user.send("Jeszcze nikt nie zagłosował.")
                    await msg.remove_reaction("👥", user)
                    continue

                # Normalny głos
                if emoji_str in votes:
                    if user.id not in voters[emoji_str]:
                        # Usuwamy poprzedni głos tej osoby (jeśli był)
                        for em in votes:
                            if user.id in voters[em]:
                                voters[em].remove(user.id)
                                votes[em] -= 1
                                break

                        # Dodajemy nowy głos
                        votes[emoji_str] += 1
                        voters[emoji_str].add(user.id)
                        voted_users.add(user.id)

                        # Dodajemy reakcję 👥 dopiero po pierwszym głosie
                        if not show_voters_reaction_added and sum(votes.values()) > 0:
                            await msg.add_reaction("👥")
                            show_voters_reaction_added = True

                        # Aktualizacja embeda z wynikami
                        total = sum(votes.values())
                        linie = []
                        for i, em in enumerate(emojis[:len(opcje)]):
                            proc = round(votes[em] / total * 100, 1) if total > 0 else 0
                            linie.append(f"{em} **{votes[em]}** ({proc}%) – {opcje[i]}")

                        embed = discord.Embed(
                            title=f"📊 {pytanie}",
                            description="**Wyniki na żywo** (głosuj reakcją)\n\n" + "\n".join(linie),
                            color=0x00ff88
                        )
                        embed.set_footer(text=f"{total} głosów • Stworzona przez {ctx.author.display_name} • ❌ zamknij • 👥 kto głosował")
                        await msg.edit(embed=embed)

                    await msg.remove_reaction(emoji_str, user)

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
