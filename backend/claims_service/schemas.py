"""
Dev 4: Claims Service Schemas
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from typing import Optional


class ClaimListItem(BaseModel):
    claim_id: UUID
    type: str
    disruption_type: Optional[str] = None
    income_loss: int
    payout_amount: int
    fraud_score: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ClaimDetailResponse(BaseModel):
    claim_id: UUID
    rider_id: UUID
    policy_id: UUID
    disruption_event_id: Optional[UUID] = None
    type: str
    disruption_type: Optional[str] = None
    income_loss: int
    expected_earnings: int
    actual_earnings: int
    payout_amount: int
    fraud_score: int
    status: str
    created_at: datetime
    paid_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ManualClaimInput(BaseModel):
    rider_id: UUID
    policy_id: UUID
    disruption_type: str
    description: Optional[str] = ""
    incident_time: datetime
    spam_score: int
    geo_valid: bool
    gps_distance_m: Optional[int] = None
    weather_match: Optional[bool] = None
    traffic_match: Optional[bool] = None


class ClaimResult(BaseModel):
    claim_id: UUID
    status: str
    payout_amount: int
