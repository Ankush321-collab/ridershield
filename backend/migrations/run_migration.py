"""
Run DB migration via SQLAlchemy async — no psql needed.
Usage: python migrations/run_migration.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    from shared.database import AsyncSessionLocal
    from sqlalchemy import text

    migration = """
DO $$
BEGIN
    -- Add 'premium' column (rename from premium_paid if exists)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='policies' AND column_name='premium'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='policies' AND column_name='premium_paid'
        ) THEN
            ALTER TABLE policies RENAME COLUMN premium_paid TO premium;
        ELSE
            ALTER TABLE policies ADD COLUMN premium INTEGER NOT NULL DEFAULT 0;
        END IF;
    END IF;

    -- Add 'coverage_pct' column (rename from coverage_percent if exists)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='policies' AND column_name='coverage_pct'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='policies' AND column_name='coverage_percent'
        ) THEN
            ALTER TABLE policies RENAME COLUMN coverage_percent TO coverage_pct;
        ELSE
            ALTER TABLE policies ADD COLUMN coverage_pct INTEGER NOT NULL DEFAULT 70;
        END IF;
    END IF;

    -- Add 'slots_covered' JSONB column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='policies' AND column_name='slots_covered'
    ) THEN
        ALTER TABLE policies ADD COLUMN slots_covered JSONB;
    END IF;

    -- Fix 'status' column: ensure NOT NULL with default
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='policies' AND column_name='status' AND is_nullable='YES'
    ) THEN
        UPDATE policies SET status = 'active' WHERE status IS NULL;
        ALTER TABLE policies ALTER COLUMN status SET NOT NULL;
        ALTER TABLE policies ALTER COLUMN status SET DEFAULT 'active';
    END IF;

    -- Add UNIQUE constraint on (rider_id, week) if missing
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname IN ('policies_rider_id_week_key', 'uq_policies_rider_week')
          AND conrelid = 'policies'::regclass
    ) THEN
        BEGIN
            ALTER TABLE policies ADD CONSTRAINT policies_rider_id_week_key UNIQUE (rider_id, week);
        EXCEPTION WHEN duplicate_table THEN
            -- already exists under different name
            NULL;
        END;
    END IF;
END $$;
"""
    async with AsyncSessionLocal() as db:
        # Check current columns BEFORE migration
        r = await db.execute(text(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns WHERE table_name='policies' ORDER BY ordinal_position"
        ))
        print("=== BEFORE MIGRATION ===")
        for row in r.fetchall():
            print(f"  {row[0]:20s} {row[1]:15s} nullable={row[2]} default={row[3]}")

        # Run migration
        await db.execute(text(migration))
        await db.commit()
        print("\n✅ Migration executed successfully")

        # Check columns AFTER migration
        r2 = await db.execute(text(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns WHERE table_name='policies' ORDER BY ordinal_position"
        ))
        print("\n=== AFTER MIGRATION ===")
        for row in r2.fetchall():
            print(f"  {row[0]:20s} {row[1]:15s} nullable={row[2]} default={row[3]}")

        # Check zone names
        r3 = await db.execute(text("SELECT name FROM zones ORDER BY name"))
        print("\n=== ZONE NAMES IN DB ===")
        for row in r3.fetchall():
            print(f"  {row[0]}")

asyncio.run(main())
