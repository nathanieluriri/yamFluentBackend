import asyncio
import json
import os
import redis

cache_db = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    username=os.getenv("REDIS_USERNAME"),
    password=os.getenv("REDIS_PASSWORD"),
   decode_responses=True
)

async def cache_get_json(key: str):
    value = await asyncio.to_thread(cache_db.get, key)
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None

async def cache_set_json(key: str, value: dict, ttl_seconds: int):
    payload = json.dumps(value)
    await asyncio.to_thread(cache_db.setex, key, ttl_seconds, payload)

async def cache_delete(key: str):
    await asyncio.to_thread(cache_db.delete, key)
