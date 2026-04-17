from typing import Dict, List, Optional

from pydantic import BaseModel


class PremiumRequest(BaseModel):
    zone: str
    slots: List[str]
    plan_tier: str
    rider_tenure_days: int


class SlotBreakdown(BaseModel):
    slot: str
    risk: int
    premium: int

    model_config = {"from_attributes": True}


class PremiumResponse(BaseModel):
    risk_score: int
    disruption_probability: float
    premium: Dict[str, int]
    explanation: str
    tenure_discount: float
    breakdown: List[SlotBreakdown]

    model_config = {"from_attributes": True}


class MLPredictRequest(BaseModel):
    zone_flood_risk: int
    zone_traffic_risk: int
    zone_store_risk: int
    day_of_week: int
    hour: int
    is_weekend: bool
    is_monsoon: bool
    rider_tenure_days: int
    rider_avg_earnings: float
    rider_order_consistency: float
    forecast_rainfall: float
    forecast_aqi: int


class MLPredictResponse(BaseModel):
    disruption_probability: float
    risk_band: str
    expected_earnings_multiplier: float

    model_config = {"from_attributes": True}
