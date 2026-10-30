from datetime import datetime, timezone

from config import STEAM_MEDIA


def fmt_duration(seconds: int) -> str:
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def kda_color(k: int, d: int, a: int) -> int:
    ratio = (k + a) / max(d, 1)
    if ratio >= 4:
        return 0x2ECC71
    if ratio >= 2:
        return 0xF1C40F
    if ratio >= 1:
        return 0xE67E22
    return 0xE74C3C


def hero_icon_url(hero: dict | None) -> str | None:
    if not hero:
        return None
    img = hero.get("img")
    if not img:
        return None
    return f"https://cdn.cloudflare.steamstatic.com{img}" if img.startswith("/") else img


def item_img_url(info: dict | None) -> str | None:
    if not info or not info.get("img"):
        return None
    return STEAM_MEDIA + info["img"]


def fmt_timestamp(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()