"""
Dev 4: Claims Service Router
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.auth import get_current_rider
from claims_service.models import Claim
from claims_service.schemas import ClaimListItem, ClaimDetailResponse

router = APIRouter()


@router.get("", response_model=dict)
async def list_claims(rider=Depends(get_current_rider), db: AsyncSession = Depends(get_db)):
    """
    List all claims for the authenticated rider.
    """
    result = await db.execute(
        select(Claim).where(Claim.rider_id == rider.id).order_by(Claim.created_at.desc())
    )
    claims = result.scalars().all()
    
    return {
        "claims": [{
            "claim_id": str(c.id),
            "type": c.type,
            "disruption_type": c.disruption_type,
            "income_loss": c.income_loss,
            "payout_amount": c.payout_amount,
            "fraud_score": c.fraud_score,
            "status": c.status,
            "created_at": c.created_at
        } for c in claims]
    }


@router.get("/{claim_id}", response_model=ClaimDetailResponse)
async def get_claim(claim_id: UUID, rider=Depends(get_current_rider), db: AsyncSession = Depends(get_db)):
    """
    Get full breakdown for a specific claim.
    """
    result = await db.execute(
        select(Claim).where(Claim.id == claim_id, Claim.rider_id == rider.id)
    )
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    return ClaimDetailResponse(
        claim_id=claim.id,
        rider_id=claim.rider_id,
        policy_id=claim.policy_id,
        disruption_event_id=claim.disruption_event_id,
        type=claim.type,
        disruption_type=claim.disruption_type,
        income_loss=claim.income_loss,
        expected_earnings=claim.expected_earnings,
        actual_earnings=claim.actual_earnings,
        payout_amount=claim.payout_amount,
        fraud_score=claim.fraud_score,
        status=claim.status,
        created_at=claim.created_at,
        paid_at=claim.processed_at
    )
