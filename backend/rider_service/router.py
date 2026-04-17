from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database import get_db
from shared.auth import get_current_rider, verify_token
from rider_service import service
from rider_service.schemas import (
    OTPRequest, OTPResponse, OTPVerifyRequest, OTPVerifyResponse,
    RiderRegisterRequest, RiderProfileResponse, RiskProfileResponse
)
from rider_service.models import RiderRiskProfile, Zone
from premium_service.service import calculate_premium as calculate_risk_premium
from policy_service.models import Policy
from trigger_service.models import PlatformSnapshot, DisruptionEvent
from ml.temporal import summarize_snapshot_series, build_next_week_forecast
from trigger_service.service import get_active_triggers

router = APIRouter()


def _slot_average_earnings(baselines, selected_slots: list[str]) -> float:
    if not baselines:
        return 600.0

    baseline_map = {b.slot_time: b.avg_earnings for b in baselines}
    matching = [baseline_map[slot] for slot in selected_slots if slot in baseline_map]
    if matching:
        return max(sum(matching) / len(matching), 1)

    all_values = [b.avg_earnings for b in baselines]
    return max(sum(all_values) / max(len(all_values), 1), 1)


# ─── POST /send-otp ─────────────────────────────────
@router.post("/send-otp", response_model=OTPResponse)
async def send_otp(request: OTPRequest):
    """Send OTP to phone number (mock)."""
    return await service.send_otp(request.phone)


# ─── POST /verify-otp ───────────────────────────────
@router.post("/verify-otp", response_model=OTPVerifyResponse)
async def verify_otp(request: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    """Verify OTP and log in existing riders directly, otherwise return a temporary token for registration."""
    result = await service.verify_otp(request.phone, request.otp, db)
    if not result["valid"]:
        error_code = result.get("error", "INVALID_OTP")
        message = "OTP expired or not found" if error_code == "OTP_EXPIRED" else "Invalid OTP"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": error_code, "message": message}
        )

    return result


# ─── POST /register ─────────────────────────────────
@router.post("/register", status_code=201, response_model=RiderProfileResponse)
async def register(
    request: RiderRegisterRequest, 
    authorization: str = Header(..., description="Bearer {temp_token}"),
    db: AsyncSession = Depends(get_db)
):
    """Create rider profile after OTP verification."""
    # 1. Verify temp token
    token = authorization.replace("Bearer ", "")
    payload = verify_token(token)
    
    if payload.get("role") != "temp":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALID", "message": "Invalid registration token"}
        )
    
    phone = payload.get("sub")
    
    from shared.schemas import Platform
    
    # 2. Validate platform
    valid_platforms = [p.value for p in Platform]
    if request.platform.lower() not in valid_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PLATFORM", "message": f"Platform must be one of: {', '.join(valid_platforms)}"}
        )
    
    # 3. Validate zone exists
    zone_result = await db.execute(select(Zone).where(Zone.id == request.zone_id))
    if not zone_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_ZONE", "message": "Zone does not exist"}
        )
    
    # 4. Call service
    data = request.model_dump()
    data["phone"] = phone
    
    try:
        return await service.register_rider(data, db)
    except Exception as e:
        # Handle duplicate phone or other DB errors
        if "unique constraint" in str(e).lower():
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "DUPLICATE_PHONE", "message": "Phone already registered"}
            )
        raise e


# ─── POST /onboard ──────────────────────────────────
@router.post("/onboard")
async def onboard(data: dict, rider=Depends(get_current_rider), db: AsyncSession = Depends(get_db)):
    """
    Generate earnings baseline and get premium quote.
    Queries rider's zone risk, then delegates premium calculation to premium_service.
    """
    from rider_service.models import RiderZoneBaseline

    # 1. Fetch zone risk data
    zone_result = await db.execute(select(Zone).where(Zone.id == rider.zone_id))
    zone = zone_result.scalar_one_or_none()

    # 2. Fetch rider's risk profile
    rp_result = await db.execute(
        select(RiderRiskProfile).where(RiderRiskProfile.rider_id == rider.id)
    )
    risk_profile = rp_result.scalar_one_or_none()

    # 3. Fetch baselines for slot breakdown
    bl_result = await db.execute(
        select(RiderZoneBaseline).where(RiderZoneBaseline.rider_id == rider.id)
    )
    baselines = bl_result.scalars().all()

    # 4. Call the real premium engine directly
    from datetime import datetime, timezone

    created_at = rider.created_at
    if getattr(created_at, "tzinfo", None) is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    rider_tenure_days = max((datetime.now(timezone.utc) - created_at).days, 0)

    selected_slots = data.get("typical_slots", ["18:00-21:00"])
    rider_avg_earnings = _slot_average_earnings(baselines, selected_slots)

    premium_response = await calculate_risk_premium(
        zone=zone.name if zone else rider.city,
        slots=selected_slots,
        plan_tier=data.get("plan_tier", "balanced"),
        rider_tenure_days=rider_tenure_days,
        db=db,
        rider_avg_earnings=rider_avg_earnings,
    )

    # 5. Build volatility label
    vol = float(risk_profile.income_volatility) if risk_profile else 0
    vol_label = "low" if vol < 0.3 else ("medium" if vol < 0.5 else "high")

    # 6. Build slot breakdown from real baselines (fallback to defaults)
    slot_breakdown = []
    if baselines:
        seen_slots = set()
        for b in baselines:
            if b.slot_time not in seen_slots:
                seen_slots.add(b.slot_time)
                slot_breakdown.append({
                    "slot": b.slot_time,
                    "expected_earnings": b.avg_earnings,
                    "risk_score": zone.composite_risk_score if zone else 0,
                })
    if not slot_breakdown:
        slot_breakdown = [
            {"slot": "18:00-21:00", "expected_earnings": 360, "risk_score": 75},
            {"slot": "21:00-23:00", "expected_earnings": 240, "risk_score": 68},
        ]

    return {
        "risk_profile": {
            "zone_risk_score": zone.composite_risk_score if zone else 0,
            "income_volatility": vol_label,
            "disruption_probability": float(risk_profile.disruption_probability) if risk_profile else 0,
            "explanation": f"Zone '{zone.name}' — flood risk {zone.flood_risk_score}, traffic risk {zone.traffic_risk_score}" if zone else "Zone data unavailable",
        },
        "premium_quote": {
            "essential": {"weekly": premium_response.get("premium", {}).get("essential", 99), "coverage": "70%"},
            "balanced": {"weekly": premium_response.get("premium", {}).get("balanced", 129), "coverage": "80%"},
            "max_protect": {"weekly": premium_response.get("premium", {}).get("max_protect", 169), "coverage": "90%"},
        },
        "slot_breakdown": slot_breakdown,
    }


# ─── GET /me ─────────────────────────────────────────
@router.get("/me", response_model=RiderProfileResponse)
async def get_me(rider=Depends(get_current_rider), db: AsyncSession = Depends(get_db)):
    """Return authenticated rider's full profile."""
    zone_result = await db.execute(select(Zone).where(Zone.id == rider.zone_id))
    zone = zone_result.scalar_one_or_none()
    return {
        "rider_id": rider.id,
        "name": rider.name,
        "phone": rider.phone,
        "platform": rider.platform,
        "city": rider.city,
        "zone_id": rider.zone_id,
        "zone": zone.name if zone else None,
        "upi_id": rider.upi_id,
        "kyc_status": rider.kyc_status,
        "trust_score": rider.trust_score
    }


# ─── GET /me/intelligence ─────────────────────────────
@router.get("/me/intelligence")
async def get_rider_intelligence(
    days: int = 7,
    rider=Depends(get_current_rider),
    db: AsyncSession = Depends(get_db),
):
    zone_result = await db.execute(select(Zone).where(Zone.id == rider.zone_id))
    zone = zone_result.scalar_one_or_none()

    risk_result = await db.execute(select(RiderRiskProfile).where(RiderRiskProfile.rider_id == rider.id))
    risk_profile = risk_result.scalar_one_or_none()

    snapshots = (
        await db.execute(
            select(PlatformSnapshot)
            .where(PlatformSnapshot.rider_id == rider.id)
            .order_by(PlatformSnapshot.time.desc())
            .limit(64)
        )
    ).scalars().all()
    snapshot_payload = [
        {
            "order_rate_drop_pct": s.order_rate_drop_pct,
            "congestion_index": s.congestion_index,
            "earnings_current_slot": s.earnings_current_slot,
        }
        for s in snapshots
    ]
    summary = summarize_snapshot_series(snapshot_payload)
    forecast = build_next_week_forecast(
        zone_risk_score=float(zone.composite_risk_score if zone else 55),
        disruption_probability=float(risk_profile.disruption_probability if risk_profile else 0.35),
        avg_order_drop_pct=float(summary["avg_order_drop_pct"]),
        earnings_volatility=float(summary["earnings_volatility"]),
        days=max(3, min(days, 14)),
    )

    active_policy = (
        await db.execute(
            select(Policy)
            .where(Policy.rider_id == rider.id, Policy.status == "active")
            .order_by(Policy.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    recent_events = (
        await db.execute(
            select(DisruptionEvent)
            .where(DisruptionEvent.zone_id == rider.zone_id)
            .order_by(DisruptionEvent.created_at.desc())
            .limit(5)
        )
    ).scalars().all()

    alerts: list[dict] = []
    high_risk_days = [d for d in forecast if d["predicted_disruption_probability"] >= 0.65]
    if high_risk_days:
        alerts.append(
            {
                "type": "high_risk_window",
                "severity": "high",
                "message": f"{len(high_risk_days)} high-risk day(s) expected in the next week.",
                "dates": [d["date"] for d in high_risk_days[:3]],
            }
        )

    active_zone_triggers = [t for t in get_active_triggers() if str(t.get("zone_id")) == str(rider.zone_id)]
    if active_zone_triggers:
        alerts.append(
            {
                "type": "active_zone_trigger",
                "severity": "medium",
                "message": f"{len(active_zone_triggers)} live disruption signal(s) in your zone.",
                "triggers": [t.get("type") for t in active_zone_triggers[:3]],
            }
        )

    if active_policy and active_policy.coverage_limit > 0:
        usage_ratio = float(active_policy.coverage_used or 0) / float(active_policy.coverage_limit)
        if usage_ratio >= 0.75:
            alerts.append(
                {
                    "type": "coverage_depletion_risk",
                    "severity": "medium",
                    "message": "Policy coverage usage has crossed 75%. Consider renewal planning.",
                    "coverage_used_ratio": round(usage_ratio, 3),
                }
            )

    return {
        "zone": zone.name if zone else rider.city,
        "next_week_forecast": forecast,
        "forward_alerts": alerts,
        "recent_zone_events": [
            {
                "trigger_type": e.trigger_type,
                "severity": e.severity,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "affected_riders": e.affected_riders,
            }
            for e in recent_events
        ],
    }


# ─── GET /me/risk-profile ───────────────────────────
@router.get("/me/risk-profile", response_model=RiskProfileResponse)
async def get_risk_profile(rider=Depends(get_current_rider), db: AsyncSession = Depends(get_db)):
    """Fetch RiderRiskProfile for this rider."""
    from rider_service.models import RiderZoneBaseline
    
    result = await db.execute(
        select(RiderRiskProfile).where(RiderRiskProfile.rider_id == rider.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Risk profile not found")

    # Fetch zone risks
    zone_result = await db.execute(select(Zone).where(Zone.id == rider.zone_id))
    zone = zone_result.scalar_one_or_none()

    # Fetch avg_per_slot from baselines dynamically instead of stubbing
    baseline_result = await db.execute(
        select(RiderZoneBaseline).where(RiderZoneBaseline.rider_id == rider.id)
    )
    baselines = baseline_result.scalars().all()
    
    avg_per_slot = {b.slot_time: b.avg_earnings for b in baselines}
    if not avg_per_slot:
        avg_per_slot = {"18:00-21:00": 360, "21:00-23:00": 240} # fallback

    return {
        "zone_flood_risk": zone.flood_risk_score if zone else 0,
        "zone_traffic_risk": zone.traffic_risk_score if zone else 0,
        "income_volatility": float(profile.income_volatility),
        "composite_risk_score": zone.composite_risk_score if zone else 0,
        "four_week_earnings": profile.four_week_earnings,
        "avg_per_slot": avg_per_slot
    }

# ─── GET /zones ──────────────────────────────────────
@router.get("/zones")
async def list_zones(db: AsyncSession = Depends(get_db)):
    """List available zones."""
    result = await db.execute(select(Zone))
    zones = result.scalars().all()
    return {"zones": [{"id": str(z.id), "name": z.name, "city": z.city, "risk_score": z.composite_risk_score} for z in zones]}
