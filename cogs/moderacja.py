# cogs/moderacja.py
import discord
from discord.ext import commands
from datetime import timedelta

class Moderacja(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Sprawdza, czy wywołujący ma uprawnienia + bot ma wyższe role niż cel
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Nie masz uprawnień do tej komendy.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Bot nie ma wymaganych uprawnień (Kick/Ban/Moderate Members).")
        else:
            await ctx.send(f"Błąd: {error}")

    @commands.command(aliases=["wyrzuć"])
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Brak powodu"):
        """Wyrzuca użytkownika z serwera   8kick @osoba [powód]"""
        if member == ctx.author:
            return await ctx.send("Nie możesz wyrzucić samego siebie.")
        if member.top_role >= ctx.me.top_role:
            return await ctx.send("Nie mogę wyrzucić kogoś z wyższą lub równą rolą niż moja.")

        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} został wyrzucony.\nPowód: {reason}")
        except discord.Forbidden:
            await ctx.send("Nie mam uprawnień do wyrzucenia tej osoby (moja rola jest za nisko?).")
        except Exception as e:
            await ctx.send(f"Błąd podczas kick: {e}")

    @commands.command(aliases=["zbanuj", "banhammer"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Brak powodu"):
        """Banuje użytkownika   8ban @osoba [powód]"""
        if member == ctx.author:
            return await ctx.send("Nie możesz zbanować samego siebie.")
        if member.top_role >= ctx.me.top_role:
            return await ctx.send("Nie mogę zbanować kogoś z wyższą lub równą rolą niż moja.")

        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} został zbanowany.\nPowód: {reason}")
        except discord.Forbidden:
            await ctx.send("Nie mam uprawnień do bana tej osoby.")
        except Exception as e:
            await ctx.send(f"Błąd podczas bana: {e}")

    @commands.command(aliases=["odbanuj", "unbanuj", "odbani", "removeban"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.User, *, reason: str = "Brak powodu"):
        """Odbanowuje użytkownika po ID lub @mention   8unban ID_lub_@osoba [powód]"""
        try:
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(f"{user.mention} ({user.id}) został odbanowany.\nPowód: {reason}")
        except discord.NotFound:
            await ctx.send("Nie znaleziono takiego bana.")
        except discord.Forbidden:
            await ctx.send("Nie mam uprawnień do odbanowania.")
        except Exception as e:
            await ctx.send(f"Błąd: {e}")

    @commands.command(aliases=["timeout", "wycisz", "zamknijgębę"])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, czas: str, *, reason: str = "Brak powodu"):
        """
        Wycisza użytkownika na określony czas   8mute @osoba 30m [powód]
        Format czasu: liczba + jednostka (s, m, h, d) np. 45m, 2h, 1d
        """
        if member == ctx.author:
            return await ctx.send("Nie możesz wyciszyć samego siebie.")
        if member.top_role >= ctx.me.top_role:
            return await ctx.send("Nie mogę wyciszyć kogoś z wyższą lub równą rolą niż moja.")

        try:
            duration = self.parse_duration(czas)
            if duration.total_seconds() <= 0 or duration.total_seconds() > 2419200:  # max 28 dni
                return await ctx.send("Czas musi być między 1 sekundą a 28 dniami.")

            await member.timeout(duration, reason=reason)
            await ctx.send(f"{member.mention} został wyciszony na {czas}.\nPowód: {reason}")
        except discord.Forbidden:
            await ctx.send("Nie mam uprawnień do timeoutu tej osoby.")
        except ValueError:
            await ctx.send("Nieprawidłowy format czasu. Przykład: 30m, 2h, 1d")
        except Exception as e:
            await ctx.send(f"Błąd podczas mute: {e}")

    @commands.command(aliases=["unmute", "odcisz"])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str = "Brak powodu"):
        """Zdejmuje timeout   8unmute @osoba [powód]"""
        if member.timed_out_until is None:
            return await ctx.send(f"{member.mention} nie jest wyciszony.")

        try:
            await member.timeout(None, reason=reason)
            await ctx.send(f"{member.mention} został odciszony.\nPowód: {reason}")
        except discord.Forbidden:
            await ctx.send("Nie mam uprawnień do zdjęcia timeoutu.")
        except Exception as e:
            await ctx.send(f"Błąd: {e}")

    def parse_duration(self, time_str: str) -> timedelta:
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
            raise ValueError("Nieprawidłowy format")
        seconds = int(num) * multipliers[unit]
        return timedelta(seconds=seconds)

async def setup(bot):
    await bot.add_cog(Moderacja(bot))
