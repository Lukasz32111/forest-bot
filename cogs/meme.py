# cogs/meme.py
import discord
from discord.ext import commands
import aiohttp

class Meme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["losmeme", "mem", "śmieszne"]) 
    async def meme(self, ctx):                  
        """Wysyła losowego mema z reddita"""   
        url = "https://meme-api.com/gimme"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        await ctx.send("Ups... coś nie działa z memami 😅 Spróbuj później!")
                        return

                    data = await resp.json()

                    # Sprawdzamy czy mamy to co trzeba
                    if "url" not in data or not data["url"].startswith("https://i.redd.it/"):
                        await ctx.send("Dostałem dziwnego mema... spróbuj jeszcze raz!")
                        return

                    title = data.get("title", "Bez tytułu :(")
                    post_link = data.get("postLink", "https://reddit.com")
                    subreddit = data.get("subreddit", "memes")

                    embed = discord.Embed(
                        title=title,
                        url=post_link,
                        color=0xff4500  # pomarańczowy redditowy
                    )
                    embed.set_image(url=data["url"])
                    embed.set_footer(text=f"r/{subreddit} • Powered by meme-api.com")

                    await ctx.send(embed=embed)

        except Exception as e:
            print(f"Błąd w memie: {e}")
            await ctx.send("Memy się schowały... spróbuj za chwilę 🫣")

async def setup(bot):
    await bot.add_cog(Meme(bot))
