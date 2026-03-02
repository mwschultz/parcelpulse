import json
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cache import ApiCache


async def get_cached(db: AsyncSession, key: str) -> dict | None:
    result = await db.execute(
        select(ApiCache).where(ApiCache.cache_key == key)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at and row.expires_at < datetime.now(timezone.utc):
        await db.delete(row)
        await db.commit()
        return None
    return json.loads(row.response_json)


async def set_cached(
    db: AsyncSession,
    key: str,
    service: str,
    data: dict,
    expires_days: int = 30,
) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
    result = await db.execute(
        select(ApiCache).where(ApiCache.cache_key == key)
    )
    row = result.scalar_one_or_none()
    if row:
        row.response_json = json.dumps(data)
        row.expires_at = expires_at
    else:
        db.add(ApiCache(
            cache_key=key,
            service=service,
            response_json=json.dumps(data),
            expires_at=expires_at,
        ))
    await db.commit()
