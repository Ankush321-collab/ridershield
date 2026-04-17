"""
Trigger Service Router — 3 endpoints as specified in TASK-3:

  GET  /api/triggers/status          → active triggers + community signals
  GET  /api/disruption-events        → paginated event log with optional filter
  POST /api/triggers/inject          → demo-only instant disruption injection
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone
from typing import Optional
import uuid

from shared.database import get_db
from shared.auth import require_admin
from shared.zones import get_zone_by_name, get_all_zones
from trigger_service.models import DisruptionEvent
from trigger_service.schemas import (
    TriggerStatusResponse, ActiveTrigger, CommunitySignal,
    DisruptionEventOut, DisruptionEventListResponse,
    InjectTriggerRequest, InjectTriggerResponse,
)
from trigger_service.service import (
    get_active_triggers, get_community_signals, get_last_evaluation,
    inject_disruption_event,
)
from data_collectors.platform_simulator import (
    inject_scenario, DisruptionScenario, ScenarioKey,
)

router = APIRouter()


# ─── 1. GET /api/triggers/status ─────────────────────────────────────────────
@router.get("/status", response_model=TriggerStatusResponse, summary="Active triggers")
async def get_trigger_status():
    """
    Returns all currently active parametric triggers and community signals.
    Updated every 5 minutes by the background scheduler.
    """
    raw_triggers  = get_active_triggers()
    raw_signals   = get_community_signals()
    last_eval     = get_last_evaluation() or datetime.now(timezone.utc)

    active = [
        ActiveTrigger(
            trigger_id     = t["trigger_id"],
            type           = t["type"],
            zone           = t["zone"],
            zone_id        = t["zone_id"],
            threshold      = t["threshold"],
            active_since   = t["active_since"],
            affected_riders= t["affected_riders"],
            severity       = t["severity"],
        )
        for t in raw_triggers
    ]

    signals = [
        CommunitySignal(
            zone           = s["zone"],
            zone_id        = s["zone_id"],
            affected_pct   = s["affected_pct"],
            threshold_pct  = s["threshold_pct"],
            affected_riders= s["affected_riders"],
            total_riders   = s["total_riders"],
            detected_at    = s["detected_at"],
        )
        for s in raw_signals
    ]

    return TriggerStatusResponse(
        active_triggers   = active,
        community_signals = signals,
        last_evaluation   = last_eval,
    )


# ─── 2. GET /api/disruption-events ───────────────────────────────────────────
@router.get(
    "/disruption-events",
    response_model=DisruptionEventListResponse,
    summary="Disruption event log",
)
async def list_disruption_events(
    zone: Optional[str] = Query(None, description="Filter by zone name e.g. gachibowli"),
    trigger_type: Optional[str] = Query(None, description="Filter by trigger type"),
    from_ts: Optional[datetime] = Query(None, alias="from", description="ISO 8601 start time"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns paginated disruption events.
    Query: ?zone=koramangala&from=2026-03-30T00:00:00Z
    """
    stmt = select(DisruptionEvent).order_by(desc(DisruptionEvent.created_at))

    if zone:
        zone_obj = get_zone_by_name(zone)
        if not zone_obj:
            raise HTTPException(status_code=404, detail=f"Zone '{zone}' not found")
        stmt = stmt.where(DisruptionEvent.zone_id == uuid.UUID(zone_obj["id"]))

    if trigger_type:
        stmt = stmt.where(DisruptionEvent.trigger_type == trigger_type)

    if from_ts:
        stmt = stmt.where(DisruptionEvent.created_at >= from_ts)

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    events = [
        DisruptionEventOut(
            event_id    = r.id,
            trigger_type= r.trigger_type,
            zone        = r.zone_name or str(r.zone_id),
            zone_id     = r.zone_id,
            slot        = f"{r.slot_start.strftime('%H:%M')}-{r.slot_end.strftime('%H:%M')}",
            severity    = r.severity,
            affected_riders = r.affected_riders or 0,
            data        = r.data_json,
            created_at  = r.created_at,
        )
        for r in rows
    ]

    return DisruptionEventListResponse(events=events, total=len(events))


# ─── 3. POST /api/triggers/inject (demo only) ────────────────────────────────
_TRIGGER_TO_SCENARIO = {
    "heavy_rain":        ScenarioKey.HEAVY_RAIN,
    "aqi_grap":          ScenarioKey.AQI_GRAP,
    "store_closure":     ScenarioKey.STORE_CLOSURE,
    "platform_outage":   ScenarioKey.PLATFORM_OUTAGE,
    "gps_shadowban":     ScenarioKey.GPS_SHADOWBAN,
    "dark_store_queue":  ScenarioKey.DARK_STORE_QUEUE,
    "algorithmic_shock": ScenarioKey.ALGORITHMIC_SHOCK,
    "regulatory_curfew": ScenarioKey.REGULATORY_CURFEW,
    "inventory_stockout": ScenarioKey.INVENTORY_STOCKOUT,
    "road_closure":       ScenarioKey.ROAD_CLOSURE,
    "rwa_friction":       ScenarioKey.RWA_FRICTION,
    "civic_event":        ScenarioKey.CIVIC_EVENT,
    "grap_vehicle_ban":   ScenarioKey.GRAP_BAN,
    "supply_cascade":     ScenarioKey.SUPPLY_CASCADE,
    "traffic_congestion": None,   # handled by traffic mock
}

@router.post(
    "/inject",
    response_model=InjectTriggerResponse,
    summary="[DEMO] Inject a disruption instantly",
)
async def inject_trigger(
    body: InjectTriggerRequest,
    admin=Depends(require_admin), # CRITICAL: keep admin protection
    db: AsyncSession = Depends(get_db),
):
    """
    **Demo-only endpoint** — instantly creates a DisruptionEvent and
    activates the corresponding PlatformSimulator scenario.
    """
    zone_obj = get_zone_by_name(body.zone)
    if not zone_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{body.zone}' not found. Available: "
                   + ", ".join(z["name"] for z in get_all_zones())
        )

    zone_id   = zone_obj["id"]
    zone_name = zone_obj["name"]
    riders    = zone_obj["rider_ids"]

    # ── Activate simulator scenario ───────
    scenario_key = _TRIGGER_TO_SCENARIO.get(body.trigger_type)
    if scenario_key:
        inject_scenario(DisruptionScenario(
            key              = scenario_key,
            zone_id          = zone_id,
            duration_seconds = body.duration_seconds,
        ))

    # ── Create DB event immediately ───────────────────────────
    extra: dict = {"injected": True, "duration_seconds": body.duration_seconds}
    if body.trigger_type == "gps_shadowban":
        extra.update({
            "shadowban_active": True,
            "rider_status": "OFFLINE",
            "ban_applied": True,
            "confirmed": True,
            "allocation_anomaly": True,
        })
    if body.rainfall_mm is not None:
        extra["rainfall_mm"] = body.rainfall_mm
    if body.congestion_index is not None:
        extra["congestion_index"] = body.congestion_index

    # Note: inject_disruption_event expects zone_id as str
    event_id = await inject_disruption_event(
        db            = db,
        trigger_type  = body.trigger_type,
        zone_id       = zone_id,
        zone_name     = zone_name,
        affected_riders= len(riders),
        extra_data    = extra,
    )

    return InjectTriggerResponse(
        injected       = True,
        event_id       = event_id,
        trigger_type   = body.trigger_type,
        zone           = zone_name,
        zone_id        = uuid.UUID(zone_id),
        affected_riders= len(riders),
        severity       = _severity(body.trigger_type),
        message        = (
            f"Disruption '{body.trigger_type}' injected into zone '{zone_name}'. "
            f"Simulator active for {body.duration_seconds}s."
        ),
    )


def _severity(trigger_type: str) -> str:
    return {
        "heavy_rain": "high", "aqi_grap": "high", "traffic_congestion": "medium",
        "store_closure": "high", "platform_outage": "critical",
        "regulatory_curfew": "critical", "gps_shadowban": "medium",
        "dark_store_queue": "low", "algorithmic_shock": "medium",
        "inventory_stockout": "medium", "road_closure": "high",
        "rwa_friction": "low", "civic_event": "medium",
        "grap_vehicle_ban": "critical", "supply_cascade": "high",
    }.get(trigger_type, "medium")
