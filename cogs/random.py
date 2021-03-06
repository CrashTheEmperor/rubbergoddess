import random
import requests

import discord
from discord.ext import commands

from core import rubbercog, utils
from core.text import text


class Random(rubbercog.Rubbercog):
    """Pick, flip, roll dice"""

    def __init__(self, bot):
        super().__init__(bot)

    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def pick(self, ctx, *args):
        """"Pick an option"""
        option = self.sanitise(random.choice(args), limit=50)
        if option is not None:
            await ctx.send(text.fill("random", "answer", mention=ctx.author.mention, option=option))

        await utils.room_check(ctx)
        arg_list = " ".join([f"`{self.sanitise(x)}`" for x in args])[:1900]

    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def flip(self, ctx):
        """Yes/No"""
        option = random.choice(text.get("random", "flip"))
        await ctx.send(text.fill("random", "answer", mention=ctx.author.mention, option=option))

        await utils.room_check(ctx)

    @commands.cooldown(rate=5, per=20.0, type=commands.BucketType.user)
    @commands.command()
    async def random(self, ctx, first: int, second: int = None):
        """Pick number from interval"""
        if second is None:
            second = 0

        if first > second:
            first, second = second, first

        option = str(random.randint(first, second))
        await ctx.send(text.fill("random", "answer", mention=ctx.author.mention, option=option))

        await utils.room_check(ctx)

    @commands.cooldown(rate=5, per=20, type=commands.BucketType.channel)
    @commands.command(aliases=["unsplash"])
    async def picsum(self, ctx, seed: str = None):
        """Get random image from picsum.photos"""
        size = "450/300"
        url = "https://picsum.photos/"
        if seed:
            url += "seed/" + seed + "/"
        url += f"{size}.jpg?random={ctx.message.id}"

        # we cannot use the URL directly, because embed will contain other image than its thumbnail
        image = requests.get(url)
        if image.status_code != 200:
            return await ctx.send(f"E{image.status_code}")

        # get image info
        # example url: https://i.picsum.photos/id/857/600/360.jpg?hmac=.....
        image_id = image.url.split("/id/", 1)[1].split("/")[0]
        image_info = requests.get(f"https://picsum.photos/id/{image_id}/info")
        try:
            image_url = image_info.json()["url"]
            log_url = "<" + image_url + ">"
        except:
            image_url = discord.Embed.Empty
            log_url = "with picsum ID " + image_id

        embed = self.embed(ctx=ctx, title=discord.Embed.Empty, description=image_url, footer=seed)
        embed.set_image(url=image.url)
        await ctx.send(embed=embed)

        await utils.room_check(ctx)


def setup(bot):
    bot.add_cog(Random(bot))
