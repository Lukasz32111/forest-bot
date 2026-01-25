# cogs/pomoc.py
from discord.ext import commands
import discord

class Pomoc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pomoc", aliases=["help", "h", "komendy", "commands"])
    async def pomoc(self, ctx):
        """Pokazuje listę wszystkich komend"""
        embed = discord.Embed(
            title="📚 Pomoc – podstawowe komendy",
            description="Prefix: **8**   |   Wszystkie komendy zaczynają się od ósemki\n\nPełna lista wkrótce w rozbudowanej wersji",
            color=0x5865f2
        )

        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        embed.add_field(
            name="🎲 Gra w Farkle",
            value="`8rzut` – nowa gra vs bot\n`8skończ` – kończy grę",
            inline=False
        )

        embed.add_field(
            name="🎵 Muzyka z YouTube",
            value=(
                "`8dołącz` – bot dołącza do kanału głosowego\n"
                "`8opuść` – bot wychodzi\n"
                "`8graj <nazwa/link>` – puszcza piosenkę\n"
                "`8skip` – pomija\n"
                "`8pauza` / `8wznów` – pauza / wznowienie\n"
                "`8kolejka` – pokazuje kolejkę\n"
                "`8podobne` – podobny utwór do ostatniego\n"
                "`8poprzedni` – wraca do poprzedniego\n"
                "`8zakończ` – zatrzymuje muzykę i czyści kolejkę"
            ),
            inline=False
        )

        embed.add_field(
            name="😂 Memy",
            value="`8meme` – losowy mem (głównie anglo)\n`8polmeme` – losowy polski mem",
            inline=False
        )

        embed.add_field(
            name="🛡️ Moderacja (dla uprawnionych)",
            value=(
                "`8wyrzuc @osoba [powód]` – kick\n"
                "`8zbanuj @osoba [powód]` – ban\n"
                "`8odbanuj ID/@osoba [powód]` – odbanuj\n"
                "`8wycisz @osoba czas [powód]` – wycisza (np. 30m, 2h, 1d)\n"
                "`8odcisz @osoba [powód]` – zdejmuje wyciszenie"
            ),
            inline=False
        )

        embed.set_footer(text="Bot Seby • Farkle + Muzyka + Memy + Moderacja • v1.0 • 8testpomoc – sprawdź cog")
        await ctx.send(embed=embed)

    @commands.command()
    async def testpomoc(self, ctx):
        await ctx.send("Cog pomoc żyje! Komenda testowa działa.")

async def setup(bot):
    await bot.add_cog(Pomoc(bot))
