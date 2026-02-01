# cogs/propozycje.py
import discord
from discord.ext import commands
import asyncio

class Propozycje(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.propozycje_kanal_id = 1455914898390257805  # Twój kanał

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.channel.id != self.propozycje_kanal_id:
            return

        # Usuwamy oryginalną wiadomość (kanał zostaje czysty)
        try:
            await message.delete()
        except:
            pass

        # Tworzymy ładny embed
        embed = discord.Embed(
            description=message.content or "Propozycja bez treści",
            color=discord.Color.blue()
        )
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.avatar.url if message.author.avatar else None
        )
        embed.set_footer(text="Głosuj reakcjami poniżej • + = podoba mi się • – = nie podoba mi się • X = nie mam zdania")

        msg = await message.channel.send(embed=embed)

        # Dodajemy trzy reakcje do głosowania
        await msg.add_reaction("👍")  # plus – popieram / podoba mi się
        await msg.add_reaction("👎")  # minus – nie podoba mi się
        await msg.add_reaction("❌")  # X – nie mam zdania

        # Tworzymy aktywny wątek do dyskusji
        thread_name = f"{message.author.name} – {message.content[:50]}{'...' if len(message.content) > 50 else ''}"
        thread = await msg.create_thread(
            name=thread_name,
            type=discord.ChannelType.public_thread,
            auto_archive_duration=10080,  # 7 dni
            reason=f"Propozycja od {message.author}"
        )

        # Startowa wiadomość w wątku
        await thread.send(
            f"Witajcie! To jest wątek dyskusyjny do propozycji od {message.author.mention}.\n"
            f"Możecie tu normalnie pisać, zadawać pytania, dyskutować.\n"
            f"Oryginalna propozycja w wiadomości powyżej ↑"
        )

    @commands.command(name="zamknij")
    @commands.has_permissions(manage_messages=True)
    async def zamknij(self, ctx):
        """Zamyka bieżący wątek propozycji – tylko moderatorzy"""
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.send("Ta komenda działa tylko wewnątrz wątku.")

        thread = ctx.channel
        await thread.edit(archived=True, locked=True)
        await thread.send("Wątek zamknięty przez moderatora – dyskusja zakończona.")

async def setup(bot):
    await bot.add_cog(Propozycje(bot))
