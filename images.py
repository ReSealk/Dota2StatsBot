import asyncio
import io

from PIL import Image, ImageDraw, ImageFont

from api import api
from config import (
    ITEM_ICON_SIZE,
    ITEM_ICON_PADDING,
    LABEL_BLOCK_HEIGHT,
    LABEL_LINE_HEIGHT,
    LABEL_MAX_LINES,
)


def _load_font(size: int) -> ImageFont.ImageFont:
    for path in (
        "DejaVuSans.ttf",
        "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ):
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
    if _measure(font, text) <= max_width:
        return [text]
    words = text.split()
    line1, idx = "", 0
    for i, w in enumerate(words):
        candidate = (line1 + " " + w).strip()
        if _measure(font, candidate) <= max_width:
            line1, idx = candidate, i + 1
        else:
            break
    rest = " ".join(words[idx:]).strip()
    if not line1:
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


async def build_build_image(
    main_items: list[tuple[str, str]],
    bp_items: list[tuple[str, str]],
) -> io.BytesIO | None:
    all_items = main_items + bp_items
    if not all_items:
        return None

    raw_results = await asyncio.gather(
        *(api.get_bytes(url) if url else asyncio.sleep(0, result=None) for _, url in all_items),
        return_exceptions=True,
    )

    font = _load_font(11)
    fill = (255, 255, 255, 255)

    prepared_main: list[tuple[Image.Image, str]] = []
    prepared_bp: list[tuple[Image.Image, str]] = []

    for (name, _url), raw in zip(all_items, raw_results):
        if isinstance(raw, Exception) or not raw:
            icon = Image.new("RGBA", (ITEM_ICON_SIZE, ITEM_ICON_SIZE), (40, 40, 40, 255))
        else:
            try:
                icon = Image.open(io.BytesIO(raw)).convert("RGBA")
                icon = icon.resize((ITEM_ICON_SIZE, ITEM_ICON_SIZE), Image.LANCZOS)
            except Exception:
                icon = Image.new("RGBA", (ITEM_ICON_SIZE, ITEM_ICON_SIZE), (40, 40, 40, 255))
        if len(prepared_main) < len(main_items):
            prepared_main.append((icon, name))
        else:
            prepared_bp.append((icon, f"[bp] {name}"))

    cols = max(len(prepared_main), len(prepared_bp), 1)
    rows = 2 if prepared_bp else 1
    cell_h = LABEL_BLOCK_HEIGHT + ITEM_ICON_SIZE
    width = cols * ITEM_ICON_SIZE + (cols + 1) * ITEM_ICON_PADDING
    height = rows * cell_h + (rows + 1) * ITEM_ICON_PADDING

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    def draw_row(items, row_index):
        y_top = ITEM_ICON_PADDING + row_index * (cell_h + ITEM_ICON_PADDING)
        x = ITEM_ICON_PADDING
        for icon, name in items:
            cx = x + ITEM_ICON_SIZE / 2
            ly = y_top
            for line in _wrap_two_lines(name, font, ITEM_ICON_SIZE + 8)[:LABEL_MAX_LINES]:
                w = _measure(font, line)
                draw.text((cx - w / 2, ly), line, font=font, fill=fill)
                ly += LABEL_LINE_HEIGHT
            canvas.paste(icon, (x, y_top + LABEL_BLOCK_HEIGHT), icon)
            x += ITEM_ICON_SIZE + ITEM_ICON_PADDING

    draw_row(prepared_main, 0)
    if prepared_bp:
        draw_row(prepared_bp, 1)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf