# cogs/ankieta.py
import discord
from discord.ext import commands
import asyncio
from datetime import timedelta

class Ankieta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_duration(self, time_str: str) -> timedelta:
        """Parsuje czas w formacie 30m, 2h, 1d, 3600s"""
        time_str = time_str.lower().replace(" ", "")
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        num = ""
        unit = ""
        for char in time_str:
            if char.isdigit():
                num += char
            else:
                unit = char
                break
        if not num or unit not in multipliers:
            raise ValueError("Nieprawidłowy format czasu")
        seconds = int(num) * multipliers[unit]
        return timedelta(seconds=seconds)

    @commands.command(name="ankieta", aliases=["poll", "głosowanie", "sonda"])
    async def ankieta(self, ctx, *, args: str):
        """
        Tworzy ankietę z reakcjami + opcjonalnym czasem zamknięcia
        Przykład:
        8ankieta "Która pizza?" "Pepperoni" "Margherita" "Hawaje" 30m
        """
        # Normalizujemy polskie cudzysłowy → zwykłe
        tekst = args.replace('“', '"').replace('”', '"').replace('„', '"').replace('”', '"').strip()

        # Rozdzielamy po cudzysłowach
        części = [p.strip() for p in tekst.split('"') if p.strip()]

        if len(części) < 3 or len(części) % 2 == 0:
            return await ctx.send(
                "❌ Zły format!\n\n"
                "Poprawnie:\n"
                '`8ankieta "Pytanie?" "Opcja 1" "Opcja 2" [czas]`\n\n'
                "Czas opcjonalny: 30m, 2h, 1d, 3600s"
            )

        pytanie = części[0]
        ostatni = części[-1]

        # Sprawdzamy, czy ostatni argument to czas
        timeout_sec = 600  # domyślnie 10 minut
        opcje = części[1:]

        if ostatni.lower().endswith(('s', 'm', 'h', 'd')) and ostatni[:-1].isdigit():
            try:
                duration = self.parse_duration(ostatni)
                timeout_sec = int(duration.total_seconds())
                opcje = części[1:-1]  # ostatni to czas → opcje do przedostatniego
            except ValueError:
                pass  # traktujemy jako zwykłą opcję

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
        embed.set_footer(text=f"Stworzona przez {ctx.author.display_name} • Zamyka się za {timeout_sec//60} min • ❌ zamknąć ręcznie")

        msg = await ctx.send(embed=embed)

        for emoji in emojis[:len(opcje)]:
            await msg.add_reaction(emoji)
        await msg.add_reaction("❌")

        votes = {emoji: 0 for emoji in emojis[:len(opcje)]}
        voters = {emoji: set() for emoji in emojis[:len(opcje)]}
        voted_users = set()
        show_voters_reaction_added = False

        try:
            while True:
                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    timeout=timeout_sec,
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
                    title=f"📊 {pytanie} – ZAKOŃCZONA (czas minął)",
                    description="\n".join(linie) + f"\n\n**Zwycięzca:** {', '.join(zwycięzcy)} ({max_v} głosów)",
                    color=0xffd700
                )
                embed.set_footer(text=f"{total} głosów • Ankieta zakończona automatycznie")
                await msg.edit(embed=embed)

async def setup(bot):
    await bot.add_cog(Ankieta(bot))
