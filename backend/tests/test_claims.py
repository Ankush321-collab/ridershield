"""
Test script for Task 4 Claims + Payouts
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claims_test.sqlite3")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

import asyncio
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from shared.database import AsyncSessionLocal, init_db, close_db

from rider_service.models import Rider, Zone, RiderZoneBaseline
from policy_service.models import Policy
from trigger_service.models import DisruptionEvent, PlatformSnapshot
from claims_service.models import Claim, Payout
from claims_service.service import process_auto_claims


async def run_test():
    await init_db()
    async with AsyncSessionLocal() as session:
        try:
            print("🚀 Checking for existing test zones/riders...")
            rider_result = await session.execute(text("SELECT id, zone_id FROM riders LIMIT 1"))
            rider = rider_result.fetchone()
            
            if not rider:
                print("No rider found! Creating one...")
                zone_id = uuid4()
                await session.execute(text("""
                    INSERT INTO zones (
                        id, name, city, flood_risk_score, traffic_risk_score, store_risk_score, composite_risk_score
                    ) VALUES (
                        :id, 'Test Zone', 'Test City', 45, 50, 40, 45
                    )
                """), {"id": str(zone_id)})
                
                rider_id = uuid4()
                await session.execute(text("""
                    INSERT INTO riders (id, name, phone, platform, city, zone_id, kyc_status, trust_score) 
                    VALUES (:id, 'Test Rider', '8888888888', 'zepto', 'Test City', :zone_id, 'verified', 80)
                """), {"id": str(rider_id), "zone_id": str(zone_id)})
                await session.commit()
            else:
                rider_id, zone_id = rider[0], rider[1]

            print(f"✅ Using Rider: {rider_id} in Zone: {zone_id}")
            
            current_time = datetime.now(timezone.utc)
            current_week = current_time.strftime("%Y-W%V")
            
            # Determine appropriate time bucket
            hour = current_time.hour
            if 18 <= hour < 21: slot_time = "18:00-21:00"
            elif 21 <= hour < 23: slot_time = "21:00-23:00"
            else: slot_time = f"{hour:02d}:00-{(hour+3):02d}:00"

            print(f"Creating Policy, Baseline, and Snapshot for {slot_time}...")
            
            # 1. Create Active Policy
            policy_id = uuid4()
            await session.execute(text("""
                INSERT INTO policies (id, rider_id, plan_tier, week, status, coverage_limit, coverage_used, premium, coverage_pct, expires_at)
                VALUES (:id, :rider_id, 'balanced', :week, 'active', 5000, 0, 100, 80, :expires_at)
            """), {"id": str(policy_id), "rider_id": str(rider_id), "week": current_week, "expires_at": current_time + timedelta(days=7)})

            # 2. Create Baseline
            baseline_id = uuid4()
            await session.execute(text("""
                INSERT INTO rider_zone_baselines (id, rider_id, zone_id, week, slot_time, avg_earnings, avg_orders, disruption_count)
                VALUES (:id, :rider_id, :zone_id, :week, :slot_time, 700, 10, 0)
            """), {"id": str(baseline_id), "rider_id": str(rider_id), "zone_id": str(zone_id), "week": current_week, "slot_time": slot_time})

            # 3. Create platform snapshot for this specific time with LOWER earnings
            snapshot_id = uuid4()
            await session.execute(text("""
                INSERT INTO platform_snapshots (
                    id, time, rider_id, zone_id, earnings_current_slot, earnings_rolling_baseline,
                    rider_status, platform_status, shadowban_active, shadowban_duration_min,
                    allocation_anomaly, curfew_active, road_blocked
                )
                VALUES (
                    :id, :time, :rider_id, :zone_id, 100, 700,
                    'ONLINE', 'UP', 0, 0,
                    0, 0, 0
                )
            """), {"id": str(snapshot_id), "time": current_time, "rider_id": str(rider_id), "zone_id": str(zone_id)})
            
            # 4. Create Disruption Event
            event_id = uuid4()
            await session.execute(text("""
                INSERT INTO disruption_events (
                    id, trigger_type, zone_id, zone_name, slot_start, slot_end, severity, affected_riders, created_at
                )
                VALUES (
                    :id, 'heavy_rain', :zone_id, 'Test Zone', :time, :end_time, 'high', 1, :time
                )
            """), {"id": str(event_id), "zone_id": str(zone_id), "time": current_time, "end_time": current_time + timedelta(hours=3)})
            
            await session.commit()
            print("✅ Test data created. Running process_auto_claims...")
            
            # 5. Execute Auto Claims Logic
            claims_generated = await process_auto_claims(event_id, session)
            print(f"🎉 Auto Claims Geneated: {claims_generated}")
            
            # 6. Verify Results
            claim_q = await session.execute(select(Claim).where(Claim.disruption_event_id == event_id))
            claim = claim_q.scalar_one_or_none()
            
            if claim:
                print(f"✅ Claim Found: {claim.id} | Income Loss: {claim.income_loss} | Payout: {claim.payout_amount} | Status: {claim.status}")
                payout_q = await session.execute(select(Payout).where(Payout.claim_id == claim.id))
                payout = payout_q.scalar_one_or_none()
                if payout:
                    print(f"✅ Payout Found: {payout.id} | Amount: {payout.amount} | Ref: {payout.reference_id} | Status: {payout.status}")
                else:
                    print("❌ Failure: Payout record not created")

        except Exception as e:
            print(f"❌ Test Failed: {e}")
            await session.rollback()
    await close_db()

if __name__ == "__main__":
    asyncio.run(run_test())
