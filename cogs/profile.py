import discord
from discord.ext import commands

from api import ApiError, api
from config import OPENDOTA
from utils import kda_color


class Profile(commands.Cog):
    """Профиль игрока и сравнение (без MMR)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _fetch_player(self, account_id: int) -> dict:
        return await api.get_json(f"{OPENDOTA}/players/{account_id}")

    @commands.hybrid_command(name="profile", description="Профиль игрока Dota 2 (без MMR)")
    async def profile_cmd(self, ctx: commands.Context, account_id: int):
        await ctx.defer()
        try:
            data = await self._fetch_player(account_id)
        except ApiError as e:
            await ctx.send(f"ошибка API: {e}")
            return

        profile = data.get("profile") or {}
        name = profile.get("personaname") or f"Игрок {account_id}"
        avatar = profile.get("avatarfull")

        embed = discord.Embed(title=name, color=0x9B59B6)
        if avatar:
            embed.set_thumbnail(url=avatar)

        embed.add_field(name="Steam ID", value=str(account_id), inline=True)
        embed.add_field(name="Страна", value=profile.get("loccountrycode") or "—", inline=True)

        try:
            wl = await api.get_json(f"{OPENDOTA}/players/{account_id}/wl")
            win = wl.get("win", 0)
            lose = wl.get("lose", 0)
            total = win + lose
            wr = f"{win / total * 100:.1f}%" if total else "—"
            embed.add_field(name="Победы / Поражения", value=f"{win} / {lose} ({wr})", inline=False)
        except ApiError:
            embed.add_field(name="Победы / Поражения", value="нет данных", inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="compare", description="Сравнить двух игроков (без MMR)")
    async def compare_cmd(self, ctx: commands.Context, account_id_1: int, account_id_2: int):
        await ctx.defer()
        try:
            p1 = await self._fetch_player(account_id_1)
            p2 = await self._fetch_player(account_id_2)
            wl1 = await api.get_json(f"{OPENDOTA}/players/{account_id_1}/wl")
            wl2 = await api.get_json(f"{OPENDOTA}/players/{account_id_2}/wl")
        except ApiError as e:
            await ctx.send(f"ошибка API: {e}")
            return

        def _stats(p, wl):
            name = (p.get("profile") or {}).get("personaname") or "?"
            win = wl.get("win", 0)
            lose = wl.get("lose", 0)
            total = win + lose
            wr = f"{win / total * 100:.1f}%" if total else "—"
            return name, win, lose, wr

        n1, w1, l1, wr1 = _stats(p1, wl1)
        n2, w2, l2, wr2 = _stats(p2, wl2)

        try:
            r1 = float(wr1.strip("%")) if wr1 != "—" else 0
            r2 = float(wr2.strip("%")) if wr2 != "—" else 0
        except ValueError:
            r1 = r2 = 0
        color = 0x2ECC71 if r1 > r2 else (0xE74C3C if r2 > r1 else 0xF1C40F)

        embed = discord.Embed(title="Сравнение игроков", color=color)
        embed.add_field(name="Игрок 1", value=n1, inline=True)
        embed.add_field(name="Игрок 2", value=n2, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Победы", value=str(w1), inline=True)
        embed.add_field(name="Победы", value=str(w2), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Поражения", value=str(l1), inline=True)
        embed.add_field(name="Поражения", value=str(l2), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Винрейт", value=wr1, inline=True)
        embed.add_field(name="Винрейт", value=wr2, inline=True)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))