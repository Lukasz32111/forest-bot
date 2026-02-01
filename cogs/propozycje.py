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

        # Usuwamy oryginalną wiadomość
        try:
            await message.delete()
        except:
            pass

        # Embed z propozycją
        embed = discord.Embed(
            description=message.content or "Propozycja bez treści",
            color=discord.Color.blue()
        )
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.avatar.url if message.author.avatar else None
        )
        embed.set_footer(text="Głosuj reakcjami poniżej • 👍 = popieram • ❌ = nie mam zdania • możesz zmienić głos")

        try:
            msg = await message.channel.send(embed=embed)
        except Exception as e:
            print(f"Błąd wysyłania embeda: {e}")
            return

        # Reakcje – tylko 👍 i ❌
        try:
            await msg.add_reaction("👍")
            await msg.add_reaction("❌")
        except Exception as e:
            print(f"Błąd dodawania reakcji: {e}")

        # Tworzenie wątku
        thread_name = f"{message.author.name} – {message.content[:50]}{'...' if len(message.content) > 50 else ''}"
        try:
            thread = await msg.create_thread(
                name=thread_name,
                auto_archive_duration=10080,  # 7 dni
                reason=f"Propozycja od {message.author}"
            )
            await thread.send(
                f"Witajcie! To jest wątek dyskusyjny do propozycji od {message.author.mention}.\n"
                f"Możecie tu normalnie pisać, dyskutować, zadawać pytania.\n"
                f"Oryginalna propozycja w wiadomości powyżej ↑"
            )
        except Exception as e:
            print(f"Błąd tworzenia wątku: {e}")
            await msg.reply(f"Nie udało się stworzyć wątku: {e}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot:
            return

        if reaction.message.channel.id != self.propozycje_kanal_id:
            return

        msg = reaction.message
        if not msg.embeds:
            return

        allowed = ["👍", "❌"]
        if str(reaction.emoji) not in allowed:
            return

        # Usuwamy drugą reakcję, jeśli użytkownik ma już jedną
        other_emoji = "👍" if str(reaction.emoji) == "❌" else "❌"
        other_reaction = discord.utils.get(msg.reactions, emoji=other_emoji)
        if other_reaction:
            async for u in other_reaction.users():
                if u.id == user.id:
                    await msg.remove_reaction(other_emoji, user)
                    break

    @commands.command(name="zamknijprop", aliases=["closeprop"])
    @commands.has_permissions(manage_messages=True)
    async def zamknijprop(self, ctx):
        """Zamyka bieżący wątek propozycji – tylko moderatorzy"""
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.send("Ta komenda działa tylko wewnątrz wątku propozycji.")

        thread = ctx.channel
        await thread.edit(archived=True, locked=True)
        await thread.send("Wątek zamknięty przez moderatora – dyskusja zakończona.")

async def setup(bot):
    await bot.add_cog(Propozycje(bot))
