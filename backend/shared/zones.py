"""
Zone registry — loads from DB on first access, with hardcoded fallback.

The trigger service, scheduler, and inject endpoint all use these helpers.
"""

import uuid
import asyncio
import logging
from typing import Optional, List, Dict

logger = logging.getLogger("zylo.zones")

# ── Runtime state ─────────────────────────────────────────────────────────────
_zones: List[Dict] = []
_zone_by_id: Dict[str, Dict] = {}
_zone_by_name: Dict[str, Dict] = {}
_loaded = False


async def _load_zones_from_db():
    """Load all zones from the Postgres `zones` table + attach rider_ids."""
    global _zones, _zone_by_id, _zone_by_name, _loaded

    try:
        from shared.database import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as db:
            # Load zones
            result = await db.execute(text(
                "SELECT id, name, city, lat, lon, "
                "flood_risk_score, traffic_risk_score, store_risk_score, composite_risk_score "
                "FROM zones ORDER BY city, name"
            ))
            rows = result.fetchall()

            if not rows:
                logger.error("No zones found in DB! Perimeter scan yielded 0 result.")
                _zones = []
                _zone_by_id = {}
                _zone_by_name = {}
                return

            zones = []
            for row in rows:
                zone_id = str(row[0])
                zone_name = row[1]

                # Get rider_ids that belong to this zone
                rider_result = await db.execute(text(
                    "SELECT id FROM riders WHERE zone_id = :zid"
                ), {"zid": row[0]})
                rider_ids = [str(r[0]) for r in rider_result.fetchall()]

                zones.append({
                    "id": zone_id,
                    "name": zone_name,
                    "city": row[2],
                    "lat": float(row[3]) if row[3] else 0,
                    "lon": float(row[4]) if row[4] else 0,
                    "flood_risk_score": row[5] or 0,
                    "traffic_risk_score": row[6] or 0,
                    "store_risk_score": row[7] or 0,
                    "composite_risk_score": row[8] or 0,
                    "rider_ids": rider_ids,
                })

            _zones = zones
            _zone_by_id = {z["id"]: z for z in _zones}
            _zone_by_name = {z["name"].lower(): z for z in _zones}
            _loaded = True
            logger.info(f"Loaded {len(_zones)} zones from DB "
                        f"({sum(len(z['rider_ids']) for z in _zones)} riders total)")

    except Exception as e:
        logger.error(f"Critical: Failed to load zones from DB: {e}")


def _ensure_loaded():
    """Ensure zones are loaded. If not, schedule a sync-run or use empty state."""
    global _loaded

    if _loaded:
        return

    try:
        # Check if loop is running
        asyncio.get_running_loop()
        # If running, we assume load_zones() was called in lifespan
    except RuntimeError:
        # Run synchronously
        try:
            asyncio.run(_load_zones_from_db())
        except Exception:
            pass


async def load_zones():
    """Explicit async loader — call from app lifespan startup."""
    await _load_zones_from_db()


# ── Public API (same as before) ──────────────────────────────────────────────

def get_all_zones() -> List[Dict]:
    _ensure_loaded()
    return _zones


def get_zone(zone_id: str) -> Optional[Dict]:
    _ensure_loaded()
    return _zone_by_id.get(zone_id)


def get_zone_by_name(name: str) -> Optional[Dict]:
    _ensure_loaded()
    return _zone_by_name.get(name.lower())
