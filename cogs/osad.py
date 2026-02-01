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

        # Rola Skazaniec – blokada pisania wszędzie poza sądem
        rola_skazaniec = discord.utils.get(guild.roles, name="Skazaniec")
        if not rola_skazaniec:
            rola_skazaniec = await guild.create_role(
                name="Skazaniec",
                color=discord.Color.red(),
                hoist=True,
                permissions=discord.Permissions.none()
            )

        await skazany.add_roles(rola_skazaniec)

        # Blokada globalna (oprócz sądu)
        for channel in guild.text_channels:
            if channel.category_id != kategoria_sady.id:
                try:
                    await channel.set_permissions(
                        rola_skazaniec,
                        send_messages=False,
                        add_reactions=False,
                        read_messages=False
                    )
                except:
                    pass

        # Kanał sądowy
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            rola_skazaniec: discord.PermissionOverwrite(
                view_channel=True, send_messages=False, read_message_history=True, add_reactions=False
            ),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }

        for role in guild.roles:
            if role.permissions.manage_guild or role.permissions.ban_members or role.permissions.moderate_members:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        kanal = await guild.create_text_channel(
            f"sąd-{skazany.name.lower().replace(' ', '-')}",
            category=kategoria_sady,
            overwrites=overwrites,
            topic=f"Osąd: {skazany} | 3 ostrzeżenia | {reason}"
        )

        # Ping tylko @Zweryfikowany
        rola_zw = discord.utils.get(guild.roles, name="Zweryfikowany")
        ping = f"<@&{rola_zw.id}>" if rola_zw else ""

        # Embed z ankietą
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
        embed.set_footer(text="Głosowanie trwa 1 godzinę • Decyduje większość • 👥 kto głosował")

        msg = await kanal.send(content=ping, embed=embed)

        # Reakcje
        for emoji in ["1️⃣", "2️⃣", "3️⃣", "❌", "👥"]:
            try:
                await msg.add_reaction(emoji)
                await asyncio.sleep(0.5)
            except Exception as e:
                await kanal.send(f"Błąd reakcji {emoji}: {e}")

        # Głosowanie
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

                # 👥 – kto głosował (tylko moderatorzy)
                if emoji_str == "👥" and user.guild_permissions.manage_messages:
                    lista = []
                    for em, usr_set in voters.items():
                        if usr_set:
                            opcja = {"1️⃣": "Wyrzuć", "2️⃣": "Zmutuj", "3️⃣": "Zbanuj"}[em]
                            lista.append(f"{em} → {opcja}: {', '.join([f'<@{u.id}>' for u in usr_set])}")
                    if lista:
                        await user.send(f"**Głosy w osądzie {skazany}:**\n" + "\n".join(lista))
                    else:
                        await user.send("Nikt jeszcze nie zagłosował.")
                    await msg.remove_reaction("👥", user)
                    continue

                # Zamknięcie przez moderatora
                if emoji_str == "❌" and user.guild_permissions.manage_messages:
                    await self.zakoncz_osad(guild, kanal, skazany, msg, user, votes)
                    break  # Wyjście z pętli po zamknięciu

                # Głosowanie normalne
                if emoji_str in votes:
                    if user.id not in voted_users:
                        # Usuwamy poprzedni głos
                        for em in votes:
                            if user.id in voters[em]:
                                voters[em].remove(user.id)
                                votes[em] -= 1
                                break

                        votes[emoji_str] += 1
                        voters[emoji_str].add(user.id)
                        voted_users.add(user.id)

                        # Aktualizacja embeda
                        total = sum(votes.values())
                        linie = []
                        for em in ["1️⃣", "2️⃣", "3️⃣"]:
                            proc = round(votes[em] / total * 100, 1) if total > 0 else 0
                            linie.append(f"{em} **{votes[em]}** ({proc}%)")

                        embed.description = (
                            f"Użytkownik otrzymał **trzecie ostrzeżenie**.\n"
                            f"Powód ostatniego: {reason}\n\n"
                            f"**Głosuj reakcją (raz na osobę):**\n"
                            f"1️⃣ Wyrzuć z serwera\n"
                            f"2️⃣ Zmutuj na 28 dni\n"
                            f"3️⃣ Zbanuj\n\n"
                            f"**Wyniki na żywo:**\n" + "\n".join(linie) + "\n\n"
                            f"Zamknij ❌ (moderator)"
                        )
                        embed.set_footer(text=f"{total} głosów • Pozostało ~{int(3600 - (asyncio.get_event_loop().time() - start_time)) // 60} min • 👥 kto głosował")
                        await msg.edit(embed=embed)

                    await msg.remove_reaction(emoji_str, user)

            except asyncio.TimeoutError:
                await self.zakoncz_osad(guild, kanal, skazany, msg, None, votes)
                break  # Wyjście po timeout

    async def zakoncz_osad(self, guild, kanal, skazany, msg, mod=None, votes=None):
        if votes is None:
            votes = {"1️⃣": 0, "2️⃣": 0, "3️⃣": 0}

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
                wynik = ["Wyrzucony z serwera", "Zmutowany na 28 dni", "Zbanowany"][idx]

        embed = discord.Embed(
            title="WYROK OSĄDU",
            description=f"{skazany.mention} → **{wynik}**\n"
                        f"{'Zamknął: ' + mod.mention if mod else 'Zamknięto automatycznie po 1h'}\n"
                        f"Powód: Społeczność tak zadecydowała",
            color=0xff0000
        )
        await kanal.send(embed=embed)

        # Wyrok na kanał ID 1458853426707304540
        try:
            kanal_kary = guild.get_channel(1458853426707304540)
            if kanal_kary:
                await kanal_kary.send(embed=embed)
            else:
                await kanal.send("Kanał kary (ID 1458853426707304540) nie znaleziony.")
        except Exception as e:
            await kanal.send(f"Błąd wysyłania wyroku: {e}")

        # Wykonanie kary
        reason_kary = "Społeczność tak zadecydowała"
        if kara == 1:
            await skazany.kick(reason=reason_kary)
        elif kara == 2:
            await skazany.timeout(timedelta(days=28), reason=reason_kary)
        elif kara == 3:
            await skazany.ban(reason=reason_kary)

        # Log do kanału "kary"
        kanal_kary = guild.get_channel(1458853426707304540)
        if kanal_kary:
            await kanal_kary.send(embed=embed)

        # Usuwamy rolę po wyroku
        rola_skazaniec = discord.utils.get(guild.roles, name="Skazaniec")
        if rola_skazaniec:
            await skazany.remove_roles(rola_skazaniec)

        # Archiwizacja
        archiwum = discord.utils.get(guild.categories, name="Archiwum Osądów")
        if archiwum:
            try:
                await kanal.edit(category=archiwum, name=f"arch-{kanal.name}")
                await kanal.set_permissions(guild.default_role, send_messages=False, add_reactions=False)
                await kanal.send("Kanał przeniesiony do archiwum – tylko do odczytu.")
            except Exception as e:
                await kanal.send(f"Błąd archiwizacji: {e}")
        else:
            await kanal.send("Brak kategorii archiwum – kanał zostaje.")

async def setup(bot):
    await bot.add_cog(Osad(bot))
