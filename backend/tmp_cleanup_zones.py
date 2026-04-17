import asyncio
import os
import sys

# 1. Ensure env is loaded (usually via .env or shell)
# No hardcoded overrides here to allow production/AWS use.

# 2. Add path and imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy import text
from shared.database import AsyncSessionLocal

async def cleanup():
    async with AsyncSessionLocal() as session:
        # Get duplicates
        res = await session.execute(text("SELECT lower(name), lower(city), array_agg(id) FROM zones GROUP BY 1, 2 HAVING count(*) > 1"))
        rows = res.fetchall()
        
        if not rows:
            print("✨ No duplicates found.")
            return

        for name, city, ids in rows:
            survivor = ids[0]
            others = ids[1:]
            print(f"🔩 Merging '{name}' into {survivor}")
            
            # Update all potential FK tables
            for table in ["riders", "rider_risk_profiles", "rider_zone_baselines", "disruption_events", "weather_data", "platform_snapshots", "micro_slots"]:
                try:
                    await session.execute(
                        text(f"UPDATE {table} SET zone_id = :survivor WHERE zone_id IN :others"),
                        {"survivor": survivor, "others": tuple(others)}
                    )
                except Exception:
                    pass
            
            # Commit re-assignments BEFORE deleting zones
            await session.commit()
            
            # Now delete the redundant zones
            await session.execute(
                text("DELETE FROM zones WHERE id IN :others"),
                {"others": tuple(others)}
            )
            await session.commit()
            
    print("✅ Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup())
