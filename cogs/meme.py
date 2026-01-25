import discord
from discord.ext import commands
import aiohttp
import random

class Meme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Lista polskich subredditów – można łatwo rozbudowywać
        self.polish_subreddits = [
            "Polska_jest_najlepsza",
            "poland",
            "Polska",
            "polmemes",              # jeśli istnieje / odradza się
            "PolskaMemes",           # alternatywna nazwa
            "polandmemes",           # angielsko-polska mieszanka
        ]

    @commands.command(aliases=["mem", "losmeme", "śmieszne"])
    async def meme(self, ctx):
        """Losowy mem (głównie anglojęzyczne)   8meme"""
        await self._send_random_meme(ctx, subreddit=None)

    @commands.command(name="polmeme", aliases=["memepl", "polskiememy", "mempl", "plmeme"])
    async def polmeme(self, ctx):
        """Losowy polski mem (z kilku subredditów)   8polmeme / 8memepl"""
        subreddit = random.choice(self.polish_subreddits)
        await self._send_random_meme(ctx, subreddit=subreddit)

    async def _send_random_meme(self, ctx, subreddit=None):
        base_url = "https://meme-api.com/gimme"
        url = f"{base_url}/{subreddit}" if subreddit else base_url

        max_retries = 4  # ile razy próbujemy innego subreddita
        for attempt in range(max_retries):
            current_sub = subreddit if subreddit else "losowy"
            if subreddit and attempt > 0:
                current_sub = random.choice(self.polish_subreddits)
                url = f"{base_url}/{current_sub}"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status != 200:
                            print(f"Błąd {resp.status} dla r/{current_sub}")
                            continue  # próbujemy następny

                        data = await resp.json()

                        if "url" not in data or not data.get("url", "").startswith(("https://i.redd.it/", "https://preview.redd.it/")):
                            print(f"Nieprawidłowy mem z r/{current_sub}")
                            continue

                        title = data.get("title", "Bez tytułu :(")
                        post_link = data.get("postLink", "https://reddit.com/r/" + current_sub)
                        sub = data.get("subreddit", current_sub)

                        embed = discord.Embed(
                            title=title,
                            url=post_link,
                            color=0xe31e24  # czerwony dla polskich memów
                        )
                        embed.set_image(url=data["url"])
                        embed.set_footer(text=f"r/{sub} • Powered by meme-api.com • Próba {attempt+1}/{max_retries}")

                        await ctx.send(embed=embed)
                        return  # sukces → wychodzimy

            except Exception as e:
                print(f"Błąd podczas próby {attempt+1} (r/{current_sub}): {e}")

        # Jeśli wszystkie próby zawiodły
        await ctx.send(
            "Serwis memów ma obecnie przerwę na polskich subredditach 😅\n"
            "Spróbuj za chwilę lub użyj `8meme` na anglojęzyczne śmieszki."
        )

async def setup(bot):
    await bot.add_cog(Meme(bot))
