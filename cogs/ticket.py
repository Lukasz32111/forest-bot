# cogs/ticket.py
import discord
from discord.ext import commands
import asyncio

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ticket", aliases=["zgłoś", "zgłoszenie"])
    async def ticket(self, ctx, *, reason: str = "Brak powodu"):
        """
        Tworzy prywatny ticket / zgłoszenie
        8ticket [powód opcjonalny]
        """
        guild = ctx.guild
        author = ctx.author

        # Kategoria dla otwartych ticketów
        category = discord.utils.get(guild.categories, name="Tickety")
        if not category:
            category = await guild.create_category("Tickety")

        # Kategoria dla archiwum (zamkniętych ticketów)
        archive_category = discord.utils.get(guild.categories, name="Archiwum Ticketów")
        if not archive_category:
            archive_category = await guild.create_category("Archiwum Ticketów")

        # Nazwa kanału
        channel_name = f"ticket-{author.name.lower().replace(' ', '-')}-{author.discriminator}"

        # Sprawdzamy duplikat
        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            return await ctx.send(f"{author.mention}, masz już otwarty ticket: {existing.mention}")

        # Uprawnienia dla otwartego ticketu
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, manage_channels=True),
        }

        # Rola moderatorów – zmień nazwę roli na swoją (np. "Support", "Moderator", "Admin")
        support_role = discord.utils.get(guild.roles, name="Support")
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)

        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket użytkownika {author} | Powód: {reason}"
        )

        # Embed powitalny
        embed = discord.Embed(
            title="Ticket utworzony!",
            description=f"Cześć {author.mention}! To Twój prywatny kanał na zgłoszenie.\n\n**Powód:** {reason}\n\nOpisz swój problem – moderatorzy niedługo Ci pomogą.",
            color=0x00ff88
        )
        embed.set_thumbnail(url=author.avatar.url if author.avatar else None)

        # Przycisk do zamykania
        view = discord.ui.View(timeout=None)
        close_button = discord.ui.Button(label="Zamknij ticket", style=discord.ButtonStyle.red, emoji="🔒")
        view.add_item(close_button)

        async def close_callback(interaction: discord.Interaction):
            if interaction.user != author and not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message("Tylko autor ticketu lub moderator może go zamknąć.", ephemeral=True)
                return

            await interaction.response.defer()

            # Zmiana kategorii na archiwum
            await channel.edit(category=archive_category, name=f"closed-{channel.name}")

            # Zmiana uprawnień na tylko do odczytu
            await channel.set_permissions(author, send_messages=False)
            if support_role:
                await channel.set_permissions(support_role, send_messages=False)

            # Embed zamknięcia
            closed_embed = discord.Embed(
                title="Ticket zamknięty",
                description=f"Zamknięty przez {interaction.user.mention}\nHistoria rozmowy została przeniesiona do archiwum.",
                color=0xff5555
            )
            await channel.send(embed=closed_embed)

            # Opcjonalny przycisk "Usuń całkowicie" (tylko dla modów)
            delete_view = discord.ui.View(timeout=None)
            delete_button = discord.ui.Button(label="Usuń całkowicie", style=discord.ButtonStyle.danger, emoji="🗑️")
            delete_view.add_item(delete_button)

            async def delete_callback(interaction: discord.Interaction):
                if not interaction.user.guild_permissions.manage_channels:
                    await interaction.response.send_message("Tylko moderator może usunąć kanał.", ephemeral=True)
                    return
                await interaction.response.defer()
                await interaction.followup.send("Kanał zostanie usunięty za 5 sekund...")
                await asyncio.sleep(5)
                await channel.delete()

            delete_button.callback = delete_callback

            await channel.send("**Jeśli chcesz całkowicie usunąć kanał, kliknij poniżej (tylko moderatorzy)**", view=delete_view)

        close_button.callback = close_callback

        await channel.send(embed=embed, content=f"{author.mention} <@&{support_role.id}>", view=view)
        await ctx.send(f"{author.mention}, Twój ticket został utworzony: {channel.mention}")

async def setup(bot):
    await bot.add_cog(Ticket(bot))
