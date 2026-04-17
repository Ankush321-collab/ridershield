"""
Dev 4: Payout Service Schemas
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from typing import Optional


class PayoutListItem(BaseModel):
    payout_id: UUID
    claim_id: UUID
    amount: int
    method: str
    upi_id: Optional[str] = None
    status: str
    reference_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
