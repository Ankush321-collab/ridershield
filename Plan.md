# GuideWire / Zylo — Gap-Closure Implementation Plan

This document maps every known gap (missing triggers, partial implementations, and fraud-layer deficiencies) to a concrete, self-contained implementation task. Tasks are ordered so that each one can be developed and tested independently without blocking or waiting for another task to finish.

---

## Summary of Gaps

| # | Gap | Gap Type |
|---|-----|----------|
| G1 | AQI / GRAP Stage 3-4 trigger evaluator | Missing trigger |
| G2 | Inventory Stockout standalone evaluator | Partial trigger |
| G3 | Road Closure as independent trigger | Partial trigger |
| G4 | Gated Community / RWA Friction trigger | Missing trigger |
| G5 | VIP Convoy / Civic Event trigger | Missing trigger |
| G6 | GRAP-mandated Vehicle Ban trigger | Missing trigger |
| G7 | Warehouse / Supply Chain Cascade trigger | Missing trigger |
| G8 | Fraud score gating for auto-claims | Missing enforcement |
| G9 | Behavioural anomaly detection (Isolation Forest) | Missing ML |
| G10 | Graph / Collusion detection | Missing ML |
| G11 | AQI data collection (OWM Air Pollution API) | Missing data collector |

---

## Task Breakdown

---

### TASK-A — AQI Data Collection & GRAP Trigger (G1 + G11)

**What it solves:** AQI values are mocked in `weather_client.py` and stored in the DB, but (a) the real OpenWeatherMap Air Pollution API is never called, and (b) there is no evaluator that fires a disruption event when AQI breaches GRAP Stage 3/4 (AQI > 300).

**Scope:**

1. **`data_collectors/weather_client.py`**
   - Add a second OWM HTTP call to `http://api.openweathermap.org/data/2.5/air_pollution` using the same lat/lon per zone.
   - Parse `list[0].main.aqi` (OWM 1–5 scale) and `list[0].components.pm2_5` + `pm10`.
   - Map OWM AQI 1–5 → Indian AQI approximation (× 60 as a reasonable linear proxy, capped at 500).
   - Store the result in the `aqi` column of `WeatherData` that already exists in `trigger_service/models.py`.
   - The mock fallback `_mock_weather()` already returns a random `aqi` value (50–180); adjust the mock range to also occasionally produce GRAP Stage 3/4 values (> 300) for demo purposes.

2. **`trigger_service/service.py`**
   - Add threshold constant: `AQI_GRAP_THRESHOLD = 300`.
   - Add `eval_aqi(weather: dict, zone: dict) -> Optional[dict]` evaluator that returns a disruption result when `weather["aqi"] > AQI_GRAP_THRESHOLD`.
   - Register `eval_aqi` in the weather-trigger loop inside `evaluate_all_zones()` (same path as `eval_heavy_rain` and `eval_heat` — no 3-factor gate).
   - Assign `trigger_type = "aqi_grap"`, `severity = "high"`.

3. **`data_collectors/platform_simulator.py`**
   - Add `ScenarioKey.AQI_GRAP = "AQI_GRAP"`.
   - When the scenario is active: reduce `orders_hr` by 40–60 %, set `rider_status = "OFFLINE"` with 30 % probability (vehicle ban effect).

4. **`trigger_service/router.py`** — add `"aqi_grap"` to the list of valid `trigger_type` values accepted by `POST /api/triggers/inject`.

5. **Tests** — add unit test for `eval_aqi` threshold boundary in `backend/tests/`.

**Dependencies:** None — weather data pipeline and DB schema already exist.

---

### TASK-B — Inventory Stockout Standalone Trigger (G2)

**What it solves:** `stock_level = CRITICAL` is set by the platform simulator (and stored in `PlatformSnapshot.stock_level`) but there is no `eval_stockout()` evaluator — the condition only surfaces when `store_status = CLOSED` fires first.

**Scope:**

1. **`trigger_service/service.py`**
   - Add threshold constant: `STOCKOUT_ORDER_DROP_THRESHOLD = 40.0` (orders must also drop ≥ 40 % to confirm the stockout is causing rider harm, not just a quiet hour).
   - Add `eval_stockout(snap: dict, zone: dict) -> Optional[dict]` that returns a result when `snap["stock_level"] == "CRITICAL"` **and** `snap["order_rate_drop_pct"] >= STOCKOUT_ORDER_DROP_THRESHOLD`.
   - Register `eval_stockout` in the rider-level trigger loop inside `evaluate_all_zones()` alongside `eval_store_closure` (3-factor gate applies).
   - Assign `trigger_type = "inventory_stockout"`, `severity = "medium"`.

2. **`data_collectors/platform_simulator.py`**
   - Add `ScenarioKey.INVENTORY_STOCKOUT = "INVENTORY_STOCKOUT"`.
   - When the scenario is active: set `stock = "CRITICAL"`, reduce `orders_hr` by 30–50 %, keep `store_status = "DEGRADED"` (not CLOSED — to distinguish from the store_closure trigger).

3. **`trigger_service/router.py`** — add `"inventory_stockout"` to the inject endpoint's allowed trigger types.

4. **Tests** — unit test for `eval_stockout` covering: CRITICAL+high-drop fires, CRITICAL+low-drop does not, LOW+high-drop does not.

**Dependencies:** None — `stock_level` field already exists in `PlatformSnapshot`.

---

### TASK-C — Road Closure as Independent Trigger (G3)

**What it solves:** `road_blocked = TRUE` is evaluated inside `eval_traffic()` and shares the `"traffic_congestion"` trigger type. Road closure is a distinct event that should produce its own `DisruptionEvent` with `trigger_type = "road_closure"` and bypass the 55-minute duration guard that applies to congestion.

**Scope:**

1. **`trigger_service/service.py`**
   - Extract road-closure detection into a new `eval_road_closure(snap: dict, zone: dict) -> Optional[dict]` evaluator.
   - This evaluator fires immediately when `snap["road_blocked"] == True` (no duration guard).
   - Assign `trigger_type = "road_closure"`, `severity = "high"`.
   - Remove the `or rb` branch from `eval_traffic()` so congestion and road closure are evaluated on separate paths.
   - Register `eval_road_closure` in the rider-level trigger loop.

2. **`data_collectors/platform_simulator.py`**
   - Add `ScenarioKey.ROAD_CLOSURE = "ROAD_CLOSURE"`.
   - When the scenario is active: set `road_blocked = True`, reduce `orders_hr` by 50–70 %.

3. **`trigger_service/router.py`** — add `"road_closure"` to the inject endpoint's allowed trigger types.

4. **Tests** — unit test: road_blocked=True fires immediately; road_blocked=False + congestion still uses duration guard.

**Dependencies:** None — `road_blocked` field already exists in `PlatformSnapshot`.

---

### TASK-D — Gated Community / RWA Friction Trigger (G4)

**What it solves:** No evaluator, no simulator field for gated-community access friction (security guards blocking riders, intercom delays). This is trigger #13 from the README.

**Scope:**

1. **`trigger_service/service.py`**
   - Add threshold constants:
     - `RWA_DISPATCH_LATENCY_THRESHOLD = 300` (seconds, > 5 min avg dispatch = access friction)
     - `RWA_ORDER_DROP_THRESHOLD = 30.0`
   - Add `eval_rwa_friction(snap: dict, zone: dict) -> Optional[dict]` that fires when `snap["dispatch_latency_sec"] >= RWA_DISPATCH_LATENCY_THRESHOLD` **and** `snap["order_rate_drop_pct"] >= RWA_ORDER_DROP_THRESHOLD`.
   - Register in rider-level trigger loop (3-factor gate applies).
   - Assign `trigger_type = "rwa_friction"`, `severity = "low"`.

2. **`data_collectors/platform_simulator.py`**
   - Add `ScenarioKey.RWA_FRICTION = "RWA_FRICTION"`.
   - When the scenario is active: set `dispatch_lat` to `rng.randint(320, 600)`, reduce `orders_hr` by 25–40 %.

3. **`trigger_service/router.py`** — add `"rwa_friction"` to the inject endpoint's allowed trigger types.

4. **Tests** — unit test threshold boundary for `eval_rwa_friction`.

**Dependencies:** None — `dispatch_latency_sec` field already exists in `PlatformSnapshot`.

---

### TASK-E — VIP Convoy / Civic Event Traffic Spike Trigger (G5)

**What it solves:** VIP convoys and spontaneous civic events (protests, rallies) cause sudden, localised traffic spikes distinguishable from ordinary congestion by their abruptness. Trigger #14 from the README.

**Scope:**

1. **`trigger_service/service.py`**
   - Add threshold constants:
     - `CIVIC_CONGESTION_SPIKE = 90` (sudden spike to ≥ 90/100, higher than normal congestion threshold of 80)
     - `CIVIC_SPIKE_WINDOW_MIN = 10` (spike within the last 10 minutes — no sustained-duration requirement, opposite of regular congestion)
      - `CIVIC_SPIKE_DELTA = 20` (must jump by at least 20 points vs recent 10-minute baseline)
   - Add `eval_civic_event(snap: dict, zone: dict) -> Optional[dict]` that fires only when:
     - `snap["congestion_index"] >= CIVIC_CONGESTION_SPIKE`, and
     - short-window delta (`current_congestion - min(last_10m_congestion)`) is `>= CIVIC_SPIKE_DELTA`.
   - This ensures abrupt civic/VIP spikes are distinguishable from ordinary sustained congestion.
   - To prevent duplicate overlap with `eval_traffic`, skip `eval_civic_event` for the same zone in the same slot if a `traffic_congestion` event was already created.
   - Assign `trigger_type = "civic_event"`, `severity = "medium"`.
   - Register in rider-level trigger loop (3-factor gate applies).

2. **`data_collectors/platform_simulator.py`**
   - Add `ScenarioKey.CIVIC_EVENT = "CIVIC_EVENT"`.
   - When the scenario is active: set `congestion = rng.randint(90, 100)`, set `road_blocked = True` with 20 % probability, reduce `orders_hr` by 40–60 %.

3. **`trigger_service/router.py`** — add `"civic_event"` to the inject endpoint's allowed trigger types.

4. **Tests** — unit test: congestion ≥ 90 fires civic_event; congestion 81–89 does not.

**Dependencies:** None — `congestion_index` field already exists in `PlatformSnapshot`.

---

### TASK-F — GRAP-Mandated Vehicle Ban Trigger (G6)

**What it solves:** GRAP (Graded Response Action Plan) Stage 3/4 mandates bans on diesel two-wheelers and three-wheelers in NCR/Delhi zones. No evaluator or DB flag exists. Trigger #16 from the README.

**Scope:**

1. **`trigger_service/models.py` / `PlatformSnapshot`**
   - Add column `grap_vehicle_ban: Mapped[bool] = mapped_column(default=False)`.
   - Create an Alembic migration for this column addition.

2. **`data_collectors/platform_simulator.py`**
   - Add `grap_vehicle_ban = False` to the default snapshot output.
   - Add `ScenarioKey.GRAP_BAN = "GRAP_BAN"`.
   - When the scenario is active: set `grap_vehicle_ban = True`, set `curfew = True` only for diesel-vehicle riders (simulate by `rng.random() < 0.60`), reduce `orders_hr` by 60–80 %.

3. **`trigger_service/service.py`**
   - Add `eval_grap_ban(snap: dict, zone: dict) -> Optional[dict]` that fires when `snap["grap_vehicle_ban"] == True`.
   - Assign `trigger_type = "grap_vehicle_ban"`, `severity = "critical"`.
   - Register in rider-level trigger loop (3-factor gate applies).

4. **`trigger_service/router.py`** — add `"grap_vehicle_ban"` to the inject endpoint's allowed trigger types.

5. **Tests** — unit test for `eval_grap_ban` + migration is valid (Alembic check).

**Dependencies:** Requires DB migration (column add). Self-contained — does not depend on Tasks A–E.

---

### TASK-G — Warehouse / Supply Chain Cascade Trigger (G7)

**What it solves:** Multi-store inventory failures (e.g., a single distributor supplying three dark stores fails) cause cascading stockouts across a zone. Trigger #17 from the README.

**Scope:**

1. **`trigger_service/service.py`**
   - Add threshold constants:
     - `SUPPLY_CASCADE_ZONE_STOCKOUT_PCT = 0.50` (≥ 50 % of snapshots in a zone report `stock_level = CRITICAL`)
     - `SUPPLY_CASCADE_ORDER_DROP = 35.0`
   - Add `eval_supply_cascade(snapshots: list[dict], zone: dict) -> Optional[dict]` (zone-level evaluator, same pattern as `eval_community_signal`):
     - Count how many snapshots have `stock_level == "CRITICAL"`.
     - If ≥ 50 % AND average `order_rate_drop_pct` ≥ 35 % → fire.
   - Call `eval_supply_cascade` after the rider-level loop in `evaluate_all_zones()`, alongside where `eval_community_signal` is called.
   - Assign `trigger_type = "supply_cascade"`, `severity = "high"`.
   - Dedup key and `_created_events` check apply as usual.

2. **`data_collectors/platform_simulator.py`**
   - Add `ScenarioKey.SUPPLY_CASCADE = "SUPPLY_CASCADE"`.
   - When the scenario is active: set `stock = "CRITICAL"` for all riders in the zone, reduce `orders_hr` by 50–70 %.

3. **`trigger_service/router.py`** — add `"supply_cascade"` to the inject endpoint's allowed trigger types.

4. **Tests** — unit test: 60 % CRITICAL snapshots fire; 40 % CRITICAL snapshots do not.

**Dependencies:** None — uses existing snapshot data. TASK-B (inventory stockout) and TASK-G are complementary but independent.

---

### TASK-H — Fraud Score Gating for Auto-Claims (G8)

**What it solves:** `run_fraud_check()` computes a score 0–100 but the score is never used to block a payout. A rider with fraud_score = 100 still gets paid automatically. This is the most critical integrity gap.

**Scope:**

1. **`claims_service/fraud.py`**
   - Add constant `AUTO_CLAIM_FRAUD_THRESHOLD = 75` (configurable via env var `FRAUD_THRESHOLD`, default 75).
   - Export this constant so `service.py` can import it.

2. **`claims_service/service.py`** — `process_auto_claims()`
   - After calling `run_fraud_check()`, check: `if fraud_score >= AUTO_CLAIM_FRAUD_THRESHOLD`.
   - If the threshold is exceeded:
     - Create the `Claim` record with `status = "flagged"` (new status) instead of `"paid"`.
     - Set `payout_amount = 0` on the flagged record.
     - Do **not** call `process_upi_payout()`.
     - Log a warning with rider_id, fraud_score, disruption_event_id.
   - If the threshold is not exceeded: proceed as before (`status = "paid"`, call UPI payout).

3. **`claims_service/models.py`**
   - Add `"flagged"` to the valid status enum / check constraint documentation comment (the column is a `String` so no enum migration needed, but update the comment).

4. **`admin_service/`** — verify that the admin claim-review endpoints can also surface `status = "flagged"` claims for human review. If there is a filter that excludes these, add `"flagged"` to the reviewable statuses.

5. **Tests**
   - Unit test: fraud_score ≥ 75 → claim created with status="flagged", payout NOT called.
   - Unit test: fraud_score = 74 → claim created with status="paid", payout IS called.

**Dependencies:** None — all changes are inside the claims service.

---

### TASK-I — Behavioural Anomaly Detection with Isolation Forest (G9)

**What it solves:** The README describes an ML-based behavioural anomaly detector (Isolation Forest) to catch unusual earnings patterns. Currently `DemoRiskModel` is a simple linear formula used only for premium calculation, not fraud.

**Scope:**

1. **`ml/training/`** — create `train_isolation_forest.py`
   - Train an `sklearn.ensemble.IsolationForest` on feature vectors derived from `PlatformSnapshot` rows:
     - `[orders_per_hour, earnings_current_slot, earnings_rolling_baseline, order_rate_drop_pct, avg_pickup_wait_sec, congestion_index]`
   - Use `contamination=0.05` (5 % expected anomaly rate).
   - Persist the trained model to `ml/model_artifacts/isolation_forest.pkl` using `joblib`.
   - Include a `generate_synthetic_training_data()` helper that creates a realistic dataset (using the same statistical distributions as the platform simulator) so training can run without a live DB.

2. **`ml/serve.py`** — add `predict_anomaly(features: dict) -> float` function
   - Load `isolation_forest.pkl` on startup (lazy-load, cached).
   - Return an anomaly score in [0, 1] using percentile-based normalization from `decision_function` against a rolling/reference distribution (preferred over ad-hoc raw-score scaling).
   - Keep probability calibration (`CalibratedClassifierCV`) as optional phase-2; start with percentile normalization for stability and simplicity.
   - Fall back gracefully (return 0.0) if the model file is absent (e.g., first boot before training).

3. **`claims_service/fraud.py`** — `run_fraud_check()`
   - After the existing 4 rule checks, call `predict_anomaly()` with the rider's snapshot features.
   - If anomaly_score > 0.7 → add 20 pts to fraud_score (capped at 100).
   - This makes the ML signal an additive contributor to the existing rule-based score, not a replacement.

4. **`ml/Dockerfile`** — add `scikit-learn` and `joblib` to `requirements.txt`; add a `RUN python training/train_isolation_forest.py` step to pre-train at image build time.

5. **Tests** — unit test: mock `predict_anomaly` returning 0.8 → fraud_score increases by 20; mock returning 0.5 → no change.

**Dependencies:** None — the ML service is already a separate Docker container. The fraud.py integration requires `ml/serve.py` to be reachable (already wired in docker-compose).

---

### TASK-J — Graph-Based Collusion Detection (G10)

**What it solves:** The README calls for graph/collusion detection to catch coordinated fraud rings (multiple riders filing claims simultaneously in the same zone for the same event). Currently no such check exists.

**Scope:**

1. **`claims_service/fraud.py`** — add `detect_collusion(rider_id, disruption_event_id, zone_id, db) -> int`
    - Query `Claim` table: count **distinct riders** who filed a claim for the **same** `disruption_event_id` within the last 10 minutes (`created_at >= now - 10min`).
   - If count > a threshold (e.g., `COLLUSION_SPIKE_THRESHOLD = 15`), compute the "collusion suspicion" for this rider:
       - Ratio = `(distinct_riders_in_window / max(total_online_riders_in_zone, 1))`, capped to `1.0`.
     - If ratio > 0.80 (> 80 % of zone riders filing at once, which is statistically unlikely): return 25 pts.
     - Otherwise return 0 pts.
    - Repeated claims from the same rider should be tracked separately as a duplicate/retry fraud feature, not inflate the collusion denominator ratio.

2. **`claims_service/fraud.py`** — `run_fraud_check()`
   - Call `detect_collusion()` and add its returned pts to `score`.

3. **`shared/zones.py`** — expose `get_rider_count_for_zone(zone_id)` or look it up from the DB. The collusion check needs the total online rider count as a denominator.

4. **Tests**
   - Unit test: 20 claims for the same event in 10 min, only 10 total online riders → ratio = 2.0 (> 0.80) → 25 pts added.
   - Unit test: 5 claims, 50 online riders → ratio = 0.10 → 0 pts.

**Dependencies:** None — reads from the existing `Claim` table. Can be merged independently of TASK-H and TASK-I.

---

## Cross-Cutting Checklist (applies to every task above)

- [ ] New `trigger_type` strings added to `_severity_for()` and `_threshold_for()` helper functions in `trigger_service/service.py`.
- [ ] New `ScenarioKey` constants added to `platform_simulator.py` also handled in the inject endpoint schema (`trigger_service/schemas.py`).
- [ ] Each new evaluator has a corresponding unit test in `backend/tests/`.
- [ ] DB migrations (only TASK-F requires one) run cleanly via `alembic upgrade head`.
- [ ] `walkthrough.md` updated to document the newly activatable triggers.

---

## Task Dependency Graph

```
TASK-A  ─────────────────────────────────── independent
TASK-B  ─────────────────────────────────── independent
TASK-C  ─────────────────────────────────── independent
TASK-D  ─────────────────────────────────── independent
TASK-E  ─────────────────────────────────── independent
TASK-F  ─────────────────── needs Alembic migration ─── independent
TASK-G  ─────────────────────────────────── independent (complements B)
TASK-H  ─────────────────────────────────── independent (fraud gate)
TASK-I  ─────────────────────────────────── independent (ML layer)
TASK-J  ──────── reads Claim table ───────── independent (fraud graph)
```

Every task can be developed, reviewed, and merged in any order. The only shared edit surface is `trigger_service/service.py` (multiple tasks add evaluators there) — coordinate merges to avoid conflicts in that file.

---

## Recommended Merge Order (to minimise conflicts in service.py)

1. TASK-H (fraud gating — touches only claims_service)
2. TASK-I (ML model — touches only ml/ and claims_service/fraud.py)
3. TASK-J (graph fraud — touches only claims_service/fraud.py)
4. TASK-F (GRAP ban — needs migration, touches trigger_service + simulator)
5. TASK-A (AQI — touches weather_client + trigger_service)
6. TASK-B (stockout — touches trigger_service + simulator)
7. TASK-C (road closure — touches trigger_service + simulator)
8. TASK-D (RWA friction — touches trigger_service + simulator)
9. TASK-E (civic event — touches trigger_service + simulator)
10. TASK-G (supply cascade — touches trigger_service + simulator)
