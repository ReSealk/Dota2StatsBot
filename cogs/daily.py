import discord
from discord.ext import commands, tasks

from api import ApiError, api
from config import OPENDOTA


class Daily(commands.Cog):
    """Ежедневная сводка (раз в сутки в указанный канал)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_channel_id: int | None = None

    async def cog_load(self):
        self.daily_task.start()

    def cog_unload(self):
        self.daily_task.cancel()

    @tasks.loop(hours=24)
    async def daily_task(self):
        if not self.daily_channel_id:
            return
        channel = self.bot.get_channel(self.daily_channel_id)
        if not channel:
            return
        try:
            stats = await api.get_json(f"{OPENDOTA}/heroStats")
        except ApiError:
            return
        ranked = sorted(
            [s for s in stats if s.get("pub_pick", 0) > 100],
            key=lambda x: x.get("pub_win", 0) / max(x.get("pub_pick", 1), 1),
            reverse=True,
        )[:5]
        lines = []
        for s in ranked:
            name = s.get("localized_name", "?")
            wr = s.get("pub_win", 0) / max(s.get("pub_pick", 1), 1) * 100
            lines.append(f"**{name}** — {wr:.1f}%")
        embed = discord.Embed(
            title="📊 Топ-5 героев по винрейту за сутки",
            description="\n".join(lines) if lines else "нет данных",
            color=0x3498DB,
        )
        await channel.send(embed=embed)

    @commands.hybrid_command(name="dailyset", description="Установить канал для ежедневной сводки (админ)")
    @commands.has_permissions(administrator=True)
    async def dailyset_cmd(self, ctx: commands.Context, channel: discord.TextChannel):
        self.daily_channel_id = channel.id
        await ctx.send(f"ежедневная сводка будет отправляться в {channel.mention}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Daily(bot))