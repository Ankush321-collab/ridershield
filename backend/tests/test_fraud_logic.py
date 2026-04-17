import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claims_service import fraud as fraud_module
from claims_service.service import process_auto_claims
from ml import serve as ml_serve


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


class _ScalarsResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values


class FakeFraudDb:
    def __init__(self, results):
        self.results = list(results)

    async def execute(self, _query):
        return self.results.pop(0)


class FakeClaimsDb:
    def __init__(self, results):
        self.results = list(results)
        self.added = []

    async def execute(self, _query):
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None

    async def commit(self):
        return None


def test_predict_anomaly_missing_artifact_returns_zero():
    original_path = ml_serve.ANOMALY_MODEL_PATH
    original_model = ml_serve._anomaly_model
    try:
        ml_serve.ANOMALY_MODEL_PATH = Path("does-not-exist.pkl")
        ml_serve._anomaly_model = None
        score = ml_serve.predict_anomaly({
            "orders_per_hour": 1,
            "earnings_current_slot": 1,
            "earnings_rolling_baseline": 1,
            "order_rate_drop_pct": 1,
            "avg_pickup_wait_sec": 1,
            "congestion_index": 1,
        })
        assert score == 0.0
    finally:
        ml_serve.ANOMALY_MODEL_PATH = original_path
        ml_serve._anomaly_model = original_model


def test_run_fraud_check_adds_anomaly_points():
    rider_id = uuid4()
    zone_id = uuid4()
    event_id = uuid4()
    slot_start = datetime.utcnow()
    snapshot = SimpleNamespace(
        zone_id=zone_id,
        orders_per_hour=1,
        earnings_current_slot=10,
        earnings_rolling_baseline=200,
        order_rate_drop_pct=95.0,
        avg_pickup_wait_sec=700,
        congestion_index=96,
    )
    db = FakeFraudDb([
        _ScalarResult(snapshot),
        _ScalarResult(120),
        _ScalarResult(1),
        _ScalarResult(None),
        _ScalarResult(0),
    ])

    with patch.object(fraud_module, "predict_anomaly", return_value=0.8):
        score = asyncio.run(
            fraud_module.run_fraud_check(
                rider_id=rider_id,
                zone_id=zone_id,
                disruption_event_id=event_id,
                actual_earnings=10,
                slot_start=slot_start,
                db=db,
            )
        )
    assert score == 45


def test_run_fraud_check_ignores_low_anomaly_score():
    rider_id = uuid4()
    zone_id = uuid4()
    event_id = uuid4()
    slot_start = datetime.utcnow()
    snapshot = SimpleNamespace(
        zone_id=zone_id,
        orders_per_hour=8,
        earnings_current_slot=60,
        earnings_rolling_baseline=100,
        order_rate_drop_pct=40.0,
        avg_pickup_wait_sec=120,
        congestion_index=40,
    )
    db = FakeFraudDb([
        _ScalarResult(snapshot),
        _ScalarResult(120),
        _ScalarResult(1),
        _ScalarResult(0),
        _ScalarResult(0),
        _ScalarResult(10),
    ])

    with patch.object(fraud_module, "predict_anomaly", return_value=0.5):
        score = asyncio.run(
            fraud_module.run_fraud_check(
                rider_id=rider_id,
                zone_id=zone_id,
                disruption_event_id=event_id,
                actual_earnings=60,
                slot_start=slot_start,
                db=db,
            )
        )
    assert score == 25


def test_detect_collusion_high_ratio_adds_points():
    db = FakeFraudDb([
        _ScalarResult(20),
        _ScalarResult(10),
    ])
    points = asyncio.run(
        fraud_module.detect_collusion(
            rider_id=uuid4(),
            disruption_event_id=uuid4(),
            zone_id=uuid4(),
            slot_start=datetime.utcnow(),
            db=db,
        )
    )
    assert points == fraud_module.COLLUSION_FRAUD_POINTS


def test_detect_collusion_low_ratio_adds_no_points():
    db = FakeFraudDb([
        _ScalarResult(5),
    ])
    points = asyncio.run(
        fraud_module.detect_collusion(
            rider_id=uuid4(),
            disruption_event_id=uuid4(),
            zone_id=uuid4(),
            slot_start=datetime.utcnow(),
            db=db,
        )
    )
    assert points == 0


def test_process_auto_claims_flags_high_fraud_score_without_payout():
    event_id = uuid4()
    zone_id = uuid4()
    rider_id = uuid4()
    policy_id = uuid4()
    slot_start = datetime.utcnow().replace(microsecond=0)
    event = SimpleNamespace(id=event_id, zone_id=zone_id, slot_start=slot_start, trigger_type="heavy_rain")
    policy = SimpleNamespace(id=policy_id, rider_id=rider_id, coverage_limit=5000, coverage_used=0)
    baseline = SimpleNamespace(avg_earnings=700)
    snapshot = SimpleNamespace(earnings_current_slot=100)
    db = FakeClaimsDb([
        _ScalarResult(event),
        _ScalarsResult([policy]),
        _ScalarResult(baseline),
        _ScalarResult(snapshot),
    ])
    payout_calls = []

    async def _never_called(*args, **kwargs):
        payout_calls.append((args, kwargs))

    with patch("claims_service.service.check_duplicate_claim", return_value=False), patch(
        "claims_service.service.run_fraud_check", return_value=90
    ), patch("claims_service.service.process_upi_payout", side_effect=_never_called):
        claims_created = asyncio.run(process_auto_claims(event_id, db))

    claim = db.added[0]
    assert claims_created == 1
    assert claim.status == "flagged"
    assert claim.payout_amount == 0
    assert payout_calls == []


def test_process_auto_claims_pays_low_fraud_score():
    event_id = uuid4()
    zone_id = uuid4()
    rider_id = uuid4()
    policy_id = uuid4()
    slot_start = datetime.utcnow().replace(microsecond=0)
    event = SimpleNamespace(id=event_id, zone_id=zone_id, slot_start=slot_start, trigger_type="heavy_rain")
    policy = SimpleNamespace(id=policy_id, rider_id=rider_id, coverage_limit=5000, coverage_used=0)
    baseline = SimpleNamespace(avg_earnings=700)
    snapshot = SimpleNamespace(earnings_current_slot=100)
    db = FakeClaimsDb([
        _ScalarResult(event),
        _ScalarsResult([policy]),
        _ScalarResult(baseline),
        _ScalarResult(snapshot),
    ])
    payout_calls = []

    async def _record_payout(*args, **kwargs):
        payout_calls.append((args, kwargs))
        return SimpleNamespace(id=uuid4())

    with patch("claims_service.service.check_duplicate_claim", return_value=False), patch(
        "claims_service.service.run_fraud_check", return_value=74
    ), patch("claims_service.service.process_upi_payout", side_effect=_record_payout):
        claims_created = asyncio.run(process_auto_claims(event_id, db))

    claim = db.added[0]
    assert claims_created == 1
    assert claim.status == "paid"
    assert claim.payout_amount == 600
    assert len(payout_calls) == 1
