"""
Seed micro_slots table with risk data for demo zones.
Run: python backend/policy_service/seed_zones.py
"""

import asyncio
from datetime import time

from sqlalchemy import select

try:
    from backend.policy_service.models import MicroSlot
    from backend.rider_service.models import Zone
    from backend.shared.database import AsyncSessionLocal
except ImportError:
    from policy_service.models import MicroSlot
    from rider_service.models import Zone
    from shared.database import AsyncSessionLocal


ZONE_SLOTS = [
    ("koramangala", 0, time(18, 0), time(21, 0), 450, 0.72, 80, 75, 65),
    ("koramangala", 0, time(21, 0), time(23, 0), 300, 0.68, 75, 70, 60),
    ("koramangala", 5, time(8, 0), time(11, 0), 380, 0.65, 70, 65, 55),
    ("indiranagar", 0, time(18, 0), time(21, 0), 420, 0.70, 75, 72, 62),
    ("indiranagar", 0, time(21, 0), time(23, 0), 280, 0.65, 70, 68, 58),
    ("whitefield", 0, time(18, 0), time(21, 0), 350, 0.42, 45, 50, 40),
    ("whitefield", 0, time(21, 0), time(23, 0), 220, 0.38, 40, 45, 35),
    ("pune_suburb", 0, time(18, 0), time(21, 0), 300, 0.20, 20, 25, 15),
    ("pune_suburb", 0, time(21, 0), time(23, 0), 180, 0.18, 18, 22, 12),
    ("gachibowli", 0, time(18, 0), time(21, 0), 430, 0.75, 85, 70, 60),
    ("gachibowli", 0, time(21, 0), time(23, 0), 290, 0.70, 80, 65, 55),
]


async def seed():
    print("Seeding micro_slots table...")

    async with AsyncSessionLocal() as db:
        seeded = 0

        for (
            zone_name,
            day_of_week,
            time_start,
            time_end,
            expected_earnings,
            disruption_prob,
            weather_risk,
            traffic_risk,
            store_risk,
        ) in ZONE_SLOTS:
            zone_result = await db.execute(
                select(Zone).where(Zone.name.ilike(zone_name))
            )
            zone = zone_result.scalar_one_or_none()
            if zone is None:
                print(f"Skipping unknown zone: {zone_name}")
                continue

            existing_result = await db.execute(
                select(MicroSlot).where(
                    MicroSlot.zone_id == zone.id,
                    MicroSlot.day_of_week == day_of_week,
                    MicroSlot.time_start == time_start,
                    MicroSlot.time_end == time_end,
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing is not None:
                existing.expected_earnings = expected_earnings
                existing.disruption_probability = disruption_prob
                existing.weather_risk_score = weather_risk
                existing.traffic_risk_score = traffic_risk
                existing.store_risk_score = store_risk
            else:
                db.add(
                    MicroSlot(
                        zone_id=zone.id,
                        day_of_week=day_of_week,
                        time_start=time_start,
                        time_end=time_end,
                        expected_earnings=expected_earnings,
                        disruption_probability=disruption_prob,
                        weather_risk_score=weather_risk,
                        traffic_risk_score=traffic_risk,
                        store_risk_score=store_risk,
                    )
                )
            seeded += 1

        await db.commit()

    print(f"Seeded {seeded} micro_slot records")
    print("High risk zones: koramangala, indiranagar, gachibowli")
    print("Low risk zones: pune_suburb, whitefield")


if __name__ == "__main__":
    asyncio.run(seed())
