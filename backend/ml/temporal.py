from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def percentile_value(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int((len(ordered) - 1) * max(0.0, min(pct, 1.0)))
    return ordered[idx]


def smooth_threshold(
    default_value: float,
    observed_values: list[float],
    *,
    floor: float,
    ceiling: float,
    percentile_rank: float = 0.85,
    min_samples: int = 12,
    smoothing: float = 0.65,
) -> float:
    if len(observed_values) < min_samples:
        return float(default_value)

    observed = percentile_value(observed_values, percentile_rank)
    blended = (default_value * smoothing) + (observed * (1 - smoothing))
    return max(floor, min(ceiling, blended))


def summarize_snapshot_series(snapshots: list[dict]) -> dict:
    if not snapshots:
        return {
            "avg_order_drop_pct": 0.0,
            "avg_congestion": 0.0,
            "earnings_volatility": 0.0,
            "observations": 0,
        }

    drops = [_to_float(s.get("order_rate_drop_pct")) for s in snapshots]
    congestion = [_to_float(s.get("congestion_index")) for s in snapshots]
    earnings = [_to_float(s.get("earnings_current_slot")) for s in snapshots]

    return {
        "avg_order_drop_pct": round(mean(drops), 2),
        "avg_congestion": round(mean(congestion), 2),
        "earnings_volatility": round(pstdev(earnings), 2) if len(earnings) > 1 else 0.0,
        "observations": len(snapshots),
    }


def build_next_week_forecast(
    *,
    zone_risk_score: float,
    disruption_probability: float,
    avg_order_drop_pct: float,
    earnings_volatility: float,
    days: int = 7,
) -> list[dict]:
    now = datetime.now(timezone.utc)
    zone_component = max(0.0, min(zone_risk_score / 100, 1.0)) * 0.36
    disruption_component = max(0.0, min(disruption_probability, 1.0)) * 0.24
    order_drop_component = max(0.0, min(avg_order_drop_pct / 100, 1.0)) * 0.18
    volatility_adj = max(0.0, min(earnings_volatility / 800, 0.12))
    base_risk = max(
        0.04,
        min(0.9, 0.1 + zone_component + disruption_component + order_drop_component + volatility_adj),
    )
    weekday_adjustments = {
        0: -0.02,
        1: -0.01,
        2: 0.0,
        3: 0.01,
        4: 0.04,
        5: 0.07,
        6: 0.05,
    }

    forecast: list[dict] = []
    for i in range(days):
        day = now + timedelta(days=i + 1)
        weekday = day.weekday()
        recency_decay = min(0.12, i * 0.018)
        cycle_adjustment = ((i % 3) - 1) * 0.008
        day_risk = max(
            0.03,
            min(
                0.95,
                base_risk
                + weekday_adjustments.get(weekday, 0.0)
                + cycle_adjustment
                - recency_decay,
            ),
        )
        expected_multiplier = round(max(0.45, 1 - (day_risk * 0.55)), 3)

        forecast.append(
            {
                "date": day.date().isoformat(),
                "day_of_week": weekday,
                "predicted_disruption_probability": round(day_risk, 3),
                "risk_band": (
                    "critical"
                    if day_risk >= 0.75
                    else "high"
                    if day_risk >= 0.55
                    else "medium"
                    if day_risk >= 0.35
                    else "low"
                ),
                "expected_earnings_multiplier": expected_multiplier,
            }
        )
    return forecast
