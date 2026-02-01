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
        # 1. Kategorie
        kategoria_sady = discord.utils.get(guild.categories, name="Sądy")
        if not kategoria_sady:
            kategoria_sady = await guild.create_category("Sądy")

        kategoria_archiwum = discord.utils.get(guild.categories, name="Archiwum Osądów")
        if not kategoria_archiwum:
            kategoria_archiwum = await guild.create_category("Archiwum Osądów")

        # 2. Rola Skazaniec (tworzymy jeśli nie istnieje)
        rola_skazaniec = discord.utils.get(guild.roles, name="Skazaniec")
        if not rola_skazaniec:
            rola_skazaniec = await guild.create_role(
                name="Skazaniec",
                color=discord.Color.red(),
                hoist=True,
                mentionable=False
            )

        # 3. Nadajemy rolę Skazaniec
        await skazany.add_roles(rola_skazaniec)

        # 4. Tworzymy kanał sądowy – tylko skazany widzi + moderatorzy + bot
        kanal_nazwa = f"sąd-{skazany.name.lower().replace(' ', '-')}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            rola_skazaniec: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                add_reactions=False,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True
            ),
        }

        # Dajemy dostęp roli moderatorów (np. Support / Moderator / Admin)
        for rola in guild.roles:
            if rola.permissions.manage_guild or rola.permissions.ban_members:
                overwrites[rola] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        kanal = await guild.create_text_channel(
            kanal_nazwa,
            category=kategoria_sady,
            overwrites=overwrites,
            topic=f"Osąd: {skazany} | Powód: {reason} | 3 ostrzeżenia"
        )

        # 5. Powitalna wiadomość + ankieta
        embed = discord.Embed(
            title=f"OSĄD – {skazany}",
            description=(
                f"**Użytkownik {skazany.mention}** otrzymał **trzecie ostrzeżenie**.\n"
                f"Ostatni powód: {reason}\n\n"
                "**Co z nim zrobić?** Głosujcie poniżej ↓\n"
                "• Każdy oprócz skazanego może zagłosować **raz** (zmiana głosu usunie poprzedni)\n"
                "• Zamknięcie tylko przez moderatora – reakcja **X**\n"
                "• Czas na głosowanie: do decyzji moderatora"
            ),
            color=0xff0000
        )
        embed.set_thumbnail(url=skazany.avatar.url if skazany.avatar else None)
        embed.set_footer(text="Głosujcie uczciwie • Społeczność decyduje")

        msg = await kanal.send(embed=embed, content="@everyone (oprócz skazanego) – czas na osąd!")

        opcje = [
            "1️⃣ Wyrzuć z serwera (kick)",
            "2️⃣ Zmutuj na maksymalny czas (28 dni)",
            "3️⃣ Zbanuj z serwera",
            "4️⃣ Odroczyć karę / ukarać inaczej"
        ]

        for opcja in opcje:
            await msg.add_reaction(opcja[0])

        await msg.add_reaction("X")  # zamknięcie

        # 6. Czekamy na reakcję X od osoby z uprawnieniami
        def check(reaction, user):
            return (
                str(reaction.emoji) == "X"
                and reaction.message.id == msg.id
                and user != self.bot.user
                and user.guild_permissions.manage_guild  # lub inne uprawnienie
            )

        try:
            reaction, mod = await self.bot.wait_for("reaction_add", timeout=86400, check=check)  # 24h
            await self.zakoncz_osad(guild, kanal, skazany, msg, mod)
        except asyncio.TimeoutError:
            await kanal.send("**Czas na decyzję minął – osąd zostaje bez kary.**")
            await self.archiwizuj_kanal(kanal, kategoria_archiwum)

    async def zakoncz_osad(self, guild, kanal, skazany, msg, mod):
        """Zlicza głosy i wykonuje wyrok"""
        msg = await kanal.fetch_message(msg.id)  # odświeżamy

        votes = {1: 0, 2: 0, 3: 0, 4: 0}
        for reaction in msg.reactions:
            if reaction.emoji in "1️⃣2️⃣3️⃣4️⃣":
                idx = int(reaction.emoji[0])
                # liczymy głosy bez bota
                users = [u async for u in reaction.users() if u != self.bot.user]
                votes[idx] = len(users)

        max_v = max(votes.values())
        wygrane = [k for k, v in votes.items() if v == max_v]

        if len(wygrane) > 1:
            wynik = "Remis – kara nie została wykonana."
            kara = None
        else:
            wynik_map = {
                1: "Wyrzuć z serwera (kick)",
                2: "Zmutuj na 28 dni",
                3: "Zbanuj z serwera",
                4: "Odroczyć karę / ukarać inaczej"
            }
            wynik = wynik_map[wygrane[0]]
            kara = wygrane[0]

        embed = discord.Embed(
            title="WYROK OSĄDU",
            description=f"**{skazany.mention}** został osądzony.\n"
                        f"**Decyzja społeczności:** {wynik}\n"
                        f"**Zamknął głosowanie:** {mod.mention}\n"
                        f"**Powód:** Społeczność tak zadecydowała",
            color=0x00ff00 if kara == 4 else 0xff0000
        )

        await kanal.send(embed=embed)

        # Wykonanie kary
        reason_kary = "Społeczność tak zadecydowała"
        if kara == 1:
            await skazany.kick(reason=reason_kary)
            await kanal.send(f"{skazany.mention} został **wyrzucony** z serwera.")
        elif kara == 2:
            await skazany.timeout(timedelta(days=28), reason=reason_kary)
            await kanal.send(f"{skazany.mention} został **zmutowany na 28 dni**.")
        elif kara == 3:
            await skazany.ban(reason=reason_kary)
            await kanal.send(f"{skazany.mention} został **zbanowany** z serwera.")
        else:
            await kanal.send(f"{skazany.mention} – kara odroczona / zmieniona.")

        # Archiwizacja
        await self.archiwizuj_kanal(kanal, discord.utils.get(guild.categories, name="Archiwum Osądów"))

    async def archiwizuj_kanal(self, kanal, kategoria_archiwum):
        if not kategoria_archiwum:
            return
        await kanal.edit(category=kategoria_archiwum, name=f"arch-{kanal.name}")
        await kanal.set_permissions(kanal.guild.default_role, send_messages=False)
        await kanal.set_permissions(kanal.guild.me, send_messages=True)
        await kanal.send("Kanał przeniesiony do archiwum – tylko do odczytu.")

async def setup(bot):
    await bot.add_cog(Osad(bot))
