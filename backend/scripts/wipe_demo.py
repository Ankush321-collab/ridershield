"""
Cleanup script — Wipe all data (riders, policies, baselines) but keep zones.
"""
import asyncio
from sqlalchemy import text
from shared.database import AsyncSessionLocal

async def wipe():
    print("🧹 Wiping demo data (keeping zones)...")
    async with AsyncSessionLocal() as session:
        # Tables to clear in order (due to FK constraints)
        tables = [
            "rider_zone_baselines",
            "rider_risk_profiles",
            "policies",
            "riders"
        ]
        
        for table in tables:
            print(f"   Deleting from {table}...")
            await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            
        await session.commit()
    print("✅ System cleaned. Database is ready for real registrations.")

if __name__ == "__main__":
    asyncio.run(wipe())
