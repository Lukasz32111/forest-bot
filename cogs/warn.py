# cogs/warn.py
import discord
from discord.ext import commands
import json
import os
from datetime import datetime
import aiohttp
import asyncio

# Zmienne środowiskowe – dodaj w panelu hosta
JSONBIN_ID = os.getenv("697f8cb343b1c97be95da3bd")
JSONBIN_KEY = os.getenv("$2a$10$28OLRCkFBrvrj2q.WKo7JeHUGKrp0ISyujHzguxBM82RP8r3eGzZ6")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"

class Warn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warns = {}
        asyncio.create_task(self.load_warns_from_jsonbin())

    async def load_warns_from_jsonbin(self):
        if not JSONBIN_ID or not JSONBIN_KEY:
            print("[WARN] Brak JSONBIN_ID lub JSONBIN_KEY w zmiennych środowiskowych – używam pamięci")
            return

        async with aiohttp.ClientSession() as session:
            headers = {"X-Master-Key": JSONBIN_KEY}
            try:
                async with session.get(JSONBIN_URL, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.warns = data['record']
                        print(f"[WARN] Załadowano {len(self.warns)} użytkowników z JSONBin")
                    else:
                        print(f"[WARN] Błąd ładowania JSONBin: {resp.status} – {await resp.text()}")
            except Exception as e:
                print(f"[WARN] Błąd połączenia z JSONBin: {e}")

    async def save_warns_to_jsonbin(self):
        if not JSONBIN_ID or not JSONBIN_KEY:
            print("[WARN] Brak JSONBIN – nie zapisuję")
            return

        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "X-Master-Key": JSONBIN_KEY
            }
            try:
                async with session.put(JSONBIN_URL, headers=headers, json=self.warns) as resp:
                    if resp.status in (200, 201):
                        print(f"[WARN] Zapisano {len(self.warns)} użytkowników do JSONBin")
                    else:
                        print(f"[WARN] Błąd zapisu JSONBin: {resp.status} – {await resp.text()}")
            except Exception as e:
                print(f"[WARN] Błąd zapisu do JSONBin: {e}")

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
        await self.save_warns_to_jsonbin()

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
            await self.save_warns_to_jsonbin()
            await ctx.send(f"Usunięto ostatnie ostrzeżenie ({removed['reason']}) od {member.mention}.\nPozostało: {len(self.warns[user_id])}")
        else:
            if 1 <= numer <= len(self.warns[user_id]):
                removed = self.warns[user_id].pop(numer - 1)
                await self.save_warns_to_jsonbin()
                await ctx.send(f"Usunięto ostrzeżenie #{numer} ({removed['reason']}) od {member.mention}.\nPozostało: {len(self.warns[user_id])}")
            else:
                await ctx.send(f"Nieprawidłowy numer ostrzeżenia. Aktualna liczba: {len(self.warns[user_id])}")

async def setup(bot):
    await bot.add_cog(Warn(bot))
