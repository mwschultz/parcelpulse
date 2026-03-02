from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cache import ApiUsage


async def check_and_increment(service: str, cap: int, db: AsyncSession) -> bool:
    """Returns True if under cap (and increments the counter). False if cap exceeded."""
    today = date.today().isoformat()

    result = await db.execute(
        select(ApiUsage).where(ApiUsage.service == service, ApiUsage.date == today)
    )
    row = result.scalar_one_or_none()

    if row is None:
        db.add(ApiUsage(service=service, calls_today=1, date=today))
        await db.commit()
        return True

    if row.calls_today >= cap:
        return False

    row.calls_today += 1
    await db.commit()
    return True
