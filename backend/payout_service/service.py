"""
Dev 4: Payout Service - Business Logic
"""

import logging
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from claims_service.models import Claim, Payout
from policy_service.models import Policy
from rider_service.models import Rider

logger = logging.getLogger("zylo.payouts")


async def process_upi_payout(claim_id: UUID, rider_id: UUID, amount: int, db: AsyncSession) -> Payout:
    """
    Simulates sending an instant UPI payment.
    Always succeeds and returns the created Payout record.
    Also incrementally updates the policy's coverage_used.
    """
    logger.info(f"Processing UPI payout of ₹{amount} for claim {claim_id}")

    # 1. Fetch Rider for UPI ID
    rider_result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = rider_result.scalar_one_or_none()
    upi_id = rider.upi_id if rider else "mock@upi"

    # 2. Fetch Claim to get policy_id
    claim_result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = claim_result.scalar_one_or_none()

    if claim and claim.policy_id:
        # 3. Update Policy coverage_used atomically
        policy_result = await db.execute(select(Policy).where(Policy.id == claim.policy_id))
        policy = policy_result.scalar_one_or_none()
        if policy:
            policy.coverage_used += amount
            db.add(policy)
            logger.info(f"Updated policy {policy.id} coverage_used +{amount} (now {policy.coverage_used})")

    # 4. Create Payout record
    payout = Payout(
        id=uuid4(),
        claim_id=claim_id,
        rider_id=rider_id,
        amount=amount,
        method="upi",
        upi_id=upi_id,
        status="completed",
        reference_id=f"UPI-{uuid4().hex[:12].upper()}",
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    
    db.add(payout)
    await db.flush()  # assign ID without full commit
    
    logger.info(f"Payout {payout.id} completed. Ref: {payout.reference_id}")
    return payout


async def get_rider_payouts(rider_id: UUID, db: AsyncSession) -> list[Payout]:
    """Fetch all payouts for a rider, descending by creation time."""
    result = await db.execute(
        select(Payout).where(Payout.rider_id == rider_id).order_by(Payout.created_at.desc())
    )
    return result.scalars().all()
