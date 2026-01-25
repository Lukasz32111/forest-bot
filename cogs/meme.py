import discord
from discord.ext import commands
import aiohttp

class Meme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["mem", "losmeme", "śmieszne"])
    async def meme(self, ctx):
        """Losowy mem (głównie anglojęzyczne)   8meme"""
        await self._send_random_meme(ctx, subreddit=None)

    @commands.command(name="polmeme", aliases=["memepl", "polskiememy", "mempl", "plmeme"])
    async def polmeme(self, ctx):
        """Losowy polski mem   8polmeme  albo 8memepl"""
        await self._send_random_meme(ctx, subreddit="Polska_jest_najlepsza")

    async def _send_random_meme(self, ctx, subreddit=None):
        base_url = "https://meme-api.com/gimme"
        url = f"{base_url}/{subreddit}" if subreddit else base_url

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=12) as resp:
                    if resp.status != 200:
                        await ctx.send("Serwis memów ma przerwę... spróbuj za chwilę 😅")
                        return

                    data = await resp.json()

                    if "url" not in data or not data["url"].startswith(("https://i.redd.it/", "https://preview.redd.it/")):
                        await ctx.send("Dostałem link, który nie wygląda na mem... spróbuj ponownie!")
                        return

                    title = data.get("title", "Bez tytułu :(")
                    post_link = data.get("postLink", "https://reddit.com")
                    sub = data.get("subreddit", subreddit or "mieszane")

                    embed = discord.Embed(
                        title=title,
                        url=post_link,
                        color=0xe31e24 if "pl" in sub.lower() else 0xff4500
                    )
                    embed.set_image(url=data["url"])
                    embed.set_footer(text=f"r/{sub} • Powered by meme-api.com")

                    await ctx.send(embed=embed)

        except Exception as e:
            print(f"Błąd memów: {e}")
            await ctx.send("Memy uciekły... spróbuj jeszcze raz 🏃‍♂️💨")

async def setup(bot):
    await bot.add_cog(Meme(bot))
