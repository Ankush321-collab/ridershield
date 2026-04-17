from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from premium_service.schemas import PremiumRequest, PremiumResponse
from premium_service.service import calculate_premium
from shared.database import get_db


router = APIRouter(prefix="/api/risk", tags=["Premium & Risk"])


@router.post("/premium", response_model=PremiumResponse)
async def calculate_risk_premium(
    request: PremiumRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Internal API - calculate dynamic premium using ML model.
    Called by: Dev 1 (onboarding quotes), Dev 3 (trigger evaluation).
    """
    if request.plan_tier not in ["essential", "balanced", "max_protect"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_TIER",
                "message": "plan_tier must be: essential, balanced, or max_protect"
            }
        )

    result = await calculate_premium(
        zone=request.zone,
        slots=request.slots,
        plan_tier=request.plan_tier,
        rider_tenure_days=request.rider_tenure_days,
        db=db
    )

    return PremiumResponse(**result)
