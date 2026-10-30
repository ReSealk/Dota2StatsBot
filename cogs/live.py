import discord
from discord.ext import commands

from api import ApiError, api
from config import OPENDOTA


class Live(commands.Cog):
    """Текущие профессиональные матчи."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="live", description="Текущие профессиональные матчи")
    async def live_cmd(self, ctx: commands.Context):
        await ctx.defer()
        try:
            data = await api.get_json(f"{OPENDOTA}/live")
        except ApiError as e:
            await ctx.send(f"ошибка API: {e}")
            return

        if not data:
            await ctx.send("сейчас нет активных матчей")
            return

        embed = discord.Embed(title="🔴 Live матчи", color=0xE74C3C)
        for m in data[:8]:
            radiant = m.get("team_name_radiant") or "Свет"
            dire = m.get("team_name_dire") or "Тьма"
            score = f"{m.get('radiant_score', 0)} : {m.get('dire_score', 0)}"
            timer = m.get("game_time", 0)
            mins, secs = divmod(timer, 60)
            league = m.get("league_name") or "—"
            embed.add_field(
                name=f"{radiant} vs {dire}",
                value=f"счёт `{score}` · `{mins}:{secs:02d}` · {league}",
                inline=False,
            )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Live(bot))