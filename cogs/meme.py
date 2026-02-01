import discord
from discord.ext import commands
import aiohttp
import random

class Meme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Najlepsze aktywne polskie subreddity z memami (2025/2026)
        self.polish_subreddits = [
            "Polska_wpz",             # obecnie najwięcej memów
            "Polska",
            "Polska_jest_najlepsza",
            "PolskaMemes",
            "polandmemes",
            "PolskaDankMemes",
            "PolskaWpzMemes",
            "poland",
            "polmemes",               # czasem wraca do życia
        ]

    @commands.command(aliases=["mem", "losmeme", "śmieszne"])
    async def meme(self, ctx):
        """Losowy mem (głównie anglojęzyczne) – 8meme"""
        await self._send_random_meme(ctx, subreddit=None)

    @commands.command(name="polmeme", aliases=["memepl", "polskiememy", "mempl", "plmeme"])
    async def polmeme(self, ctx):
        """Losowy **polski** mem – naprawdę po polsku – 8polmeme"""
        subreddit = random.choice(self.polish_subreddits)
        await self._send_random_meme(ctx, subreddit=subreddit)

    async def _send_random_meme(self, ctx, subreddit=None):
        base_url = "https://meme-api.com/gimme"
        url = f"{base_url}/{subreddit}" if subreddit else base_url

        max_retries = 6
        for attempt in range(max_retries):
            current_sub = subreddit if subreddit else "losowy (anglo)"
            if subreddit and attempt > 0:
                current_sub = random.choice(self.polish_subreddits)
                url = f"{base_url}/{current_sub}"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=12) as resp:
                        if resp.status != 200:
                            continue

                        data = await resp.json()

                        # Sprawdzamy, czy to naprawdę obrazek
                        img_url = data.get("url", "")
                        if not img_url or not img_url.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                            continue  # pomijamy tekstowe posty, linki YT itp.

                        title = data.get("title", "Bez tytułu")
                        post_link = data.get("postLink", f"https://reddit.com/r/{current_sub}")
                        sub = data.get("subreddit", current_sub)

                        embed = discord.Embed(
                            title=title,
                            url=post_link,
                            color=0xff4500  # pomarańczowy – polski vibe
                        )
                        embed.set_image(url=img_url)
                        embed.set_footer(text=f"r/{sub} • meme-api.com • Próba {attempt+1}/{max_retries}")

                        await ctx.send(embed=embed)
                        return  # sukces!

            except Exception as e:
                print(f"Błąd mema ({current_sub}, próba {attempt+1}): {e}")

        # Jeśli wszystko zawiodło
        await ctx.send(
            "Cholera, dzisiaj polskie subreddity milczą 😭\n"
            "Spróbuj za chwilę albo użyj `8meme` na anglojęzyczne memy."
        )

async def setup(bot):
    await bot.add_cog(Meme(bot))
