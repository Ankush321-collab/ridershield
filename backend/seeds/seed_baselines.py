"""
Seed script — Generate earnings baselines for all seeded riders.
Creates 2 slots × 4 weeks of historical data per rider.

Run:  python -m seeds.seed_baselines
      (from backend/ directory, AFTER seed_riders.py)
"""

import asyncio
import uuid
import random
from datetime import datetime, timedelta
from sqlalchemy import text
from shared.database import AsyncSessionLocal

SLOTS = ["18:00-21:00", "21:00-23:00"]

# Earnings ranges per slot (₹ per shift)
SLOT_EARNINGS = {
    "18:00-21:00": (280, 420),   # evening rush
    "21:00-23:00": (180, 300),   # late-night
}

SLOT_ORDERS = {
    "18:00-21:00": (8, 16),
    "21:00-23:00": (5, 10),
}


async def seed():
    print("📊 Seeding earnings baselines...")
    random.seed(42)  # reproducible demo data

    async with AsyncSessionLocal() as session:
        # Get all riders with their zone IDs
        result = await session.execute(text("SELECT id, zone_id FROM riders"))
        riders = [(str(row[0]), str(row[1])) for row in result.fetchall()]

        if not riders:
            print("❌ No riders found! Run seed_riders.py first.")
            return

        # Generate last 4 week labels
        now = datetime.now()
        weeks = []
        for i in range(4):
            d = now - timedelta(weeks=i)
            weeks.append(d.strftime("%Y-W%V"))

        count = 0
        for rider_id, zone_id in riders:
            for week in weeks:
                for slot in SLOTS:
                    lo_earn, hi_earn = SLOT_EARNINGS[slot]
                    lo_ord, hi_ord = SLOT_ORDERS[slot]

                    avg_earnings = random.randint(lo_earn, hi_earn)
                    avg_orders = random.randint(lo_ord, hi_ord)
                    disruptions = random.choices([0, 0, 0, 1, 1, 2], k=1)[0]  # mostly 0

                    await session.execute(
                        text("""
                            INSERT INTO rider_zone_baselines
                                (id, rider_id, zone_id, week, slot_time, avg_earnings, avg_orders, disruption_count)
                            VALUES
                                (:id, :rider_id, :zone_id, :week, :slot, :earn, :orders, :disruptions)
                            ON CONFLICT (rider_id, zone_id, week, slot_time) DO NOTHING
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "rider_id": rider_id,
                            "zone_id": zone_id,
                            "week": week,
                            "slot": slot,
                            "earn": avg_earnings,
                            "orders": avg_orders,
                            "disruptions": disruptions,
                        },
                    )
                    count += 1

        await session.commit()
    print(f"✅ Seeded {count} baseline records ({len(riders)} riders × {len(weeks)} weeks × {len(SLOTS)} slots).")


if __name__ == "__main__":
    asyncio.run(seed())
