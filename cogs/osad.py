# cogs/osad.py
import discord
from discord.ext import commands
import asyncio
from datetime import timedelta

class Osad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def rozpocznij_osad(self, guild: discord.Guild, skazany: discord.Member, reason: str):
        """Uruchamia osąd po 3. warnie"""
        # Kategorie
        kategoria_sady = discord.utils.get(guild.categories, name="Sądy") or await guild.create_category("Sądy")
        kategoria_archiwum = discord.utils.get(guild.categories, name="Archiwum Osądów") or await guild.create_category("Archiwum Osądów")

        # Rola Skazaniec
        rola_skazaniec = discord.utils.get(guild.roles, name="Skazaniec") or await guild.create_role(
            name="Skazaniec", color=discord.Color.red(), hoist=True
        )
        await skazany.add_roles(rola_skazaniec)

        # Kanał sądowy
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            rola_skazaniec: discord.PermissionOverwrite(
                view_channel=True, send_messages=False, read_message_history=True, add_reactions=False
            ),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }

        # Dostęp dla moderatorów
        for role in guild.roles:
            if role.permissions.manage_guild or role.permissions.ban_members:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )

        kanal = await guild.create_text_channel(
            f"sąd-{skazany.name.lower().replace(' ', '-')}",
            category=kategoria_sady,
            overwrites=overwrites,
            topic=f"Osąd: {skazany} | 3 ostrzeżenia | {reason}"
        )

        # Ping tylko @Zweryfikowany (bez dodatkowego tekstu)
        rola_zw = discord.utils.get(guild.roles, name="Zweryfikowany")
        ping = f"<@&{rola_zw.id}>" if rola_zw else ""

        # Czysty embed – bez zbędnych pól
        embed = discord.Embed(
            title=f"OSĄD – {skazany}",
            description=(
                f"Użytkownik otrzymał **trzecie ostrzeżenie**.\n"
                f"Powód ostatniego: {reason}\n\n"
                f"**Co zrobić?** Głosuj reakcją (raz na osobę):"
            ),
            color=discord.Color.red()
        )
        embed.add_field(name="1 – Wyrzuć z serwera", value="\u200b", inline=False)
        embed.add_field(name="2 – Zmutuj na 28 dni", value="\u200b", inline=False)
        embed.add_field(name="3 – Zbanuj", value="\u200b", inline=False)
        embed.add_field(name="X – Zamknij głosowanie (tylko moderator)", value="\u200b", inline=False)
        embed.set_footer(text="Decyduje większość • Zamknięcie przez moderatora")

        msg = await kanal.send(content=ping, embed=embed)

        # Dodajemy reakcje – zwykłe cyfry + X (bezpieczne)
        reakcje = ["1️⃣", "2️⃣", "3️⃣", "❌"]  # ❌ zamiast X – działa lepiej
        for emoji in reakcje:
            try:
                await msg.add_reaction(emoji)
                await asyncio.sleep(0.5)  # unikamy rate limitu
            except discord.HTTPException as e:
                await kanal.send(f"Błąd dodawania reakcji {emoji}: {e}")

        # Czekamy na ❌ od moderatora
        def check(r, u):
            return str(r.emoji) in ["❌", "X"] and r.message.id == msg.id and u.guild_permissions.manage_messages

        try:
            _, mod = await self.bot.wait_for("reaction_add", timeout=86400, check=check)
            await self.zakoncz_osad(guild, kanal, skazany, msg, mod)
        except asyncio.TimeoutError:
            await kanal.send("Osąd zakończony automatycznie – bez kary.")
            await self.archiwizuj_kanal(kanal, kategoria_archiwum)

    async def zakoncz_osad(self, guild, kanal, skazany, msg, mod):
        msg = await kanal.fetch_message(msg.id)

        votes = {1: 0, 2: 0, 3: 0}
        for r in msg.reactions:
            if r.emoji in ["1️⃣", "2️⃣", "3️⃣"]:
                idx = int(r.emoji[0])
                users = [u async for u in r.users() if u != self.bot.user and u != skazany]
                votes[idx] = len(users)

        if sum(votes.values()) == 0:
            wynik = "Brak głosów – kara odroczona."
            kara = None
        else:
            max_v = max(votes.values())
            wygrane = [k for k, v in votes.items() if v == max_v]
            if len(wygrane) > 1:
                wynik = "Remis – kara odroczona."
                kara = None
            else:
                kara = wygrane[0]
                wynik = ["Wyrzucony", "Zmutowany na 28 dni", "Zbanowany"][kara-1]

        embed = discord.Embed(
            title="WYROK OSĄDU",
            description=f"{skazany.mention} → **{wynik or 'kara odroczona'}**\nZamknął: {mod.mention}\nPowód: Społeczność tak zadecydowała",
            color=discord.Color.red()
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

        # Log do kanału "kary"
        kanal_kary = discord.utils.get(guild.text_channels, name="kary")
        if kanal_kary:
            await kanal_kary.send(f"{skazany.mention} → {wynik.upper()} • Społeczność zadecydowała")

        # Archiwizacja
        await self.archiwizuj_kanal(kanal, discord.utils.get(guild.categories, name="Archiwum Osądów"))

    async def archiwizuj_kanal(self, kanal, kategoria_archiwum):
        if kategoria_archiwum:
            await kanal.edit(category=kategoria_archiwum, name=f"arch-{kanal.name}")
            await kanal.set_permissions(kanal.guild.default_role, send_messages=False, add_reactions=False)
            await kanal.send("Kanał przeniesiony do archiwum – tylko do odczytu.")

async def setup(bot):
    await bot.add_cog(Osad(bot))
