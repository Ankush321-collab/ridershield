"""
Dev 4: Payout Service Router
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.auth import get_current_rider
from payout_service.service import get_rider_payouts

router = APIRouter()


@router.get("", response_model=dict)
async def list_payouts(rider=Depends(get_current_rider), db: AsyncSession = Depends(get_db)):
    """
    List payouts for the authenticated rider.
    """
    payouts = await get_rider_payouts(rider.id, db)
    return {
        "payouts": [{
            "payout_id": str(p.id),
            "claim_id": str(p.claim_id),
            "amount": p.amount,
            "method": p.method,
            "upi_id": p.upi_id,
            "status": p.status,
            "reference_id": p.reference_id,
            "created_at": p.created_at
        } for p in payouts]
    }
