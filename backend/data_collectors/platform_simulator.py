"""
Platform Simulator — mimics Zepto / Blinkit / Swiggy Instamart APIs.

Implements exactly the statistical model described in README §10.3:
- Orders/hr: Normal(μ=10, σ=2.5) × time-of-day multiplier
- Earnings/order: LogNormal(μ=18, σ=5)
- Store status: Markov chain OPEN→DEGRADED→CLOSED
- Dispatch latency: Gamma(k=2, θ=45s)
- Pickup queue: Poisson(λ=4 normal / λ=12 stockout)
- Surge: discrete distribution

Uses a deterministic seed per (rider_id, zone_id, iso_week) for
reproducibility.  DisruptionScenario object overrides distributions.
"""

import random
import math
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


# ─── Disruption scenario keys ─────────────────────────────────────────────────
class ScenarioKey:
    HEAVY_RAIN        = "HEAVY_RAIN"
    AQI_GRAP          = "AQI_GRAP"
    STORE_CLOSURE     = "STORE_CLOSURE"
    PLATFORM_OUTAGE   = "PLATFORM_OUTAGE"
    GPS_SHADOWBAN     = "GPS_SHADOWBAN"
    DARK_STORE_QUEUE  = "DARK_STORE_QUEUE"
    ALGORITHMIC_SHOCK = "ALGORITHMIC_SHOCK"
    REGULATORY_CURFEW = "REGULATORY_CURFEW"
    INVENTORY_STOCKOUT = "INVENTORY_STOCKOUT"
    ROAD_CLOSURE       = "ROAD_CLOSURE"
    RWA_FRICTION       = "RWA_FRICTION"
    CIVIC_EVENT        = "CIVIC_EVENT"
    GRAP_BAN           = "GRAP_BAN"
    SUPPLY_CASCADE     = "SUPPLY_CASCADE"


@dataclass
class DisruptionScenario:
    key: str
    zone_id: Optional[str] = None
    rider_id: Optional[str] = None       # None = zone-wide
    duration_seconds: int = 1800
    injected_at: datetime = field(default_factory=datetime.utcnow)
    rainfall_mm: Optional[float] = None  # for HEAVY_RAIN injection override


# ─── Active injected scenarios (in-memory store) ──────────────────────────────
_active_scenarios: list[DisruptionScenario] = []


def inject_scenario(scenario: DisruptionScenario):
    """Called by the demo inject endpoint to override simulator output."""
    _active_scenarios.append(scenario)


def clear_expired_scenarios():
    now = datetime.utcnow()
    before = len(_active_scenarios)
    _active_scenarios[:] = [
        s for s in _active_scenarios
        if (now - s.injected_at).total_seconds() < s.duration_seconds
    ]


def _active_scenario_for(zone_id: str, rider_id: str) -> Optional[DisruptionScenario]:
    clear_expired_scenarios()
    for s in reversed(_active_scenarios):
        zone_match  = s.zone_id is None or s.zone_id == zone_id
        rider_match = s.rider_id is None or s.rider_id == rider_id
        if zone_match and rider_match:
            return s
    return None


# ─── Time-of-day multiplier ───────────────────────────────────────────────────
_DEMAND = [(0,5,0.3),(6,8,0.5),(9,10,0.9),(11,13,1.1),(14,16,0.6),(17,19,1.4),(20,22,1.2)]


def _demand_mult(utc_hour: int) -> float:
    ist = (utc_hour + 5) % 24
    for lo, hi, m in _DEMAND:
        if lo <= ist <= hi:
            return m
    return 0.3


# ─── Statistical helpers ──────────────────────────────────────────────────────
def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def _lognormal(rng: random.Random, mu: float, sigma: float) -> float:
    return rng.lognormvariate(math.log(mu), sigma / mu)


def _gamma_approx(rng: random.Random, k: int, theta: float) -> float:
    """Approximate Gamma(k, θ) as sum of k Exponential(1/θ)."""
    return sum(-theta * math.log(max(rng.random(), 1e-9)) for _ in range(k))


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth Poisson generator."""
    L = math.exp(-lam)
    k, p = 0, 1.0
    while p > L:
        k += 1
        p *= rng.random()
    return k - 1


def _surge(rng: random.Random) -> float:
    r = rng.random()
    if r < 0.70: return 1.0
    if r < 0.85: return 1.25
    if r < 0.95: return 1.5
    if r < 0.99: return 2.0
    return 2.5


# ─── Store Markov state (in-memory per zone) ─────────────────────────────────
_store_states: dict[str, str] = {}   # zone_id → "OPEN" / "DEGRADED" / "CLOSED"


def _store_transition(zone_id: str, rng: random.Random) -> str:
    state = _store_states.get(zone_id, "OPEN")
    r = rng.random()
    if state == "OPEN":
        if r < 0.02:   state = "DEGRADED"
    elif state == "DEGRADED":
        if r < 0.15:   state = "CLOSED"
        elif r < 0.45: state = "OPEN"
    elif state == "CLOSED":
        if r < 0.30:   state = "OPEN"
    _store_states[zone_id] = state
    return state


# ─── Public: get_rider_snapshot ───────────────────────────────────────────────
def get_rider_snapshot(rider_id: str, zone_id: str) -> dict:
    """
    Returns a PlatformSnapshot dict for the given rider/zone.
    """
    now   = datetime.utcnow()
    iso_week = now.isocalendar()[1]
    seed  = abs(hash(f"{rider_id}:{zone_id}:{iso_week}:{now.hour}:{now.minute // 5}"))
    rng   = _rng(seed)

    mult  = _demand_mult(now.hour)
    scenario = _active_scenario_for(zone_id, rider_id)

    # ── Defaults ──────────────────────────────────────────────────────────────
    orders_hr      = max(0, int(rng.gauss(10 * mult, 2.5)))
    earn_per_order = max(12, int(_lognormal(rng, 18, 5)))
    surge          = _surge(rng)
    baseline       = rng.randint(80, 250)   # rider's rolling 4-week average
    current_earn   = min(300, orders_hr * earn_per_order)
    drop_pct       = max(0.0, round((baseline - current_earn) / max(baseline, 1) * 100, 1))
    store          = _store_transition(zone_id, rng)
    stock          = "NORMAL" if store == "OPEN" else ("LOW" if store == "DEGRADED" else "CRITICAL")
    platform       = "UP"
    shadowban      = False
    shadow_dur     = 0
    alloc_anomaly  = False
    curfew         = False
    grap_vehicle_ban = False
    dispatch_lat   = int(_gamma_approx(rng, 2, 45))
    queue_depth    = _poisson(rng, 4)
    wait_sec       = max(30, int(_gamma_approx(rng, 2, 90)))
    rider_status   = "ONLINE" if rng.random() > 0.1 else "OFFLINE"
    congestion     = int(min(100, max(0, rng.gauss(40 * mult, 12))))
    road_blocked   = rng.random() < 0.04

    # ── Scenario overrides ────────────────────────────────────────────────────
    if scenario:
        k = scenario.key

        if k == ScenarioKey.HEAVY_RAIN:
            orders_hr     = max(0, int(orders_hr * rng.uniform(0.20, 0.35)))
            current_earn  = orders_hr * earn_per_order
            drop_pct      = max(0.0, round((baseline - current_earn) / max(baseline,1)*100, 1))
            if rng.random() < 0.10:
                rider_status = "OFFLINE"

        elif k == ScenarioKey.AQI_GRAP:
            drop_pct_ = rng.uniform(40, 60)
            orders_hr = max(0, int(orders_hr * (1 - drop_pct_ / 100)))
            current_earn = orders_hr * earn_per_order
            drop_pct = max(drop_pct_, round((baseline - current_earn) / max(baseline, 1) * 100, 1))
            if rng.random() < 0.30:
                rider_status = "OFFLINE"

        elif k == ScenarioKey.STORE_CLOSURE:
            store         = "CLOSED"
            stock         = "CRITICAL"
            orders_hr     = 0
            current_earn  = 0
            drop_pct      = 100.0
            _store_states[zone_id] = "CLOSED"

        elif k == ScenarioKey.PLATFORM_OUTAGE:
            platform      = "DOWN"
            orders_hr     = 0
            current_earn  = 0
            drop_pct      = 100.0

        elif k == ScenarioKey.GPS_SHADOWBAN:
            shadowban     = True
            shadow_dur    = min(120, int((now - scenario.injected_at).total_seconds() // 60))
            rider_status  = "OFFLINE"
            orders_hr     = 0
            current_earn  = 0
            alloc_anomaly = True

        elif k == ScenarioKey.DARK_STORE_QUEUE:
            queue_depth   = rng.randint(15, 25)
            wait_sec      = rng.randint(320, 900)   # > 300s SLA

        elif k == ScenarioKey.ALGORITHMIC_SHOCK:
            alloc_anomaly = True
            drop_pct_     = rng.uniform(50, 70)
            orders_hr     = max(0, int(orders_hr * (1 - drop_pct_ / 100)))
            current_earn  = orders_hr * earn_per_order
            drop_pct      = drop_pct_

        elif k == ScenarioKey.REGULATORY_CURFEW:
            curfew        = True
            rider_status  = "OFFLINE"
            orders_hr     = 0
            current_earn  = 0
            drop_pct      = 100.0

        elif k == ScenarioKey.INVENTORY_STOCKOUT:
            store         = "DEGRADED"
            stock         = "CRITICAL"
            drop_pct_     = rng.uniform(30, 50)
            orders_hr     = max(0, int(orders_hr * (1 - drop_pct_ / 100)))
            current_earn  = orders_hr * earn_per_order
            drop_pct      = max(drop_pct_, round((baseline - current_earn) / max(baseline, 1) * 100, 1))

        elif k == ScenarioKey.ROAD_CLOSURE:
            road_blocked  = True
            drop_pct_     = rng.uniform(50, 70)
            orders_hr     = max(0, int(orders_hr * (1 - drop_pct_ / 100)))
            current_earn  = orders_hr * earn_per_order
            drop_pct      = max(drop_pct_, round((baseline - current_earn) / max(baseline, 1) * 100, 1))

        elif k == ScenarioKey.RWA_FRICTION:
            dispatch_lat  = rng.randint(320, 600)
            drop_pct_     = rng.uniform(25, 40)
            orders_hr     = max(0, int(orders_hr * (1 - drop_pct_ / 100)))
            current_earn  = orders_hr * earn_per_order
            drop_pct      = max(drop_pct_, round((baseline - current_earn) / max(baseline, 1) * 100, 1))

        elif k == ScenarioKey.CIVIC_EVENT:
            congestion    = rng.randint(90, 100)
            road_blocked  = rng.random() < 0.20
            drop_pct_     = rng.uniform(40, 60)
            orders_hr     = max(0, int(orders_hr * (1 - drop_pct_ / 100)))
            current_earn  = orders_hr * earn_per_order
            drop_pct      = max(drop_pct_, round((baseline - current_earn) / max(baseline, 1) * 100, 1))

        elif k == ScenarioKey.GRAP_BAN:
            grap_vehicle_ban = True
            curfew        = rng.random() < 0.60
            if curfew:
                rider_status = "OFFLINE"
            drop_pct_     = rng.uniform(60, 80)
            orders_hr     = max(0, int(orders_hr * (1 - drop_pct_ / 100)))
            current_earn  = orders_hr * earn_per_order
            drop_pct      = max(drop_pct_, round((baseline - current_earn) / max(baseline, 1) * 100, 1))

        elif k == ScenarioKey.SUPPLY_CASCADE:
            stock         = "CRITICAL"
            drop_pct_     = rng.uniform(50, 70)
            orders_hr     = max(0, int(orders_hr * (1 - drop_pct_ / 100)))
            current_earn  = orders_hr * earn_per_order
            drop_pct      = max(drop_pct_, round((baseline - current_earn) / max(baseline, 1) * 100, 1))

    return {
        "time":                    now,
        "rider_id":                rider_id,
        "zone_id":                 zone_id,
        "orders_per_hour":         orders_hr,
        "earnings_current_slot":   current_earn,
        "earnings_rolling_baseline": baseline,
        "earnings_per_order":      earn_per_order,
        "surge_multiplier":        surge,
        "order_rate_drop_pct":     drop_pct,
        "rider_status":            rider_status,
        "store_status":            store,
        "stock_level":             stock,
        "platform_status":         platform,
        "shadowban_active":        shadowban,
        "shadowban_duration_min":  shadow_dur,
        "allocation_anomaly":      alloc_anomaly,
        "curfew_active":           curfew,
        "grap_vehicle_ban":        grap_vehicle_ban,
        "congestion_index":        congestion,
        "road_blocked":            road_blocked,
        "pickup_queue_depth":      queue_depth,
        "avg_pickup_wait_sec":     wait_sec,
        "dispatch_latency_sec":    dispatch_lat,
    }
