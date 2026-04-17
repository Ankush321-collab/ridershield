import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.policy_service.schemas import QuoteResponse
    from backend.policy_service.service import get_policy_quote
except ImportError:
    from policy_service.schemas import QuoteResponse
    from policy_service.service import get_policy_quote

from shared.auth import get_current_rider
from shared.database import get_db


router = APIRouter(prefix="/api/policies", tags=["Policies"])


@router.get("/quote", response_model=QuoteResponse)
async def get_quote(
    slots: str = Query(..., description="Comma-separated slots: '18:00-21:00,21:00-23:00'"),
    city: str = Query(default="bengaluru"),
    current_rider=Depends(get_current_rider),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dynamic premium quotes for all 3 tiers.
    Query: ?slots=18:00-21:00,21:00-23:00&city=bengaluru
    """
    slot_list = [s.strip() for s in slots.split(",") if s.strip()]

    if not slot_list:
        raise HTTPException(status_code=400, detail="At least one slot is required")

    slot_pattern = re.compile(r"^\d{2}:\d{2}-\d{2}:\d{2}$")
    for slot in slot_list:
        if not slot_pattern.match(slot):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid slot format: '{slot}'. Expected: HH:MM-HH:MM"
            )

    result = await get_policy_quote(
        rider_id=str(current_rider.id),
        slots=slot_list,
        db=db,
        city=city
    )
    return QuoteResponse(**result)
