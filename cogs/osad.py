# cogs/osad.py
import discord
from discord.ext import commands

class Osad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def rozpocznij_osad(self, guild: discord.Guild, skazany: discord.Member, reason: str):
        """Uruchamia prosty osąd po 3. warnie – bez ankiety, bez auto-archiwizacji"""
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
                view_channel=True,
                send_messages=True,          # teraz może pisać na kanale sądowym
                read_message_history=True,
                add_reactions=True
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

        # Prosta wiadomość powitalna
        embed = discord.Embed(
            title=f"OSĄD – {skazany}",
            description=(
                f"Użytkownik otrzymał **trzecie ostrzeżenie**.\n"
                f"Powód ostatniego: {reason}\n\n"
                f"Kanał jest prywatny – możesz tu opisać sytuację. Moderatorzy zdecydują o karze.\n\n"
                f"**Aby przenieść kanał do archiwum, wpisz na tym kanale:** `8archiwizuj`"
            ),
            color=0xff0000
        )
        embed.set_footer(text="Kanał pozostanie aktywny do ręcznego archiwizowania")

        await kanal.send(content=ping, embed=embed)

    @commands.command(name="archiwizuj")
    @commands.has_permissions(manage_messages=True)  # tylko moderatorzy mogą użyć
    async def archiwizuj(self, ctx):
        """Przenosi bieżący kanał sądowy do archiwum – tylko do odczytu"""
        kanal = ctx.channel

        # Sprawdzamy, czy to kanał sądowy
        if not kanal.name.startswith("sąd-"):
            return await ctx.send("Ta komenda działa tylko na kanałach sądowych (nazwa zaczyna się od 'sąd-').")

        kategoria_archiwum = discord.utils.get(ctx.guild.categories, name="Archiwum Osądów")
        if not kategoria_archiwum:
            return await ctx.send("Nie znaleziono kategorii 'Archiwum Osądów'.")

        try:
            await kanal.edit(category=kategoria_archiwum, name=f"arch-{kanal.name}")
            await kanal.set_permissions(ctx.guild.default_role, send_messages=False, add_reactions=False)
            await kanal.set_permissions(ctx.guild.me, send_messages=True)  # bot nadal może pisać
            await ctx.send("Kanał przeniesiony do archiwum – tylko do odczytu.")
        except Exception as e:
            await ctx.send(f"Błąd przeniesienia kanału: {e}")

    async def zakoncz_osad(self, guild, kanal, skazany):
        """Usuwa rolę Skazaniec po archiwizacji (opcjonalnie – możesz to usunąć)"""
        rola_skazaniec = discord.utils.get(guild.roles, name="Skazaniec")
        if rola_skazaniec:
            await skazany.remove_roles(rola_skazaniec)

async def setup(bot):
    await bot.add_cog(Osad(bot))
