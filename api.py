import asyncio
import logging
from typing import Any

import aiohttp

from config import USER_AGENT, OPENDOTA, CACHE_TTL_HEROES, CACHE_TTL_ITEMS, CACHE_TTL_MATCH

log = logging.getLogger("dota-bot.api")


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class TTLCache:
    def __init__(self, ttl: int):
        self.ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if not item:
            return None
        expires, value = item
        if asyncio.get_event_loop().time() > expires:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (asyncio.get_event_loop().time() + self.ttl, value)


heroes_cache = TTLCache(CACHE_TTL_HEROES)
items_cache = TTLCache(CACHE_TTL_ITEMS)
match_cache = TTLCache(CACHE_TTL_MATCH)


class ApiClient:
    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def start(self):
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": USER_AGENT},
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_json(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        retries: int = 2,
    ) -> Any:
        session = await self.start()
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", "2"))
                        log.warning("rate limit %s, sleep %ss", url, retry_after)
                        await asyncio.sleep(retry_after)
                        continue
                    if resp.status != 200:
                        raise ApiError(f"HTTP {resp.status} for {url}", status=resp.status)
                    try:
                        return await resp.json(content_type=None)
                    except Exception as e:
                        raise ApiError(f"invalid JSON from {url}: {e}")
            except aiohttp.ClientError as e:
                last_exc = e
                if attempt < retries:
                    await asyncio.sleep(1 + attempt)
                    continue
                raise ApiError(f"network error: {e}")
        raise ApiError(f"request failed: {last_exc}")

    async def get_bytes(self, url: str) -> bytes | None:
        try:
            session = await self.start()
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception as e:
            log.debug("get_bytes fail %s: %s", url, e)
        return None


api = ApiClient()


async def fetch_match(match_id: int) -> dict:
    cached = match_cache.get(f"match:{match_id}")
    if cached is not None:
        return cached
    data = await api.get_json(f"{OPENDOTA}/matches/{match_id}")
    if not isinstance(data, dict) or "radiant_win" not in data:
        raise ApiError(f"match {match_id} not found")
    match_cache.set(f"match:{match_id}", data)
    return data


async def fetch_heroes() -> dict[int, dict]:
    cached = heroes_cache.get("heroes")
    if cached is not None:
        return cached
    data = await api.get_json(f"{OPENDOTA}/heroes")
    if not isinstance(data, list):
        raise ApiError("heroes unavailable")
    result = {h["id"]: h for h in data if "id" in h}
    heroes_cache.set("heroes", result)
    return result


async def fetch_items() -> dict[int, dict]:
    cached = items_cache.get("items")
    if cached is not None:
        return cached
    data = await api.get_json(f"{OPENDOTA}/constants/items")
    if not isinstance(data, dict):
        raise ApiError("items unavailable")
    result = {}
    for key, item in data.items():
        if isinstance(item, dict) and "id" in item:
            result[item["id"]] = {
                "name": item.get("dname") or key,
                "img": item.get("img"),
            }
    items_cache.set("items", result)
    return result