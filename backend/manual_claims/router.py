import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database import get_db
from shared.auth import get_current_rider
from policy_service.models import Policy, get_current_iso_week
from manual_claims.models import ManualClaim
from manual_claims.adjudication import adjudicate_manual_claim
from manual_claims.photo_handler import extract_exif_data
from manual_claims.geo_validation import (
    haversine_distance,
    calculate_spam_score,
)
from trigger_service.service import check_historical_conditions
from claims_service.service import process_manual_claim as dev4_process_manual_claim

router = APIRouter()

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("", status_code=201)
async def submit_manual_claim(
    disruption_type: str = Form(...),
    description: str = Form(""),
    incident_time: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    photo: UploadFile = File(...),
    rider=Depends(get_current_rider),
    db: AsyncSession = Depends(get_db),
):
    """
    Rider-facing manual claim submission with automated trust verification.
    """
    # 1. Validate Active Policy
    current_week = get_current_iso_week()
    policy_stmt = select(Policy).where(
        Policy.rider_id == rider.id,
        Policy.status == "active",
        Policy.week == current_week,
    ).order_by(Policy.created_at.desc())
    policy_result = await db.execute(policy_stmt)
    policy = policy_result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(status_code=400, detail="No active policy found for this rider.")

    # 2. Allow resubmission after rejection, but block duplicate open/resolved claims
    existing_stmt = select(ManualClaim).where(
        ManualClaim.policy_id == policy.id,
        ManualClaim.review_status.in_(["pending", "approved"])
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="A manual claim is already active for this policy period."
        )

    # 3. Save Photo
    file_ext = os.path.splitext(photo.filename)[1]
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    with open(file_path, "wb") as f:
        f.write(await photo.read())

    # 4. Extract EXIF & Validate
    exif_data = extract_exif_data(file_path)
    
    has_exif_gps = exif_data.get("lat") is not None and exif_data.get("lon") is not None
    has_exif_timestamp = exif_data.get("timestamp") is not None

    # Haversine distance: Photo GPS vs Declared GPS
    dist_m = haversine_distance(
        exif_data.get("lat"), exif_data.get("lon"),
        latitude, longitude
    )
    
    # Time delta
    incident_dt = datetime.fromisoformat(incident_time.replace('Z', '+00:00'))
    time_delta_min = 0
    if has_exif_timestamp:
        time_delta_min = abs((exif_data["timestamp"] - incident_dt.replace(tzinfo=None)).total_seconds() / 60)
    else:
        time_delta_min = 0

    # Corroboration from Dev 3
    conditions = await check_historical_conditions(str(rider.zone_id), incident_dt, db)
    
    # 5. Calculate Spam Score
    spam_score = calculate_spam_score(
        gps_distance_m=dist_m,
        time_delta_min=time_delta_min,
        disruption_type=disruption_type,
        weather_match=conditions.get("weather", False),
        traffic_match=conditions.get("traffic", False),
        exif_gps_available=has_exif_gps,
        exif_timestamp_available=has_exif_timestamp,
    )

    adjudication = await adjudicate_manual_claim(
        {
            "rider_id": rider.id,
            "policy_id": policy.id,
            "disruption_type": disruption_type,
            "description": description,
            "incident_time": incident_dt,
            "spam_score": spam_score,
            "gps_distance_m": int(dist_m) if dist_m < 999999 else None,
            "geo_valid": (dist_m < 500) if has_exif_gps else None,
            "weather_match": conditions.get("weather"),
            "traffic_match": conditions.get("traffic"),
            "time_delta_min": time_delta_min,
            "exif_gps_available": has_exif_gps,
            "exif_timestamp_available": has_exif_timestamp,
            "photo_path": file_path,
        },
        db=db,
    )
    review_status = adjudication.decision
    review_notes = (
        f"Auto-adjudicated by Nebius Kimi: {adjudication.reason_summary} "
        f"| confidence={adjudication.confidence:.2f} "
        f"| band={adjudication.threshold_context.get('band')} "
        f"| aligned={adjudication.threshold_context.get('aligned_with_threshold')} "
        f"| evidence={', '.join(adjudication.evidence_used) if adjudication.evidence_used else 'none'}"
    )

    # 6. Create Records
    dev4_result = await dev4_process_manual_claim(
        {
            "rider_id": rider.id,
            "policy_id": policy.id,
            "disruption_type": disruption_type,
            "incident_time": incident_dt,
            "spam_score": spam_score,
            "review_decision": review_status,
            "review_reason": adjudication.reason_summary,
        },
        db=db
    )
    dev4_claim_id = dev4_result["claim_id"]

    new_manual = ManualClaim(
        rider_id=rider.id,
        policy_id=policy.id,
        claim_id=uuid.UUID(dev4_claim_id),
        disruption_type=disruption_type,
        description=description,
        incident_time=incident_dt.replace(tzinfo=None),
        photo_path=file_path,
        photo_exif_lat=exif_data.get("lat"),
        photo_exif_lon=exif_data.get("lon"),
        telemetry_lat=latitude,
        telemetry_lon=longitude,
        gps_distance_m=int(dist_m) if dist_m < 999999 else None,
        spam_score=spam_score,
        geo_valid=(dist_m < 500) if has_exif_gps else False,
        weather_match=conditions.get("weather"),
        traffic_match=conditions.get("traffic"),
        review_status=review_status,
        reviewer_notes=review_notes,
        reviewed_at=datetime.utcnow(),
    )
    
    db.add(new_manual)
    await db.commit()
    
    return {
        "claim_id": dev4_claim_id,
        "manual_claim_id": str(new_manual.id),
        "status": review_status,
        "spam_score": spam_score,
        "message": adjudication.reason_summary,
        "confidence": adjudication.confidence,
        "evidence_used": adjudication.evidence_used,
        "threshold_context": adjudication.threshold_context,
    }

@router.get("/{claim_id}")
async def get_manual_claim(
    claim_id: uuid.UUID,
    rider=Depends(get_current_rider),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ManualClaim).where(ManualClaim.id == claim_id, ManualClaim.rider_id == rider.id)
    result = await db.execute(stmt)
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")
        
    return claim
