"""
Dev 2: Policy Service Router — Full Implementation
Wires the service layer functions into FastAPI endpoints.
"""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.auth import get_current_rider
from policy_service.service import (
    get_policy_quote,
    create_policy,
    get_active_policy,
    get_policy_by_id,
    renew_policy,
    cancel_policy,
    calculate_hours_remaining,
)

router = APIRouter()


@router.get("/quote")
async def get_quote(
    slots: str = Query(..., description="Comma-separated slots: '18:00-21:00,21:00-23:00'"),
    city: str = Query(default="bengaluru"),
    rider=Depends(get_current_rider),
    db: AsyncSession = Depends(get_db),
):
    """Get dynamic premium quotes for all 3 tiers."""
    import re
    slot_list = [s.strip() for s in slots.split(",") if s.strip()]
    if not slot_list:
        raise HTTPException(status_code=400, detail="At least one slot is required")
    pattern = re.compile(r"^\d{2}:\d{2}-\d{2}:\d{2}$")
    for s in slot_list:
        if not pattern.match(s):
            raise HTTPException(status_code=400, detail=f"Invalid slot format: '{s}'")
    result = await get_policy_quote(str(rider.id), slot_list, db, city)
    return result


@router.post("", status_code=201)
async def create_policy_endpoint(
    data: dict,
    rider=Depends(get_current_rider),
    db: AsyncSession = Depends(get_db),
):
    """Create a new policy for the current week."""
    plan_tier = data.get("plan_tier", "balanced")
    slots = data.get("slots", ["18:00-21:00"])
    payment_method = data.get("payment_method", "upi")
    upi_id = data.get("upi_id") or rider.upi_id

    if plan_tier not in ("essential", "balanced", "max_protect"):
        raise HTTPException(status_code=400, detail=f"Invalid plan_tier: {plan_tier}")
    if not isinstance(slots, list) or not slots:
        raise HTTPException(status_code=400, detail="At least one slot is required")

    policy = await create_policy(
        str(rider.id),
        plan_tier,
        slots,
        db,
        payment_method=payment_method,
        upi_id=upi_id,
    )
    return {
        "policy_id": str(policy.id),
        "rider_id": str(policy.rider_id),
        "plan_tier": policy.plan_tier,
        "coverage_week": policy.week,
        "premium": policy.premium,
        "premium_paid": policy.premium,
        "coverage_limit": policy.coverage_limit,
        "coverage_pct": policy.coverage_pct,
        "status": policy.status,
        "slots_covered": policy.slots_covered,
        "payment_method": payment_method,
        "upi_id": upi_id,
        "created_at": str(policy.created_at) if policy.created_at else None,
        "expires_at": str(policy.expires_at) if policy.expires_at else None,
    }


@router.get("/active")
async def get_active_policy_endpoint(
    rider=Depends(get_current_rider),
    db: AsyncSession = Depends(get_db),
):
    """Get rider's active policy for the current week."""
    policy = await get_active_policy(str(rider.id), db)
    if not policy:
        raise HTTPException(status_code=404, detail="No active policy for this week")

    return {
        "policy_id": str(policy.id),
        "rider_id": str(policy.rider_id),
        "plan_tier": policy.plan_tier,
        "coverage_week": policy.week,
        "premium": policy.premium,
        "premium_paid": policy.premium,
        "coverage_limit": policy.coverage_limit,
        "coverage_pct": policy.coverage_pct,
        "coverage_used": policy.coverage_used,
        "status": policy.status,
        "slots_covered": policy.slots_covered,
        "hours_remaining": calculate_hours_remaining(policy),
        "expires_at": str(policy.expires_at) if policy.expires_at else None,
    }


@router.get("/{policy_id}")
async def get_policy(
    policy_id: UUID,
    rider=Depends(get_current_rider),
    db: AsyncSession = Depends(get_db),
):
    """Return full policy details."""
    policy = await get_policy_by_id(str(policy_id), str(rider.id), db)
    return {
        "policy_id": str(policy.id),
        "rider_id": str(policy.rider_id),
        "plan_tier": policy.plan_tier,
        "coverage_week": policy.week,
        "premium": policy.premium,
        "premium_paid": policy.premium,
        "coverage_limit": policy.coverage_limit,
        "coverage_pct": policy.coverage_pct,
        "coverage_used": policy.coverage_used,
        "status": policy.status,
        "slots_covered": policy.slots_covered,
        "expires_at": str(policy.expires_at) if policy.expires_at else None,
    }


@router.put("/{policy_id}/renew")
async def renew_policy_endpoint(
    policy_id: UUID,
    data: dict = {},
    rider=Depends(get_current_rider),
    db: AsyncSession = Depends(get_db),
):
    """Renew policy for next week, optionally changing tier."""
    new_tier = data.get("plan_tier")
    result = await renew_policy(str(policy_id), str(rider.id), new_tier, db)
    return result


@router.delete("/{policy_id}", status_code=204)
async def cancel_policy_endpoint(
    policy_id: UUID,
    rider=Depends(get_current_rider),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an active policy."""
    await cancel_policy(str(policy_id), str(rider.id), db)
    return None
