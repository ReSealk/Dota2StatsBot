import logging

import discord
from discord.ext import commands
from discord.ui import Button, View, button

from api import ApiError, fetch_heroes, fetch_items, fetch_match
from config import STEAM_MEDIA
from images import build_build_image
from utils import fmt_duration, hero_icon_url, kda_color

log = logging.getLogger("dota-bot.dota")


class PlayersView(View):
    def __init__(self, players: list, heroes: dict[int, dict]):
        super().__init__(timeout=300)
        self.players = players
        self.heroes = heroes
        for idx, p in enumerate(players[:10]):
            hero = heroes.get(p.get("hero_id"))
            hero_name = hero["localized_name"] if hero else f"#{p.get('hero_id')}"
            name = p.get("name") or p.get("personaname") or f"Игрок {idx + 1}"
            label = f"{name} · {hero_name}"
            if len(label) > 80:
                label = label[:77] + "..."
            btn = Button(label=label, style=discord.ButtonStyle.secondary)
            btn.callback = self._callback(idx)
            self.add_item(btn)

    def _callback(self, idx: int):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            player = self.players[idx]
            items_map = await fetch_items()
            hero = self.heroes.get(player.get("hero_id"))

            hero_name = hero["localized_name"] if hero else f"Герой #{player.get('hero_id')}"
            player_name = player.get("name") or player.get("personaname") or f"Игрок {idx + 1}"
            k = player.get("kills", 0)
            d = player.get("deaths", 0)
            a = player.get("assists", 0)

            embed = discord.Embed(
                title=f"{player_name} — {hero_name}",
                color=kda_color(k, d, a),
            )
            icon = hero_icon_url(hero)
            if icon:
                embed.set_thumbnail(url=icon)

            side = "Свет" if player.get("isRadiant") else "Тьма"
            embed.add_field(name="Сторона", value=side, inline=True)
            embed.add_field(name="KDA", value=f"{k}/{d}/{a}", inline=True)
            embed.add_field(name="GPM", value=str(player.get("gold_per_min", 0)), inline=True)
            embed.add_field(name="XPM", value=str(player.get("xp_per_min", 0)), inline=True)
            embed.add_field(name="Урон", value=str(player.get("hero_damage", 0)), inline=True)
            embed.add_field(name="Лечение", value=str(player.get("hero_healing", 0)), inline=True)
            embed.add_field(name="LH/DN", value=f"{player.get('last_hits', 0)}/{player.get('denies', 0)}", inline=True)
            embed.add_field(name="Уровень", value=str(player.get("level", 0)), inline=True)
            embed.add_field(name="Нетворс", value=str(player.get("net_worth", 0)), inline=True)

            main_items: list[tuple[str, str]] = []
            bp_items: list[tuple[str, str]] = []
            for slot in range(6):
                item_id = player.get(f"item_{slot}", 0)
                if item_id:
                    info = items_map.get(item_id, {"name": f"#{item_id}", "img": None})
                    url = STEAM_MEDIA + info["img"] if info["img"] else ""
                    main_items.append((info["name"], url))
            for slot in range(3):
                item_id = player.get(f"backpack_{slot}", 0)
                if item_id:
                    info = items_map.get(item_id, {"name": f"#{item_id}", "img": None})
                    url = STEAM_MEDIA + info["img"] if info["img"] else ""
                    bp_items.append((info["name"], url))

            build_image = await build_build_image(main_items, bp_items)
            files = []
            if build_image:
                files.append(discord.File(build_image, filename="build.png"))
                embed.set_image(url="attachment://build.png")

            await interaction.followup.send(
                embed=embed,
                files=files if files else discord.utils.MISSING,
                ephemeral=True,
            )
        return callback


class MatchView(View):
    def __init__(self, match: dict, heroes: dict[int, dict]):
        super().__init__(timeout=300)
        self.match = match
        self.heroes = heroes

    @button(label="Пики/Баны", style=discord.ButtonStyle.blurple)
    async def picks_bans(self, interaction: discord.Interaction, _: Button):
        await interaction.response.defer(ephemeral=True)
        pb = self.match.get("picks_bans") or []
        if not pb:
            await interaction.followup.send("нет данных о пиках/банах", ephemeral=True)
            return

        radiant, dire = [], []
        for entry in pb:
            hero = self.heroes.get(entry.get("hero_id"))
            name = hero["localized_name"] if hero else f"#{entry.get('hero_id')}"
            tag = "🟢" if entry.get("is_pick") else "🔴"
            line = f"{tag} {name}"
            (radiant if entry.get("team") == 0 else dire).append(line)

        embed = discord.Embed(title="Пики/Баны", color=0x3498DB)
        embed.add_field(name="Свет 🟦", value="\n".join(radiant) or "—", inline=True)
        embed.add_field(name="Тьма 🟥", value="\n".join(dire) or "—", inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @button(label="Игроки", style=discord.ButtonStyle.green)
    async def players(self, interaction: discord.Interaction, _: Button):
        await interaction.response.defer(ephemeral=True)
        players = self.match.get("players") or []
        if not players:
            await interaction.followup.send("нет данных об игроках", ephemeral=True)
            return

        lines = []
        for idx, p in enumerate(players):
            hero = self.heroes.get(p.get("hero_id"))
            hero_name = hero["localized_name"] if hero else f"#{p.get('hero_id')}"
            name = p.get("name") or p.get("personaname") or f"Игрок {idx + 1}"
            side = "🟦" if p.get("isRadiant") else "🟥"
            lines.append(f"{side} **{name}** — {hero_name}")

        embed = discord.Embed(
            title="Игроки матча",
            description="\n".join(lines),
            color=0x2ECC71,
        )
        embed.set_footer(text="Кнопки ниже — детали по игроку")
        view = PlayersView(players, self.heroes)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class Dota(commands.Cog):
    """Команды Dota 2."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="match",
        aliases=["game", "stats"],
        description="Статистика матча Dota 2",
    )
    async def match_cmd(self, ctx: commands.Context, match_id: int):
        await ctx.defer()
        try:
            match = await fetch_match(match_id)
            heroes = await fetch_heroes()
        except ApiError as e:
            await ctx.send(f"ошибка API: {e}")
            return

        radiant_win = bool(match.get("radiant_win"))
        winner = "Свет" if radiant_win else "Тьма"
        color = 0x2ECC71 if radiant_win else 0xE74C3C

        embed = discord.Embed(
            title=f"Матч {match_id}",
            description=f"🏆 Победа: **{winner}**",
            color=color,
        )
        embed.add_field(name="Длительность", value=fmt_duration(match.get("duration", 0)), inline=True)
        embed.add_field(
            name="Счёт",
            value=f"{match.get('radiant_score', 0)} : {match.get('dire_score', 0)}",
            inline=True,
        )
        embed.add_field(name="Режим", value=str(match.get("game_mode", "—")), inline=True)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed, view=MatchView(match, heroes))

    @commands.hybrid_command(name="heroes", description="Список героев (кратко)")
    async def heroes_cmd(self, ctx: commands.Context):
        await ctx.defer()
        try:
            heroes = await fetch_heroes()
        except ApiError as e:
            await ctx.send(f"ошибка API: {e}")
            return
        names = sorted(h["localized_name"] for h in heroes.values())
        text = ", ".join(names)
        if len(text) > 1900:
            text = text[:1900] + "..."
        embed = discord.Embed(title="Герои", description=text, color=0x3498DB)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Dota(bot))