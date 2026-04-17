"""
Shared Pydantic schemas — used across ALL services for inter-module communication.

These are the "contracts" between modules. If a schema is only used within
one service, define it in that service's own schemas.py instead.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


# ─── Enums ───────────────────────────────────────────

class Platform(str, Enum):
    ZEPTO = "zepto"
    BLINKIT = "blinkit"
    SWIGGY = "swiggy"


class PlanTier(str, Enum):
    ESSENTIAL = "essential"
    BALANCED = "balanced"
    MAX_PROTECT = "max_protect"


class PolicyStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ClaimType(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class ClaimStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    FLAGGED = "flagged"
    UNDER_REVIEW = "under_review"


class PayoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TriggerType(str, Enum):
    HEAVY_RAIN = "heavy_rain"
    AQI_GRAP = "aqi_grap"
    EXTREME_HEAT = "extreme_heat"
    TRAFFIC_CONGESTION = "traffic_congestion"
    ROAD_CLOSURE = "road_closure"
    CIVIC_EVENT = "civic_event"
    STORE_CLOSURE = "store_closure"
    INVENTORY_STOCKOUT = "inventory_stockout"
    SUPPLY_CASCADE = "supply_cascade"
    PLATFORM_OUTAGE = "platform_outage"
    REGULATORY_CURFEW = "regulatory_curfew"
    GRAP_VEHICLE_BAN = "grap_vehicle_ban"
    GPS_SHADOWBAN = "gps_shadowban"
    DARK_STORE_QUEUE = "dark_store_queue"
    RWA_FRICTION = "rwa_friction"
    ALGORITHMIC_SHOCK = "algorithmic_shock"
    COMMUNITY_SIGNAL = "community_signal"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


# ─── Shared Base Schemas ─────────────────────────────

class RiderBase(BaseModel):
    id: UUID
    phone: str
    name: str
    platform: Platform
    zone_id: UUID

    model_config = {"from_attributes": True}


class PolicyBase(BaseModel):
    id: UUID
    rider_id: UUID
    plan_tier: PlanTier
    week: str
    premium: int
    status: PolicyStatus

    model_config = {"from_attributes": True}


class DisruptionEventBase(BaseModel):
    id: UUID
    trigger_type: TriggerType
    zone_id: UUID
    slot_start: datetime
    severity: Severity

    model_config = {"from_attributes": True}


class ClaimBase(BaseModel):
    id: UUID
    rider_id: UUID
    policy_id: UUID
    type: ClaimType
    income_loss: int
    payout_amount: int
    status: ClaimStatus

    model_config = {"from_attributes": True}


class PayoutBase(BaseModel):
    id: UUID
    claim_id: UUID
    rider_id: UUID
    amount: int
    status: PayoutStatus

    model_config = {"from_attributes": True}


class TokenData(BaseModel):
    rider_id: UUID
    role: str  # "rider" | "admin" | "temp"


# ─── Error Response ──────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail
