# cogs/ticket.py
import discord
from discord.ext import commands
import asyncio

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ticket", aliases=["zgłoś", "support"])
    async def ticket(self, ctx, *, reason: str = "Brak powodu"):
        """
        Tworzy prywatny ticket / zgłoszenie
        8ticket [powód opcjonalny]
        """
        guild = ctx.guild
        author = ctx.author

        # Tworzymy kategorię "Tickety" jeśli nie istnieje
        category = discord.utils.get(guild.categories, name="Tickety")
        if not category:
            category = await guild.create_category("Tickety")

        # Tworzymy nazwę kanału (ticket-username lub ticket-id)
        channel_name = f"ticket-{author.name.lower().replace(' ', '-')}-{author.discriminator}"

        # Sprawdzamy, czy kanał już istnieje (unikamy duplikatów)
        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            return await ctx.send(f"{author.mention}, masz już otwarty ticket: {existing.mention}")

        # Tworzymy kanał
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, manage_channels=True),
        }

        # Dodajemy rolę moderatorów (zmień "Support" na nazwę swojej roli)
        support_role = discord.utils.get(guild.roles, name="Support")
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)

        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket użytkownika {author} | Powód: {reason}"
        )

        # Embed powitalny w tickecie
        embed = discord.Embed(
            title="Ticket został utworzony!",
            description=f"Cześć {author.mention}! To Twój prywatny kanał na zgłoszenie.\n\n**Powód:** {reason}\n\nOpisz swój problem, a moderatorzy niedługo Ci pomogą.\n\nAby zamknąć ticket, kliknij przycisk poniżej.",
            color=0x00ff88
        )
        embed.set_thumbnail(url=author.avatar.url if author.avatar else None)
        embed.set_footer(text="Ticket zostanie usunięty po zamknięciu")

        # Przycisk do zamykania
        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(label="Zamknij ticket", style=discord.ButtonStyle.red, emoji="🔒")
        view.add_item(button)

        async def close_ticket(interaction: discord.Interaction):
            if interaction.user != author and not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message("Tylko autor ticketu lub moderator może go zamknąć.", ephemeral=True)
                return

            await interaction.response.defer()
            await channel.send(f"Ticket zamykany przez {interaction.user.mention}...")
            await asyncio.sleep(2)
            await channel.delete()

        button.callback = close_ticket

        await channel.send(embed=embed, view=view)
        await ctx.send(f"{author.mention}, Twój ticket został utworzony: {channel.mention}")

async def setup(bot):
    await bot.add_cog(Ticket(bot))
