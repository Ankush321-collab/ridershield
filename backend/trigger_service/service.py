"""
Trigger Service — core business logic.

Evaluates public/mock automated parametric triggers against live data snapshots:
  1. Heavy Rain          rainfall_mm > 40
  2. Extreme Heat        heat index > threshold
  3. Traffic Congestion  congestion_index > 80 for 60+ min
  4. Dark Store Closure  store_status = CLOSED
  5. Platform Outage     platform_status = DOWN
  6. Regulatory Curfew   curfew_active = TRUE
  7. GPS Shadowban       shadowban flag + duration anomaly
  8. Dark Store Queue    pickup wait and queue SLA breach
  9. Algorithmic Shock   allocation anomaly + order-rate collapse

Three-Factor Validation Gate:
  A DisruptionEvent is created ONLY when ALL 3 conditions are met:
  1. Trigger condition is TRUE
  2. Rider is ONLINE and in-zone (platform_status = ONLINE)
  3. Actual earnings fall below the rolling baseline

Also detects Community Signal: >70% of zone riders see order collapse.
"""

import uuid
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from trigger_service.models import DisruptionEvent, WeatherData, PlatformSnapshot
from shared.zones import get_zone_by_name, get_all_zones
from ml.temporal import smooth_threshold

# ─── In-memory trigger state ──────────────────────────────────────────────────
# Tracks how long a trigger has been active (for sustained-duration checks)
_trigger_active_since: dict[str, datetime] = {}   # key: "trigger_type:zone_id"
_active_triggers_cache: list[dict] = []            # filled each scheduler cycle
_community_signals_cache: list[dict] = []
_last_evaluation: Optional[datetime] = None
_civic_congestion_window: dict[str, list[tuple[datetime, int]]] = {}
_adaptive_threshold_cache: dict[str, dict] = {}
_adaptive_threshold_lock = asyncio.Lock()

# Dedup: zone+trigger+slot already created
_created_events: set[str] = set()   # "zone_id:trigger_type:slot_start_iso"


# ─── Trigger threshold constants ──────────────────────────────────────────────
RAIN_THRESHOLD_MM     = 40.0     # > 40mm / 1hr
HEAT_INDEX_THRESHOLD  = 32.0    # wet-bulb > 32°C
CONGESTION_THRESHOLD  = 80      # > 80/100
CONGESTION_DURATION   = 55      # minutes sustained (rounds run every 5 min)
COMMUNITY_PCT         = 0.70    # > 70% riders affected
EARNINGS_DROP_PCT     = 20.0    # must drop ≥ 20% vs baseline
SHADOWBAN_DURATION    = 30      # minutes
SHADOWBAN_CONFIRMATION_MIN = 10 # minutes before confirmation can lock
QUEUE_WAIT_THRESHOLD  = 300     # 5 min pickup wait SLA breach
QUEUE_DEPTH_THRESHOLD = 12
ALGO_DROP_THRESHOLD   = 50.0
AQI_GRAP_THRESHOLD = 300
STOCKOUT_ORDER_DROP_THRESHOLD = 40.0
RWA_DISPATCH_LATENCY_THRESHOLD = 300
RWA_ORDER_DROP_THRESHOLD = 30.0
CIVIC_CONGESTION_SPIKE = 90
CIVIC_SPIKE_WINDOW_MIN = 10
CIVIC_SPIKE_DELTA = 20
SUPPLY_CASCADE_ZONE_STOCKOUT_PCT = 0.50
SUPPLY_CASCADE_ORDER_DROP = 35.0


def _default_zone_thresholds() -> dict[str, float]:
    return {
        "rainfall_mm": RAIN_THRESHOLD_MM,
        "heat_index": HEAT_INDEX_THRESHOLD,
        "aqi": AQI_GRAP_THRESHOLD,
        "congestion_index": CONGESTION_THRESHOLD,
        "queue_wait_sec": QUEUE_WAIT_THRESHOLD,
        "queue_depth": QUEUE_DEPTH_THRESHOLD,
        "algo_drop_pct": ALGO_DROP_THRESHOLD,
    }


async def _self_calibrated_thresholds(db: AsyncSession, zone_id: str) -> dict[str, float]:
    now = datetime.now(timezone.utc)
    async with _adaptive_threshold_lock:
        cached = _adaptive_threshold_cache.get(zone_id)
        if cached and cached.get("expires_at") and cached["expires_at"] > now:
            return cached["thresholds"]

    defaults = _default_zone_thresholds()
    lookback = now - timedelta(days=14)

    weather_rows = (
        await db.execute(
            select(WeatherData).where(
                WeatherData.zone_id == uuid.UUID(zone_id),
                WeatherData.time >= lookback.replace(tzinfo=None),
            )
        )
    ).scalars().all()
    snapshot_rows = (
        await db.execute(
            select(PlatformSnapshot).where(
                PlatformSnapshot.zone_id == uuid.UUID(zone_id),
                PlatformSnapshot.time >= lookback.replace(tzinfo=None),
            )
        )
    ).scalars().all()

    rain = [float(w.rainfall_mm) for w in weather_rows if w.rainfall_mm is not None]
    heat = [float(w.heat_index) for w in weather_rows if w.heat_index is not None]
    aqi = [float(w.aqi) for w in weather_rows if w.aqi is not None]
    congestion = [float(s.congestion_index) for s in snapshot_rows if s.congestion_index is not None]
    queue_wait = [float(s.avg_pickup_wait_sec) for s in snapshot_rows if s.avg_pickup_wait_sec is not None]
    queue_depth = [float(s.pickup_queue_depth) for s in snapshot_rows if s.pickup_queue_depth is not None]
    algo_drop = [float(s.order_rate_drop_pct) for s in snapshot_rows if s.order_rate_drop_pct is not None]

    calibrated = {
        "rainfall_mm": round(
            smooth_threshold(defaults["rainfall_mm"], rain, floor=28.0, ceiling=70.0, percentile_rank=0.9), 2
        ),
        "heat_index": round(
            smooth_threshold(defaults["heat_index"], heat, floor=28.0, ceiling=40.0, percentile_rank=0.85), 2
        ),
        "aqi": round(
            smooth_threshold(defaults["aqi"], aqi, floor=220.0, ceiling=420.0, percentile_rank=0.9), 2
        ),
        "congestion_index": round(
            smooth_threshold(defaults["congestion_index"], congestion, floor=65.0, ceiling=95.0, percentile_rank=0.85), 2
        ),
        "queue_wait_sec": round(
            smooth_threshold(defaults["queue_wait_sec"], queue_wait, floor=180.0, ceiling=600.0, percentile_rank=0.8), 2
        ),
        "queue_depth": round(
            smooth_threshold(defaults["queue_depth"], queue_depth, floor=8.0, ceiling=25.0, percentile_rank=0.8), 2
        ),
        "algo_drop_pct": round(
            smooth_threshold(defaults["algo_drop_pct"], algo_drop, floor=30.0, ceiling=70.0, percentile_rank=0.85), 2
        ),
    }
    async with _adaptive_threshold_lock:
        _adaptive_threshold_cache[zone_id] = {
            "thresholds": calibrated,
            "expires_at": now + timedelta(minutes=30),
        }
    return calibrated


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _slot_now() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = now - timedelta(minutes=now.minute % 30, seconds=now.second)
    return start, start + timedelta(minutes=30)


def _dedup_key(zone_id: str, trigger_type: str, slot_start: datetime) -> str:
    return f"{zone_id}:{trigger_type}:{slot_start.isoformat()}"


def _trigger_key(trigger_type: str, zone_id: str) -> str:
    return f"{trigger_type}:{zone_id}"


# ─── Three-Factor Validation ───────────────────────────────────────────────────
def _three_factor_valid(snap: dict) -> bool:
    """
    True only when:
    1. Rider is ONLINE (factor 2 — in-zone confirmed by platform_status)
    2. Earnings drop ≥ threshold vs rolling baseline (factor 3)
    (Factor 1 is the trigger condition itself, checked by caller.)
    """
    if snap.get("rider_status") != "ONLINE":
        return False
    baseline = snap.get("earnings_rolling_baseline", 0) or 1
    current  = snap.get("earnings_current_slot", 0) or 0
    drop     = (baseline - current) / baseline * 100
    return drop >= EARNINGS_DROP_PCT


def _trigger_gate_valid(trigger_type: str, snap: dict) -> bool:
    """
    Trigger-aware gate validation.

    Most triggers use the standard three-factor rule. GPS shadowban is special:
    the platform can intentionally force rider OFFLINE first, so ONLINE is not
    required for this trigger.
    """
    if trigger_type == "gps_shadowban":
        baseline = snap.get("earnings_rolling_baseline", 0) or 1
        current = snap.get("earnings_current_slot", 0) or 0
        drop = (baseline - current) / baseline * 100
        ban_applied = bool(snap.get("shadowban_active")) and snap.get("rider_status") == "OFFLINE"
        return ban_applied and drop >= EARNINGS_DROP_PCT
    return _three_factor_valid(snap)


# ─── Per-trigger evaluators ───────────────────────────────────────────────────
def eval_heavy_rain(weather: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    limits = thresholds or _default_zone_thresholds()
    rain_threshold = limits["rainfall_mm"]
    rain = weather.get("rainfall_mm", 0) or 0
    if rain > rain_threshold:
        return {
            "trigger_type": "heavy_rain",
            "severity":     "high",
            "threshold":    f"{rain:.1f}mm/1hr > {rain_threshold:.1f}mm",
            "data":         {"rainfall_mm": rain, "temperature": weather.get("temperature")},
        }
    return None


def eval_heat(weather: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    limits = thresholds or _default_zone_thresholds()
    heat_threshold = limits["heat_index"]
    hi = weather.get("heat_index") or 0
    temp = weather.get("temperature") or 0
    if hi > heat_threshold or temp > 42:
        return {
            "trigger_type": "extreme_heat",
            "severity":     "medium",
            "threshold":    f"heat_index={hi}°C>{heat_threshold:.1f}°C or temp={temp}°C > 42°C",
            "data":         {"heat_index": hi, "temperature": temp},
        }
    return None


def eval_aqi(weather: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    limits = thresholds or _default_zone_thresholds()
    aqi_threshold = limits["aqi"]
    aqi = weather.get("aqi")
    if aqi is not None and aqi > aqi_threshold:
        return {
            "trigger_type": "aqi_grap",
            "severity": "high",
            "threshold": f"aqi={aqi} > {aqi_threshold:.0f}",
            "data": {
                "aqi": aqi,
                "pm2_5": weather.get("pm2_5"),
                "pm10": weather.get("pm10"),
            },
        }
    return None


def eval_traffic(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    limits = thresholds or _default_zone_thresholds()
    congestion_threshold = limits["congestion_index"]
    ci = snap.get("congestion_index", 0) or 0
    tk = _trigger_key("traffic_congestion", zone["id"])

    if ci > congestion_threshold:
        if tk not in _trigger_active_since:
            _trigger_active_since[tk] = datetime.now(timezone.utc)
        elapsed = (datetime.now(timezone.utc) - _trigger_active_since[tk]).total_seconds() / 60
        if elapsed >= CONGESTION_DURATION:
            return {
                "trigger_type": "traffic_congestion",
                "severity":     "medium",
                "threshold":    f"congestion={ci}/100>{congestion_threshold:.0f} sustained>={CONGESTION_DURATION}min",
                "data":         {"congestion_index": ci, "elapsed_min": elapsed},
            }
        return None   # not yet sustained
    else:
        _trigger_active_since.pop(tk, None)
        return None


def eval_stockout(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    drop_pct = snap.get("order_rate_drop_pct", 0) or 0
    if snap.get("stock_level") == "CRITICAL" and drop_pct >= STOCKOUT_ORDER_DROP_THRESHOLD:
        return {
            "trigger_type": "inventory_stockout",
            "severity":     "medium",
            "threshold":    f"stock=CRITICAL order_drop={drop_pct:.1f}%",
            "data":         {
                "stock_level": snap.get("stock_level"),
                "order_rate_drop_pct": drop_pct,
                "store_status": snap.get("store_status"),
            },
        }
    return None


def eval_road_closure(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    if snap.get("road_blocked") is True:
        return {
            "trigger_type": "road_closure",
            "severity":     "high",
            "threshold":    "road_blocked=TRUE",
            "data":         {
                "road_blocked": True,
                "congestion_index": snap.get("congestion_index"),
            },
        }
    return None


def eval_store_closure(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    if snap.get("store_status") == "CLOSED":
        return {
            "trigger_type": "store_closure",
            "severity":     "high",
            "threshold":    "store_status=CLOSED",
            "data":         {"store_status": "CLOSED", "stock_level": snap.get("stock_level")},
        }
    return None


def eval_platform_outage(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    if snap.get("platform_status") == "DOWN":
        return {
            "trigger_type": "platform_outage",
            "severity":     "critical",
            "threshold":    "platform_status=DOWN",
            "data":         {"platform_status": "DOWN"},
        }
    return None


def eval_curfew(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    if snap.get("curfew_active"):
        return {
            "trigger_type": "regulatory_curfew",
            "severity":     "critical",
            "threshold":    "curfew_active=TRUE",
            "data":         {"curfew_active": True},
        }
    return None


def eval_gps_shadowban(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    duration = snap.get("shadowban_duration_min", 0) or 0
    ban_applied = bool(snap.get("shadowban_active")) and snap.get("rider_status") == "OFFLINE"
    confirmed = bool(snap.get("allocation_anomaly")) or duration >= SHADOWBAN_CONFIRMATION_MIN

    # Shadowban flow is ban-first: rider is blocked from delivery, then confirmed.
    if ban_applied and confirmed:
        return {
            "trigger_type": "gps_shadowban",
            "severity":     "medium",
            "threshold":    f"shadowban_ban=TRUE confirm_after={duration}min",
            "data":         {
                "shadowban_duration_min": duration,
                "rider_status": snap.get("rider_status"),
                "ban_applied": ban_applied,
                "confirmed": confirmed,
                "allocation_anomaly": snap.get("allocation_anomaly", False),
            },
        }
    return None


def eval_dark_store_queue(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    limits = thresholds or _default_zone_thresholds()
    queue_wait_threshold = limits["queue_wait_sec"]
    queue_depth_threshold = limits["queue_depth"]
    wait_sec = snap.get("avg_pickup_wait_sec", 0) or 0
    queue_depth = snap.get("pickup_queue_depth", 0) or 0
    if wait_sec >= queue_wait_threshold and queue_depth >= queue_depth_threshold:
        return {
            "trigger_type": "dark_store_queue",
            "severity":     "low",
            "threshold":    f"wait={wait_sec}s>={queue_wait_threshold:.0f}s queue_depth={queue_depth}>={queue_depth_threshold:.0f}",
            "data":         {
                "avg_pickup_wait_sec": wait_sec,
                "pickup_queue_depth": queue_depth,
                "store_status": snap.get("store_status"),
            },
        }
    return None


def eval_algorithmic_shock(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    limits = thresholds or _default_zone_thresholds()
    algo_drop_threshold = limits["algo_drop_pct"]
    drop_pct = snap.get("order_rate_drop_pct", 0) or 0
    if snap.get("allocation_anomaly") and drop_pct >= algo_drop_threshold:
        return {
            "trigger_type": "algorithmic_shock",
            "severity":     "medium",
            "threshold":    f"allocation_anomaly=TRUE order_drop={drop_pct:.1f}%>={algo_drop_threshold:.1f}%",
            "data":         {
                "order_rate_drop_pct": drop_pct,
                "orders_per_hour": snap.get("orders_per_hour"),
                "dispatch_latency_sec": snap.get("dispatch_latency_sec"),
            },
        }
    return None


def eval_rwa_friction(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    latency = snap.get("dispatch_latency_sec", 0) or 0
    drop_pct = snap.get("order_rate_drop_pct", 0) or 0
    if latency >= RWA_DISPATCH_LATENCY_THRESHOLD and drop_pct >= RWA_ORDER_DROP_THRESHOLD:
        return {
            "trigger_type": "rwa_friction",
            "severity":     "low",
            "threshold":    f"dispatch_latency={latency}s order_drop={drop_pct:.1f}%",
            "data":         {
                "dispatch_latency_sec": latency,
                "order_rate_drop_pct": drop_pct,
            },
        }
    return None


def eval_civic_event(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    zone_id = zone["id"]
    now = datetime.now(timezone.utc)
    ci = snap.get("congestion_index", 0) or 0
    cutoff = now - timedelta(minutes=CIVIC_SPIKE_WINDOW_MIN)
    prev = [
        (ts, val)
        for ts, val in _civic_congestion_window.get(zone_id, [])
        if ts >= cutoff
    ]
    base = min((val for _, val in prev), default=ci)
    delta = ci - base

    _civic_congestion_window[zone_id] = [*prev, (now, ci)]

    if ci >= CIVIC_CONGESTION_SPIKE and delta >= CIVIC_SPIKE_DELTA:
        return {
            "trigger_type": "civic_event",
            "severity":     "medium",
            "threshold":    (
                f"congestion={ci}/100 delta={delta} "
                f"window={CIVIC_SPIKE_WINDOW_MIN}min"
            ),
            "data":         {
                "congestion_index": ci,
                "congestion_delta": delta,
                "road_blocked": bool(snap.get("road_blocked", False)),
            },
        }
    return None


def eval_grap_ban(snap: dict, zone: dict, thresholds: Optional[dict] = None) -> Optional[dict]:
    if snap.get("grap_vehicle_ban") is True:
        return {
            "trigger_type": "grap_vehicle_ban",
            "severity":     "critical",
            "threshold":    "grap_vehicle_ban=TRUE",
            "data":         {
                "grap_vehicle_ban": True,
                "curfew_active": bool(snap.get("curfew_active", False)),
            },
        }
    return None


# ─── Community Signal ──────────────────────────────────────────────────────────
def eval_community_signal(snapshots: list[dict], zone: dict) -> Optional[dict]:
    total = len(snapshots)
    if total == 0:
        return None
    affected = sum(
        1 for s in snapshots
        if (s.get("order_rate_drop_pct") or 0) >= 40
    )
    pct = affected / total * 100
    if pct > COMMUNITY_PCT * 100:
        return {
            "zone":            zone["name"],
            "zone_id":         zone["id"],
            "affected_pct":    round(pct, 1),
            "threshold_pct":   COMMUNITY_PCT * 100,
            "affected_riders": affected,
            "total_riders":    total,
            "detected_at":     datetime.now(timezone.utc),
        }
    return None


def eval_supply_cascade(snapshots: list[dict], zone: dict) -> Optional[dict]:
    total = len(snapshots)
    if total == 0:
        return None

    critical = [s for s in snapshots if s.get("stock_level") == "CRITICAL"]
    critical_ratio = len(critical) / total
    avg_drop = sum((s.get("order_rate_drop_pct") or 0) for s in snapshots) / total

    if critical_ratio >= SUPPLY_CASCADE_ZONE_STOCKOUT_PCT and avg_drop >= SUPPLY_CASCADE_ORDER_DROP:
        return {
            "trigger_type": "supply_cascade",
            "severity":     "high",
            "threshold":    (
                f"critical_stock_pct={critical_ratio*100:.1f}% avg_order_drop={avg_drop:.1f}%"
            ),
            "data":         {
                "critical_stock_pct": round(critical_ratio * 100, 1),
                "avg_order_rate_drop_pct": round(avg_drop, 1),
                "critical_riders": len(critical),
                "total_riders": total,
            },
        }
    return None


# ─── Main evaluation loop (called by scheduler) ───────────────────────────────
async def evaluate_all_zones(db: AsyncSession, weather_map: dict, snapshot_map: dict):
    """
    weather_map:   zone_id → weather dict
    snapshot_map:  zone_id → list[rider_snapshot dict]

    Creates DisruptionEvent rows in DB for every valid trigger that passes
    the three-factor gate.  Deduplicates by zone+trigger+slot.
    """
    global _active_triggers_cache, _community_signals_cache, _last_evaluation

    new_active  = []
    new_signals = []
    slot_start, slot_end = _slot_now()

    for zone in get_all_zones():
        zid    = zone["id"]
        zname  = zone["name"]
        snaps  = snapshot_map.get(zid, [])
        weather= weather_map.get(zid, {})
        zone_thresholds = await _self_calibrated_thresholds(db, zid)

        # ── Weather triggers (zone-level, no per-rider gate) ──────────────────
        for eval_fn in (eval_heavy_rain, eval_heat, eval_aqi):
            result = eval_fn(weather, zone, zone_thresholds)
            if result:
                dk = _dedup_key(zid, result["trigger_type"], slot_start)
                if dk not in _created_events:
                    affected = len([s for s in snaps if s.get("rider_status") == "ONLINE"])
                    event_id = await _create_event(
                        db, result, zid, zname, slot_start, slot_end, affected
                    )
                    _created_events.add(dk)
                    new_active.append({
                        "trigger_id":      str(event_id),
                        "type":            result["trigger_type"],
                        "zone":            zname,
                        "zone_id":         zid,
                        "threshold":       result["threshold"],
                        "active_since":    datetime.now(timezone.utc),
                        "affected_riders": affected,
                        "severity":        result["severity"],
                    })

        # ── Rider-level triggers (need three-factor gate) ─────────────────────
        rider_trigger_counts: dict[str, int] = {}
        rider_trigger_samples: dict[str, dict] = {}

        for snap in snaps:
            for eval_fn in (
                eval_traffic,
                eval_stockout,
                eval_road_closure,
                eval_store_closure,
                eval_platform_outage,
                eval_curfew,
                eval_gps_shadowban,
                eval_dark_store_queue,
                eval_algorithmic_shock,
                eval_rwa_friction,
                eval_civic_event,
                eval_grap_ban,
            ):
                result = eval_fn(snap, zone, zone_thresholds)
                if result:
                    if _trigger_gate_valid(result["trigger_type"], snap):
                        ttype = result["trigger_type"]
                        if ttype == "civic_event" and rider_trigger_counts.get("traffic_congestion", 0) > 0:
                            continue
                        rider_trigger_counts[ttype] = rider_trigger_counts.get(ttype, 0) + 1
                        rider_trigger_samples.setdefault(ttype, result)

        for ttype, count in rider_trigger_counts.items():
            dk = _dedup_key(zid, ttype, slot_start)
            if dk not in _created_events:
                # Rebuild result dict from a relevant snap
                if not snaps: continue
                sample_snap = snaps[0]
                sample_result = rider_trigger_samples.get(ttype, {})
                sample_data = sample_result.get("data", {}) if isinstance(sample_result, dict) else {}
                result_data = {
                    "trigger_type": ttype,
                    "severity":     _severity_for(ttype),
                    "threshold":    sample_result.get("threshold", _threshold_for(ttype, sample_snap, zone_thresholds)),
                    "data":         {**sample_data, "affected_count": count},
                }
                event_id = await _create_event(
                    db, result_data, zid, zname, slot_start, slot_end, count
                )
                _created_events.add(dk)
                new_active.append({
                    "trigger_id":      str(event_id),
                    "type":            ttype,
                    "zone":            zname,
                    "zone_id":         zid,
                    "threshold":       result_data["threshold"],
                    "active_since":    datetime.now(timezone.utc),
                    "affected_riders": count,
                    "severity":        result_data["severity"],
                })

        # ── Community signal ───────────────────────────────────────────────────
        sig = eval_community_signal(snaps, zone)
        if sig:
            new_signals.append(sig)
            # Also persist as a disruption event
            dk = _dedup_key(zid, "community_signal", slot_start)
            if dk not in _created_events:
                event_id = await _create_event(
                    db,
                    {"trigger_type": "community_signal", "severity": "high",
                     "threshold": f">{COMMUNITY_PCT*100:.0f}% riders affected",
                     "data": sig},
                    zid, zname, slot_start, slot_end, sig["affected_riders"]
                )
                _created_events.add(dk)

        cascade = eval_supply_cascade(snaps, zone)
        if cascade:
            dk = _dedup_key(zid, cascade["trigger_type"], slot_start)
            if dk not in _created_events:
                event_id = await _create_event(
                    db,
                    cascade,
                    zid,
                    zname,
                    slot_start,
                    slot_end,
                    cascade["data"]["critical_riders"],
                )
                _created_events.add(dk)
                new_active.append({
                    "trigger_id":      str(event_id),
                    "type":            cascade["trigger_type"],
                    "zone":            zname,
                    "zone_id":         zid,
                    "threshold":       cascade["threshold"],
                    "active_since":    datetime.now(timezone.utc),
                    "affected_riders": cascade["data"]["critical_riders"],
                    "severity":        cascade["severity"],
                })

    _active_triggers_cache  = new_active
    _community_signals_cache = new_signals
    _last_evaluation = datetime.now(timezone.utc)


# ─── Instant injection (used by demo endpoint) ────────────────────────────────
async def inject_disruption_event(
    db: AsyncSession,
    trigger_type: str,
    zone_id: str,
    zone_name: str,
    affected_riders: int,
    extra_data: dict,
) -> uuid.UUID:
    slot_start, slot_end = _slot_now()
    severity = _severity_for(trigger_type)
    result = {
        "trigger_type": trigger_type,
        "severity":     severity,
        "threshold":    str(extra_data),
        "data":         extra_data,
    }
    event_id = await _create_event(
        db, result, zone_id, zone_name, slot_start, slot_end, affected_riders
    )
    # Update active cache
    _active_triggers_cache.append({
        "trigger_id":      str(event_id),
        "type":            trigger_type,
        "zone":            zone_name,
        "zone_id":         zone_id,
        "threshold":       str(extra_data),
        "active_since":    datetime.now(timezone.utc),
        "affected_riders": affected_riders,
        "severity":        severity,
    })
    return event_id


# ─── DB writer ────────────────────────────────────────────────────────────────
def _json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


async def _create_event(
    db: AsyncSession,
    result: dict,
    zone_id: str,
    zone_name: str,
    slot_start: datetime,
    slot_end: datetime,
    affected_riders: int,
) -> uuid.UUID:
    event_id = uuid.uuid4()
    # Convert zone_id string to UUID if needed
    z_id = uuid.UUID(zone_id) if isinstance(zone_id, str) else zone_id
    
    # Strip tzinfo for postgres without timezone
    if slot_start and slot_start.tzinfo:
        slot_start = slot_start.replace(tzinfo=None)
    if slot_end and slot_end.tzinfo:
        slot_end = slot_end.replace(tzinfo=None)
        
    event = DisruptionEvent(
        id            = event_id,
        trigger_type  = result["trigger_type"],
        zone_id       = z_id,
        zone_name     = zone_name,
        slot_start    = slot_start,
        slot_end      = slot_end,
        severity      = result["severity"],
        data_json     = _json_safe(result.get("data")),
        affected_riders = affected_riders,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    claims_created = 0
    try:
        from claims_service.service import process_auto_claims

        claims_created = await process_auto_claims(event_id, db)
    except Exception as exc:
        print(f"[TriggerService] Auto-claims failed for event {event_id}: {exc}")
    print(f"[TriggerService] ✅ DisruptionEvent created: {result['trigger_type']} @ {zone_name} "
          f"({claims_created} claims anchored)")
    return event_id


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _severity_for(trigger_type: str) -> str:
    return {
        "heavy_rain":        "high",
        "extreme_heat":      "medium",
        "traffic_congestion":"medium",
        "store_closure":     "high",
        "platform_outage":   "critical",
        "regulatory_curfew": "critical",
        "community_signal":  "high",
        "gps_shadowban":     "medium",
        "dark_store_queue":  "low",
        "algorithmic_shock": "medium",
        "aqi_grap":          "high",
        "inventory_stockout":"medium",
        "road_closure":      "high",
        "rwa_friction":      "low",
        "civic_event":       "medium",
        "grap_vehicle_ban":  "critical",
        "supply_cascade":    "high",
    }.get(trigger_type, "medium")


def _threshold_for(trigger_type: str, snap: dict, thresholds: Optional[dict] = None) -> str:
    limits = thresholds or _default_zone_thresholds()
    return {
        "traffic_congestion": f"congestion={snap.get('congestion_index')}/100>{limits['congestion_index']:.0f}",
        "store_closure":      "store_status=CLOSED",
        "platform_outage":    "platform_status=DOWN",
        "regulatory_curfew":  "curfew_active=TRUE",
        "gps_shadowban":      f"shadowban_duration={snap.get('shadowban_duration_min')}min",
        "dark_store_queue":   f"wait={snap.get('avg_pickup_wait_sec')}s>={limits['queue_wait_sec']:.0f}s",
        "algorithmic_shock":  f"order_drop={snap.get('order_rate_drop_pct')}%>={limits['algo_drop_pct']:.1f}%",
        "aqi_grap":           f"aqi>{limits['aqi']:.0f}",
        "inventory_stockout": f"stock=CRITICAL order_drop={snap.get('order_rate_drop_pct')}%",
        "road_closure":       "road_blocked=TRUE",
        "rwa_friction":       (
            f"dispatch_latency={snap.get('dispatch_latency_sec')}s "
            f"order_drop={snap.get('order_rate_drop_pct')}%"
        ),
        "civic_event":        f"congestion={snap.get('congestion_index')}/100 spike>=90",
        "grap_vehicle_ban":   "grap_vehicle_ban=TRUE",
        "supply_cascade":     ">=50% riders critical stock + avg drop>=35%",
    }.get(trigger_type, "—")


# ─── Cache reads (used by router) ──────────────────────────────────────────────
def get_active_triggers() -> list:
    return _active_triggers_cache


def get_community_signals() -> list:
    return _community_signals_cache


def get_last_evaluation() -> Optional[datetime]:
    return _last_evaluation


async def get_zone_thresholds(db: AsyncSession, zone_id: str) -> dict[str, float]:
    return await _self_calibrated_thresholds(db, zone_id)


async def check_historical_conditions(zone_id: str, incident_time: datetime, db: AsyncSession) -> dict:
    """Historical corroboration for manual claims."""
    # Convert zone_id string to UUID if needed
    import uuid
    from datetime import timedelta
    z_id = uuid.UUID(zone_id) if isinstance(zone_id, str) else zone_id
    
    # Check weather data within +/- 30 minutes
    start_time = incident_time - timedelta(minutes=30)
    end_time = incident_time + timedelta(minutes=30)
    
    # Weather
    weather_stmt = select(WeatherData).where(
        WeatherData.zone_id == z_id,
        WeatherData.time >= start_time,
        WeatherData.time <= end_time,
        WeatherData.rainfall_mm > RAIN_THRESHOLD_MM
    ).limit(1)
    weather_res = await db.execute(weather_stmt)
    has_weather = bool(weather_res.scalar_one_or_none())
    
    # Traffic (Platform Snapshots)
    traffic_stmt = select(PlatformSnapshot).where(
        PlatformSnapshot.zone_id == z_id,
        PlatformSnapshot.time >= start_time,
        PlatformSnapshot.time <= end_time,
        PlatformSnapshot.congestion_index > CONGESTION_THRESHOLD
    ).limit(1)
    traffic_res = await db.execute(traffic_stmt)
    has_traffic = bool(traffic_res.scalar_one_or_none())
    
    return {"weather": has_weather, "traffic": has_traffic}
