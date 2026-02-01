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

        # 2. Rola Skazaniec
        rola_skazaniec = discord.utils.get(guild.roles, name="Skazaniec")
        if not rola_skazaniec:
            rola_skazaniec = await guild.create_role(name="Skazaniec", color=0xff0000)

        await skazany.add_roles(rola_skazaniec)

        # 3. Kanał sądowy
        kanal_nazwa = f"sąd-{skazany.name.lower().replace(' ', '-')}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            rola_skazaniec: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }

        # Moderatorzy/Support
        support_role = discord.utils.get(guild.roles, name="Support")  # Zmień na nazwę roli moderatorów
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)

        kanal = await guild.create_text_channel(kanal_nazwa, category=kategoria_sady, overwrites=overwrites)

        # 4. Ping roli Zweryfikowany
        rola_zweryfikowany = discord.utils.get(guild.roles, name="Zweryfikowany")  # Zmień na dokładną nazwę roli
        ping = f"<@&{rola_zweryfikowany.id}>" if rola_zweryfikowany else "@everyone"

        # 5. Embed z ankietą
        embed = discord.Embed(
            title=f"OSĄD – {skazany}",
            description=f"Użytkownik {skazany.mention} otrzymał **trzecie ostrzeżenie**.\nPowód: {reason}\n\n**Co zrobić? Głosuj reakcją poniżej:**",
            color=0xff0000
        )
        opcje = [
            ("1️⃣", "Wyrzuć z serwera"),
            ("2️⃣", "Zmutuj na 28 dni"),
            ("3️⃣", "Zbanuj"),
            ("4️⃣", "Odroczyć karę")
        ]
        for emoji, opcja in opcje:
            embed.add_field(name=emoji, value=opcja, inline=False)

        embed.add_field(name="X", value="Zamknij ankietę (tylko moderator)", inline=False)
        embed.set_footer(text="Głosuj raz – zmiana nie jest możliwa • Decyduje większość")

        msg = await kanal.send(content=ping, embed=embed)

        # 6. Dodajemy reakcje
        for emoji, _ in opcje:
            await msg.add_reaction(emoji)
            await asyncio.sleep(0.5)  # Unikamy rate limit

        await msg.add_reaction("X")

        # 7. Czekamy na X od moderatora
        def check(reaction, user):
            return str(reaction.emoji) == "X" and reaction.message.id == msg.id and user.guild_permissions.manage_messages

        try:
            reaction, mod = await self.bot.wait_for("reaction_add", timeout=86400, check=check)
            await self.zakoncz_osad(guild, kanal, skazany, msg, mod, reason)
        except asyncio.TimeoutError:
            await kanal.send("Osąd zakończony automatycznie – bez kary.")
            await self.archiwizuj_kanal(kanal, kategoria_archiwum)

    async def zakoncz_osad(self, guild, kanal, skazany, msg, mod, reason):
        msg = await kanal.fetch_message(msg.id)

        votes = {}
        for reaction in msg.reactions:
            if reaction.emoji in "1️⃣2️⃣3️⃣4️⃣":
                idx = int(reaction.emoji[0])
                users = [u async for u in reaction.users() if u != self.bot.user and u != skazany]
                votes[idx] = len(users)

        if not votes:
            wynik = "Brak głosów – kara odroczona."
            kara = 4
        else:
            max_v = max(votes.values())
            wygrane = [k for k, v in votes.items() if v == max_v]
            if len(wygrane) > 1:
                wynik = "Remis – kara odroczona."
                kara = 4
            else:
                kara = wygrane[0]
                wynik = {
                    1: "Wyrzuć z serwera",
                    2: "Zmutuj na 28 dni",
                    3: "Zbanuj",
                    4: "Odroczyć karę"
                }[kara]

        embed = discord.Embed(
            title="WYROK OSĄDU",
            description=f"**{skazany.mention}** – {wynik}\nZamknął: {mod.mention}",
            color=0xff0000
        )
        await kanal.send(embed=embed)

        # Wykonanie kary
        reason_kary = "Społeczność tak zadecydowała"
        if kara == 1:
            await skazany.kick(reason=reason_kary)
        elif kara == 2:
            await skazany.timeout(timedelta(days=28), reason=reason_kary)
        elif kara == 3:
            await skazany.ban(reason=reason_kary)
        # 4 – nic

        # Log do kanału kary
        kanał_kary = discord.utils.get(guild.text_channels, name="kary")
        if kanał_kary:
            await kanał_kary.send(f"{skazany.mention} został {wynik.lower()}. Powód: {reason_kary}")

        # Archiwizacja
        await self.archiwizuj_kanal(kanal, discord.utils.get(guild.categories, name="Archiwum Osądów"))

    async def archiwizuj_kanal(self, kanal, kategoria_archiwum):
        if kategoria_archiwum:
            await kanal.edit(category=kategoria_archiwum, name=f"arch-{kanal.name}")
            await kanal.set_permissions(kanal.guild.default_role, send_messages=False, add_reactions=False)

async def setup(bot):
    await bot.add_cog(Osad(bot))
