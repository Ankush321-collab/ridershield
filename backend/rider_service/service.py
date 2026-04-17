import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import create_temp_token, create_access_token
from rider_service.models import Rider, RiderRiskProfile, RiderZoneBaseline, Zone
from rider_service.otp_provider import send_otp_code, verify_otp_code


def _slot_hours(slot: str) -> int:
    start_raw, end_raw = slot.split("-")
    start_hour = int(start_raw.split(":")[0])
    end_hour = int(end_raw.split(":")[0])
    return max(end_hour - start_hour, 1)


def _slot_multiplier(slot: str) -> float:
    start_hour = int(slot.split("-")[0].split(":")[0])
    if 18 <= start_hour < 21:
        return 1.15
    if 21 <= start_hour < 23:
        return 0.95
    if 8 <= start_hour < 11:
        return 1.05
    return 0.9


async def _get_zone(db: AsyncSession, zone_id: uuid.UUID) -> Zone | None:
    zone_result = await db.execute(select(Zone).where(Zone.id == zone_id))
    return zone_result.scalar_one_or_none()


async def send_otp(phone: str) -> dict:
    """Generate and dispatch a free/demo OTP."""
    return await send_otp_code(phone)


async def verify_otp(phone: str, otp: str, db: AsyncSession) -> dict:
    """Verify OTP, logging in existing riders directly and onboarding new riders with a temp token."""
    valid, error_code = await verify_otp_code(phone, otp)

    if not valid:
        return {"valid": False, "temp_token": None, "error": error_code or "INVALID_OTP"}

    rider_result = await db.execute(select(Rider).where(Rider.phone == phone))
    rider = rider_result.scalar_one_or_none()
    if rider:
        return {
            "valid": True,
            "temp_token": None,
            "jwt_token": create_access_token(data={"sub": str(rider.id), "role": "rider"}),
            "is_registered": True,
            "error": None,
        }

    return {
        "valid": True,
        "temp_token": create_temp_token(phone),
        "jwt_token": None,
        "is_registered": False,
        "error": None,
    }


async def register_rider(data: dict, db: AsyncSession) -> dict:
    """
    Finalize registration: Create Rider and RiderRiskProfile.
    Expected data: {name, platform, city, zone_id, slots, upi_id, phone}
    """
    rider = Rider(
        phone=data["phone"],
        name=data["name"],
        platform=data["platform"],
        city=data["city"],
        zone_id=data["zone_id"],
        upi_id=data.get("upi_id"),
        kyc_status="verified",
        trust_score=85,
    )
    db.add(rider)
    await db.flush()

    zone = await _get_zone(db, data["zone_id"])
    zone_risk = zone.composite_risk_score if zone else 50
    traffic_risk = zone.traffic_risk_score if zone else 50
    weekly_anchor = 3200 + zone_risk * 8

    risk_profile = RiderRiskProfile(
        rider_id=rider.id,
        zone_id=rider.zone_id,
        income_volatility=round(min(max((traffic_risk + zone_risk) / 200, 0.2), 0.75), 2),
        disruption_probability=round(min(max(zone_risk / 100, 0.15), 0.85), 2),
        four_week_earnings={
            "week_12": weekly_anchor + 240,
            "week_11": weekly_anchor - 120,
            "week_10": weekly_anchor - 320,
            "week_9": weekly_anchor + 80,
        },
    )
    db.add(risk_profile)

    await generate_baseline(rider.id, rider.zone_id, data["slots"], db)

    await db.commit()
    await db.refresh(rider)

    token = create_access_token(data={"sub": str(rider.id), "role": "rider"})

    return {
        "rider_id": rider.id,
        "name": rider.name,
        "phone": rider.phone,
        "city": rider.city,
        "platform": rider.platform,
        "zone_id": rider.zone_id,
        "kyc_status": rider.kyc_status,
        "trust_score": rider.trust_score,
        "jwt_token": token,
    }


async def generate_baseline(rider_id: uuid.UUID, zone_id: uuid.UUID, slots: list, db: AsyncSession):
    """Generate slot baselines from zone risk and selected working slots."""
    current_week = datetime.now().strftime("%Y-W%V")
    zone = await _get_zone(db, zone_id)
    zone_risk = zone.composite_risk_score if zone else 50
    traffic_risk = zone.traffic_risk_score if zone else 50
    flood_risk = zone.flood_risk_score if zone else 50
    base_hourly = 150 + round((traffic_risk * 0.35) + (zone_risk * 0.15))

    for slot in slots:
        hours = _slot_hours(slot)
        avg_earnings = int(round(base_hourly * hours * _slot_multiplier(slot)))
        avg_orders = max(int(round((avg_earnings / 35) * (1 - (flood_risk / 500)))), 4)
        baseline = RiderZoneBaseline(
            rider_id=rider_id,
            zone_id=zone_id,
            week=current_week,
            slot_time=slot,
            avg_earnings=avg_earnings,
            avg_orders=avg_orders,
        )
        db.add(baseline)
