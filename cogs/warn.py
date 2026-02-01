# cogs/warn.py
import discord
from discord.ext import commands
import json
import os
from datetime import datetime

WARN_FILE = "warns.json"  # plik z ostrzeżeniami

class Warn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warns = self.load_warns()

    def load_warns(self):
        if os.path.exists(WARN_FILE):
            with open(WARN_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_warns(self):
        with open(WARN_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.warns, f, indent=4, ensure_ascii=False)

    @commands.command(name="ostrzeżenie", aliases=["ostrzeg", "warn"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def ostrzeżenie(self, ctx, member: discord.Member, *, reason: str = "Brak powodu"):
        """Daje ostrzeżenie użytkownikowi 8ostrzeżenie @osoba [powód]"""
        if member == ctx.author:
            return await ctx.send("Nie możesz dać ostrzeżenia samemu sobie.")
        if member.top_role >= ctx.me.top_role:
            return await ctx.send("Nie mogę ostrzec kogoś z wyższą lub równą rolą niż moja.")

        user_id = str(member.id)
        if user_id not in self.warns:
            self.warns[user_id] = []

        warn_data = {
            "moderator": ctx.author.name,
            "reason": reason,
            "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        self.warns[user_id].append(warn_data)
        self.save_warns()

        count = len(self.warns[user_id])

        # Ta linia i cały blok poniżej muszą być wcięte na poziomie funkcji (4 spacje)
        await ctx.send(f"{member.mention} otrzymał **{count}. ostrzeżenie**.\nPowód: {reason}\nWydane przez: {ctx.author.mention}")

        if count >= 3:
            # Uruchamiamy osąd
            osad_cog = self.bot.get_cog("Osad")
            if osad_cog:
                await osad_cog.rozpocznij_osad(ctx.guild, member, reason)
            else:
                await ctx.send("⚠️ System osądu nie jest załadowany!")

    @commands.command(name="ostrzeżenia", aliases=["warny", "sprawdźostrzeżenia"])
    async def ostrzeżenia(self, ctx, member: discord.Member = None):
        """Pokazuje listę ostrzeżeń użytkownika 8ostrzeżenia [@osoba]"""
        if member is None:
            member = ctx.author
        user_id = str(member.id)
        if user_id not in self.warns or not self.warns[user_id]:
            return await ctx.send(f"{member.mention} nie ma żadnych ostrzeżeń.")

        embed = discord.Embed(
            title=f"Ostrzeżenia użytkownika {member}",
            description=f"Łącznie: **{len(self.warns[user_id])}** ostrzeżeń",
            color=0xffaa00
        )
        for i, warn in enumerate(self.warns[user_id], 1):
            embed.add_field(
                name=f"Ostrzeżenie #{i}",
                value=f"**Powód:** {warn['reason']}\n**Wydane przez:** {warn['moderator']}\n**Data:** {warn['date']}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="usuńostrzeżenie", aliases=["cofnijostrzeżenie", "unwarn"])
    @commands.has_permissions(manage_messages=True)
    async def usuńostrzeżenie(self, ctx, member: discord.Member, numer: int = None):
        """Usuwa ostatnie ostrzeżenie lub konkretne po numerze 8usuńostrzeżenie @osoba [numer]"""
        user_id = str(member.id)
        if user_id not in self.warns or not self.warns[user_id]:
            return await ctx.send(f"{member.mention} nie ma ostrzeżeń do usunięcia.")

        if numer is None:
            removed = self.warns[user_id].pop()
            self.save_warns()
            await ctx.send(f"Usunięto ostatnie ostrzeżenie ({removed['reason']}) od {member.mention}.\nPozostało: {len(self.warns[user_id])}")
        else:
            if 1 <= numer <= len(self.warns[user_id]):
                removed = self.warns[user_id].pop(numer - 1)
                self.save_warns()
                await ctx.send(f"Usunięto ostrzeżenie #{numer} ({removed['reason']}) od {member.mention}.\nPozostało: {len(self.warns[user_id])}")
            else:
                await ctx.send(f"Nieprawidłowy numer ostrzeżenia. Aktualna liczba: {len(self.warns[user_id])}")

async def setup(bot):
    await bot.add_cog(Warn(bot))
