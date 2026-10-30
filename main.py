import logging

import discord
from discord.ext import commands

from api import api
from config import BOT_TOKEN, LOG_LEVEL, PREFIX

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("dota-bot")


class DotaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=PREFIX, intents=intents, help_command=None)

    async def setup_hook(self):
        await api.start()
        for ext in (
            "cogs.dota",
            "cogs.furry",
            "cogs.admin",
            "cogs.help",
            "cogs.profile",
            "cogs.live",
            "cogs.daily",
            "cogs.fun",
        ):
            try:
                await self.load_extension(ext)
                log.info("loaded %s", ext)
            except Exception as e:
                log.exception("failed to load %s: %s", ext, e)
        try:
            synced = await self.tree.sync()
            log.info("synced %d slash commands", len(synced))
        except Exception as e:
            log.exception("slash sync failed: %s", e)

    async def on_ready(self):
        log.info("logged in as %s (id=%s)", self.user, self.user.id)

    async def close(self):
        await api.close()
        await super().close()


bot = DotaBot()


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"не хватает аргумента: `{error.param.name}`")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("неверный аргумент")
        return
    if isinstance(error, commands.CheckFailure):
        await ctx.send("нет доступа")
        return
    log.exception("command error", exc_info=error)
    await ctx.send("внутренняя ошибка, посмотри логи")


if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN не задан в configs.env")

bot.run(BOT_TOKEN)