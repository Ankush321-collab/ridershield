"""
APScheduler background scheduler — runs every 5 minutes.

Cycle:
  1. Poll weather for all zones           → store in weather_data
  2. Poll traffic for all zones           → store in platform_snapshots
  3. Poll platform simulator per rider    → store in platform_snapshots
  4. Evaluate all 5 triggers + community  → create DisruptionEvents
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from shared.database import AsyncSessionLocal
from shared.zones import get_all_zones
from data_collectors.weather_client import fetch_weather
from data_collectors.traffic_mock import fetch_traffic
from data_collectors.platform_simulator import get_rider_snapshot
from trigger_service.service import evaluate_all_zones
from trigger_service.models import WeatherData, PlatformSnapshot

scheduler = AsyncIOScheduler(timezone="UTC")
_cycle_count = 0


async def _run_cycle():
    global _cycle_count
    _cycle_count += 1
    print(f"\n[Scheduler] Cycle #{_cycle_count} - {datetime.now(timezone.utc).isoformat()}Z")

    async with AsyncSessionLocal() as db:
        weather_map:  dict = {}
        snapshot_map: dict = {}

        for zone in get_all_zones():
            zid   = zone["id"]
            zname = zone["name"]

            # ── 1. Weather ────────────────────────────────────────────────────
            try:
                w = await fetch_weather(zone)
                weather_map[zid] = w
                # Convert zid to UUID if it's a string
                z_uuid = uuid.UUID(zid) if isinstance(zid, str) else zid
                
                db.add(WeatherData(
                    id         = uuid.uuid4(),
                    time       = w["time"],
                    zone_id    = z_uuid,
                    zone_name  = zname,
                    temperature= w["temperature"],
                    rainfall_mm= w["rainfall_mm"],
                    aqi        = w.get("aqi"),
                    humidity   = w["humidity"],
                    wind_speed = w["wind_speed"],
                    heat_index = w.get("heat_index"),
                    source     = w["source"],
                ))
                print(f"  [Weather] {zname}: rain={w['rainfall_mm']}mm "
                      f"temp={w['temperature']}°C aqi={w.get('aqi')} src={w['source']}")
            except Exception as exc:
                print(f"  [Weather] ⚠️  {zname}: {exc}")

            # ── 2. Rider/Platform snapshots ───────────────────────────────────
            snaps = []
            for rid in zone["rider_ids"]:
                try:
                    snap = get_rider_snapshot(rid, zid)
                    # Merge traffic into snapshot
                    traffic = fetch_traffic(zone)
                    snap["congestion_index"] = traffic["congestion_index"]
                    snap["road_blocked"]     = traffic["road_blocked"]
                    snaps.append(snap)

                    # Convert rid, zid to UUID
                    r_uuid = uuid.UUID(rid) if isinstance(rid, str) else rid
                    z_uuid = uuid.UUID(zid) if isinstance(zid, str) else zid

                    db.add(PlatformSnapshot(
                        id                       = uuid.uuid4(),
                        time                     = snap["time"],
                        rider_id                 = r_uuid,
                        zone_id                  = z_uuid,
                        orders_per_hour          = snap["orders_per_hour"],
                        earnings_current_slot    = snap["earnings_current_slot"],
                        earnings_rolling_baseline= snap["earnings_rolling_baseline"],
                        earnings_per_order       = snap["earnings_per_order"],
                        surge_multiplier         = snap["surge_multiplier"],
                        order_rate_drop_pct      = snap["order_rate_drop_pct"],
                        rider_status             = snap["rider_status"],
                        store_status             = snap["store_status"],
                        stock_level              = snap["stock_level"],
                        platform_status          = snap["platform_status"],
                        shadowban_active         = snap["shadowban_active"],
                        shadowban_duration_min   = snap["shadowban_duration_min"],
                        allocation_anomaly       = snap["allocation_anomaly"],
                        curfew_active            = snap["curfew_active"],
                        grap_vehicle_ban         = snap.get("grap_vehicle_ban", False),
                        congestion_index         = snap["congestion_index"],
                        road_blocked             = snap["road_blocked"],
                        pickup_queue_depth       = snap["pickup_queue_depth"],
                        avg_pickup_wait_sec      = snap["avg_pickup_wait_sec"],
                        dispatch_latency_sec     = snap.get("dispatch_latency_sec"),
                    ))
                except Exception as exc:
                    print(f"  [Platform] ⚠️  rider={rid}: {exc}")

            snapshot_map[zid] = snaps
            print(f"  [Platform] {zname}: {len(snaps)} riders polled")

        await db.commit()

        # ── 3. Trigger evaluation ─────────────────────────────────────────────
        # Note: evaluate_all_zones might need to handle DB session differently 
        # based on existing patterns, but we pass the session here.
        await evaluate_all_zones(db, weather_map, snapshot_map)

    print(f"[Scheduler] ✅ Cycle #{_cycle_count} complete.\n")


def start_scheduler():
    scheduler.add_job(
        _run_cycle,
        trigger="interval",
        minutes=5,
        id="main_cycle",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),   # run immediately on startup
    )
    scheduler.start()
    print("[Scheduler] Started — polling every 5 minutes.")


def stop_scheduler():
    scheduler.shutdown(wait=False)
    print("[Scheduler] Stopped.")


def get_cycle_count() -> int:
    return _cycle_count


if __name__ == "__main__":
    import asyncio
    import signal

    async def main():
        print("[Scheduler] Standalone worker starting...")
        start_scheduler()
        
        # Keep the process alive
        stop_event = asyncio.Event()

        def stop_handler():
            print("\n[Scheduler] Stopping...")
            stop_scheduler()
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_handler)
            except NotImplementedError:
                # Signal handlers not implemented on Windows
                pass

        await stop_event.wait()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
