# cogs/warn.py
import discord
from discord.ext import commands
from datetime import datetime
from replit import db

class Warn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warns = db.get('warns', {})
        print(f"[WARN] Załadowano {len(self.warns)} użytkowników z Replit DB")

    def save_warns(self):
        db['warns'] = self.warns
        print(f"[WARN] Zapisano {len(self.warns)} użytkowników w Replit DB")

    @commands.command(name="ostrzeżenie", aliases=["ostrzeg", "warn"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def ostrzeżenie(self, ctx, member: discord.Member, *, reason: str = "Brak powodu"):
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
        await ctx.send(f"{member.mention} otrzymał **{count}. ostrzeżenie**.\nPowód: {reason}\nWydane przez: {ctx.author.mention}")

    @commands.command(name="ostrzeżenia", aliases=["warny", "sprawdźostrzeżenia"])
    async def ostrzeżenia(self, ctx, member: discord.Member = None):
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
