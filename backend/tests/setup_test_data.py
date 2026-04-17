import asyncio
import uuid
from sqlalchemy import text
from shared.database import engine, AsyncSessionLocal

async def setup():
    """Seed a test zone into the database."""
    print("⏳ Seeding test zone...")
    async with AsyncSessionLocal() as session:
        try:
            # Check if zones table exists and has data
            result = await session.execute(text("SELECT id FROM zones WHERE name = 'koramangala' LIMIT 1"))
            zone = result.fetchone()
            
            if not zone:
                zone_id = uuid.uuid4()
                await session.execute(text("""
                    INSERT INTO zones (id, name, city, flood_risk_score, traffic_risk_score, store_risk_score, composite_risk_score)
                    VALUES (:id, 'koramangala', 'bengaluru', 72, 65, 50, 68)
                """), {"id": zone_id})
                await session.commit()
                print(f"✅ Created test zone: koramangala (ID: {zone_id})")
            else:
                print(f"✅ Zone 'koramangala' already exists (ID: {zone[0]})")
        except Exception as e:
            print(f"❌ Error seeding zone: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(setup())
