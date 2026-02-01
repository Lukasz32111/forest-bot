# cogs/propozycje.py
import discord
from discord.ext import commands
import asyncio

class Propozycje(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["pomysł", "sugestia", "idea"])
    async def propozycja(self, ctx, *, tekst: str):
        """Wysyła propozycję na serwer – 8propozycja [tekst]"""
        # Kanał propozycji – zmień nazwę jeśli inna
        kanal_propozycje = discord.utils.get(ctx.guild.text_channels, name="propozycje")
        if not kanal_propozycje:
            return await ctx.send("Nie znaleziono kanału #propozycje – stwórz go najpierw.")

        # Kategoria archiwum (opcjonalna)
        kategoria_archiwum = discord.utils.get(ctx.guild.categories, name="Archiwum Propozycji")

        # Tworzymy wątek
        thread_name = f"Propozycja od {ctx.author.name} – {tekst[:50]}{'...' if len(tekst) > 50 else ''}"
        thread = await kanal_propozycje.create_thread(
            name=thread_name,
            type=discord.ChannelType.public_thread,
            auto_archive_duration=10080,  # 7 dni
            reason=f"Propozycja od {ctx.author}"
        )

        # Wiadomość w wątku
        embed = discord.Embed(
            title="Nowa propozycja!",
            description=tekst,
            color=discord.Color.blue()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_footer(text="Głosujcie reakcjami poniżej • Moderatorzy mogą zamknąć wątek")

        msg = await thread.send(embed=embed, content=f"{ctx.author.mention} zgłasza propozycję!")

        # Dodajemy reakcje do głosowania
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        await msg.add_reaction("👀")  # "chcę uwagi"
        await msg.add_reaction("🔒")  # zamknięcie przez moderatora

        # Usuwamy oryginalną wiadomość użytkownika (żeby nie zaśmiecał kanału)
        try:
            await ctx.message.delete()
        except:
            pass

        await ctx.send(f"Twoja propozycja została wysłana! Sprawdź wątek: {thread.mention}", delete_after=10)

    @commands.command(name="zamknij")
    @commands.has_permissions(manage_messages=True)
    async def zamknij(self, ctx):
        """Zamyka bieżący wątek propozycji – tylko moderatorzy"""
        if not ctx.channel.type == discord.ChannelType.public_thread:
            return await ctx.send("Ta komenda działa tylko wewnątrz wątku propozycji.")

        thread = ctx.channel

        # Archiwizacja (opcjonalna – usuń jeśli nie chcesz)
        kategoria_archiwum = discord.utils.get(ctx.guild.categories, name="Archiwum Propozycji")
        if kategoria_archiwum:
            await thread.edit(archived=True, locked=True)
            await thread.send("Wątek zamknięty przez moderatora. Przeniesiono do archiwum.")
        else:
            await thread.edit(archived=True, locked=True)
            await thread.send("Wątek zamknięty przez moderatora.")

        # Opcjonalnie: ping autora wątku
        creator = thread.owner
        if creator:
            await thread.send(f"{creator.mention}, Twój wątek został zamknięty.")

async def setup(bot):
    await bot.add_cog(Propozycje(bot))
