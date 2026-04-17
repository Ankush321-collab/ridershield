"""
Seed script — Create 20 demo riders across 4 cities & 3 platforms.

Run:  python -m seeds.seed_riders
      (from backend/ directory, AFTER seed_zones.py)
"""

import asyncio
import uuid
from sqlalchemy import text
from shared.database import AsyncSessionLocal

# 20 riders: spread across cities and platforms
RIDERS = [
    # ─── Bengaluru (5 riders) ──────────────────────────
    {"name": "Arjun Kumar",      "phone": "+919876543201", "platform": "zepto",   "city": "bengaluru", "zone": "koramangala",   "upi": "arjun@oksbi"},
    {"name": "Priya Sharma",     "phone": "+919876543202", "platform": "blinkit", "city": "bengaluru", "zone": "hsr_layout",    "upi": "priya@okicici"},
    {"name": "Naveen Reddy",     "phone": "+919876543203", "platform": "swiggy",  "city": "bengaluru", "zone": "whitefield",    "upi": "naveen@ybl"},
    {"name": "Lakshmi Devi",     "phone": "+919876543204", "platform": "zepto",   "city": "bengaluru", "zone": "indiranagar",   "upi": "lakshmi@paytm"},
    {"name": "Karthik Gowda",    "phone": "+919876543205", "platform": "blinkit", "city": "bengaluru", "zone": "electronic_city","upi": "karthik@oksbi"},

    # ─── Hyderabad (5 riders) ──────────────────────────
    {"name": "Ravi Teja",        "phone": "+919876543206", "platform": "swiggy",  "city": "hyderabad", "zone": "gachibowli",    "upi": "ravi@okaxis"},
    {"name": "Sameera Begum",    "phone": "+919876543207", "platform": "zepto",   "city": "hyderabad", "zone": "madhapur",      "upi": "sameera@ybl"},
    {"name": "Venkat Rao",       "phone": "+919876543208", "platform": "blinkit", "city": "hyderabad", "zone": "kondapur",      "upi": "venkat@oksbi"},
    {"name": "Anjali Prasad",    "phone": "+919876543209", "platform": "swiggy",  "city": "hyderabad", "zone": "lb_nagar",      "upi": "anjali@okicici"},
    {"name": "Suresh Naidu",     "phone": "+919876543210", "platform": "zepto",   "city": "hyderabad", "zone": "gachibowli",    "upi": "suresh@paytm"},

    # ─── Mumbai (5 riders) ─────────────────────────────
    {"name": "Rahul Patil",      "phone": "+919876543211", "platform": "blinkit", "city": "mumbai",    "zone": "andheri",       "upi": "rahul@ybl"},
    {"name": "Meena Jadhav",     "phone": "+919876543212", "platform": "swiggy",  "city": "mumbai",    "zone": "bandra",        "upi": "meena@oksbi"},
    {"name": "Amit Deshmukh",    "phone": "+919876543213", "platform": "zepto",   "city": "mumbai",    "zone": "powai",         "upi": "amit@okaxis"},
    {"name": "Sneha Kulkarni",   "phone": "+919876543214", "platform": "blinkit", "city": "mumbai",    "zone": "malad",         "upi": "sneha@okicici"},
    {"name": "Vijay Shinde",     "phone": "+919876543215", "platform": "swiggy",  "city": "mumbai",    "zone": "andheri",       "upi": "vijay@paytm"},

    # ─── Delhi NCR (5 riders) ──────────────────────────
    {"name": "Deepak Verma",     "phone": "+919876543216", "platform": "zepto",   "city": "delhi",     "zone": "dwarka",        "upi": "deepak@oksbi"},
    {"name": "Pooja Gupta",      "phone": "+919876543217", "platform": "blinkit", "city": "delhi",     "zone": "gurugram_sec29","upi": "pooja@ybl"},
    {"name": "Manish Singh",     "phone": "+919876543218", "platform": "swiggy",  "city": "delhi",     "zone": "noida_sec18",   "upi": "manish@okaxis"},
    {"name": "Sunita Yadav",     "phone": "+919876543219", "platform": "zepto",   "city": "delhi",     "zone": "rohini",        "upi": "sunita@okicici"},
    {"name": "Rohit Chauhan",    "phone": "+919876543220", "platform": "blinkit", "city": "delhi",     "zone": "dwarka",        "upi": "rohit@paytm"},
]


async def seed():
    print("🏍️  Seeding riders...")
    async with AsyncSessionLocal() as session:
        # Build zone name→id lookup
        result = await session.execute(text("SELECT id, name FROM zones"))
        zone_map = {row[1]: str(row[0]) for row in result.fetchall()}

        if not zone_map:
            print("❌ No zones found! Run seed_zones.py first.")
            return

        count = 0
        for r in RIDERS:
            # Check if rider already exists by phone to avoid duplicates and FK errors
            check = await session.execute(
                text("SELECT id FROM riders WHERE phone = :phone"), 
                {"phone": r["phone"]}
            )
            existing = check.fetchone()
            if existing:
                continue

            zone_id = zone_map.get(r["zone"])
            if not zone_id:
                print(f"  ⚠️  Zone '{r['zone']}' not found, skipping {r['name']}")
                continue

            rider_id = str(uuid.uuid4())

            # Insert rider
            await session.execute(
                text("""
                    INSERT INTO riders (id, phone, name, platform, city, zone_id, upi_id, kyc_status, trust_score)
                    VALUES (:id, :phone, :name, :platform, :city, :zone_id, :upi_id, 'verified', :trust)
                """),
                {
                    "id": rider_id,
                    "phone": r["phone"],
                    "name": r["name"],
                    "platform": r["platform"],
                    "city": r["city"],
                    "zone_id": zone_id,
                    "upi_id": r["upi"],
                    "trust": 75 + (count % 3) * 5,
                },
            )

            # Insert risk profile
            volatility = round(0.30 + (count % 5) * 0.08, 2)
            disruption = round(0.15 + (count % 4) * 0.12, 2)
            week_base = 3800 + (count * 50)

            await session.execute(
                text("""
                    INSERT INTO rider_risk_profiles (id, rider_id, zone_id, income_volatility, disruption_probability, four_week_earnings)
                    VALUES (:id, :rider_id, :zone_id, :vol, :dis, cast(:earnings as jsonb))
                """),
                {
                    "id": str(uuid.uuid4()),
                    "rider_id": rider_id,
                    "zone_id": zone_id,
                    "vol": volatility,
                    "dis": disruption,
                    "earnings": f'{{"week_12": {week_base}, "week_11": {week_base - 150}, "week_10": {week_base - 300}, "week_9": {week_base + 200}}}',
                },
            )

            count += 1

        await session.commit()
    print(f"✅ Seeded {count} riders with risk profiles.")


if __name__ == "__main__":
    asyncio.run(seed())
