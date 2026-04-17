import asyncio
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch

TEST_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "fraud_gating_test.sqlite3",
)
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database import Base
from claims_service.models import Claim
from claims_service.service import process_auto_claims
from policy_service.models import Policy
from rider_service.models import Rider, RiderZoneBaseline, Zone
from trigger_service.models import DisruptionEvent, PlatformSnapshot


def _slot_start() -> datetime:
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    # Keep this deterministic so slot bucket baseline lookup is stable.
    return now.replace(hour=19)


async def _seed_auto_claim_data(session):
    slot_start = _slot_start()
    zone = Zone(
        name="Fraud Test Zone",
        city="Delhi",
        flood_risk_score=40,
        traffic_risk_score=45,
        store_risk_score=35,
        composite_risk_score=40,
    )
    session.add(zone)
    await session.flush()

    rider = Rider(
        name="Fraud Test Rider",
        phone=f"9{str(abs(hash(datetime.utcnow().isoformat())))[:9]}",
        platform="zepto",
        city="Delhi",
        zone_id=zone.id,
        kyc_status="verified",
        trust_score=80,
        upi_id="fraudtest@upi",
    )
    session.add(rider)
    await session.flush()

    week = slot_start.strftime("%Y-W%V")
    policy = Policy(
        rider_id=rider.id,
        plan_tier="balanced",
        week=week,
        premium=100,
        coverage_limit=5000,
        coverage_pct=80,
        coverage_used=0,
        status="active",
        expires_at=slot_start + timedelta(days=7),
    )
    session.add(policy)

    baseline = RiderZoneBaseline(
        rider_id=rider.id,
        zone_id=zone.id,
        week=week,
        slot_time="18:00-21:00",
        avg_earnings=700,
        avg_orders=10,
        disruption_count=0,
    )
    session.add(baseline)

    snapshot = PlatformSnapshot(
        time=slot_start,
        rider_id=rider.id,
        zone_id=zone.id,
        earnings_current_slot=100,
        earnings_rolling_baseline=700,
        rider_status="ONLINE",
        platform_status="UP",
        shadowban_active=False,
        shadowban_duration_min=0,
        allocation_anomaly=False,
        curfew_active=False,
        grap_vehicle_ban=False,
        road_blocked=False,
    )
    session.add(snapshot)

    event = DisruptionEvent(
        trigger_type="heavy_rain",
        zone_id=zone.id,
        zone_name=zone.name,
        slot_start=slot_start,
        slot_end=slot_start + timedelta(hours=3),
        severity="high",
        affected_riders=1,
    )
    session.add(event)

    await session.commit()
    return event.id, rider.id


async def _run_flagged_case(fraud_score: int):
    isolated_db_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"fraud_gating_test_{uuid4().hex}.sqlite3",
    )
    engine = create_async_engine(f"sqlite+aiosqlite:///{isolated_db_path}")
    session_local = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_local() as session:
            event_id, rider_id = await _seed_auto_claim_data(session)

            with (
                patch("claims_service.service.run_fraud_check", AsyncMock(return_value=fraud_score)),
                patch("claims_service.service.process_upi_payout", AsyncMock()) as payout_mock,
            ):
                created = await process_auto_claims(event_id, session)

                claim_result = await session.execute(select(Claim).where(Claim.rider_id == rider_id))
                claim = claim_result.scalar_one_or_none()

                assert created == 1
                assert claim is not None
                return claim, payout_mock
    finally:
        await engine.dispose()
        if os.path.exists(isolated_db_path):
            os.remove(isolated_db_path)


def test_auto_claim_is_flagged_and_payout_skipped_at_threshold():
    claim, payout_mock = asyncio.run(_run_flagged_case(75))
    assert claim.status == "flagged"
    assert claim.payout_amount == 0
    payout_mock.assert_not_called()


def test_auto_claim_is_paid_and_payout_called_below_threshold():
    claim, payout_mock = asyncio.run(_run_flagged_case(74))
    assert claim.status == "paid"
    assert claim.payout_amount > 0
    payout_mock.assert_called_once()
