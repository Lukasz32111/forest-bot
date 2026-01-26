# cogs/ankieta.py
import discord
from discord.ext import commands
import asyncio
from typing import List

class Ankieta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ankieta", aliases=["poll", "głosowanie", "sonda"])
    async def ankieta(self, ctx, *, pytanie_i_opcje: str):
        """
        Tworzy ankietę z reakcjami! 8ankieta "Która pizza?" "Margherita" "Pepperoni" "Hawaii" "4 sery"
        
        • Maks 10 opcji (1️⃣ ➕ ➕ ➕ ➕ ➕ ➕ ➕ ➕ ➕)
        • ❌ zamyka ankietę
        • Automatycznie liczy głosy
        """
        # Podzielamy na pytanie i opcje (pierwsze w cudzysłowie, reszta opcje)
        parts = pytanie_i_opcje.split('"')
        if len(parts) < 3 or len(parts) % 2 == 0:
            return await ctx.send("❌ Błąd formatu! Przykład:\n`8ankieta \"Która pizza?\" \"Pepperoni\" \"Margherita\" \"Hawaii\"`")

        pytanie = parts[1].strip()
        opcje_raw = [opt.strip() for opt in parts[2::2]]
        
        if len(opcje_raw) < 2 or len(opcje_raw) > 10:
            return await ctx.send("❌ Ankieta musi mieć 2–10 opcji!")

        # Emoji dla opcji (1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣ 8️⃣ 9️⃣ 🔟)
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        opcje = opcje_raw[:10]

        embed = discord.Embed(
            title=f"📊 **{pytanie}**",
            description=f"**Głosuj reakcją!** ({len(opcje)} opcji)\n\n" + 
                       "\n".join(f"{emojis[i]} {opcje[i]}" for i in range(len(opcje))),
            color=0x5865f2
        )
        embed.set_footer(text=f"Wygłosowana przez {ctx.author.display_name} | Kliknij ❌ aby zamknąć")
        
        msg = await ctx.send(embed=embed)
        
        # Dodajemy reakcje
        for emoji in emojis[:len(opcje)]:
            await msg.add_reaction(emoji)
        await msg.add_reaction("❌")

        def check(reaction, user):
            return reaction.message.id == msg.id and str(reaction.emoji) in emojis[:len(opcje)] + ["❌"]

        votes = {emoji: 0 for emoji in emojis[:len(opcje)]}
        voters = {emoji: set() for emoji in emojis[:len(opcje)]}  # unikamy wielokrotnych głosów

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=300.0, check=check)  # 5 min timeout
                
                emoji_str = str(reaction.emoji)
                
                if emoji_str == "❌" and user == ctx.author:
                    embed.set_footer(text="Ankieta zamknięta przez twórcę")
                    await msg.edit(embed=embed)
                    break
                
                if emoji_str in votes and user.id not in voters[emoji_str]:
                    # Nowy głos
                    votes[emoji_str] += 1
                    voters[emoji_str].add(user.id)
                    
                    # Aktualizujemy embed z wynikami
                    wynik = "\n".join(f"{emoji} **{votes[emoji]}** ({opcje[i]})" 
                                     for i, emoji in enumerate(emojis[:len(opcje)]))
                    
                    embed = discord.Embed(
                        title=f"📊 **{pytanie}**",
                        description=f"**Wyniki na żywo:**\n{wynik}",
                        color=0x00ff00 if max(votes.values()) > 0 else 0x5865f2
                    )
                    embed.set_footer(text=f"{sum(voters.values())} głosujących | Zakończ ❌")
                    await msg.edit(embed=embed)
                
                # Usuwamy reakcję użytkownika (żeby nie spamował)
                try:
                    await msg.remove_reaction(reaction, user)
                except:
                    pass

            except asyncio.TimeoutError:
                # Kończymy po 5 minutach
                wynik = "\n".join(f"{emoji} **{votes[emoji]}** ({opcje[i]})" 
                                 for i, emoji in enumerate(emojis[:len(opcje)]))
                max_votes = max(votes.values())
                winners = [opcje[i] for i, v in enumerate(votes.values()) if v == max_votes]
                
                embed = discord.Embed(
                    title=f"📊 **{pytanie}** – Zakończona",
                    description=f"**Ostateczne wyniki:**\n{wynik}\n\n**Wygrywa:** {', '.join(winners)} ({max_votes} głosów)",
                    color=0xffd700
                )
                embed.set_footer(text=f"{sum(voters.values())} głosujących | Ankieta zakończona")
                await msg.edit(embed=embed)
                break

async def setup(bot):
    await bot.add_cog(Ankieta(bot))
