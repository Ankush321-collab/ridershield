import json
import pickle
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

try:
    import lightgbm as lgb
    from sklearn.metrics import classification_report, roc_auc_score
    from sklearn.model_selection import train_test_split
except Exception:
    lgb = None
    train_test_split = None
    classification_report = None
    roc_auc_score = None

from ml.demo_model import DemoRiskModel


def train_model():
    base_dir = Path(__file__).resolve().parents[1]
    training_dir = Path(__file__).resolve().parent
    model_dir = base_dir / "model_artifacts"
    model_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    df = pd.read_csv(training_dir / "synthetic_data.csv")
    
    feature_names = [
        "zone_flood_risk", "zone_traffic_risk", "zone_store_risk",
        "day_of_week", "hour", "is_weekend", "is_monsoon",
        "rider_tenure_days", "rider_avg_earnings", "rider_order_consistency",
        "forecast_rainfall", "forecast_aqi",
    ]
    
    X = df[feature_names]
    y = df["disrupted"]
    
    if lgb and train_test_split and classification_report and roc_auc_score:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            num_leaves=31,
            random_state=42,
            verbose=-1,
        )
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        print(f"AUC-ROC: {roc_auc_score(y_test, y_proba):.4f}")
        model_version = "lightgbm-demo-v1"
    else:
        model = DemoRiskModel()
        print("\nLightGBM/sklearn unavailable; using DemoRiskModel fallback artifact.")
        model_version = "rule-model-demo-v1"
    
    # Save artifacts
    with (model_dir / "risk_model.pkl").open("wb") as f:
        pickle.dump(model, f)
    metadata = {
        "features": feature_names,
        "model_version": model_version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_records": int(len(df)),
    }
    with (model_dir / "feature_names.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f)

    print(f"\nModel saved to {model_dir / 'risk_model.pkl'}")
    print(f"Features saved to {model_dir / 'feature_names.json'}")


if __name__ == "__main__":
    train_model()
