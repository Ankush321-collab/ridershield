"""
Seed script — Create active demo policies for all seeded riders.

Run:  python -m seeds.seed_policies
      (from backend/ directory, AFTER seed_riders.py)
"""

import asyncio
import uuid
from datetime import datetime

from sqlalchemy import text

from policy_service.models import get_current_iso_week, get_week_expiry
from shared.database import AsyncSessionLocal

DEFAULT_SLOTS = ["18:00-21:00", "21:00-23:00"]
DEFAULT_PREMIUM = 99
DEFAULT_COVERAGE_LIMIT = 5000
DEFAULT_COVERAGE_PCT = 80


async def seed():
    print("Seeding demo policies...")

    current_week = get_current_iso_week()
    expiry = get_week_expiry()

    async with AsyncSessionLocal() as session:
        riders_result = await session.execute(text("SELECT id FROM riders ORDER BY created_at"))
        riders = [str(row[0]) for row in riders_result.fetchall()]

        if not riders:
            print("No riders found! Run seed_riders.py first.")
            return

        created = 0
        skipped = 0

        for rider_id in riders:
            existing = await session.execute(
                text(
                    """
                    SELECT 1
                    FROM policies
                    WHERE rider_id = :rider_id AND week = :week
                    """
                ),
                {"rider_id": rider_id, "week": current_week},
            )

            if existing.first():
                skipped += 1
                continue

            await session.execute(
                text(
                    """
                    INSERT INTO policies (
                        id,
                        rider_id,
                        plan_tier,
                        week,
                        premium,
                        coverage_limit,
                        coverage_pct,
                        coverage_used,
                        status,
                        slots_covered,
                        created_at,
                        expires_at
                    )
                    VALUES (
                        :id,
                        :rider_id,
                        'balanced',
                        :week,
                        :premium,
                        :coverage_limit,
                        :coverage_pct,
                        0,
                        'active',
                        ARRAY['18:00-21:00', '21:00-23:00'],
                        :created_at,
                        :expires_at
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "rider_id": rider_id,
                    "week": current_week,
                    "premium": DEFAULT_PREMIUM,
                    "coverage_limit": DEFAULT_COVERAGE_LIMIT,
                    "coverage_pct": DEFAULT_COVERAGE_PCT,
                    "created_at": datetime.utcnow(),
                    "expires_at": expiry,
                },
            )
            created += 1

        await session.commit()

    print(
        f"Seeded {created} demo policies for week {current_week}. "
        f"Skipped {skipped} existing policies. Slots: {', '.join(DEFAULT_SLOTS)}"
    )


if __name__ == "__main__":
    asyncio.run(seed())
