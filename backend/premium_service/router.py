from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_rider
from shared.database import get_db
from policy_service.service import get_rider_weekly_baseline
from premium_service.service import calculate_premium
from rider_service.models import Zone
from sqlalchemy import select

router = APIRouter()


@router.post("/premium")
async def calculate_premium_endpoint(
    data: dict,
    rider=Depends(get_current_rider),
    db: AsyncSession = Depends(get_db),
):
    if data.get("zone"):
        zone_name = data["zone"]
    else:
        zone_result = await db.execute(select(Zone).where(Zone.id == rider.zone_id))
        zone = zone_result.scalar_one_or_none()
        zone_name = zone.name if zone else rider.city
    slots = data.get("slots") or ["18:00-21:00"]
    plan_tier = data.get("plan_tier", "balanced")

    rider_tenure_days = data.get("rider_tenure_days")
    if rider_tenure_days is None:
        created_at = rider.created_at
        if getattr(created_at, "tzinfo", None) is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        rider_tenure_days = max((datetime.now(timezone.utc) - created_at).days, 0)

    premium_response = await calculate_premium(
        zone=zone_name,
        slots=slots,
        plan_tier=plan_tier,
        rider_tenure_days=rider_tenure_days,
        db=db,
    )

    weekly_baseline = await get_rider_weekly_baseline(str(rider.id), db)
    slots_count = max(len(slots), 1)
    expected_per_slot = round(weekly_baseline / slots_count)
    slot_breakdown = []
    for row in premium_response["breakdown"]:
        slot_breakdown.append({
            "slot": row["slot"],
            "expected_earnings": expected_per_slot,
            "risk_score": row["risk"],
            "premium": row["premium"],
        })

    return {
        **premium_response,
        "zone_name": zone_name,
        "zone_risk_score": premium_response.get("zone_risk_score", premium_response["risk_score"]),
        "slot_breakdown": slot_breakdown,
    }
