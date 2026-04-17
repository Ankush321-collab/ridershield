# Zylo — Work Left Analysis (Updated)

Date: 2026-04-16  
Baseline compared: provided `work-left.md` content (Phase 3 gap list) vs current `main` code in this repository.

---

## Executive Summary

The provided gap report is **materially outdated**.  
Several Phase 3 items previously marked missing are now implemented, including:
- AQI trigger/data integration
- Isolation Forest + collusion scoring integration
- rider/admin predictive intelligence surfaces
- admin fraud queue and payout analytics
- knowledge-graph snapshot/propagation API and Neo4j service wiring
- adaptive trigger-threshold calibration

Estimated status now:

| Phase | Status | Completion (updated estimate) |
|---|---|---|
| Phase 1 — Foundation | ✅ Complete | 100% |
| Phase 2 — Automation & Protection | ✅ Complete | 100% |
| Phase 3 — Scale & Optimise | 🟡 Partial | ~75–85% |

---

## What Changed Since the Provided Work-Left Snapshot

### Now Implemented (previously listed as missing)

1. **G1 AQI/GRAP evaluator** is implemented
   - `backend/trigger_service/service.py` includes `AQI_GRAP_THRESHOLD = 300` and `eval_aqi()`.
2. **G11 OWM Air Pollution integration** is implemented
   - `backend/data_collectors/weather_client.py` calls `/data/2.5/air_pollution` and maps OWM AQI to proxy Indian AQI.
3. **AQI scenario wiring is implemented**
   - `backend/data_collectors/platform_simulator.py` has `ScenarioKey.AQI_GRAP`.
   - `backend/trigger_service/router.py` allows `"aqi_grap"` injection type.
4. **Isolation Forest-based anomaly signal is integrated**
   - Training artifact path and loader in `backend/ml/serve.py`.
   - Fraud scoring consumes anomaly score in `backend/claims_service/fraud.py`.
   - Training script exists: `backend/ml/training/train_isolation_forest.py`.
5. **Collusion spike detection exists (SQL-based)**
   - `backend/claims_service/fraud.py` has `detect_collusion()` and adds collusion points.
6. **Rider predictive intelligence is implemented**
   - `GET /riders/me/intelligence` in `backend/rider_service/router.py`.
   - Mobile dashboard surfaces next-week forecast + forward alerts in `mobile/app/(tabs)/index.tsx`.
7. **Admin predictive/fraud/payout analytics are implemented**
   - Endpoints in `backend/admin_service/router.py`: `/analytics/predictive`, `/claims/fraud-alerts`, `/analytics/payouts`.
   - UI pages exist: `admin/src/app/predictive/page.tsx`, `admin/src/app/fraud-alerts/page.tsx`, `admin/src/app/payout-analytics/page.tsx`.
8. **Self-calibrating threshold API is implemented**
   - Trigger thresholds are dynamically calibrated in `backend/trigger_service/service.py`.
   - Exposed for admin in `/analytics/thresholds`.
9. **Knowledge graph snapshot + propagation logic is implemented**
   - Graph snapshot and propagation edges in `backend/knowledge_graph/service.py`.
   - Exposed via `GET /admin/graph/knowledge`.
10. **Neo4j service is now present in stack config**
   - `docker-compose.yml` includes a `neo4j` service.

---

## Current “Work Left” (Verified)

## 1) Advanced Fraud Detection

| Component | Status | Notes |
|---|---|---|
| Rule-based fraud checks (GPS, peer, duplicate, baseline) | ✅ Done | `backend/claims_service/fraud.py` |
| Fraud gating threshold for auto-claims | ✅ Done | `AUTO_CLAIM_FRAUD_THRESHOLD` used in `backend/claims_service/service.py` |
| Isolation Forest anomaly scoring | ✅ Done (v1) | Integrated via `ml/serve.py -> predict_anomaly()` |
| Behavioural autoencoder | ❌ Missing | No autoencoder implementation found |
| Counterfactual estimator | ❌ Missing | No counterfactual model/service found |
| Geo-velocity impossibility checks | ❌ Missing | No speed/impossible travel checks found |
| Graph DB collusion (Neo4j) | 🟡 Partial | Neo4j service is configured, but fraud-scoring does not yet use graph queries |
| Collusion/ring detection (SQL heuristic) | 🟡 Partial | Exists, but not graph-based ring analytics |

## 2) Parametric Trigger Coverage

| Component | Status | Notes |
|---|---|---|
| G1 AQI/GRAP trigger | ✅ Done | `eval_aqi()` in trigger service |
| G2–G7 triggers | ✅ Done | Implemented and test-covered in `backend/tests/test_trigger_evaluators.py` |
| G11 real AQI data | ✅ Done | OWM air pollution endpoint integration present |

## 3) Instant Payout System

| Component | Status | Notes |
|---|---|---|
| UPI simulation payout | ✅ Done | `backend/payout_service/service.py` |
| Razorpay test integration | ❌ Missing | No Razorpay SDK/integration |
| Stripe sandbox integration | ❌ Missing | No Stripe integration |
| Webhook reconciliation | ❌ Missing | No payout webhook endpoints/reconciliation workers |
| FCM push on payout | ❌ Missing | No Firebase/FCM server integration |

## 4) Rider Intelligent Dashboard

| Component | Status | Notes |
|---|---|---|
| Active policy/earnings/claims/manual claim status | ✅ Done | Mobile app tabs implemented |
| Next-week risk forecast | ✅ Done | `GET /riders/me/intelligence` + mobile dashboard forecast cards |
| Predictive forward alerts | ✅ Done | Returned by rider intelligence API and surfaced in mobile UI |

## 5) Admin Intelligent Dashboard

| Component | Status | Notes |
|---|---|---|
| Overview, manual review queue, auto-claims, map/triggers | ✅ Done | Next.js admin pages exist |
| Predictive analytics (next-week) | ✅ Done | Backend endpoint + `/predictive` page implemented |
| Dedicated fraud alert queue | ✅ Done | `/claims/fraud-alerts` + `/fraud-alerts` page implemented |
| Payout analytics page | ✅ Done | `/analytics/payouts` + `/payout-analytics` page implemented |

## 6) Knowledge Graph v0

| Component | Status | Notes |
|---|---|---|
| Neo4j graph (zone/road/store/event) | 🟡 Partial | Neo4j service exists in compose; graph snapshot currently generated from relational data path |
| Propagation logic | ✅ Done | `build_graph_snapshot()` emits `propagates_with` edges |

## 7) ML Model Improvements

| Component | Status | Notes |
|---|---|---|
| LightGBM/risk model baseline | ✅ Done | Existing ML service stack present |
| Temporal model (TCN/Transformer) | 🟡 Partial | Temporal forecasting utilities exist (`backend/ml/temporal.py`), but no deep sequence model (TCN/Transformer) yet |
| Self-calibrating trigger thresholds | ✅ Done | Dynamic per-zone thresholds implemented and exposed in admin analytics |

## 8) Final Submission Package

| Component | Status | Notes |
|---|---|---|
| Full stack compose | ✅ Done | Core services in `docker-compose.yml` |
| Demo video | ❓ Not in repo | No file/artifact found |
| Pitch deck | ❓ Not in repo | No file/artifact found |

---

## Prioritized Remaining Backlog

### High Priority
1. Add **real payment rail simulation depth**: Razorpay/Stripe sandbox + webhook reconciliation.
2. Add **FCM payout notifications** on successful payout.
3. Add **geo-velocity impossibility** and stronger anti-spoofing checks into fraud scoring.
4. Evolve **Knowledge Graph v0** from relational snapshot to full **Neo4j-backed ingestion + query paths**.
5. Implement **graph-grade collusion/ring detection** over the graph layer.

### Medium Priority
6. Add **advanced fraud models** (behavioral autoencoder and counterfactual estimator) for stronger decision support.
7. Improve temporal forecasting from heuristic utilities to **sequence-learning models** (TCN/Transformer).

### Lower Priority
8. Strengthen graph semantics (road/store/event typed nodes + richer propagation causality).
9. Produce and include **final demo package artifacts** (video + pitch deck).

---

## Validation Notes (current environment)

- Baseline checks were attempted before documentation changes.
- In this environment, local tooling dependencies are currently missing:
  - `backend`: `python -m pytest -q tests` failed because `pytest` is not installed.
  - `admin`: `npm run lint` failed because `eslint` is not installed.
  - `admin`: `npm run build` failed because `next` is not installed.
- To run these checks locally after dependency setup:
  - `backend`: install dependencies (project-standard Python setup) and rerun `python -m pytest -q tests`.
  - `admin`: run `npm install`, then rerun `npm run lint` and `npm run build`.
