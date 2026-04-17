from typing import List, Optional, Dict
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from rider_service.phone_utils import normalize_indian_mobile

# ─── OTP Schemas ────────────────────────────────────

class OTPRequest(BaseModel):
    phone: str = Field(..., example="+919876543210")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_indian_mobile(value)

class OTPResponse(BaseModel):
    message: str
    expires_in: int
    dev_otp: Optional[str] = None

class OTPVerifyRequest(BaseModel):
    phone: str
    otp: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_indian_mobile(value)

class OTPVerifyResponse(BaseModel):
    valid: bool
    temp_token: Optional[str] = None
    jwt_token: Optional[str] = None
    is_registered: bool = False


# ─── Registration Schemas ──────────────────────────

class RiderRegisterRequest(BaseModel):
    name: str
    platform: str
    city: str
    zone_id: UUID
    upi_id: Optional[str] = None
    slots: List[str]  # e.g., ["18:00-21:00", "21:00-23:00"]

class RiderProfileResponse(BaseModel):
    rider_id: UUID
    name: str
    phone: str
    platform: str
    city: str
    zone_id: UUID
    zone: Optional[str] = None
    upi_id: Optional[str] = None
    kyc_status: str
    trust_score: int
    jwt_token: Optional[str] = None


# ─── Onboarding Schemas ───────────────────────────

class OnboardRequest(BaseModel):
    typical_slots: List[str]
    plan_tier: str = "balanced"

class SlotRisk(BaseModel):
    slot: str
    expected_earnings: int
    risk_score: int

class RiskProfileResponse(BaseModel):
    zone_flood_risk: int
    zone_traffic_risk: int
    income_volatility: float
    composite_risk_score: int
    four_week_earnings: Optional[Dict[str, int]] = None
    avg_per_slot: Dict[str, int]
