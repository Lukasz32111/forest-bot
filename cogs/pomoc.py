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

        # Strona 1 – wstęp + Muzyka
        embed1 = discord.Embed(
            title="📚 Pomoc – strona 1/4",
            description="Prefix: **8**   |   Używaj strzałek ◀️ ▶️ do przełączania",
            color=0x5865f2
        )
        embed1.add_field(
            name="🎵 Muzyka z YouTube",
            value=(
                "`dołącz` – dołącza do kanału głosowego\n"
                "`opuść` – wychodzi z kanału\n"
                "`graj <nazwa/link>` – dodaje i odtwarza\n"
                "`skip` – pomija utwór\n"
                "`poprzedni` – wraca do poprzedniego\n"
                "`pauza` / `wznów` – pauza / wznowienie\n"
                "`kolejka` – pokazuje kolejkę\n"
                "`podobne` – podobny utwór do ostatniego\n"
                "`zakończ` – zatrzymuje i czyści kolejkę"
            ),
            inline=False
        )
        pages.append(embed1)

        # Strona 2 – Farkle + Memy
        embed2 = discord.Embed(
            title="📚 Pomoc – strona 2/4",
            description="Prefix: **8**   |   ◀️ ▶️ do nawigacji",
            color=0x5865f2
        )
        embed2.add_field(
            name="🎲 Farkle",
            value="`rzut` – zaczyna nową grę vs bot\n`skończ` – kończy aktualną grę",
            inline=False
        )
        embed2.add_field(
            name="😂 Memy",
            value="`meme` – losowy mem (głównie anglojęzyczne)\n`polmeme` – losowy polski mem",
            inline=False
        )
        pages.append(embed2)

        # Strona 3 – Moderacja
        embed3 = discord.Embed(
            title="📚 Pomoc – strona 3/4",
            description="Prefix: **8**   |   ◀️ ▶️ do nawigacji",
            color=0x5865f2
        )
        embed3.add_field(
            name="🛡️ Moderacja (wymaga uprawnień)",
            value=(
                "`wyrzuc @osoba [powód]` – wyrzuca z serwera\n"
                "`zbanuj @osoba [powód]` – banuje\n"
                "`odbanuj ID/@osoba [powód]` – odbanowuje\n"
                "`wycisz @osoba czas [powód]` – timeout (np. 30m, 2h)\n"
                "`odcisz @osoba [powód]` – zdejmuje timeout"
            ),
            inline=False
        )
        pages.append(embed3)

        # Strona 4 – informacje dodatkowe
        embed4 = discord.Embed(
            title="📚 Pomoc – strona 4/4",
            description="Prefix: **8**   |   Koniec listy",
            color=0x5865f2
        )
        embed4.add_field(
            name="Dodatkowe info",
            value=(
                "• Bot ma włączone reakcje i embedy\n"
                "• Problemy? Napisz do twórcy"
            ),
            inline=False
        )
        pages.append(embed4)

        return pages

async def setup(bot):
    await bot.add_cog(Pomoc(bot))
