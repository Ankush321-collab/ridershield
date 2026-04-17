"""
Dev 4: Fraud Detection Logic
"""

import logging
import os
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from claims_service.models import Claim
from trigger_service.models import PlatformSnapshot
from rider_service.models import RiderZoneBaseline
from ml.serve import predict_anomaly

logger = logging.getLogger("zylo.claims.fraud")

ANOMALY_SCORE_THRESHOLD = 0.7
ANOMALY_FRAUD_POINTS = 20
COLLUSION_SPIKE_THRESHOLD = 15
COLLUSION_RATIO_THRESHOLD = 0.80
COLLUSION_FRAUD_POINTS = 25


def _load_fraud_threshold() -> int:
    raw = os.getenv("FRAUD_THRESHOLD", "75").strip()
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Invalid FRAUD_THRESHOLD=%s; falling back to 75", raw)
        return 75
    return max(0, min(value, 100))


AUTO_CLAIM_FRAUD_THRESHOLD = _load_fraud_threshold()


async def check_duplicate_claim(rider_id: UUID, disruption_event_id: UUID, db: AsyncSession) -> bool:
    """Check if a claim already exists for this rider and disruption event."""
    result = await db.execute(
        select(Claim).where(
            Claim.rider_id == rider_id,
            Claim.disruption_event_id == disruption_event_id,
            Claim.status.in_(["pending", "under_review", "approved", "paid", "flagged"])
        )
    )
    return result.scalar_one_or_none() is not None


async def detect_collusion(
    rider_id: UUID,
    disruption_event_id: UUID,
    zone_id: UUID,
    slot_start: datetime,
    db: AsyncSession,
) -> int:
    window_start = datetime.utcnow() - timedelta(minutes=10)
    collusion_count_result = await db.execute(
        select(func.count(distinct(Claim.rider_id))).where(
            Claim.disruption_event_id == disruption_event_id,
            Claim.created_at >= window_start,
        )
    )
    distinct_riders = collusion_count_result.scalar_one() or 0
    if distinct_riders <= COLLUSION_SPIKE_THRESHOLD:
        return 0

    online_riders_result = await db.execute(
        select(func.count(distinct(PlatformSnapshot.rider_id))).where(
            PlatformSnapshot.zone_id == zone_id,
            PlatformSnapshot.time == slot_start,
            PlatformSnapshot.rider_status == "ONLINE",
        )
    )
    total_online_riders = online_riders_result.scalar_one() or 0
    ratio = min(1.0, distinct_riders / max(total_online_riders, 1))
    if ratio > COLLUSION_RATIO_THRESHOLD:
        logger.warning(
            "Fraud check: Collusion spike detected for rider %s event %s (%s/%s riders)",
            rider_id,
            disruption_event_id,
            distinct_riders,
            total_online_riders,
        )
        return COLLUSION_FRAUD_POINTS
    return 0


async def run_fraud_check(
    rider_id: UUID,
    zone_id: UUID,
    disruption_event_id: UUID,
    actual_earnings: int,
    slot_start: datetime,
    db: AsyncSession
) -> int:
    """
    Calculates a fraud score (0-100).
    Higher score = higher probability of fraud.
    """
    score = 0

    # 1. GPS Consistency (30 pts)
    # Rider should have a snapshot in the disruption zone during the slot
    snapshot_result = await db.execute(
        select(PlatformSnapshot).where(
            PlatformSnapshot.rider_id == rider_id,
            PlatformSnapshot.time == slot_start
        )
    )
    snapshot = snapshot_result.scalar_one_or_none()
    
    if not snapshot or snapshot.zone_id != zone_id:
        logger.warning(f"Fraud check: GPS mismatch for rider {rider_id}")
        score += 30

    # 2. Peer Comparison (25 pts)
    # If the rider's earnings are drastically lower than peers (e.g. they stopped working)
    peer_avg_result = await db.execute(
        select(func.avg(PlatformSnapshot.earnings_current_slot)).where(
            PlatformSnapshot.zone_id == zone_id,
            PlatformSnapshot.time == slot_start,
            PlatformSnapshot.rider_id != rider_id
        )
    )
    peer_avg = peer_avg_result.scalar_one() or 0
    if peer_avg > 0 and actual_earnings < peer_avg / 3:
        logger.warning(f"Fraud check: Earnings < 33% of peers for rider {rider_id}")
        score += 25

    # 3. Baseline Validity (20 pts)
    # Rider should have historical baselines
    baseline_result = await db.execute(
        select(func.count(RiderZoneBaseline.id)).where(RiderZoneBaseline.rider_id == rider_id)
    )
    baseline_count = baseline_result.scalar_one() or 0
    if baseline_count == 0:
        logger.warning(f"Fraud check: No historical baselines for rider {rider_id}")
        score += 20

    # 4. Duplicate Claim (25 pts)
    is_duplicate = await check_duplicate_claim(rider_id, disruption_event_id, db)
    if is_duplicate:
        logger.warning(f"Fraud check: Duplicate claim detected for rider {rider_id}")
        score += 25

    # 5. Behavioural anomaly signal (20 pts)
    if snapshot:
        anomaly_score = predict_anomaly({
            "orders_per_hour": snapshot.orders_per_hour or 0,
            "earnings_current_slot": snapshot.earnings_current_slot or 0,
            "earnings_rolling_baseline": snapshot.earnings_rolling_baseline or 0,
            "order_rate_drop_pct": float(snapshot.order_rate_drop_pct or 0),
            "avg_pickup_wait_sec": snapshot.avg_pickup_wait_sec or 0,
            "congestion_index": snapshot.congestion_index or 0,
        })
        if anomaly_score > ANOMALY_SCORE_THRESHOLD:
            logger.warning(
                "Fraud check: Behaviour anomaly detected for rider %s score=%.2f",
                rider_id,
                anomaly_score,
            )
            score += ANOMALY_FRAUD_POINTS

    # 6. Coordinated claim spike / graph signal (25 pts)
    score += await detect_collusion(
        rider_id=rider_id,
        disruption_event_id=disruption_event_id,
        zone_id=zone_id,
        slot_start=slot_start,
        db=db,
    )

    return min(score, 100)
