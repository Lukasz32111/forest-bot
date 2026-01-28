# cogs/moderacja.py
import discord
from discord.ext import commands
from datetime import timedelta
import asyncio

class Moderacja(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Nie masz uprawnień do tej komendy.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Bot nie ma wymaganych uprawnień (Kick/Ban/Moderate Members).")
        else:
            await ctx.send(f"Błąd: {error}")

    @commands.command(name="wyrzuc", aliases=["wyrzuć", "wykop"])
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Brak powodu"):
        """Wyrzuca użytkownika z serwera   8wyrzuc @osoba [powód]"""
        if member == ctx.author:
            return await ctx.send("Nie możesz wyrzucić samego siebie.")
        if member.top_role >= ctx.me.top_role:
            return await ctx.send("Nie mogę wyrzucić kogoś z wyższą lub równą rolą niż moja.")

        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} został wyrzucony.\nPowód: {reason}")
        except discord.Forbidden:
            await ctx.send("Nie mam uprawnień do wyrzucenia tej osoby.")
        except Exception as e:
            await ctx.send(f"Błąd podczas wyrzucania: {e}")

    @commands.command(name="zbanuj", aliases=["banhammer", "zbanujgo"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Brak powodu"):
        """Banuje użytkownika   8zbanuj @osoba [powód]"""
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

    @commands.command(name="odbanuj", aliases=["odbani", "unbanuj", "removeban"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def odbanuj(self, ctx, user: discord.User, *, reason: str = "Brak powodu"):
        """Odbanowuje użytkownika   8odbanuj ID_lub_@osoba [powód]"""
        try:
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(f"{user.mention} ({user.id}) został odbanowany.\nPowód: {reason}")
        except discord.NotFound:
            await ctx.send("Nie znaleziono takiego bana.")
        except discord.Forbidden:
            await ctx.send("Nie mam uprawnień do odbanowania.")
        except Exception as e:
            await ctx.send(f"Błąd: {e}")

    @commands.command(name="wycisz", aliases=["zamknij", "timeoutpl"])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def wycisz(self, ctx, member: discord.Member, czas: str, *, reason: str = "Brak powodu"):
        """
        Wycisza użytkownika na dowolny czas (do 28 dni – limit Discorda)
        """
        if member == ctx.author:
            return await ctx.send("Nie możesz wyciszyć samego siebie.")

        if member.top_role >= ctx.me.top_role:
            return await ctx.send("Nie mogę wyciszyć kogoś z wyższą lub równą rolą niż moja.")

        try:
            duration = self.parse_duration(czas)
            if duration.total_seconds() <= 0:
                return await ctx.send("Czas musi być dłuższy niż 0 sekund.")

            if duration.total_seconds() > 2419200:
                return await ctx.send("Discord pozwala na maksymalnie 28 dni wyciszenia.")

            await member.timeout(duration, reason=reason)
            await ctx.send(f"{member.mention} został wyciszony na **{czas}**.\nPowód: {reason}")

        except discord.Forbidden:
            await ctx.send("Nie mam uprawnień do wyciszenia tej osoby (sprawdź pozycję roli bota).")
        except ValueError:
            await ctx.send("Nieprawidłowy format czasu. Przykłady:\n`30m`, `2h`, `7d`, `3600s`, `1h30m`")
        except Exception as e:
            await ctx.send(f"Błąd podczas wyciszania: {e}")

    @commands.command(name="odcisz", aliases=["untimeout", "odmute", "odblokujgłos"])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def odcisz(self, ctx, member: discord.Member, *, reason: str = "Brak powodu"):
        """Zdejmuje wyciszenie   8odcisz @osoba [powód]"""
        if member.timed_out_until is None:
            return await ctx.send(f"{member.mention} nie jest wyciszony.")

        try:
            await member.timeout(None, reason=reason)
            await ctx.send(f"{member.mention} został odciszony.\nPowód: {reason}")
        except discord.Forbidden:
            await ctx.send("Nie mam uprawnień do zdjęcia wyciszenia.")
        except Exception as e:
            await ctx.send(f"Błąd: {e}")

    @commands.command(name="czyść", aliases=["purge", "usuńwiadomości", "clear"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def czyść(self, ctx, limit: int = 50, member: discord.Member = None):
        """
        Usuwa ostatnie wiadomości z kanału
        8czyść [ilość] [@osoba opcjonalnie]
        """
        if limit < 1 or limit > 1000:
            return await ctx.send("Możesz usunąć od 1 do 1000 wiadomości naraz.")

        def check(msg):
            return member is None or msg.author == member

        try:
            deleted = await ctx.channel.purge(limit=limit + 1, check=check)
            msg = await ctx.send(f"Usunięto **{len(deleted)-1}** wiadomości.")
            await asyncio.sleep(3)
            await msg.delete()
        except discord.Forbidden:
            await ctx.send("Nie mam uprawnień do usuwania wiadomości w tym kanale.")
        except Exception as e:
            await ctx.send(f"Błąd podczas usuwania: {e}")

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
