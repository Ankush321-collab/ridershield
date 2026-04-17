"""
Pydantic schemas for the Trigger Service API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
import uuid


class ActiveTrigger(BaseModel):
    trigger_id: str
    type: str
    zone: str
    zone_id: str
    threshold: str
    active_since: datetime
    affected_riders: int
    severity: str


class CommunitySignal(BaseModel):
    zone: str
    zone_id: str
    affected_pct: float
    threshold_pct: float = 70.0
    affected_riders: int
    total_riders: int
    detected_at: datetime


class TriggerStatusResponse(BaseModel):
    active_triggers: List[ActiveTrigger]
    community_signals: List[CommunitySignal]
    last_evaluation: datetime


class DisruptionEventOut(BaseModel):
    event_id: uuid.UUID
    trigger_type: str
    zone: str
    zone_id: uuid.UUID
    slot: str
    severity: str
    affected_riders: int
    data: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DisruptionEventListResponse(BaseModel):
    events: List[DisruptionEventOut]
    total: int


class InjectTriggerRequest(BaseModel):
    trigger_type: str = Field(
        ...,
        description="One of: heavy_rain, aqi_grap, traffic_congestion, store_closure, "
                    "platform_outage, regulatory_curfew, gps_shadowban, "
                    "dark_store_queue, algorithmic_shock, inventory_stockout, "
                    "road_closure, rwa_friction, civic_event, grap_vehicle_ban, "
                    "supply_cascade",
        examples=["heavy_rain"]
    )
    zone: str = Field(..., description="Zone name e.g. gachibowli", examples=["gachibowli"])
    duration_seconds: int = Field(1800, ge=60, le=86400)
    # Optional per-trigger overrides
    rainfall_mm: Optional[float] = Field(None, description="Override for heavy_rain trigger")
    congestion_index: Optional[int] = Field(None, description="Override for traffic trigger")


class InjectTriggerResponse(BaseModel):
    injected: bool
    event_id: uuid.UUID
    trigger_type: str
    zone: str
    zone_id: uuid.UUID
    affected_riders: int
    severity: str
    message: str
