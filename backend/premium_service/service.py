import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings

ML_SERVICE_URL = settings.ML_SERVICE_URL
ML_TIMEOUT_SECONDS = float(os.getenv("ML_TIMEOUT_SECONDS", "0.8"))

TIER_MULTIPLIER = {
    "essential": 0.7,
    "balanced": 1.0,
    "max_protect": 1.3
}

TIER_COVERAGE_PCT = {
    "essential": 70,
    "balanced": 80,
    "max_protect": 90
}

BASE_PREMIUM_BY_BAND = {
    "low": 25,
    "medium": 40,
    "high": 55,
    "critical": 70
}

WEEKLY_PREMIUM_CAPS = {
    "essential": 99,
    "balanced": 129,
    "max_protect": 169,
}

DEMO_ZONE_DEFAULTS = {
    "koramangala": {"flood_risk_score": 80, "traffic_risk_score": 75, "store_risk_score": 65},
    "indiranagar": {"flood_risk_score": 75, "traffic_risk_score": 72, "store_risk_score": 62},
    "gachibowli": {"flood_risk_score": 85, "traffic_risk_score": 70, "store_risk_score": 60},
    "whitefield": {"flood_risk_score": 45, "traffic_risk_score": 50, "store_risk_score": 40},
    "pune_suburb": {"flood_risk_score": 20, "traffic_risk_score": 25, "store_risk_score": 15},
}


def parse_slot_hour(slot: str) -> int:
    """Parse '18:00-21:00' -> returns start hour 18"""
    return int(slot.split("-")[0].split(":")[0])


def is_monsoon_now() -> bool:
    return datetime.now(timezone.utc).month in [6, 7, 8, 9]


def get_day_of_week() -> int:
    return datetime.now(timezone.utc).weekday()


def calculate_tenure_discount(tenure_days: int) -> float:
    return round(min(tenure_days / 365, 0.15), 4)


def get_base_premium(risk_band: str) -> int:
    return BASE_PREMIUM_BY_BAND.get(risk_band, 100)


def get_zone_fallback(zone_name: str) -> Dict:
    zone_key = (zone_name or "").strip().lower()
    zone_defaults = DEMO_ZONE_DEFAULTS.get(
        zone_key,
        {"flood_risk_score": 50, "traffic_risk_score": 50, "store_risk_score": 50},
    )
    return {
        "flood_risk_score": zone_defaults["flood_risk_score"],
        "traffic_risk_score": zone_defaults["traffic_risk_score"],
        "store_risk_score": zone_defaults["store_risk_score"],
        "mock_rainfall": 5.0,
        "mock_aqi": 150,
        "found": False
    }


async def get_zone_risk_scores(zone_name: str, db: AsyncSession) -> Dict:
    """
    Fetch zone risk scores from the zones table.
    Returns dict with flood_risk_score, traffic_risk_score, store_risk_score.
    Falls back to medium-risk defaults if zone not found.
    """
    try:
        try:
            from backend.rider_service.models import Zone
        except ImportError:
            try:
                from rider_service.models import Zone
            except ImportError as exc:
                raise ImportError("Zone model not found - check Dev 1's models") from exc

        result = await db.execute(
            select(Zone).where(Zone.name.ilike(zone_name))
        )
        zone = result.scalar_one_or_none()

        if zone is None:
            return get_zone_fallback(zone_name)

        return {
            "flood_risk_score": getattr(zone, "flood_risk_score", 50),
            "traffic_risk_score": getattr(zone, "traffic_risk_score", 50),
            "store_risk_score": getattr(zone, "store_risk_score", 50),
            "mock_rainfall": 5.0,
            "mock_aqi": 150,
            "found": True
        }
    except Exception:
        return get_zone_fallback(zone_name)


async def call_ml_model(
    zone_data: Dict,
    slot: str,
    rider_tenure_days: int,
    rider_avg_earnings: float = 600.0
) -> Dict:
    """
    Call ML model server for a single slot's disruption prediction.
    Falls back to rule-based calculation if ML server is unavailable.
    """
    start_hour = parse_slot_hour(slot)
    day_of_week = get_day_of_week()

    payload = {
        "zone_flood_risk": zone_data["flood_risk_score"],
        "zone_traffic_risk": zone_data["traffic_risk_score"],
        "zone_store_risk": zone_data["store_risk_score"],
        "day_of_week": day_of_week,
        "hour": start_hour,
        "is_weekend": day_of_week >= 5,
        "is_monsoon": is_monsoon_now(),
        "rider_tenure_days": rider_tenure_days,
        "rider_avg_earnings": rider_avg_earnings,
        "rider_order_consistency": 0.75,
        "forecast_rainfall": zone_data.get("mock_rainfall", 5.0),
        "forecast_aqi": zone_data.get("mock_aqi", 150)
    }

    try:
        async with httpx.AsyncClient(timeout=ML_TIMEOUT_SECONDS) as client:
            response = await client.post(f"{ML_SERVICE_URL}/predict", json=payload)
            response.raise_for_status()
            return response.json()
    except Exception:
        return rule_based_fallback(zone_data)


def rule_based_fallback(zone_data: Dict) -> Dict:
    """Fallback when ML service is unavailable."""
    avg_risk = (
        zone_data["flood_risk_score"] +
        zone_data["traffic_risk_score"] +
        zone_data["store_risk_score"]
    ) / 3

    if avg_risk < 30:
        band, prob = "low", 0.20
    elif avg_risk < 55:
        band, prob = "medium", 0.45
    elif avg_risk < 75:
        band, prob = "high", 0.65
    else:
        band, prob = "critical", 0.85

    return {
        "disruption_probability": prob,
        "risk_band": band,
        "expected_earnings_multiplier": round(1.0 - prob * 0.6, 4),
        "explanation": f"Rule-based pricing (ML service unavailable). Zone risk: {avg_risk:.0f}/100."
    }


async def calculate_premium(
    zone: str,
    slots: List[str],
    plan_tier: str,
    rider_tenure_days: int,
    db: AsyncSession,
    rider_avg_earnings: float = 600.0,
) -> Dict:
    """
    Main premium calculation function.
    Returns full PremiumResponse data dict.
    """
    zone_data = await get_zone_risk_scores(zone, db)
    tenure_discount = calculate_tenure_discount(rider_tenure_days)

    slot_results = []
    total_disruption_prob = 0.0
    total_risk_score = 0

    for slot in slots:
        ml_result = await call_ml_model(zone_data, slot, rider_tenure_days, rider_avg_earnings)

        prob = ml_result["disruption_probability"]
        band = ml_result["risk_band"]
        base_prem = get_base_premium(band)
        risk_score = int(prob * 100)

        slot_premiums = {}
        for tier, multiplier in TIER_MULTIPLIER.items():
            slot_prem = base_prem * (1 - tenure_discount) * multiplier
            slot_premiums[tier] = round(slot_prem)

        slot_results.append({
            "slot": slot,
            "risk": risk_score,
            "premium": slot_premiums.get(plan_tier, slot_premiums["balanced"]),
            "disruption_probability": prob,
            "risk_band": band,
            "all_tier_premiums": slot_premiums
        })

        total_disruption_prob += prob
        total_risk_score += risk_score

    avg_prob = total_disruption_prob / len(slots)
    avg_risk = total_risk_score // len(slots)

    final_premiums = {}
    for tier in TIER_MULTIPLIER.keys():
        computed = sum(s["all_tier_premiums"][tier] for s in slot_results)
        final_premiums[tier] = min(computed, WEEKLY_PREMIUM_CAPS[tier])

    risk_breakdown = {
        "weather": zone_data["flood_risk_score"],
        "traffic": zone_data["traffic_risk_score"],
        "store": zone_data["store_risk_score"]
    }

    explanation = generate_premium_explanation(
        zone, slots, avg_prob, zone_data, tenure_discount, plan_tier
    )

    return {
        "risk_score": avg_risk,
        "zone_risk_score": int((
            zone_data["flood_risk_score"] +
            zone_data["traffic_risk_score"] +
            zone_data["store_risk_score"]
        ) / 3),
        "disruption_probability": round(avg_prob, 4),
        "premium": final_premiums,
        "explanation": explanation,
        "tenure_discount": tenure_discount,
        "breakdown": [{"slot": s["slot"], "risk": s["risk"], "premium": s["premium"]}
                      for s in slot_results],
        "risk_breakdown": risk_breakdown,
        "zone_found": zone_data.get("found", False)
    }


def generate_premium_explanation(zone, slots, avg_prob, zone_data, tenure_discount, tier) -> str:
    reasons = []
    if zone_data["flood_risk_score"] > 70:
        reasons.append(f"flood-prone zone (risk score {zone_data['flood_risk_score']}/100)")
    if zone_data["traffic_risk_score"] > 70:
        reasons.append(f"high traffic congestion ({zone_data['traffic_risk_score']}/100)")
    if is_monsoon_now():
        reasons.append("active monsoon season")
    if any(parse_slot_hour(s) >= 18 for s in slots):
        reasons.append("peak evening hours (6PM-11PM)")

    discount_str = f" A {tenure_discount*100:.0f}% loyalty discount has been applied." if tenure_discount > 0 else ""

    if not reasons:
        return (
            f"Standard risk conditions for {zone}. "
            f"Disruption probability: {avg_prob:.0%}.{discount_str}"
        )

    return (
        f"Premium for {zone} is higher due to: {', '.join(reasons)}. "
        f"Overall disruption probability: {avg_prob:.0%}.{discount_str}"
    )
