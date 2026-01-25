# cogs/music.py
import discord
from discord.ext import commands

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def graj(self, ctx, *, query):
        await ctx.send(f"🎵 Komenda graj działa! Szukam: {query} (pełna muzyka wkrótce)")

    @commands.command()
    async def skip(self, ctx):
        await ctx.send("⏭ Skip działa!")

    # inne komendy możesz dodać później

async def setup(bot):
    await bot.add_cog(Music(bot))
