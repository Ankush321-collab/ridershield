# TASK-3: Trigger Service + Data Collection + External APIs

**Owner:** Developer 3  
**Module:** Trigger Service + Data Collectors  
**Priority:** P0 (Core differentiator — "parametric" means auto-triggers)

---

## 1. Ownership Summary

You own the **parametric engine** — the heart of Zylo. Your triggers automatically detect disruptions without rider action. This is the "zero-touch" magic.

**You are responsible for:**
- External API polling (weather, traffic, platform status)
- 5 trigger condition evaluations (rain, traffic, store, platform, regulatory)
- Background scheduler running every 5 minutes
- DisruptionEvent creation + duplicate prevention
- Community signal detection (mass order collapse)
- Platform Simulator (mock Zepto/Blinkit order data)
- Demo trigger injection endpoint

---

## 2. Database Tables You Own

### `disruption_events`
```sql
CREATE TABLE disruption_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_type VARCHAR(50) NOT NULL,
    zone_id UUID NOT NULL REFERENCES zones(id),
    slot_start TIMESTAMP NOT NULL,
    slot_end TIMESTAMP NOT NULL,
    severity VARCHAR(20) NOT NULL,  -- low, medium, high, critical
    data_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### `weather_data` (TimescaleDB hypertable)
```sql
CREATE TABLE weather_data (
    time TIMESTAMPTZ NOT NULL,
    zone_id UUID NOT NULL,
    temperature DECIMAL(5, 2),
    rainfall_mm DECIMAL(6, 2),
    aqi INTEGER,
    humidity INTEGER,
    wind_speed DECIMAL(5, 2),
    PRIMARY KEY (time, zone_id)
);
SELECT create_hypertable('weather_data', 'time');
```

### `platform_snapshots` (TimescaleDB hypertable)
```sql
CREATE TABLE platform_snapshots (
    time TIMESTAMPTZ NOT NULL,
    rider_id UUID NOT NULL,
    zone_id UUID NOT NULL,
    orders_per_hour INTEGER,
    earnings_current_slot INTEGER,
    rider_status VARCHAR(20),
    store_status VARCHAR(20),
    platform_status VARCHAR(20),
    PRIMARY KEY (time, rider_id)
);
SELECT create_hypertable('platform_snapshots', 'time');
```

---

## 3. The 5 Triggers

| # | Trigger | Condition | Source | Severity |
|---|---------|-----------|--------|----------|
| 1 | Heavy Rain | `rainfall_mm > 40` in 1hr | OpenWeatherMap | high |
| 2 | Traffic Congestion | `congestion_index > 80` for 60+ min | Mock | medium |
| 3 | Dark Store Closure | `store_status = CLOSED` | Platform Simulator | high |
| 4 | Platform Outage | `platform_status = DOWN` | Platform Simulator | critical |
| 5 | Regulatory/Curfew | `curfew_active = TRUE` | Mock data | critical |

### Three-Factor Validation Gate
A DisruptionEvent is created ONLY when ALL 3 conditions met:
1. Trigger Condition TRUE
2. Rider Online & In-Zone
3. Earnings Below Baseline

---

## 4. API Endpoints You Build

### `GET /api/triggers/status`
```json
{
  "active_triggers": [
    { "trigger_id": "tr_001", "type": "heavy_rain", "zone": "gachibowli",
      "threshold": "52mm/1hr", "active_since": "2026-03-30T15:05:00Z", "affected_riders": 12 }
  ],
  "community_signals": [],
  "last_evaluation": "2026-03-30T15:05:00Z"
}
```

### `GET /api/disruption-events`
Query: `?zone=koramangala&from=2026-03-30T00:00:00Z`
```json
{
  "events": [
    { "event_id": "de_001", "trigger_type": "heavy_rain", "zone": "gachibowli",
      "slot": "15:00-15:30", "severity": "high", "created_at": "2026-03-30T15:05:00Z" }
  ]
}
```

### `POST /api/triggers/inject` (Demo Only)
**Critical for demo** — instant disruption injection.
```json
// Request
{ "trigger_type": "heavy_rain", "zone": "gachibowli", "rainfall_mm": 52, "duration_seconds": 1800 }
// Response
{ "injected": true, "event_id": "de_002", "affected_riders": 8 }
```

---

## 5. External API Integrations

- **OpenWeatherMap**: Poll every 5 min per zone, store in `weather_data`
- **Traffic (Mock)**: Return random congestion_index 20-95
- **Platform Simulator**: Simulate store/platform/rider status

---

## 6. Background Scheduler

APScheduler running every 5 minutes:
1. Poll all external data sources
2. Store snapshots in TimescaleDB
3. Evaluate all 5 triggers per zone
4. Apply 3-factor validation
5. Create DisruptionEvent (with duplicate suppression)
6. Notify Dev 4's Claims Service

---

## 7. Dependencies

| You Call | Owned By | What |
|----------|----------|------|
| `zones` table | Dev 1 | Zone coordinates for API polling |
| `riders` table | Dev 1 | Online riders in affected zones |
| `policies` table | Dev 2 | Insured riders in zone |
| `rider_zone_baselines` | Dev 1 | Baseline earnings comparison |

### Others Depend on You

| Consumer | What They Need | Deadline |
|----------|---------------|----------|
| **Dev 4** (Claims) | `disruption_events` table + `platform_snapshots` | Day 7 |
| **Dev 5** (Admin) | `weather_data` for corroboration | Day 8 |

---

## 8. File Structure

```
backend/
├── trigger_service/
│   ├── router.py, service.py, scheduler.py, models.py, schemas.py
├── data_collectors/
│   ├── weather_client.py, traffic_mock.py, platform_simulator.py
```

---

## 9. Day-by-Day Plan

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | External API client stubs | Clients return mock data |
| 2 | Weather API with OpenWeatherMap | Real weather stored |
| 3 | Traffic + store mocks | All data sources work |
| 4 | Trigger scheduler (APScheduler) | Runs on startup |
| 5 | Evaluate rain + traffic triggers | 2 triggers fire |
| 6 | Store + platform + regulatory triggers | All 5 work |
| 7 | DisruptionEvent creation + dedup, **INTEGRATION** | Events in DB |
| 8 | Community signal detection | Mass collapse detected |
| 9 | Demo injection endpoint | Demo trigger works |
| 10 | Three-factor validation gate | Only valid events pass |
| 11 | **FULL INTEGRATION** with Dev 4 | E2E auto-payout |
| 12-14 | PWA UI, polish, demo | Demo-ready |

---

## 10. Acceptance Criteria

- [x] Weather polling stores data every 5 min
- [x] All 5 triggers evaluate correctly
- [x] Three-factor gate prevents false positives
- [x] DisruptionEvent created with correct metadata
- [x] Duplicates suppressed (same zone+slot+trigger)
- [x] Community signal fires at >70% affected
- [x] `POST /api/triggers/inject` creates instant disruption
- [x] Platform Simulator generates realistic data
- [x] Scheduler recovers from API failures (cached fallback)

## 11. User Stories: US-11, US-12

## 12. Demo: [1:00–1:15] — Admin injects HEAVY_RAIN → trigger fires → "Just data signals"
