from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, UUID4, field_validator


class PlanTier(str, Enum):
    essential = "essential"
    balanced = "balanced"
    max_protect = "max_protect"


class PolicyStatus(str, Enum):
    active = "active"
    cancelled = "cancelled"
    expired = "expired"


class PolicyCreateRequest(BaseModel):
    plan_tier: PlanTier
    payment_method: str
    upi_id: Optional[str] = None

    @field_validator("plan_tier")
    @classmethod
    def validate_tier(cls, v):
        if v not in [t.value for t in PlanTier]:
            raise ValueError("plan_tier must be one of: essential, balanced, max_protect")
        return v


class PolicyRenewRequest(BaseModel):
    plan_tier: Optional[PlanTier] = None


class RiskBreakdown(BaseModel):
    weather: int
    traffic: int
    store: int

    model_config = {"from_attributes": True}


class QuoteTier(BaseModel):
    tier: str
    weekly_premium: int
    coverage_pct: int
    coverage_limit: int
    slots_covered: int
    risk_breakdown: RiskBreakdown

    model_config = {"from_attributes": True}


class QuoteResponse(BaseModel):
    quotes: List[QuoteTier]
    valid_until: datetime

    model_config = {"from_attributes": True}


class PolicyResponse(BaseModel):
    policy_id: str
    rider_id: str
    plan_tier: str
    week: str
    premium: int
    coverage_limit: int
    coverage_pct: int
    status: str
    slots_covered: List[str]
    coverage_used: int
    created_at: datetime
    expires_at: datetime
    claims_history: Optional[List[Dict]] = []

    model_config = {"from_attributes": True}


class ActivePolicyResponse(BaseModel):
    policy_id: str
    plan_tier: str
    week: str
    status: str
    slots_covered: List[str]
    hours_remaining: int
    coverage_used: int
    coverage_limit: int
    expires_at: datetime

    model_config = {"from_attributes": True}


class RenewResponse(BaseModel):
    policy_id: str
    previous_policy_id: str
    week: str
    new_premium: int
    status: str

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: Optional[str] = None

    model_config = {"from_attributes": True}
