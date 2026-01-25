# cogs/pomoc.py
from discord.ext import commands
import discord

class Pomoc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
@commands.command(name="pomoc", aliases=["h", "cmds", "komendy", "commands"])
async def pomoc(self, ctx):
    embed = discord.Embed(
        title="📚 Pomoc – podstawowe komendy",
        description="Prefix: **8** | Pełna lista wkrótce w rozbudowanej wersji",
        color=0x5865f2
    )
    
    if self.bot.user.avatar:
        embed.set_thumbnail(url=self.bot.user.avatar.url)

    embed.add_field(
        name="Gra w Farkle",
        value="`8rzut` – nowa gra vs bot\n`8skończ` – kończy grę",
        inline=False
    )
    
    embed.add_field(
        name="Muzyka",
        value="`8graj <nazwa/link>` – puszcza piosenkę\n`8skip` – pomija\n`8pauza` / `8wznów`\n`8kolejka` – pokazuje kolejkę\n`8dołącz` / `8opuść`",
        inline=False
    )
    
    embed.add_field(
        name="Memy",
        value="`8meme` – losowy mem\n`8polmeme` – polski mem",
        inline=False
    )
    
    embed.add_field(
        name="Moderacja",
        value="`8wyrzuc @osoba`\n`8zbanuj @osoba`\n`8odbanuj ID/@osoba`\n`8wycisz @osoba 30m`\n`8odcisz @osoba`",
        inline=False
    )
    
    embed.set_footer(text="Bot Seby • v1.0 • Testuj 8testpomoc żeby sprawdzić cog")
    
    await ctx.send(embed=embed)
        
    @commands.command()
    async def testpomoc(self, ctx):
        await ctx.send("Cog pomoc żyje! Komenda testowa działa.")

async def setup(bot):
    await bot.add_cog(Pomoc(bot))
