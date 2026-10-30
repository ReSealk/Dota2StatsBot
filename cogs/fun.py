import random

import discord
from discord.ext import commands

from api import ApiError, fetch_heroes

# Цитаты героев (можно расширять)
HERO_QUOTES = [
    ("Pudge", "Ah, fresh meat!"),
    ("Invoker", "You die, and I live. A fair trade."),
    ("Axe", "Axe is not amused."),
    ("Juggernaut", "The wheel turns."),
    ("Crystal Maiden", "I'm all warmed up."),
    ("Shadow Fiend", "You're no match for me."),
    ("Storm Spirit", "I'm the storm that's coming."),
    ("Lina", "Burn!"),
    ("Riki", "Stealth is my weapon."),
    ("Sniper", "Headshot!"),
]


class Fun(commands.Cog):
    """Развлечения: случайный герой, цитаты, roll."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="randomhero", description="Случайный герой Dota 2")
    async def randomhero_cmd(self, ctx: commands.Context):
        await ctx.defer()
        try:
            heroes = await fetch_heroes()
        except ApiError as e:
            await ctx.send(f"ошибка API: {e}")
            return
        hero = random.choice(list(heroes.values()))
        name = hero.get("localized_name", "?")
        img = hero.get("img")
        embed = discord.Embed(title=f"🎲 {name}", color=0x9B59B6)
        if img:
            embed.set_thumbnail(url=f"https://cdn.cloudflare.steamstatic.com{img}")
        roles = hero.get("roles", [])
        if roles:
            embed.add_field(name="Роли", value=", ".join(roles), inline=True)
        attr = hero.get("primary_attr", "")
        if attr:
            embed.add_field(name="Основной атрибут", value=attr, inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="quote", description="Случайная цитата героя Dota 2")
    async def quote_cmd(self, ctx: commands.Context):
        hero, line = random.choice(HERO_QUOTES)
        embed = discord.Embed(
            title=f"🎙️ {hero}",
            description=f"*{line}*",
            color=0xF1C40F,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="roll", description="Бросить кубик (по умолчанию 1–100)")
    async def roll_cmd(self, ctx: commands.Context, max_value: int = 100):
        if max_value < 2:
            max_value = 2
        result = random.randint(1, max_value)
        embed = discord.Embed(
            title="🎲 Бросок",
            description=f"Выпало **{result}** (1–{max_value})",
            color=0x2ECC71,
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))