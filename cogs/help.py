import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View


class HelpView(View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=180)
        self.bot = bot

    def _make_cog_embed(self, cog_name: str) -> discord.Embed | None:
        cog = self.bot.get_cog(cog_name)
        if not cog:
            return None
        embed = discord.Embed(title=f"{cog_name}", color=0x3498DB)
        for cmd in cog.get_commands():
            if cmd.hidden:
                continue
            desc = cmd.description or cmd.help or "—"
            embed.add_field(
                name=f"`{cmd.qualified_name}`",
                value=desc,
                inline=False,
            )
        return embed

    @discord.ui.button(label="Dota", style=discord.ButtonStyle.blurple)
    async def dota_btn(self, interaction: discord.Interaction, _: Button):
        embed = self._make_cog_embed("Dota")
        if embed:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("ког Dota не загружен", ephemeral=True)

    @discord.ui.button(label="Развлечения", style=discord.ButtonStyle.green)
    async def fun_btn(self, interaction: discord.Interaction, _: Button):
        embed = self._make_cog_embed("Furry")
        if embed:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("ког Furry не загружен", ephemeral=True)

    @discord.ui.button(label="Админ", style=discord.ButtonStyle.red)
    async def admin_btn(self, interaction: discord.Interaction, _: Button):
        embed = self._make_cog_embed("Admin")
        if embed:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("ког Admin не загружен", ephemeral=True)


class Help(commands.Cog):
    """Справка по командам."""

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

        # --- справка по конкретной команде ---
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
            await ctx.send(embed=embed)
            return

        # --- общая справка ---
        embed = discord.Embed(
            title="📖 Справка",
            description=(
                f"Префикс: `{prefix}` (или slash-команды `/...`)\n"
                f"Всего команд: **{len([c for c in self.bot.commands if not c.hidden])}**\n\n"
                "Нажми кнопку ниже, чтобы посмотреть категорию.\n"
                f"Подробнее: `{prefix}help <команда>`"
            ),
            color=0x9B59B6,
        )

        # краткая сводка по когам
        for cog_name in ("Dota", "Furry", "Admin"):
            cog = self.bot.get_cog(cog_name)
            if not cog:
                continue
            names = [f"`{c.name}`" for c in cog.get_commands() if not c.hidden]
            if names:
                embed.add_field(name=cog_name, value=" ".join(names), inline=False)

        embed.set_footer(text="Кнопки ниже — подробная справка по категориям")
        await ctx.send(embed=embed, view=HelpView(self.bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))