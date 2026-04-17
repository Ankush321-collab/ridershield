from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


FEATURE_NAMES = [
    "orders_per_hour",
    "earnings_current_slot",
    "earnings_rolling_baseline",
    "order_rate_drop_pct",
    "avg_pickup_wait_sec",
    "congestion_index",
]


def generate_synthetic_training_data(n_records: int = 5000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    orders = np.clip(rng.normal(10, 3, n_records), 0, None).round().astype(int)
    earnings_per_order = np.clip(rng.normal(18, 5, n_records), 10, None)
    current_earnings = np.clip(orders * earnings_per_order, 0, 350)
    baseline = np.clip(rng.normal(180, 45, n_records), 80, 320)
    drop_pct = np.clip((baseline - current_earnings) / np.maximum(baseline, 1) * 100, 0, 100)
    wait_sec = np.clip(rng.gamma(2.0, 90.0, n_records), 30, 1200)
    congestion = np.clip(rng.normal(45, 20, n_records), 0, 100)

    normal = pd.DataFrame({
        "orders_per_hour": orders,
        "earnings_current_slot": current_earnings.round(1),
        "earnings_rolling_baseline": baseline.round(1),
        "order_rate_drop_pct": drop_pct.round(1),
        "avg_pickup_wait_sec": wait_sec.round(1),
        "congestion_index": congestion.round(1),
    })

    anomaly_count = max(100, n_records // 20)
    anomalies = pd.DataFrame({
        "orders_per_hour": rng.integers(0, 2, anomaly_count),
        "earnings_current_slot": rng.uniform(0, 20, anomaly_count).round(1),
        "earnings_rolling_baseline": rng.uniform(220, 350, anomaly_count).round(1),
        "order_rate_drop_pct": rng.uniform(75, 100, anomaly_count).round(1),
        "avg_pickup_wait_sec": rng.uniform(600, 1800, anomaly_count).round(1),
        "congestion_index": rng.uniform(85, 100, anomaly_count).round(1),
    })

    return pd.concat([normal, anomalies], ignore_index=True)


def train_isolation_forest() -> Path:
    base_dir = Path(__file__).resolve().parents[1]
    model_dir = base_dir / "model_artifacts"
    model_dir.mkdir(parents=True, exist_ok=True)

    df = generate_synthetic_training_data()
    model = IsolationForest(
        contamination=0.05,
        n_estimators=200,
        random_state=42,
    )
    model.fit(df[FEATURE_NAMES])

    model_path = model_dir / "isolation_forest.pkl"
    joblib.dump(model, model_path)
    return model_path


if __name__ == "__main__":
    path = train_isolation_forest()
    print(f"Isolation forest saved to {path}")
