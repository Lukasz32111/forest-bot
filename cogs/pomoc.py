# cogs/pomoc.py
from discord.ext import commands
import discord
import asyncio

class Pomoc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pomoc", aliases=["h", "komendy"])
    async def pomoc(self, ctx):
        pages = self.get_pages()
        current_page = 0

        msg = await ctx.send(embed=pages[current_page])

        # Dodajemy strzałki tylko jeśli jest więcej niż jedna strona
        if len(pages) > 1:
            await msg.add_reaction("◀️")
            await msg.add_reaction("▶️")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) in ["◀️", "▶️"]
                and reaction.message.id == msg.id
            )

        while True:
            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=120.0, check=check
                )

                if str(reaction.emoji) == "▶️" and current_page < len(pages) - 1:
                    current_page += 1
                    await msg.edit(embed=pages[current_page])

                elif str(reaction.emoji) == "◀️" and current_page > 0:
                    current_page -= 1
                    await msg.edit(embed=pages[current_page])

                # Usuwamy reakcję użytkownika (żeby mógł znowu kliknąć)
                await msg.remove_reaction(reaction.emoji, ctx.author)

            except asyncio.TimeoutError:
                # Po 2 minutach usuwamy strzałki
                try:
                    await msg.clear_reactions()
                except:
                    pass
                break

    def get_pages(self):
        """Zwraca listę embedów – każda strona to jeden embed"""
        pages = []

        # Strona 1 – wstęp + Farkle + Memy (muzyka usunięta)
        embed1 = discord.Embed(
            title="📚 Pomoc – strona 1/3",
            description="Prefix: **8** | Używaj strzałek ◀️ ▶️ do przełączania",
            color=0x5865f2
        )
        embed1.add_field(
            name="🎲 Farkle",
            value=(
                "`rzut [@osoba]` – zaczyna nową grę\n"
                " • bez @ – grasz z botem\n"
                " • z @ – grasz z inną osobą (1v1)\n"
                "`skończ` – przerywa aktualną grę"
            ),
            inline=False
        )
        embed1.add_field(
            name="😂 Memy",
            value="`meme` – losowy mem (głównie anglojęzyczne)\n`polmeme` – losowy polski mem",
            inline=False
        )
        pages.append(embed1)

        # Strona 2 – Moderacja
        embed2 = discord.Embed(
            title="📚 Pomoc – strona 2/3",
            description="Prefix: **8** | ◀️ ▶️ do nawigacji",
            color=0x5865f2
        )
        embed2.add_field(
            name="🛡️ Moderacja (wymaga uprawnień)",
            value=(
                "`wyrzuc @osoba [powód]` – wyrzuca z serwera\n"
                "`zbanuj @osoba [powód]` – banuje\n"
                "`odbanuj ID/@osoba [powód]` – odbanowuje\n"
                "`wycisz @osoba <czas> [powód]` – wycisza (do 28 dni, np. 30m, 2h, 7d)\n"
                "`odcisz @osoba [powód]` – zdejmuje timeout\n"
                "`ostrzeżenie @osoba [powód]` – daje ostrzeżenie\n"
                "`ostrzeżenia [@osoba]` – pokazuje ostrzeżenia danej osoby\n"
                "`usuńostrzeżenie @osoba [numer]` – usuwa ostrzeżenie (ostatnie lub konkretne)\n"
                "`czyść [ilość]` – usuwa wiadomości (domyślnie 50, max 1000)\n"
                "`ankieta \"Pytanie?\" \"Opcja1\" \"Opcja2\" ...` – tworzy ankietę z reakcjami (2–10 opcji)\n"
                " • Głosuj klikając 1️⃣ 2️⃣ itd.\n"
                " • Kliknij 👥 aby zobaczyć kto na co zagłosował (w prywatnej wiadomości)"
            ),
            inline=False
        )
        pages.append(embed2)

        # Strona 3 – informacje dodatkowe + ticket
        embed3 = discord.Embed(
            title="📚 Pomoc – strona 3/3",
            description="Prefix: **8** | Koniec listy",
            color=0x5865f2
        )
        embed3.add_field(
            name="Dodatkowe info",
            value=(
                "`ticket [powód]` – tworzy prywatny kanał na zgłoszenie / pytanie\n"
                "• Bot ma włączone reakcje i embedy\n"
                "• Problemy? Napisz do twórcy"
            ),
            inline=False
        )
        pages.append(embed3)

        return pages

async def setup(bot):
    await bot.add_cog(Pomoc(bot))
