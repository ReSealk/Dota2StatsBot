import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View


# Человекочитаемые названия когов
COG_TITLES = {
    "Dota": "🎮 Dota 2",
    "Profile": "👤 Профиль и сравнение",
    "Live": "🔴 Live-матчи",
    "Daily": "📊 Ежедневная сводка",
    "Fun": "🎲 Развлечения",
    "Furry": "🦊 e621",
    "Admin": "🛠 Админ",
    "Help": "📖 Справка",
}


class CategoryButton(Button):
    def __init__(self, cog_name: str, bot: commands.Bot, label: str, style: discord.ButtonStyle):
        super().__init__(label=label, style=style)
        self.cog_name = cog_name
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        cog = self.bot.get_cog(self.cog_name)
        if not cog:
            await interaction.response.send_message(
                f"ког `{self.cog_name}` не загружен", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=COG_TITLES.get(self.cog_name, self.cog_name),
            color=0x3498DB,
        )
        cmds = [c for c in cog.get_commands() if not c.hidden]
        if not cmds:
            embed.description = "нет доступных команд"
        else:
            for cmd in cmds:
                desc = cmd.description or cmd.help or "—"
                aliases = f"\n*алиасы:* {', '.join(cmd.aliases)}" if cmd.aliases else ""
                embed.add_field(
                    name=f"`{cmd.qualified_name}`",
                    value=f"{desc}{aliases}",
                    inline=False,
                )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class HelpView(View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=180)
        # Порядок и стили кнопок
        specs = [
            ("Dota", "Dota", discord.ButtonStyle.blurple),
            ("Profile", "Профиль", discord.ButtonStyle.blurple),
            ("Live", "Live", discord.ButtonStyle.danger),
            ("Daily", "Сводка", discord.ButtonStyle.secondary),
            ("Fun", "Развлечения", discord.ButtonStyle.green),
            ("Furry", "e621", discord.ButtonStyle.secondary),
        ]
        for cog_name, label, style in specs:
            if bot.get_cog(cog_name):
                self.add_item(CategoryButton(cog_name, bot, label, style))


class Help(commands.Cog):
    """Справка по командам бота."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="help",
        description="Справка по командам бота",
        aliases=["h", "помощь"],
    )
    @app_commands.describe(command="Конкретная команда для подробной справки")
    async def help_cmd(self, ctx: commands.Context, *, command: str | None = None):
        prefix = ctx.prefix or "d!"

        # --- Справка по конкретной команде ---
        if command:
            cmd = self.bot.get_command(command)
            if not cmd:
                await ctx.send(f"команда `{command}` не найдена")
                return

            embed = discord.Embed(
                title=f"`{prefix}{cmd.qualified_name}`",
                description=cmd.description or cmd.help or "—",
                color=0x3498DB,
            )
            if cmd.aliases:
                embed.add_field(
                    name="Алиасы",
                    value=", ".join(f"`{a}`" for a in cmd.aliases),
                    inline=False,
                )
            if isinstance(cmd, commands.HybridCommand):
                embed.add_field(
                    name="Slash",
                    value=f"`/{cmd.qualified_name}` тоже работает",
                    inline=False,
                )
            usage = cmd.usage or f"{prefix}{cmd.qualified_name} {cmd.signature}".strip()
            embed.add_field(name="Использование", value=f"`{usage}`", inline=False)
            if cmd.cog_name:
                embed.set_footer(text=f"Категория: {COG_TITLES.get(cmd.cog_name, cmd.cog_name)}")
            await ctx.send(embed=embed)
            return

        # --- Общая справка ---
        visible_cmds = [c for c in self.bot.commands if not c.hidden]
        embed = discord.Embed(
            title="📖 Справка",
            description=(
                f"Префикс: `{prefix}` (или slash-команды `/...`)\n"
                f"Всего команд: **{len(visible_cmds)}**\n\n"
                "Нажми кнопку ниже, чтобы посмотреть категорию.\n"
                f"Подробнее по команде: `{prefix}help <команда>`"
            ),
            color=0x9B59B6,
        )

        # Краткая сводка по когам
        for cog_name in (
            "Dota",
            "Profile",
            "Live",
            "Daily",
            "Fun",
            "Furry",
            "Admin",
        ):
            cog = self.bot.get_cog(cog_name)
            if not cog:
                continue
            names = [f"`{c.name}`" for c in cog.get_commands() if not c.hidden]
            if names:
                embed.add_field(
                    name=COG_TITLES.get(cog_name, cog_name),
                    value=" ".join(names),
                    inline=False,
                )

        embed.set_footer(text="Кнопки ниже — подробная справка по категориям")
        await ctx.send(embed=embed, view=HelpView(self.bot))

    @help_cmd.autocomplete("command")
    async def _help_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        current = current.lower()
        return [
            app_commands.Choice(name=c.qualified_name, value=c.qualified_name)
            for c in self.bot.commands
            if not c.hidden and current in c.qualified_name.lower()
        ][:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))