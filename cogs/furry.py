import logging

import discord
from discord.ext import commands

from api import ApiError, api
from config import E621, E621_API, E621_LOGIN

log = logging.getLogger("dota-bot.furry")


class Furry(commands.Cog):
    """e621."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="furry",
        aliases=["e621"],
        description="Случайный пост с e621",
    )
    async def furry_cmd(self, ctx: commands.Context, *, tags: str = ""):
        if not E621_API or not E621_LOGIN:
            await ctx.send("e621 не настроен (нет E621_API / E621_LOGIN в configs.env)")
            return

        await ctx.defer()
        params = {
            "api_key": E621_API,
            "login": E621_LOGIN,
            "limit": 1,
        }
        if tags.strip():
            params["tags"] = tags.strip()

        try:
            data = await api.get_json(
                f"{E621}/posts/random.json",
                params=params,
                headers={"User-Agent": "discordBot/2.0 (by Re_Sea1k)"},
            )
        except ApiError as e:
            await ctx.send(f"e621: {e}")
            return

        if not isinstance(data, dict):
            await ctx.send("e621 вернул неожиданный ответ")
            return

        post = data.get("post") or {}
        file_url = (post.get("file") or {}).get("url")
        if not file_url:
            await ctx.send("у поста нет прямой ссылки на файл")
            return

        rating = post.get("rating", "?")
        tags_str = " ".join(post.get("tags", {}).get("general", [])[:10])
        embed = discord.Embed(
            title="e621",
            description=f"rating: **{rating}**",
            color=0xF1C40F,
        )
        if tags_str:
            embed.add_field(name="Теги", value=tags_str, inline=False)
        embed.set_image(url=file_url)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Furry(bot))