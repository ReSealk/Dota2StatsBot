import logging
import time

import discord
from discord.ext import commands

from api import OPENDOTA, ApiError, api

log = logging.getLogger("dota-bot.admin")


class Admin(commands.Cog):
    """Админские команды."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._start = time.time()

    @commands.hybrid_command(name="ping", description="Проверка задержки")
    async def ping_cmd(self, ctx: commands.Context):
        ws = round(self.bot.latency * 1000)
        t0 = time.perf_counter()
        try:
            await api.get_json(f"{OPENDOTA}/heroes")
            http_ms = round((time.perf_counter() - t0) * 1000)
        except ApiError as e:
            http_ms = f"error: {e}"
        uptime = int(time.time() - self._start)
        h, rem = divmod(uptime, 3600)
        m, s = divmod(rem, 60)
        embed = discord.Embed(title="Pong", color=0x2ECC71)
        embed.add_field(name="WebSocket", value=f"{ws} ms", inline=True)
        embed.add_field(name="OpenDota", value=f"{http_ms} ms", inline=True)
        embed.add_field(name="Uptime", value=f"{h}:{m:02d}:{s:02d}", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cmd(self, ctx: commands.Context, cog: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await ctx.send(f"cog `{cog}` перезагружен")
        except Exception as e:
            await ctx.send(f"ошибка: {e}")

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_cmd(self, ctx: commands.Context):
        synced = await self.bot.tree.sync()
        await ctx.send(f"синхронизировано {len(synced)} slash-команд")


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))