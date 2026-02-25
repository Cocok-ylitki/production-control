import json
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, TypeVar

import redis.asyncio as aioredis
import redis as sync_redis

from src.core.config import get_settings

KEY_PREFIX = "production_control:"
STATISTICS_KEY = KEY_PREFIX + "statistics"
DASHBOARD_KEY = KEY_PREFIX + "dashboard_stats"
BATCHES_LIST_PREFIX = KEY_PREFIX + "batches_list:"
BATCH_DETAIL_PREFIX = KEY_PREFIX + "batch_detail:"
BATCH_STATISTICS_PREFIX = KEY_PREFIX + "batch_statistics:"

T = TypeVar("T")


def _get_redis_sync() -> sync_redis.Redis:
    settings = get_settings()
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


def set_cached_statistics(stats: dict[str, Any]) -> None:
    """Сохраняет статистику в Redis (sync, для Celery)."""
    r = _get_redis_sync()
    r.set(STATISTICS_KEY, json.dumps(stats), ex=3600)


def get_cached_statistics() -> dict[str, Any] | None:
    """Возвращает кэшированную статистику или None (sync)."""
    r = _get_redis_sync()
    data = r.get(STATISTICS_KEY)
    if data is None:
        return None
    return json.loads(data)


def invalidate_on_aggregation_sync(batch_id: int) -> None:
    """Инвалидация кэша при аггрегации (sync, для Celery)."""
    r = _get_redis_sync()
    r.delete(DASHBOARD_KEY)
    r.delete(f"{BATCH_DETAIL_PREFIX}{batch_id}")
    r.delete(f"{BATCH_STATISTICS_PREFIX}{batch_id}")



_async_redis: aioredis.Redis | None = None


async def get_redis_async() -> aioredis.Redis:
    global _async_redis
    if _async_redis is None:
        settings = get_settings()
        _async_redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _async_redis


def _full_key(prefix: str, *parts: Any) -> str:
    return prefix + ":".join(str(p) for p in parts)


async def cache_get(key: str) -> dict[str, Any] | list | None:
    """Читает значение из кэша. key без префикса — добавится KEY_PREFIX."""
    r = await get_redis_async()
    full_key = key if key.startswith(KEY_PREFIX) else KEY_PREFIX + key
    data = await r.get(full_key)
    if data is None:
        return None
    return json.loads(data)


async def cache_set(key: str, value: Any, ttl: int) -> None:
    """Записывает значение в кэш с TTL (секунды)."""
    r = await get_redis_async()
    full_key = key if key.startswith(KEY_PREFIX) else KEY_PREFIX + key
    await r.set(full_key, json.dumps(value, default=str), ex=ttl)


async def cache_delete(key: str) -> None:
    """Удаляет ключ."""
    r = await get_redis_async()
    full_key = key if key.startswith(KEY_PREFIX) else KEY_PREFIX + key
    await r.delete(full_key)


async def cache_delete_pattern(pattern: str) -> None:
    """Удаляет все ключи по паттерну (например batches_list:*)."""
    r = await get_redis_async()
    full_pattern = pattern if pattern.startswith(KEY_PREFIX) else KEY_PREFIX + pattern
    keys = []
    async for k in r.scan_iter(match=full_pattern):
        keys.append(k)
    if keys:
        await r.delete(*keys)




async def invalidate_dashboard() -> None:
    await cache_delete(DASHBOARD_KEY)


async def invalidate_batches_list() -> None:
    await cache_delete_pattern("batches_list:*")


async def invalidate_batch_detail(batch_id: int) -> None:
    await cache_delete(f"{BATCH_DETAIL_PREFIX}{batch_id}")


async def invalidate_batch_statistics(batch_id: int) -> None:
    await cache_delete(f"{BATCH_STATISTICS_PREFIX}{batch_id}")


async def invalidate_on_batch_change(batch_id: int | None = None) -> None:
    """При создании/обновлении партии."""
    await invalidate_dashboard()
    await invalidate_batches_list()
    if batch_id is not None:
        await invalidate_batch_detail(batch_id)
        await invalidate_batch_statistics(batch_id)


async def invalidate_on_aggregation(batch_id: int) -> None:
    """При аггрегации продукции."""
    await invalidate_dashboard()
    await invalidate_batch_detail(batch_id)
    await invalidate_batch_statistics(batch_id)



def cached(ttl: int, key_prefix: str):
    """
    Декоратор для async-функций. Ключ: key_prefix (без аргументов) или key_prefix:arg1:arg2:...
    Значение и TTL кэшируются в Redis. Результат должен быть JSON-serializable (dict, list).
    """

    def decorator(f: Callable[..., T]):
        @wraps(f)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if not args and not kwargs:
                key = KEY_PREFIX + key_prefix
            else:
                key_parts = [key_prefix] + [str(a) for a in args]
                for k in sorted(kwargs.keys()):
                    key_parts.append(f"{k}={kwargs[k]}")
                key = KEY_PREFIX + ":".join(key_parts)
            r = await get_redis_async()
            data = await r.get(key)
            if data is not None:
                return json.loads(data)
            result = await f(*args, **kwargs)
            to_store = result.model_dump() if hasattr(result, "model_dump") else result
            await r.set(key, json.dumps(to_store, default=str), ex=ttl)
            return result

        return wrapper

    return decorator
