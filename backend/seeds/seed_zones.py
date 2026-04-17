"""
Seed script — Populate zones table with demo data.
4 cities × multiple zones = realistic delivery coverage.

Run:  python -m seeds.seed_zones
      (from backend/ directory)
"""

import asyncio
import uuid
from sqlalchemy import text
from shared.database import engine, AsyncSessionLocal

ZONES = [
    # ─── Bengaluru ─────────────────────────────────────
    {"name": "koramangala",    "city": "bengaluru", "flood_risk": 45, "traffic_risk": 78, "store_risk": 30, "composite": 72, "lat": 12.9352, "lon": 77.6245},
    {"name": "hsr_layout",     "city": "bengaluru", "flood_risk": 55, "traffic_risk": 65, "store_risk": 25, "composite": 65, "lat": 12.9116, "lon": 77.6389},
    {"name": "whitefield",     "city": "bengaluru", "flood_risk": 60, "traffic_risk": 82, "store_risk": 35, "composite": 78, "lat": 12.9698, "lon": 77.7500},
    {"name": "indiranagar",    "city": "bengaluru", "flood_risk": 40, "traffic_risk": 75, "store_risk": 20, "composite": 68, "lat": 12.9784, "lon": 77.6408},
    {"name": "electronic_city","city": "bengaluru", "flood_risk": 50, "traffic_risk": 70, "store_risk": 40, "composite": 70, "lat": 12.8399, "lon": 77.6770},

    # ─── Hyderabad ─────────────────────────────────────
    {"name": "gachibowli",     "city": "hyderabad", "flood_risk": 65, "traffic_risk": 60, "store_risk": 28, "composite": 65, "lat": 17.4401, "lon": 78.3489},
    {"name": "madhapur",       "city": "hyderabad", "flood_risk": 55, "traffic_risk": 72, "store_risk": 32, "composite": 68, "lat": 17.4486, "lon": 78.3908},
    {"name": "kondapur",       "city": "hyderabad", "flood_risk": 60, "traffic_risk": 68, "store_risk": 25, "composite": 66, "lat": 17.4599, "lon": 78.3525},
    {"name": "lb_nagar",       "city": "hyderabad", "flood_risk": 70, "traffic_risk": 58, "store_risk": 30, "composite": 62, "lat": 17.3457, "lon": 78.5522},

    # ─── Mumbai ────────────────────────────────────────
    {"name": "andheri",        "city": "mumbai", "flood_risk": 80, "traffic_risk": 85, "store_risk": 20, "composite": 82, "lat": 19.1136, "lon": 72.8697},
    {"name": "bandra",         "city": "mumbai", "flood_risk": 75, "traffic_risk": 88, "store_risk": 18, "composite": 80, "lat": 19.0596, "lon": 72.8295},
    {"name": "powai",          "city": "mumbai", "flood_risk": 70, "traffic_risk": 72, "store_risk": 22, "composite": 72, "lat": 19.1176, "lon": 72.9060},
    {"name": "malad",          "city": "mumbai", "flood_risk": 78, "traffic_risk": 76, "store_risk": 28, "composite": 76, "lat": 19.1874, "lon": 72.8484},

    # ─── Delhi NCR ─────────────────────────────────────
    {"name": "dwarka",         "city": "delhi", "flood_risk": 50, "traffic_risk": 80, "store_risk": 35, "composite": 74, "lat": 28.5921, "lon": 77.0460},
    {"name": "gurugram_sec29", "city": "delhi", "flood_risk": 55, "traffic_risk": 85, "store_risk": 30, "composite": 76, "lat": 28.4595, "lon": 77.0266},
    {"name": "noida_sec18",    "city": "delhi", "flood_risk": 60, "traffic_risk": 78, "store_risk": 32, "composite": 73, "lat": 28.5706, "lon": 77.3219},
    {"name": "rohini",         "city": "delhi", "flood_risk": 45, "traffic_risk": 70, "store_risk": 25, "composite": 64, "lat": 28.7495, "lon": 77.0565},
]


async def seed():
    print("🌍 Seeding zones...")
    async with AsyncSessionLocal() as session:
        for z in ZONES:
            # Check if zone with this name already exists
            check = await session.execute(
                text("SELECT id FROM zones WHERE name = :name"),
                {"name": z["name"]}
            )
            if check.fetchone():
                print(f"  ⚠️  Zone '{z['name']}' already exists, skipping.")
                continue

            await session.execute(
                text("""
                    INSERT INTO zones (id, name, city, flood_risk_score, traffic_risk_score, store_risk_score, composite_risk_score, lat, lon)
                    VALUES (:id, :name, :city, :flood, :traffic, :store, :composite, :lat, :lon)
                """),
                {
                    "id": uuid.uuid4().hex,
                    "name": z["name"],
                    "city": z["city"],
                    "flood": z["flood_risk"],
                    "traffic": z["traffic_risk"],
                    "store": z["store_risk"],
                    "composite": z["composite"],
                    "lat": z["lat"],
                    "lon": z["lon"],
                },
            )
        await session.commit()
    print(f"✅ Seeded {len(ZONES)} zones across 4 cities.")


if __name__ == "__main__":
    asyncio.run(seed())
