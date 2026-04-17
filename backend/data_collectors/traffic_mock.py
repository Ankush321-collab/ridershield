"""
Traffic mock client — returns a realistic congestion_index (0-100)
and road_blocked flag per zone.
"""

import random
from datetime import datetime


# Demand multipliers by IST hour
_DEMAND_CURVE = [
    (0,  5,  0.3),   # 22:30–06:00 IST
    (6,  8,  0.5),   # 06:00–08:30 IST
    (9,  10, 0.9),   # 08:30–11:00 IST
    (11, 13, 1.1),   # 11:00–14:00 IST
    (14, 16, 0.6),   # 14:00–17:00 IST
    (17, 19, 1.4),   # 17:00–20:00 IST  ← peak
    (20, 22, 1.2),   # 20:00–22:30 IST
]


def _demand_multiplier(ist_hour: int) -> float:
    for h_start, h_end, mult in _DEMAND_CURVE:
        if h_start <= ist_hour <= h_end:
            return mult
    return 0.3


def fetch_traffic(zone: dict) -> dict:
    """Return mock traffic snapshot for a zone."""
    utc_hour = datetime.utcnow().hour
    ist_hour  = (utc_hour + 5) % 24   # rough IST

    mult       = _demand_multiplier(ist_hour)
    base_idx   = 40.0
    congestion = int(min(100, max(0, random.gauss(base_idx * mult, 12))))
    road_blocked = random.random() < 0.04   # 4% chance of road block

    return {
        "zone_id":        zone["id"],
        "zone_name":      zone["name"],
        "congestion_index": congestion,
        "road_blocked":   road_blocked,
        "source":         "mock_traffic",
        "time":           datetime.utcnow(),
    }
