from __future__ import annotations

from uuid import UUID
from typing import TYPE_CHECKING, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from policy_service.models import Policy


def _as_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _week_sort_key(week_value: str) -> tuple[int, int]:
    try:
        year, week = week_value.split("-W")
        return int(year), int(week)
    except Exception:
        return (0, 0)


async def get_policy_quote(
    rider_id: str,
    slots: List[str],
    db: AsyncSession,
    city: str = "bengaluru"
) -> Dict:
    """
    Generate premium quotes for all 3 tiers for the given rider and slots.
    Called by GET /api/policies/quote
    """
    try:
        from backend.premium_service.service import calculate_premium, get_zone_risk_scores
    except ImportError:
        from premium_service.service import calculate_premium, get_zone_risk_scores

    rider = await get_rider(rider_id, db)
    zone_name = await get_rider_zone_name(rider, db, city)

    tenure_days = 90
    if hasattr(rider, "created_at") and rider.created_at:
        from datetime import datetime, timezone

        created_at = rider.created_at
        if getattr(created_at, "tzinfo", None) is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        tenure_days = max((datetime.now(timezone.utc) - created_at).days, 0)

    weekly_baseline = await get_rider_weekly_baseline(rider_id, db)
    expected_per_slot = round(weekly_baseline / max(len(slots), 1))

    quotes = []
    quote_explanation = None
    slot_breakdown = []
    for tier in ["essential", "balanced", "max_protect"]:
        result = await calculate_premium(
            zone=zone_name,
            slots=slots,
            plan_tier=tier,
            rider_tenure_days=tenure_days,
            db=db,
            rider_avg_earnings=expected_per_slot,
        )

        coverage_pct = {"essential": 70, "balanced": 80, "max_protect": 90}[tier]
        coverage_limit = int(weekly_baseline * coverage_pct / 100)

        quotes.append({
            "tier": tier,
            "weekly_premium": result["premium"][tier],
            "coverage_pct": coverage_pct,
            "coverage_limit": coverage_limit,
            "slots_covered": len(slots),
            "risk_breakdown": result.get(
                "risk_breakdown",
                {"weather": 50, "traffic": 50, "store": 50}
            )
        })

        if quote_explanation is None:
            quote_explanation = result.get("explanation")
            slot_breakdown = [
                {
                    "slot": row["slot"],
                    "expected_earnings": expected_per_slot,
                    "risk_score": row["risk"],
                    "premium": row["premium"],
                }
                for row in result.get("breakdown", [])
            ]
            zone_risk_score = result.get("zone_risk_score", result.get("risk_score", 0))

    from datetime import datetime, timezone

    valid_until = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)

    return {
        "quotes": quotes,
        "valid_until": valid_until,
        "zone_name": zone_name,
        "zone_risk_score": zone_risk_score,
        "slot_breakdown": slot_breakdown,
        "explanation": quote_explanation,
    }


async def get_rider(rider_id: str, db: AsyncSession):
    """Fetch rider from DB. Import Rider model from Dev 1's module."""
    try:
        from backend.rider_service.models import Rider
    except ImportError:
        from rider_service.models import Rider

    rider_uuid = _as_uuid(rider_id)
    result = await db.execute(select(Rider).where(Rider.id == rider_uuid))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    return rider


async def get_rider_zone_name(rider, db: AsyncSession, fallback: str = "bengaluru") -> str:
    try:
        from backend.rider_service.models import Zone
    except ImportError:
        from rider_service.models import Zone

    result = await db.execute(select(Zone).where(Zone.id == rider.zone_id))
    zone = result.scalar_one_or_none()
    return zone.name if zone else (rider.city or fallback)


async def get_rider_weekly_baseline(rider_id: str, db: AsyncSession) -> int:
    """
    Get rider's weekly earnings baseline from rider_zone_baselines table.
    Falls back to zone median if rider has no history.
    """
    try:
        try:
            from backend.rider_service.models import RiderZoneBaseline
        except ImportError:
            from rider_service.models import RiderZoneBaseline

        rider_uuid = _as_uuid(rider_id)
        result = await db.execute(
            select(RiderZoneBaseline).where(RiderZoneBaseline.rider_id == rider_uuid)
        )
        baselines = result.scalars().all()
        if baselines:
            latest_week = max((baseline.week for baseline in baselines), key=_week_sort_key)
            return int(sum(b.avg_earnings for b in baselines if b.week == latest_week))
    except Exception:
        pass
    return 3600


async def create_policy(
    rider_id: str,
    plan_tier: str,
    slots: List[str],
    db: AsyncSession,
    payment_method: str = "upi",
    upi_id: Optional[str] = None,
) -> Policy:
    """
    Create a new active policy for the current calendar week.
    Enforces: one active policy per rider per week.
    """
    try:
        from backend.policy_service.models import Policy, get_current_iso_week, get_week_expiry
    except ImportError:
        from policy_service.models import Policy, get_current_iso_week, get_week_expiry

    try:
        from backend.premium_service.service import calculate_premium
    except ImportError:
        from premium_service.service import calculate_premium

    rider_uuid = _as_uuid(rider_id)
    current_week = get_current_iso_week()

    existing = await db.execute(
        select(Policy).where(
            Policy.rider_id == rider_uuid,
            Policy.week == current_week,
            Policy.status == "active"
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "DUPLICATE_POLICY",
                "message": f"An active policy already exists for week {current_week}"
            }
        )

    rider = await get_rider(rider_id, db)
    zone_name = await get_rider_zone_name(rider, db, "bengaluru")
    tenure_days = 90
    if hasattr(rider, "created_at") and rider.created_at:
        from datetime import datetime, timezone

        created_at = rider.created_at
        if getattr(created_at, "tzinfo", None) is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        tenure_days = max((datetime.now(timezone.utc) - created_at).days, 0)

    # ── SS Code, 2020 — Engagement Rule ──────────────────────────
    # Riders must complete a minimum number of days on-platform before
    # qualifying for parametric income protection (configurable via env).
    from shared.config import settings as app_settings
    min_days = app_settings.MIN_ENGAGEMENT_DAYS
    if min_days > 0 and tenure_days < min_days:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "ENGAGEMENT_RULE",
                "message": (
                    f"SS Code 2020 compliance: Rider must complete {min_days} days "
                    f"on-platform before purchasing a policy. "
                    f"Current tenure: {tenure_days} days."
                ),
                "tenure_days": tenure_days,
                "required_days": min_days,
            },
        )

    premium_data = await calculate_premium(
        zone=zone_name,
        slots=slots,
        plan_tier=plan_tier,
        rider_tenure_days=tenure_days,
        db=db,
        rider_avg_earnings=max(await get_rider_weekly_baseline(rider_id, db) / max(len(slots), 1), 1),
    )

    weekly_baseline = await get_rider_weekly_baseline(rider_id, db)
    coverage_pct = {"essential": 70, "balanced": 80, "max_protect": 90}[plan_tier]
    coverage_limit = int(weekly_baseline * coverage_pct / 100)

    if payment_method != "upi":
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_PAYMENT_METHOD",
                "message": "Only demo UPI payments are supported",
            },
        )

    if not upi_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "UPI_REQUIRED",
                "message": "UPI ID is required for demo payment",
            },
        )

    policy = Policy(
        rider_id=rider_uuid,
        plan_tier=plan_tier,
        week=current_week,
        premium=premium_data["premium"][plan_tier],
        coverage_limit=coverage_limit,
        coverage_pct=coverage_pct,
        status="active",
        slots_covered=slots,
        coverage_used=0,
        expires_at=get_week_expiry()
    )

    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


async def get_active_policy(rider_id: str, db: AsyncSession) -> Optional[Policy]:
    try:
        from backend.policy_service.models import Policy, get_current_iso_week
    except ImportError:
        from policy_service.models import Policy, get_current_iso_week

    rider_uuid = _as_uuid(rider_id)
    current_week = get_current_iso_week()

    result = await db.execute(
        select(Policy).where(
            Policy.rider_id == rider_uuid,
            Policy.status == "active",
            Policy.week == current_week,
        ).order_by(Policy.created_at.desc())
    )
    return result.scalar_one_or_none()


def calculate_hours_remaining(policy: Policy) -> int:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    expires_at = policy.expires_at
    if getattr(expires_at, "tzinfo", None) is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        return 0
    delta = expires_at - now
    return int(delta.total_seconds() // 3600)


async def get_policy_by_id(policy_id: str, rider_id: str, db: AsyncSession) -> Policy:
    try:
        from backend.policy_service.models import Policy
    except ImportError:
        from policy_service.models import Policy

    policy_uuid = _as_uuid(policy_id)
    rider_uuid = _as_uuid(rider_id)
    result = await db.execute(
        select(Policy).where(
            Policy.id == policy_uuid,
            Policy.rider_id == rider_uuid
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "POLICY_NOT_FOUND",
                "message": f"Policy {policy_id} not found"
            }
        )
    return policy


async def renew_policy(
    policy_id: str,
    rider_id: str,
    new_tier: Optional[str],
    db: AsyncSession
) -> Dict:
    """
    Renew policy for the NEXT calendar week.
    Re-runs ML model with fresh zone risk data.
    Returns new policy details.
    """
    try:
        from backend.policy_service.models import Policy
    except ImportError:
        from policy_service.models import Policy

    try:
        from backend.premium_service.service import calculate_premium
    except ImportError:
        from premium_service.service import calculate_premium

    from datetime import datetime, timezone, timedelta

    current_policy = await get_policy_by_id(policy_id, rider_id, db)
    rider_uuid = _as_uuid(rider_id)

    if current_policy.status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "POLICY_EXPIRED",
                "message": "Cannot renew a cancelled policy"
            }
        )

    current_year, current_week = map(int, current_policy.week.split("-W"))
    next_week_num = current_week + 1
    next_year = current_year
    if next_week_num > 52:
        next_week_num = 1
        next_year += 1
    next_week = f"{next_year}-W{next_week_num:02d}"

    # Check if policy for next week already exists
    existing_result = await db.execute(
        select(Policy).where(
            Policy.rider_id == rider_uuid,
            Policy.week == next_week,
            Policy.status == "active"
        )
    )
    existing_policy = existing_result.scalar_one_or_none()

    # If exists, update it with new tier instead of rejecting
    if existing_policy:
        tier = new_tier or existing_policy.plan_tier
        rider = await get_rider(rider_id, db)
        zone_name = await get_rider_zone_name(rider, db, "bengaluru")
        tenure_days = 90
        if hasattr(rider, "created_at") and rider.created_at:
            created_at = rider.created_at
            if getattr(created_at, "tzinfo", None) is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            tenure_days = max((datetime.now(timezone.utc) - created_at).days, 0)

        premium_data = await calculate_premium(
            zone=zone_name,
            slots=existing_policy.slots_covered or [],
            plan_tier=tier,
            rider_tenure_days=tenure_days,
            db=db,
            rider_avg_earnings=max(await get_rider_weekly_baseline(rider_id, db) / max(len(existing_policy.slots_covered or []), 1), 1),
        )

        weekly_baseline = await get_rider_weekly_baseline(rider_id, db)
        coverage_pct = {"essential": 70, "balanced": 80, "max_protect": 90}[tier]
        coverage_limit = int(weekly_baseline * coverage_pct / 100)

        # Update existing policy
        existing_policy.plan_tier = tier
        existing_policy.premium = premium_data["premium"][tier]
        existing_policy.coverage_limit = coverage_limit
        existing_policy.coverage_pct = coverage_pct

        db.add(existing_policy)
        await db.commit()
        await db.refresh(existing_policy)

        return {
            "policy_id": str(existing_policy.id),
            "previous_policy_id": policy_id,
            "week": next_week,
            "new_premium": existing_policy.premium,
            "status": existing_policy.status,
            "updated": True,
            "message": "Policy for next week updated with new tier"
        }

    tier = new_tier or current_policy.plan_tier

    rider = await get_rider(rider_id, db)
    zone_name = await get_rider_zone_name(rider, db, "bengaluru")
    tenure_days = 90
    if hasattr(rider, "created_at") and rider.created_at:
        created_at = rider.created_at
        if getattr(created_at, "tzinfo", None) is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        tenure_days = max((datetime.now(timezone.utc) - created_at).days, 0)

    premium_data = await calculate_premium(
        zone=zone_name,
        slots=current_policy.slots_covered or [],
        plan_tier=tier,
        rider_tenure_days=tenure_days,
        db=db,
        rider_avg_earnings=max(await get_rider_weekly_baseline(rider_id, db) / max(len(current_policy.slots_covered or []), 1), 1),
    )

    weekly_baseline = await get_rider_weekly_baseline(rider_id, db)
    coverage_pct = {"essential": 70, "balanced": 80, "max_protect": 90}[tier]
    coverage_limit = int(weekly_baseline * coverage_pct / 100)

    now = datetime.now(timezone.utc)
    days_to_next_sunday = (6 - now.weekday() + 7) % 7 + 7
    next_sunday = now + timedelta(days=days_to_next_sunday)
    next_expiry = next_sunday.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=None)

    new_policy = Policy(
        rider_id=rider_uuid,
        plan_tier=tier,
        week=next_week,
        premium=premium_data["premium"][tier],
        coverage_limit=coverage_limit,
        coverage_pct=coverage_pct,
        status="active",
        slots_covered=current_policy.slots_covered,
        coverage_used=0,
        expires_at=next_expiry
    )

    db.add(new_policy)
    await db.commit()
    await db.refresh(new_policy)

    return {
        "policy_id": str(new_policy.id),
        "previous_policy_id": policy_id,
        "week": next_week,
        "new_premium": new_policy.premium,
        "status": new_policy.status
    }


async def cancel_policy(policy_id: str, rider_id: str, db: AsyncSession) -> None:
    """Cancel an active policy. Sets status to 'cancelled'."""
    policy = await get_policy_by_id(policy_id, rider_id, db)

    if policy.status != "active":
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "POLICY_EXPIRED",
                "message": f"Policy is already {policy.status}"
            }
        )

    policy.status = "cancelled"
    await db.commit()
