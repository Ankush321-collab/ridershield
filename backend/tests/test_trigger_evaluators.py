import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trigger_service.service import (
    _civic_congestion_window,
    _trigger_gate_valid,
    _trigger_active_since,
    eval_aqi,
    eval_civic_event,
    eval_grap_ban,
    eval_gps_shadowban,
    eval_road_closure,
    eval_rwa_friction,
    eval_stockout,
    eval_supply_cascade,
    eval_traffic,
)


ZONE = {"id": "11111111-1111-1111-1111-111111111111", "name": "test-zone"}


def test_eval_stockout_variants():
    assert eval_stockout({"stock_level": "CRITICAL", "order_rate_drop_pct": 45.0}, ZONE) is not None
    assert eval_stockout({"stock_level": "CRITICAL", "order_rate_drop_pct": 20.0}, ZONE) is None
    assert eval_stockout({"stock_level": "LOW", "order_rate_drop_pct": 50.0}, ZONE) is None


def test_eval_aqi_threshold_boundary():
    assert eval_aqi({"aqi": 300}, ZONE) is None
    hit = eval_aqi({"aqi": 301, "pm2_5": 120.5, "pm10": 240.0}, ZONE)
    assert hit is not None
    assert hit["trigger_type"] == "aqi_grap"


def test_eval_road_closure_immediate_and_traffic_guard():
    _trigger_active_since.clear()

    road_hit = eval_road_closure({"road_blocked": True, "congestion_index": 20}, ZONE)
    assert road_hit is not None
    assert road_hit["trigger_type"] == "road_closure"

    # Congestion should still require sustained duration.
    traffic = eval_traffic({"road_blocked": False, "congestion_index": 95}, ZONE)
    assert traffic is None


def test_eval_rwa_friction_threshold_boundary():
    assert eval_rwa_friction({"dispatch_latency_sec": 300, "order_rate_drop_pct": 30.0}, ZONE) is not None
    assert eval_rwa_friction({"dispatch_latency_sec": 299, "order_rate_drop_pct": 30.0}, ZONE) is None


def test_eval_civic_event_threshold():
    _civic_congestion_window.clear()

    # First reading only establishes baseline and should not fire.
    assert eval_civic_event({"congestion_index": 70, "road_blocked": False}, ZONE) is None
    # Sharp jump within window should fire.
    assert eval_civic_event({"congestion_index": 92, "road_blocked": False}, ZONE) is not None

    _civic_congestion_window.clear()
    assert eval_civic_event({"congestion_index": 89, "road_blocked": False}, ZONE) is None


def test_eval_grap_ban():
    assert eval_grap_ban({"grap_vehicle_ban": True, "curfew_active": False}, ZONE) is not None
    assert eval_grap_ban({"grap_vehicle_ban": False}, ZONE) is None


def test_eval_gps_shadowban_ban_first_confirmation():
    # Ban applied but no confirmation signal yet.
    assert eval_gps_shadowban(
        {
            "shadowban_active": True,
            "rider_status": "OFFLINE",
            "shadowban_duration_min": 4,
            "allocation_anomaly": False,
        },
        ZONE,
    ) is None

    # Ban applied + confirmation by anomaly.
    hit = eval_gps_shadowban(
        {
            "shadowban_active": True,
            "rider_status": "OFFLINE",
            "shadowban_duration_min": 3,
            "allocation_anomaly": True,
        },
        ZONE,
    )
    assert hit is not None
    assert hit["trigger_type"] == "gps_shadowban"


def test_shadowban_trigger_gate_allows_offline_banned_rider():
    snap = {
        "shadowban_active": True,
        "rider_status": "OFFLINE",
        "earnings_current_slot": 0,
        "earnings_rolling_baseline": 100,
    }
    assert _trigger_gate_valid("gps_shadowban", snap) is True

    # Generic triggers still require ONLINE via standard 3-factor rule.
    assert _trigger_gate_valid("traffic_congestion", snap) is False


def test_eval_supply_cascade_ratio_and_drop():
    snapshots_fire = [
        {"stock_level": "CRITICAL", "order_rate_drop_pct": 40.0},
        {"stock_level": "CRITICAL", "order_rate_drop_pct": 35.0},
        {"stock_level": "CRITICAL", "order_rate_drop_pct": 38.0},
        {"stock_level": "NORMAL", "order_rate_drop_pct": 30.0},
        {"stock_level": "NORMAL", "order_rate_drop_pct": 32.0},
    ]
    assert eval_supply_cascade(snapshots_fire, ZONE) is not None

    snapshots_no_fire = [
        {"stock_level": "CRITICAL", "order_rate_drop_pct": 45.0},
        {"stock_level": "CRITICAL", "order_rate_drop_pct": 40.0},
        {"stock_level": "NORMAL", "order_rate_drop_pct": 30.0},
        {"stock_level": "NORMAL", "order_rate_drop_pct": 30.0},
        {"stock_level": "NORMAL", "order_rate_drop_pct": 30.0},
    ]
    assert eval_supply_cascade(snapshots_no_fire, ZONE) is None
