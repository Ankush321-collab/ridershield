import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from lightgbm import LGBMRegressor, early_stopping
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


FEATURE_NAMES = [
    "zone_flood_risk",
    "zone_traffic_risk",
    "zone_store_risk",
    "day_of_week",
    "hour",
    "is_weekend",
    "is_monsoon",
    "rider_tenure_days",
    "rider_avg_earnings",
    "rider_order_consistency",
    "forecast_rainfall",
    "forecast_aqi"
]
TARGET = "disruption_probability"

DATA_PATH = Path("backend/ml/training/synthetic_training_data.csv")
MODEL_ARTIFACTS_DIR = Path("backend/ml/model_artifacts")
MODEL_PATH = MODEL_ARTIFACTS_DIR / "risk_model.pkl"
FEATURE_METADATA_PATH = MODEL_ARTIFACTS_DIR / "feature_names.json"

PARAMS = {
    "objective": "regression",
    "metric": "rmse",
    "boosting_type": "gbdt",
    "num_leaves": 63,
    "learning_rate": 0.05,
    "n_estimators": 500,
    "feature_fraction": 0.85,
    "bagging_fraction": 0.85,
    "bagging_freq": 5,
    "min_child_samples": 20,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "random_state": 42,
    "verbose": -1,
}


def load_training_data(data_path: Path = DATA_PATH) -> pd.DataFrame:
    return pd.read_csv(data_path)


def train_model() -> tuple[LGBMRegressor, dict]:
    df = load_training_data()

    X = df[FEATURE_NAMES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    model = LGBMRegressor(**PARAMS)
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        eval_metric="rmse",
        callbacks=[early_stopping(stopping_rounds=50, verbose=False)],
    )

    predictions = model.predict(X_test)
    predictions = predictions.clip(0.01, 0.99)

    rmse = mean_squared_error(y_test, predictions) ** 0.5
    r2 = r2_score(y_test, predictions)
    mae = mean_absolute_error(y_test, predictions)

    feature_importance = {
        feature: int(score)
        for feature, score in zip(FEATURE_NAMES, model.feature_importances_)
    }
    top_5_features = sorted(
        feature_importance.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:5]

    print(f"RMSE: {rmse:.4f}")
    print(f"R² score: {r2:.4f}")
    print(f"MAE: {mae:.4f}")
    print("Top 5 most important features by feature importance score:")
    for feature, score in top_5_features:
        print(f"- {feature}: {score}")

    if rmse > 0.10:
        print("WARNING: RMSE is above 0.10")

    metrics = {
        "rmse": float(rmse),
        "r2": float(r2),
        "mae": float(mae),
        "training_records": int(len(df)),
        "feature_importance": feature_importance,
    }
    return model, metrics


def save_artifacts(model: LGBMRegressor, metrics: dict) -> None:
    MODEL_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with MODEL_PATH.open("wb") as f:
        pickle.dump(model, f, protocol=4)

    metadata = {
        "features": FEATURE_NAMES,
        "feature_importance": metrics["feature_importance"],
        "model_version": "1.0.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_records": metrics["training_records"],
        "rmse": metrics["rmse"],
        "r2": metrics["r2"],
    }

    with FEATURE_METADATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def validate_saved_model() -> float:
    with MODEL_PATH.open("rb") as f:
        model = pickle.load(f)

    test_input = [[60, 70, 45, 3, 19, 1, 0, 90, 600.0, 0.75, 10.0, 180]]
    predicted = model.predict(test_input)
    clipped_prediction = float(max(0.01, min(0.99, predicted[0])))
    print(f"Test prediction for medium-risk evening slot: {clipped_prediction:.4f}")
    return clipped_prediction


if __name__ == "__main__":
    trained_model, metrics = train_model()
    save_artifacts(trained_model, metrics)
    validate_saved_model()
    print("Model saved successfully")
