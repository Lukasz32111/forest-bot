# cogs/osad.py
import discord
from discord.ext import commands
import asyncio
from datetime import timedelta

class Osad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def rozpocznij_osad(self, guild: discord.Guild, skazany: discord.Member, reason: str):
        """Uruchamia proces osądu po 3. warnie"""
        # 1. Tworzymy lub znajdujemy kategorie
        kategoria_sady = discord.utils.get(guild.categories, name="Sądy")
        if not kategoria_sady:
            kategoria_sady = await guild.create_category("Sądy")

        kategoria_archiwum = discord.utils.get(guild.categories, name="Archiwum Osądów")
        if not kategoria_archiwum:
            kategoria_archiwum = await guild.create_category("Archiwum Osądów")

        # 2. Tworzymy rolę Skazaniec (jeśli nie istnieje)
        rola_skazaniec = discord.utils.get(guild.roles, name="Skazaniec")
        if not rola_skazaniec:
            rola_skazaniec = await guild.create_role(name="Skazaniec", color=0xff0000)

        # 3. Nadajemy rolę Skazaniec
        await skazany.add_roles(rola_skazaniec)

        # 4. Tworzymy kanał sądowy
        kanal_nazwa = f"sąd-{skazany.name.lower().replace(' ', '-')}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            skazany: discord.PermissionOverwrite(view_channel=True, send_messages=False, add_reactions=False),
            rola_skazaniec: discord.PermissionOverwrite(view_channel=True, send_messages=False, add_reactions=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }

        # Dajemy moderatorom dostęp
        rola_support = discord.utils.get(guild.roles, name="Support")  # lub Moderacja, Admin itp.
        if rola_support:
            overwrites[rola_support] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        kanal = await guild.create_text_channel(kanal_nazwa, category=kategoria_sady, overwrites=overwrites,
                                                topic=f"Osąd użytkownika {skazany} | Powód: {reason}")

        # 5. Wysyłamy powitalną wiadomość i ankietę
        embed = discord.Embed(
            title=f"OSĄD – {skazany}",
            description=f"Użytkownik **{skazany}** otrzymał **3 ostrzeżenie**.\n"
                        f"Powód ostatniego: {reason}\n\n"
                        "**Co z nim zrobić?** Głosujcie poniżej ↓\n"
                        "Możecie głosować **raz** – kliknięcie zmienia głos.\n"
                        "Zamknięcie ankiety tylko przez moderatora (reakcja X)",
            color=0xff0000
        )
        embed.set_thumbnail(url=skazany.avatar.url if skazany.avatar else None)
        embed.set_footer(text="Głosowanie trwa do decyzji moderatora • Nie zmieniajcie zdania po głosie")

        msg = await kanal.send(embed=embed)

        opcje = [
            "1️⃣ Wyrzuć z serwera (kick)",
            "2️⃣ Zmutuj na maksymalny czas (28 dni)",
            "3️⃣ Zbanuj z serwera",
            "4️⃣ Odroczyć / ukarać inaczej"
        ]

        for opcja in opcje:
            await msg.add_reaction(opcja[0])

        await msg.add_reaction("X")  # zamknięcie przez modów

        # 6. Czekamy na zamknięcie (reakcja X przez modów)
        def check(reaction, user):
            return str(reaction.emoji) == "X" and reaction.message.id == msg.id and user.guild_permissions.manage_guild

        try:
            reaction, mod = await self.bot.wait_for("reaction_add", timeout=86400, check=check)  # 24h
            await self.zakoncz_osad(guild, kanal, skazany, msg, mod)
        except asyncio.TimeoutError:
            await kanal.send("Czas na decyzję minął – osąd zostaje bez kary.")
            await self.archiwizuj_kanal(kanal, kategoria_archiwum)

    async def zakoncz_osad(self, guild, kanal, skazany, msg, mod):
        """Zlicza głosy i wykonuje wyrok"""
        # Pobieramy aktualne reakcje
        msg = await kanal.fetch_message(msg.id)
        votes = {1: 0, 2: 0, 3: 0, 4: 0}
        for reaction in msg.reactions:
            if reaction.emoji in "1️⃣2️⃣3️⃣4️⃣":
                idx = int(reaction.emoji[0])
                votes[idx] = reaction.count - 1  # odejmujemy bota

        max_v = max(votes.values())
        wygrane = [k for k, v in votes.items() if v == max_v]

        if len(wygrane) > 1:
            wynik = "Remis – kara nie została wykonana."
        else:
            wynik = {
                1: "Wyrzuć z serwera",
                2: "Zmutuj na 28 dni",
                3: "Zbanuj",
                4: "Odroczyć / ukarać inaczej"
            }[wygrane[0]]

        embed = discord.Embed(
            title="WYROK OSĄDU",
            description=f"**{skazany}** został osądzony przez społeczność.\n"
                        f"**Decyzja:** {wynik}\n"
                        f"**Głosowanie zamknął:** {mod.mention}\n"
                        f"Powód: Społeczność tak zadecydowała",
            color=0x00ff00 if "Odroczyć" in wynik else 0xff0000
        )

        await kanal.send(embed=embed)

        # Wykonanie kary
        if "Wyrzuć" in wynik:
            await skazany.kick(reason="Społeczność tak zadecydowała")
        elif "Zmutuj" in wynik:
            await skazany.timeout(timedelta(days=28), reason="Społeczność tak zadecydowała")
        elif "Zbanuj" in wynik:
            await skazany.ban(reason="Społeczność tak zadecydowała")
        # 4 – nic nie robimy

        # Archiwizacja kanału
        await self.archiwizuj_kanal(kanal, discord.utils.get(guild.categories, name="Archiwum Osądów"))

    async def archiwizuj_kanal(self, kanal, kategoria_archiwum):
        await kanal.edit(category=kategoria_archiwum, name=f"arch-{kanal.name}")
        await kanal.set_permissions(kanal.guild.default_role, send_messages=False)
        await kanal.set_permissions(kanal.guild.me, send_messages=True)
        await kanal.send("Kanał przeniesiony do archiwum – tylko do odczytu.")

async def setup(bot):
    await bot.add_cog(Osad(bot))
