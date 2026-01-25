# cogs/help.py
from discord.ext import commands
import discord

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pomoc", aliases=["help", "h", "commands", "cmd"])
    async def pomoc(self, ctx):
        embed = discord.Embed(
            title="📜 Lista komend bota",
            description="Prefix: `8`   |   Wszystkie komendy zaczynają się od `8`",
            color=0x5865f2
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)

        # Gra Farkle
        embed.add_field(
            name="🎲 Farkle",
            value=(
                "`8rzut [opcjonalnie @osoba]` → rozpoczyna grę w Farkle (obecnie tylko vs bot)\n"
                "`8skończ` / `8stop` → przerywa aktualną grę\n"
            ),
            inline=False
        )

        # Muzyka
        embed.add_field(
            name="🎵 Muzyka",
            value=(
                "`8dołącz` → bot dołącza do Twojego kanału głosowego\n"
                "`8opuść` → bot wychodzi z kanału głosowego\n"
                "`8graj <link / nazwa>` → dodaje utwór do kolejki i odtwarza\n"
                "`8skip` → pomija aktualny utwór\n"
                "`8poprzedni` → wraca do poprzedniego utworu (z historii)\n"
                "`8pauza` → zatrzymuje odtwarzanie\n"
                "`8wznów` → wznawia odtwarzanie\n"
                "`8zakończ` → zatrzymuje muzykę i czyści kolejkę\n"
                "`8kolejka` → pokazuje aktualną kolejkę\n"
                "`8podobne` → odtwarza losowy podobny utwór do ostatniego\n"
            ),
            inline=False
        )

        # Inne / przyszłe
        embed.add_field(
            name="ℹ Inne",
            value="`8pomoc` / `8help` → właśnie to co teraz czytasz ;)\n"
                  "Więcej komend wkrótce!",
            inline=False
        )

        embed.set_footer(text="Bot stworzony przez Sebę • v1.0")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
