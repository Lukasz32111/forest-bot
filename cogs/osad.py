# cogs/osad.py
import discord
from discord.ext import commands
import asyncio
from datetime import timedelta
from collections import Counter

class Osad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def rozpocznij_osad(self, guild: discord.Guild, skazany: discord.Member, reason: str):
        """Uruchamia osąd po 3. warnie"""
        # Kategorie
        kategoria_sady = discord.utils.get(guild.categories, name="Sądy") or await guild.create_category("Sądy")
        kategoria_archiwum = discord.utils.get(guild.categories, name="Archiwum Osądów") or await guild.create_category("Archiwum Osądów")

        # Rola Skazaniec – blokuje pisanie wszędzie poza sądem
        rola_skazaniec = discord.utils.get(guild.roles, name="Skazaniec")
        if not rola_skazaniec:
            rola_skazaniec = await guild.create_role(
                name="Skazaniec",
                color=discord.Color.red(),
                hoist=True,
                permissions=discord.Permissions.none()
            )

        await skazany.add_roles(rola_skazaniec)

        # Blokada pisania globalna (oprócz kanału sądowego)
        for channel in guild.text_channels:
            if channel.category_id != kategoria_sady.id:  # wyjątek tylko dla sądów
                try:
                    await channel.set_permissions(
                        rola_skazaniec,
                        send_messages=False,
                        add_reactions=False,
                        read_messages=False  # nawet czytanie blokujemy poza sądem
                    )
                except:
                    pass

        # Kanał sądowy – nadpisujemy uprawnienia tylko dla tego kanału
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            rola_skazaniec: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                read_message_history=True,
                add_reactions=False
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True
            ),
        }

        # Moderatorzy mają dostęp
        for role in guild.roles:
            if role.permissions.manage_guild or role.permissions.ban_members or role.permissions.moderate_members:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        kanal = await guild.create_text_channel(
            f"sąd-{skazany.name.lower().replace(' ', '-')}",
            category=kategoria_sady,
            overwrites=overwrites,
            topic=f"Osąd: {skazany} | 3 ostrzeżenia | {reason}"
        )

        # Ping tylko roli Zweryfikowany – bez żadnego tekstu
        rola_zw = discord.utils.get(guild.roles, name="Zweryfikowany")
        ping = f"<@&{rola_zw.id}>" if rola_zw else ""

        # Embed + ankieta jak w Twoim stylu
        embed = discord.Embed(
            title=f"OSĄD – {skazany}",
            description=(
                f"Użytkownik otrzymał **trzecie ostrzeżenie**.\n"
                f"Powód ostatniego: {reason}\n\n"
                f"**Głosuj reakcją (raz na osobę):**\n"
                f"1️⃣ Wyrzuć z serwera\n"
                f"2️⃣ Zmutuj na 28 dni\n"
                f"3️⃣ Zbanuj\n\n"
                f"Zamknij ❌ (tylko moderator)"
            ),
            color=0xff0000
        )
        embed.set_footer(text="Głosowanie trwa dokładnie 1 godzinę • Decyduje większość")

        msg = await kanal.send(content=ping, embed=embed)

        # Dodajemy reakcje
        for emoji in ["1️⃣", "2️⃣", "3️⃣", "❌"]:
            try:
                await msg.add_reaction(emoji)
                await asyncio.sleep(0.5)
            except Exception as e:
                await kanal.send(f"Błąd reakcji: {e}")

        # Logika głosowania jak w Twojej ankiecie
        votes = {"1️⃣": 0, "2️⃣": 0, "3️⃣": 0}
        voters = {"1️⃣": set(), "2️⃣": set(), "3️⃣": set()}
        voted_users = set()

        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    timeout=3600,
                    check=lambda r, u: r.message.id == msg.id and not u.bot
                )

                emoji_str = str(reaction.emoji)
                if emoji_str == "❌" and user.guild_permissions.manage_messages:
                    await self.zakoncz_osad(guild, kanal, skazany, msg, user)
                    break

                if emoji_str in votes:
                    if user.id not in voted_users:
                        # Usuwamy poprzedni głos jeśli był
                        for em in votes:
                            if user.id in voters[em]:
                                voters[em].remove(user.id)
                                votes[em] -= 1
                                break

                        votes[emoji_str] += 1
                        voters[emoji_str].add(user.id)
                        voted_users.add(user.id)

                        # Aktualizacja embeda na żywo
                        total = sum(votes.values())
                        linie = []
                        for em in ["1️⃣", "2️⃣", "3️⃣"]:
                            proc = round(votes[em] / total * 100, 1) if total > 0 else 0
                            linie.append(f"{em} **{votes[em]}** ({proc}%)")

                        embed.description = (
                            f"Użytkownik otrzymał **trzecie ostrzeżenie**.\n"
                            f"Powód ostatniego: {reason}\n\n"
                            f"**Wyniki na żywo** (głosuj raz)\n\n" + "\n".join(linie) + "\n\n"
                            f"Zamknij ❌ (tylko moderator)"
                        )
                        embed.set_footer(text=f"{total} głosów • Pozostało ~{int(3600 - (asyncio.get_event_loop().time() - start_time)) // 60} min")
                        await msg.edit(embed=embed)

                    await msg.remove_reaction(emoji_str, user)

            except asyncio.TimeoutError:
                await self.zakoncz_osad(guild, kanal, skazany, msg, None)
                break

    async def zakoncz_osad(self, guild, kanal, skazany, msg, mod=None):
        msg = await kanal.fetch_message(msg.id)

        votes = {"1️⃣": 0, "2️⃣": 0, "3️⃣": 0}
        for r in msg.reactions:
            if r.emoji in votes:
                users = [u async for u in r.users() if u != self.bot.user and u != skazany]
                votes[r.emoji] = len(users)

        total = sum(votes.values())
        if total == 0:
            wynik = "Brak głosów – kara odroczona."
            kara = None
        else:
            max_v = max(votes.values())
            wygrane_emoji = [k for k, v in votes.items() if v == max_v]
            if len(wygrane_emoji) > 1:
                wynik = "Remis – kara odroczona."
                kara = None
            else:
                idx = "1️⃣2️⃣3️⃣".index(wygrane_emoji[0])
                kara = idx + 1
                wynik = ["Wyrzucony", "Zmutowany na 28 dni", "Zbanowany"][idx]

        embed = discord.Embed(
            title="WYROK OSĄDU",
            description=f"{skazany.mention} → **{wynik or 'kara odroczona'}**\n"
                        f"{'Zamknął: ' + mod.mention if mod else 'Zamknięto automatycznie po 1h'}\n"
                        f"Powód: Społeczność tak zadecydowała",
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

        # Log do kanału "kary"
        kanal_kary = discord.utils.get(guild.text_channels, name="kary")
        if kanal_kary:
            await kanal_kary.send(f"{skazany.mention} → {wynik.upper()} • Społeczność zadecydowała")

        # Usuwamy rolę Skazaniec po wyroku
        rola_skazaniec = discord.utils.get(guild.roles, name="Skazaniec")
        if rola_skazaniec:
            await skazany.remove_roles(rola_skazaniec)

        # Archiwizacja
        await self.archiwizuj_kanal(kanal, discord.utils.get(guild.categories, name="Archiwum Osądów"))

    async def archiwizuj_kanal(self, kanal, kategoria_archiwum):
        if kategoria_archiwum:
            await kanal.edit(category=kategoria_archiwum, name=f"arch-{kanal.name}")
            await kanal.set_permissions(kanal.guild.default_role, send_messages=False, add_reactions=False)
            await kanal.send("Kanał przeniesiony do archiwum – tylko do odczytu.")

async def setup(bot):
    await bot.add_cog(Osad(bot))
