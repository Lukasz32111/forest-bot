# cogs/pomoc.py
from discord.ext import commands
import discord

class Pomoc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pomoc", aliases=["h", "cmds", "komendy", "commands"])
    async def pomoc(self, ctx):
        embed = discord.Embed(
            title="📋 Wszystkie komendy (alfabetycznie)",
            description="Prefix: `8`   •   Pełna lista dostępnych komend",
            color=0x5865f2
        )
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        # Lista alfabetyczna – możesz łatwo dodawać nowe komendy w przyszłości
        komendy = [
            ("dołącz",     "Bot dołącza do Twojego kanału głosowego"),
            ("graj",       "<nazwa / link> → dodaje utwór do kolejki i gra"),
            ("kolejka",    "Pokazuje aktualną listę utworów w kolejce"),
            ("opuść",      "Bot wychodzi z kanału głosowego"),
            ("pauza",      "Zatrzymuje aktualnie graną piosenkę"),
            ("podobne",    "Puszcza losowy podobny utwór do ostatniego"),
            ("poprzedni",  "Wraca do poprzedniego utworu z historii"),
            ("rzut",       "[@osoba opcjonalnie] → zaczyna grę w Farkle vs bot"),
            ("skip",       "Pomija aktualny utwór"),
            ("skończ",     "Przerywa trwającą grę w Farkle (alias: stop)"),
            ("wznów",      "Wznawia zatrzymaną piosenkę"),
            ("zakończ",    "Zatrzymuje muzykę i czyści kolejkę"),
            ("pomoc",      "Pokazuje właśnie tę listę komend"),
            ("meme",       "Wysyła losowego mema z reddita (r/memes, dankmemes itp.)"),
            ("memepl",     "Wysyła losowego polskiego mema (głównie r/Polska_jest_najlepsza)"),
            ("wyrzuc",     "Wyrzuca użytkownika z serwera   @osoba [powód]"),
            ("zbanuj",     "Banuje użytkownika   @osoba [powód]"),
            ("odbanuj",    "Odbanowuje użytkownika   ID/@osoba [powód]"),
            ("wycisz",     "Wycisza użytkownika na czas   @osoba czas [powód]"),
            ("odcisz",     "Zdejmuje wyciszenie   @osoba [powód]"),
        ]

        # Sortujemy alfabetycznie po nazwie komendy
        komendy.sort(key=lambda x: x[0])

        opis = ""
        for nazwa, desc in komendy:
            opis += f"`8{nazwa}` → {desc}\n"

        embed.add_field(
            name="Komendy",
            value=opis,
            inline=False
        )

        embed.set_footer(text="Bot do Farkle + Muzyka YT • v1.0 • Użyj 8pomoc żeby wrócić")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Pomoc(bot))
