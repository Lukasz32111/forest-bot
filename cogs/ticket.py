# cogs/ticket.py
import discord
from discord.ext import commands
import asyncio

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tickets = {}  # user_id -> channel_id (ochrona 1 ticket na osobę)

    @commands.command(name="ticket", aliases=["zgłoś", "zgłoszenie"])
    async def ticket(self, ctx, *, reason: str = "Brak powodu"):
        """
        Tworzy prywatny ticket / zgłoszenie
        8ticket [powód opcjonalny]
        """
        guild = ctx.guild
        author = ctx.author
        user_id = str(author.id)

        # Usuwamy wiadomość z komendą (nie zaśmieca kanału)
        try:
            await ctx.message.delete()
        except:
            pass

        # 1. Ochrona przed duplikatami – sprawdzamy po user ID
        if user_id in self.active_tickets:
            channel_id = self.active_tickets[user_id]
            channel = guild.get_channel(channel_id)
            if channel:
                return await ctx.send(
                    f"{author.mention}, masz już otwarty ticket: {channel.mention}\n"
                    "Najpierw go zamknij, zanim stworzysz nowy.",
                    delete_after=15
                )
            else:
                # Kanał nie istnieje (np. usunięty ręcznie) – czyścimy cache
                del self.active_tickets[user_id]

        # Kategoria dla otwartych ticketów
        category = discord.utils.get(guild.categories, name="Tickety")
        if not category:
            category = await guild.create_category("Tickety")

        # Kategoria dla archiwum
        archive_category = discord.utils.get(guild.categories, name="Archiwum Ticketów")
        if not archive_category:
            archive_category = await guild.create_category("Archiwum Ticketów")

        # Nazwa kanału
        channel_name = f"ticket-{author.name.lower().replace(' ', '-')}-{author.discriminator}"

        # Uprawnienia dla otwartego ticketu
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, manage_channels=True),
        }

        # Rola moderatorów – ZMIEŃ NAZWĘ ROLI NA SWOJĄ (np. "Support", "Moderator", "Admin")
        support_role = discord.utils.get(guild.roles, name="Support")
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)

        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket użytkownika {author} | Powód: {reason}"
        )

        # Zapisujemy aktywny ticket użytkownika
        self.active_tickets[user_id] = channel.id

        # Embed powitalny w tickecie
        embed = discord.Embed(
            title="Ticket utworzony!",
            description=(
                f"Cześć {author.mention}!\n"
                "To Twój prywatny kanał na zgłoszenie.\n\n"
                f"**Powód:** {reason}\n"
                f"**Utworzony:** {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                "Opisz swój problem – moderatorzy niedługo Ci pomogą.\n"
                "Aby zamknąć ticket, kliknij przycisk poniżej ↓"
            ),
            color=0x00ff88
        )
        embed.set_thumbnail(url=author.avatar.url if author.avatar else None)
        embed.set_footer(text="Ticket zostanie przeniesiony do archiwum po zamknięciu")

        # Przycisk do zamykania
        view = discord.ui.View(timeout=None)
        close_button = discord.ui.Button(label="Zamknij ticket", style=discord.ButtonStyle.red, emoji="🔒")
        view.add_item(close_button)

        async def close_callback(interaction: discord.Interaction):
            if interaction.user != author and not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message("Tylko autor ticketu lub moderator może go zamknąć.", ephemeral=True)
                return

            await interaction.response.defer()

            # Przenosimy do archiwum
            await channel.edit(category=archive_category, name=f"closed-{channel.name}")

            # Tylko do odczytu
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

            # Zwalniamy slot (można stworzyć nowy ticket)
            if user_id in self.active_tickets:
                del self.active_tickets[user_id]

            # Przycisk "Usuń całkowicie" (tylko dla modów)
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

        # Wysyłamy embed + pingujemy autora i support
        content = f"{author.mention}"
        if support_role:
            content += f" <@&{support_role.id}>"
        await channel.send(content=content, embed=embed, view=view)

        # Potwierdzenie w kanale komendy
        await ctx.send(f"{author.mention}, Twój ticket został utworzony: {channel.mention}", delete_after=10)

async def setup(bot):
    await bot.add_cog(Ticket(bot))
