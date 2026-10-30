import sqlite3 as sq
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, button
import os
from dotenv import load_dotenv
import aiohttp
import asyncio
import io
from PIL import Image, ImageDraw, ImageFont

load_dotenv(dotenv_path='configs.env')
botToken = os.getenv('BOT_TOKEN')
e621api = os.getenv('E621_API')
e621login = os.getenv('E621_LOGIN')

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

con = sq.connect('database.db')
cur = con.cursor()
print('--------------')
print('connected to database')

client = commands.Bot(command_prefix='d!', intents=intents, help_command=None)

STEAM_MEDIA_PREFIX = "https://media.steampowered.com"
ITEM_ICON_SIZE = 64
ITEM_ICON_PADDING = 8
LABEL_LINE_HEIGHT = 14
LABEL_MAX_LINES = 2
LABEL_BLOCK_HEIGHT = LABEL_LINE_HEIGHT * LABEL_MAX_LINES  # 28 px под две строки


# ---------- HTTP ----------
async def fetch_json(url: str, headers: dict | None = None, params: dict | None = None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = None
            return resp.status, data


async def download_bytes(session: aiohttp.ClientSession, url: str) -> bytes | None:
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
    except Exception:
        pass
    return None


# ---------- Шрифт ----------
def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "DejaVuSans.ttf",
        "arial.ttf",
        "Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _measure(font, text: str) -> float:
    try:
        return font.getlength(text)
    except AttributeError:
        return font.getsize(text)[0]


def _wrap_two_lines(text: str, font, max_width: int) -> list[str]:
    """
    Разбивает текст максимум на 2 строки по ширине.
    Если не влезает — обрезает вторую строку с '...'.
    """
    if _measure(font, text) <= max_width:
        return [text]

    words = text.split()
    if not words:
        return [""]

    # подбираем первое слово/слова, которые влезут в первую строку
    line1 = ""
    idx = 0
    for i, w in enumerate(words):
        candidate = (line1 + " " + w).strip()
        if _measure(font, candidate) <= max_width:
            line1 = candidate
            idx = i + 1
        else:
            break

    # остальное — вторая строка
    rest = " ".join(words[idx:]).strip()

    # если первая строка пустая (одно длинное слово) — режем по символам
    if not line1:
        line1 = ""
        for ch in text:
            if _measure(font, line1 + ch) > max_width:
                break
            line1 += ch
        rest = text[len(line1):].strip()

    if _measure(font, rest) > max_width:
        ell = "..."
        while rest and _measure(font, rest + ell) > max_width:
            rest = rest[:-1]
        rest = rest + ell if rest else ""

    return [line1, rest]


def _draw_centered_line(draw, text: str, font, center_x: int, y: int, fill):
    if not text:
        return
    w = _measure(font, text)
    draw.text((center_x - w / 2, y), text, font=font, fill=fill)


# ---------- Pillow: билд в 2 ряда (основные + backpack), подписи в 2 строки ----------
async def build_items_image(main_items: list[tuple[str, str]],
                            backpack_items: list[tuple[str, str]]) -> io.BytesIO | None:
    """
    main_items: [(name, url), ...] — 6 слотов
    backpack_items: [(name, url), ...] — 3 слота, подписи с префиксом [bp]
    Возвращает BytesIO или None.
    """
    all_items = main_items + backpack_items
    if not all_items:
        return None

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *(download_bytes(session, url) for _, url in all_items),
            return_exceptions=True,
        )

    font = _load_font(11)
    text_fill = (255, 255, 255, 255)

    prepared_main: list[tuple[Image.Image, str]] = []
    prepared_bp: list[tuple[Image.Image, str]] = []

    for (name, _url), raw in zip(all_items, results):
        if isinstance(raw, Exception) or not raw:
            img = Image.new("RGBA", (ITEM_ICON_SIZE, ITEM_ICON_SIZE), (40, 40, 40, 255))
        else:
            try:
                img = Image.open(io.BytesIO(raw)).convert("RGBA")
                img = img.resize((ITEM_ICON_SIZE, ITEM_ICON_SIZE), Image.LANCZOS)
            except Exception:
                img = Image.new("RGBA", (ITEM_ICON_SIZE, ITEM_ICON_SIZE), (40, 40, 40, 255))

        if len(prepared_main) < len(main_items):
            prepared_main.append((img, name))
        else:
            prepared_bp.append((img, f"[bp] {name}"))

    # сколько колонок и рядов
    cols = max(len(prepared_main), len(prepared_bp), 1)
    rows = 2 if prepared_bp else 1

    cell_w = ITEM_ICON_SIZE
    cell_h = LABEL_BLOCK_HEIGHT + ITEM_ICON_SIZE

    width = cols * cell_w + (cols + 1) * ITEM_ICON_PADDING
    height = rows * cell_h + (rows + 1) * ITEM_ICON_PADDING

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    def draw_row(items, row_index):
        y_top = ITEM_ICON_PADDING + row_index * (cell_h + ITEM_ICON_PADDING)
        x = ITEM_ICON_PADDING
        for icon, name in items:
            center_x = x + ITEM_ICON_SIZE / 2

            # подпись в 2 строки
            lines = _wrap_two_lines(name, font, ITEM_ICON_SIZE + 8)
            ly = y_top
            for line in lines[:LABEL_MAX_LINES]:
                _draw_centered_line(draw, line, font, center_x, ly, text_fill)
                ly += LABEL_LINE_HEIGHT

            # иконка
            icon_y = y_top + LABEL_BLOCK_HEIGHT
            canvas.paste(icon, (x, icon_y), icon)

            x += ITEM_ICON_SIZE + ITEM_ICON_PADDING

    draw_row(prepared_main, 0)
    if prepared_bp:
        draw_row(prepared_bp, 1)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---------- Утилиты ----------
def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hour, minutes, seconds)


# ---------- Кэш констант ----------
_heroes_cache = None
_items_cache = None


async def get_heroes_map():
    global _heroes_cache
    if _heroes_cache is None:
        status, heroes = await fetch_json('https://api.opendota.com/api/heroes')
        if status == 200 and isinstance(heroes, list):
            _heroes_cache = {h['id']: h for h in heroes if 'id' in h}
    return _heroes_cache or {}


async def get_items_map():
    global _items_cache
    if _items_cache is None:
        status, items = await fetch_json('https://api.opendota.com/api/constants/items')
        if status == 200 and isinstance(items, dict):
            _items_cache = {}
            for key, item in items.items():
                if isinstance(item, dict) and 'id' in item:
                    _items_cache[item['id']] = {
                        'name': item.get('dname') or key,
                        'img': item.get('img'),
                    }
    return _items_cache or {}


# ---------- Меню игроков ----------
class PlayersView(View):
    def __init__(self, match_id: int, players: list, heroes_map: dict):
        super().__init__(timeout=180)
        self.match_id = match_id
        self.players = players
        self.heroes_map = heroes_map
        self._build_buttons()

    def _build_buttons(self):
        for idx, p in enumerate(self.players):
            hero = self.heroes_map.get(p.get('hero_id'))
            hero_name = hero['localized_name'] if hero else f"#{p.get('hero_id')}"
            name = p.get('name') or p.get('personaname') or f"Игрок {idx + 1}"
            label = f"{name} ({hero_name})"
            if len(label) > 80:
                label = label[:77] + "..."
            btn = Button(label=label, style=discord.ButtonStyle.secondary)
            btn.callback = self._make_callback(idx)
            self.add_item(btn)

    def _make_callback(self, idx: int):
        async def callback(interaction: discord.Interaction):
            player = self.players[idx]
            heroes_map = self.heroes_map
            items_map = await get_items_map()

            hero = heroes_map.get(player.get('hero_id'))
            hero_name = hero['localized_name'] if hero else f"Герой #{player.get('hero_id')}"
            player_name = player.get('name') or player.get('personaname') or f"Игрок {idx + 1}"

            k = player.get('kills', 0)
            d = player.get('deaths', 0)
            a = player.get('assists', 0)
            gpm = player.get('gold_per_min', 0)
            hero_damage = player.get('hero_damage', 0)
            hero_healing = player.get('hero_healing', 0)

            embed = discord.Embed(
                title=f"{player_name} — {hero_name}",
                color=0x9b59b6,
            )
            embed.add_field(name="KDA", value=f"{k}/{d}/{a}", inline=True)
            embed.add_field(name="GPM", value=str(gpm), inline=True)
            embed.add_field(name="Нанесено урона", value=str(hero_damage), inline=True)
            embed.add_field(name="Лечение", value=str(hero_healing), inline=True)

            # ---- Билд (только картинка) ----
            main_items: list[tuple[str, str]] = []
            bp_items: list[tuple[str, str]] = []

            for slot in range(6):
                item_id = player.get(f'item_{slot}', 0)
                if item_id:
                    info = items_map.get(item_id, {'name': f"Предмет #{item_id}", 'img': None})
                    if info.get('img'):
                        main_items.append((info['name'], STEAM_MEDIA_PREFIX + info['img']))
                    else:
                        main_items.append((info['name'], ""))

            for slot in range(3):
                item_id = player.get(f'backpack_{slot}', 0)
                if item_id:
                    info = items_map.get(item_id, {'name': f"Предмет #{item_id}", 'img': None})
                    if info.get('img'):
                        bp_items.append((info['name'], STEAM_MEDIA_PREFIX + info['img']))
                    else:
                        bp_items.append((info['name'], ""))

            build_image = await build_items_image(main_items, bp_items)

            files = []
            if build_image is not None:
                files.append(discord.File(build_image, filename="build.png"))
                embed.set_image(url="attachment://build.png")

            await interaction.response.send_message(
                embed=embed,
                files=files if files else discord.utils.MISSING,
                ephemeral=True,
            )

        return callback


# ---------- Основное View ----------
class MyView(View):
    def __init__(self, match_id: int):
        super().__init__()
        self.match_id = match_id

    @button(label='Пики/Баны', style=discord.ButtonStyle.blurple)
    async def button_picks_bans(self, interaction: discord.Interaction, button: discord.ui.Button):
        status, reqs = await fetch_json(f'https://api.opendota.com/api/matches/{self.match_id}')
        if status != 200 or not isinstance(reqs, dict):
            await interaction.response.send_message('не удалось получить данные матча', ephemeral=True)
            return

        heroes_map = await get_heroes_map()
        picks_bans = reqs.get('picks_bans') or []
        if not picks_bans:
            await interaction.response.send_message('в этом матче нет данных о пиках/банах', ephemeral=True)
            return

        embed = discord.Embed(title="Пики/баны", color=0x0000ff)
        for pb in picks_bans:
            hero = heroes_map.get(pb.get('hero_id'))
            hero_name = hero['localized_name'] if hero else f"герой #{pb.get('hero_id')}"
            action = 'пик' if pb.get('is_pick') else 'бан'
            side = 'света' if pb.get('team') == 0 else 'тьмы'
            embed.add_field(name=f'{action} {side}', value=hero_name, inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @button(label='Игроки', style=discord.ButtonStyle.green)
    async def button_players(self, interaction: discord.Interaction, button: discord.ui.Button):
        status, reqs = await fetch_json(f'https://api.opendota.com/api/matches/{self.match_id}')
        if status != 200 or not isinstance(reqs, dict):
            await interaction.response.send_message('не удалось получить данные матча', ephemeral=True)
            return

        players = reqs.get('players') or []
        if not players:
            await interaction.response.send_message('в этом матче нет данных об игроках', ephemeral=True)
            return

        heroes_map = await get_heroes_map()
        view = PlayersView(self.match_id, players, heroes_map)

        lines = []
        for idx, p in enumerate(players):
            hero = heroes_map.get(p.get('hero_id'))
            hero_name = hero['localized_name'] if hero else f"#{p.get('hero_id')}"
            name = p.get('name') or p.get('personaname') or f"Игрок {idx + 1}"
            lines.append(f"**{name}** — {hero_name}")

        embed = discord.Embed(
            title="Игроки матча",
            description="\n".join(lines),
            color=0x2ecc71,
        )
        embed.set_footer(text="Нажми кнопку ниже, чтобы посмотреть детали игрока")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ---------- События и команды ----------
@client.event
async def on_ready():
    print(f'connected to discord as {client.user}')


@client.command(aliases=['getmatch', 'game', 'match', 'stats', 'matchstats', 'gamestats'])
async def __getmatch(ctx, match_id: int = None):
    if match_id is None:
        await ctx.send('правильный формат: d!match <айди матча>')
        return

    status, rq = await fetch_json(f'https://api.opendota.com/api/matches/{match_id}')
    if status != 200 or not isinstance(rq, dict) or 'radiant_win' not in rq:
        await ctx.send(f'матч `{match_id}` не найден или ещё не обработан OpenDota')
        return

    vict = 'света' if rq['radiant_win'] else 'тьмы'
    embed = discord.Embed(
        title=f"игра {match_id}",
        description=f"победа сил {vict}",
        color=0x00ff00,
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    embed.add_field(name="Длительность", value=convert(rq.get('duration', 0)), inline=True)
    embed.add_field(
        name="Счёт",
        value=f"{rq.get('radiant_score', 0)}:{rq.get('dire_score', 0)}",
        inline=True,
    )
    await ctx.send(embed=embed, view=MyView(match_id))


@client.command(aliases=['furry', 'getfurry', 'e621'])
async def __furry(ctx):
    headers = {'User-Agent': 'discordBot/1.0 (by Re_Sea1k)'}
    params = {'api_key': e621api, 'login': e621login}
    status, data = await fetch_json(
        'https://e621.net/posts/random.json',
        headers=headers,
        params=params,
    )

    if status != 200 or not isinstance(data, dict):
        await ctx.send('e621 не ответил (проверь api_key/login)')
        return

    post = data.get('post') or {}
    file_url = (post.get('file') or {}).get('url')
    if not file_url:
        await ctx.send('у поста нет прямой ссылки на файл')
        return

    await ctx.send(file_url)


client.run(token=botToken)