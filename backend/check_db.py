import asyncio, sys
sys.path.insert(0, '.')

async def main():
    from shared.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        r = await db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='policies' ORDER BY ordinal_position"))
        print('POLICIES COLUMNS:', [row[0] for row in r.fetchall()])
        r2 = await db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='zones' ORDER BY ordinal_position"))
        print('ZONES COLUMNS:', [row[0] for row in r2.fetchall()])
        r3 = await db.execute(text("SELECT name FROM zones ORDER BY name"))
        print('ZONE NAMES:', [row[0] for row in r3.fetchall()])
        r4 = await db.execute(text("SELECT rider_id, week, status, premium, coverage_limit, slots_covered FROM policies LIMIT 3"))
        rows = r4.fetchall()
        print('SAMPLE POLICIES:', rows)

asyncio.run(main())
