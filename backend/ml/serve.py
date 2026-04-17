import json
import pickle
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .demo_model import DemoRiskModel


MODEL_PATH = Path(__file__).resolve().parent / "model_artifacts" / "risk_model.pkl"
METADATA_PATH = Path(__file__).resolve().parent / "model_artifacts" / "feature_names.json"
ANOMALY_MODEL_PATH = Path(__file__).resolve().parent / "model_artifacts" / "isolation_forest.pkl"
ANOMALY_FEATURES = [
    "orders_per_hour",
    "earnings_current_slot",
    "earnings_rolling_baseline",
    "order_rate_drop_pct",
    "avg_pickup_wait_sec",
    "congestion_index",
]


class PredictRequest(BaseModel):
    zone_flood_risk: int
    zone_traffic_risk: int
    zone_store_risk: int
    day_of_week: int
    hour: int
    is_weekend: bool
    is_monsoon: bool
    rider_tenure_days: int
    rider_avg_earnings: float
    rider_order_consistency: float
    forecast_rainfall: float
    forecast_aqi: int


app = FastAPI(title="Zylo ML Service", version="1.0.0")

model = None
metadata = {}
feature_names = []
_anomaly_model = None


def load_artifacts() -> None:
    global model, metadata, feature_names

    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"Metadata artifact not found: {METADATA_PATH}")

    if MODEL_PATH.exists():
        with MODEL_PATH.open("rb") as f:
            model = pickle.load(f)
    else:
        # Fall back to a deterministic demo model when the artifact is missing.
        model = DemoRiskModel()

    with METADATA_PATH.open("r", encoding="utf-8") as f:
        metadata = json.load(f)

    if isinstance(metadata, list):
        feature_names = metadata
        metadata = {"features": metadata, "model_version": "legacy"}
    else:
        feature_names = metadata.get("features", [])
        if not MODEL_PATH.exists():
            metadata = {**metadata, "model_version": "demo-fallback"}


def probability_to_band(probability: float) -> str:
    if probability < 0.30:
        return "low"
    if probability < 0.55:
        return "medium"
    if probability < 0.75:
        return "high"
    return "critical"


def _load_anomaly_model():
    global _anomaly_model
    if _anomaly_model is not None:
        return _anomaly_model
    if not ANOMALY_MODEL_PATH.exists():
        return None
    _anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
    return _anomaly_model


def predict_anomaly(features: dict) -> float:
    model = _load_anomaly_model()
    if model is None:
        return 0.0

    vector = np.array([[float(features.get(name, 0.0)) for name in ANOMALY_FEATURES]])
    try:
        raw_score = float(model.decision_function(vector)[0])
    except Exception:
        return 0.0

    # IsolationForest returns lower scores for stronger anomalies.
    normalized = 1.0 / (1.0 + np.exp(raw_score * 3.0))
    return float(max(0.0, min(1.0, normalized)))


@app.on_event("startup")
async def startup_event():
    load_artifacts()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "model_version": metadata.get("model_version", "unknown"),
        "trained_at": metadata.get("trained_at"),
        "training_records": metadata.get("training_records"),
    }


@app.get("/features")
async def features():
    return {
        "features": feature_names,
        "count": len(feature_names),
    }


@app.post("/predict")
async def predict(request: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    payload = request.model_dump()
    frame = pd.DataFrame([[payload[name] for name in feature_names]], columns=feature_names)
    prediction = float(model.predict(frame)[0])
    prediction = max(0.01, min(0.99, prediction))

    return {
        "disruption_probability": round(prediction, 4),
        "risk_band": probability_to_band(prediction),
        "expected_earnings_multiplier": round(1.0 - prediction * 0.6, 4),
    }
