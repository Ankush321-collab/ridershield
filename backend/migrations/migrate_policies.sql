-- ============================================================
-- RiderShield — Migration: Fix policies table schema
-- Run ONCE on live DB to align with ORM model
-- psql -U ridershield -d ridershield -f migrations/migrate_policies.sql
-- ============================================================

-- Add missing columns (IF NOT EXISTS is safe to re-run)
DO $$
BEGIN
    -- Add 'premium' column if it doesn't exist (replaces premium_paid)
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

    -- Add 'coverage_pct' column if it doesn't exist (replaces coverage_percent)
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

    -- Add 'slots_covered' JSONB column if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='policies' AND column_name='slots_covered'
    ) THEN
        ALTER TABLE policies ADD COLUMN slots_covered JSONB;
    END IF;

    -- Ensure status NOT NULL with default
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='policies' AND column_name='status' AND is_nullable='YES'
    ) THEN
        UPDATE policies SET status = 'active' WHERE status IS NULL;
        ALTER TABLE policies ALTER COLUMN status SET NOT NULL;
        ALTER TABLE policies ALTER COLUMN status SET DEFAULT 'active';
    END IF;

    -- Ensure coverage_limit NOT NULL
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='policies' AND column_name='coverage_limit' AND is_nullable='YES'
    ) THEN
        UPDATE policies SET coverage_limit = 5000 WHERE coverage_limit IS NULL;
        ALTER TABLE policies ALTER COLUMN coverage_limit SET NOT NULL;
    END IF;

    -- Ensure coverage_used NOT NULL with default 0
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='policies' AND column_name='coverage_used' AND is_nullable='YES'
    ) THEN
        UPDATE policies SET coverage_used = 0 WHERE coverage_used IS NULL;
        ALTER TABLE policies ALTER COLUMN coverage_used SET NOT NULL;
        ALTER TABLE policies ALTER COLUMN coverage_used SET DEFAULT 0;
    END IF;

    -- Add UNIQUE constraint on (rider_id, week) if not present
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name='policies' AND tc.constraint_type='UNIQUE'
          AND ccu.column_name='week'
    ) THEN
        ALTER TABLE policies ADD CONSTRAINT policies_rider_id_week_key UNIQUE (rider_id, week);
    END IF;

END $$;

-- Verify
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'policies'
ORDER BY ordinal_position;
