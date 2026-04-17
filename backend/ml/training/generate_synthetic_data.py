"""
Dev 2: Synthetic Data Generator for ML Model Training

Generates ~50,000 synthetic records for LightGBM training.

TODO (Dev 2): Implement this script.
Run with: python -m ml.training.generate_synthetic_data
"""

import pandas as pd
import numpy as np
import random
from pathlib import Path


def generate_synthetic_data(n_records: int = 50000) -> pd.DataFrame:
    """
    Generate synthetic records with features:
    - zone_flood_risk (0-100)
    - zone_traffic_risk (0-100)
    - zone_store_risk (0-100)
    - day_of_week (0-6)
    - hour (0-23)
    - is_weekend (bool)
    - is_monsoon (bool)
    - rider_tenure_days (0-365)
    - rider_avg_earnings (200-800)
    - rider_order_consistency (0-1)
    - forecast_rainfall (0-100 mm)
    - forecast_aqi (0-300)
    
    Target: disrupted (0 or 1)
    """
    np.random.seed(42)
    
    data = {
        "zone_flood_risk": np.random.randint(0, 100, n_records),
        "zone_traffic_risk": np.random.randint(0, 100, n_records),
        "zone_store_risk": np.random.randint(0, 100, n_records),
        "day_of_week": np.random.randint(0, 7, n_records),
        "hour": np.random.randint(0, 24, n_records),
        "is_weekend": np.random.choice([0, 1], n_records, p=[0.71, 0.29]),
        "is_monsoon": np.random.choice([0, 1], n_records, p=[0.67, 0.33]),
        "rider_tenure_days": np.random.randint(1, 365, n_records),
        "rider_avg_earnings": np.random.uniform(200, 800, n_records).round(0),
        "rider_order_consistency": np.random.uniform(0.1, 1.0, n_records).round(2),
        "forecast_rainfall": np.random.exponential(10, n_records).clip(0, 100).round(1),
        "forecast_aqi": np.random.randint(20, 300, n_records),
    }
    
    df = pd.DataFrame(data)
    
    # Generate target: higher disruption probability with high risk + rain + monsoon
    disruption_prob = (
        df["zone_flood_risk"] * 0.003 +
        df["zone_traffic_risk"] * 0.002 +
        df["forecast_rainfall"] * 0.008 +
        df["is_monsoon"] * 0.15 +
        (df["hour"].between(17, 21)).astype(int) * 0.1
    ).clip(0, 1)
    
    df["disrupted"] = (np.random.random(n_records) < disruption_prob).astype(int)
    
    return df


if __name__ == "__main__":
    df = generate_synthetic_data()
    output_path = Path(__file__).resolve().parent / "synthetic_data.csv"
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} records -> {output_path}")
    print(f"Disruption rate: {df['disrupted'].mean():.2%}")
