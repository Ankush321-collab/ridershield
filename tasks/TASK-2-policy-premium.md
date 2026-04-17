# TASK-2: Policy Service + Premium Engine + ML Model

**Owner:** Developer 2  
**Module:** Policy Service + Risk/Premium Service  
**Priority:** P0 (Core product — no coverage means no claims)  
**Estimated Duration:** 14 days (parallel with other devs)

---

## 1. Ownership Summary

You own the **policy lifecycle and pricing engine** of Zylo. Your module determines what riders pay and what they're covered for. The ML model you build is the "brain" behind dynamic, zone-aware pricing — a key differentiator for hackathon judges.

**You are responsible for:**
- Policy quote generation (3 tiers: Essential, Balanced, Max Protect)
- Policy creation, activation, renewal, cancellation
- LightGBM ML model for disruption probability prediction
- Premium calculation with zone risk, tenure discount, and tier multiplier
- Premium explanation ("Why is my premium ₹180?")
- Coverage tracking (slots covered, hours remaining, coverage used)

---

## 2. Database Tables You Own

### `policies`
```sql
CREATE TABLE policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rider_id UUID NOT NULL REFERENCES riders(id),
    plan_tier VARCHAR(20) NOT NULL,  -- essential, balanced, max_protect
    week VARCHAR(10) NOT NULL,       -- 2026-W13
    premium INTEGER NOT NULL,
    coverage_limit INTEGER NOT NULL,
    coverage_pct INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'active',  -- active, cancelled, expired
    slots_covered TEXT[],            -- Array of slot strings
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    UNIQUE(rider_id, week)
);
```

### `micro_slots`
```sql
CREATE TABLE micro_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id UUID NOT NULL REFERENCES zones(id),
    day_of_week INTEGER NOT NULL,  -- 0-6
    time_start TIME NOT NULL,
    time_end TIME NOT NULL,
    expected_earnings INTEGER NOT NULL,
    disruption_probability DECIMAL(4, 2) NOT NULL,
    weather_risk_score INTEGER,
    traffic_risk_score INTEGER,
    store_risk_score INTEGER
);
```

---

## 3. API Endpoints You Build

### 3.1 `GET /api/policies/quote`
Get dynamic premium quotes for all 3 tiers based on rider's zone and slots.

**Headers:** `Authorization: Bearer {jwt_token}`  
**Query:** `?slots=18:00-21:00,21:00-23:00&city=bengaluru`

**Response (200):**
```json
{
  "quotes": [
    {
      "tier": "essential",
      "weekly_premium": 120,
      "coverage_pct": 70,
      "coverage_limit": 2520,
      "slots_covered": 2,
      "risk_breakdown": {"weather": 45, "traffic": 30, "store": 25}
    },
    {
      "tier": "balanced",
      "weekly_premium": 180,
      "coverage_pct": 80,
      "coverage_limit": 2880,
      "slots_covered": 2,
      "risk_breakdown": {"weather": 45, "traffic": 30, "store": 25}
    },
    {
      "tier": "max_protect",
      "weekly_premium": 250,
      "coverage_pct": 90,
      "coverage_limit": 3240,
      "slots_covered": 2,
      "risk_breakdown": {"weather": 45, "traffic": 30, "store": 25}
    }
  ],
  "valid_until": "2026-03-31T23:59:59Z"
}
```

**Logic:**
1. Fetch rider's zone from `riders` table
2. Call ML model → get `disruption_probability` per slot
3. Calculate base premium from risk band
4. Apply tenure discount
5. Multiply by tier factor (Essential=0.7, Balanced=1.0, MaxProtect=1.3)
6. Return all 3 tiers with breakdown

---

### 3.2 `POST /api/policies`
Create policy for current calendar week.

**Headers:** `Authorization: Bearer {jwt_token}`

**Request:**
```json
{
  "plan_tier": "balanced",
  "payment_method": "upi",
  "upi_id": "arjun@oksbi"
}
```
**Response (201):**
```json
{
  "policy_id": "pol_001",
  "rider_id": "rd_001",
  "plan_tier": "balanced",
  "week": "2026-W13",
  "premium": 180,
  "coverage_limit": 2880,
  "status": "active",
  "slots_covered": ["18:00-21:00", "21:00-23:00"],
  "created_at": "2026-03-30T10:00:00Z",
  "expires_at": "2026-04-06T00:00:00Z"
}
```

**Validation:**
- Rider must not have an active policy for the same week
- Payment must be confirmed (mock UPI — always succeeds)
- Policy expires at end of calendar week (Sunday midnight)

---

### 3.3 `GET /api/policies/active`
Get rider's active policy with live coverage status.

**Headers:** `Authorization: Bearer {jwt_token}`

**Response (200):**
```json
{
  "policy_id": "pol_001",
  "plan_tier": "balanced",
  "week": "2026-W13",
  "status": "active",
  "slots_covered": ["18:00-21:00", "21:00-23:00"],
  "hours_remaining": 8,
  "coverage_used": 0,
  "coverage_limit": 2880,
  "expires_at": "2026-04-06T00:00:00Z"
}
```

---

### 3.4 `GET /api/policies/{policy_id}`
Get full policy details including claims history.

**Headers:** `Authorization: Bearer {jwt_token}`

**Response (200):**
```json
{
  "policy_id": "pol_001",
  "rider_id": "rd_001",
  "plan_tier": "balanced",
  "week": "2026-W13",
  "premium": 180,
  "coverage_limit": 2880,
  "coverage_pct": 80,
  "status": "active",
  "slots_covered": ["18:00-21:00", "21:00-23:00"],
  "claims_history": [],
  "created_at": "2026-03-30T10:00:00Z",
  "expires_at": "2026-04-06T00:00:00Z"
}
```

---

### 3.5 `PUT /api/policies/{policy_id}/renew`
Renew policy for next week with recalculated premium.

**Headers:** `Authorization: Bearer {jwt_token}`

**Response (200):**
```json
{
  "policy_id": "pol_002",
  "previous_policy_id": "pol_001",
  "week": "2026-W14",
  "new_premium": 195,
  "status": "active"
}
```

**Logic:** Re-run ML model with updated zone risk data → recalculate premium → create new policy.

---

### 3.6 `DELETE /api/policies/{policy_id}`
Cancel active policy.

**Headers:** `Authorization: Bearer {jwt_token}`  
**Response:** `204 No Content`

---

### 3.7 `POST /api/risk/premium`
**Internal API** — called by Dev 1 (onboard) and Dev 3 (trigger evaluation).

Calculate premium with ML model.

**Request:**
```json
{
  "zone": "koramangala",
  "slots": ["18:00-21:00", "21:00-23:00"],
  "plan_tier": "balanced",
  "rider_tenure_days": 90
}
```
**Response (200):**
```json
{
  "risk_score": 72,
  "disruption_probability": 0.65,
  "premium": {
    "essential": 120,
    "balanced": 180,
    "max_protect": 250
  },
  "explanation": "Premium higher due to monsoon forecast (65% flood probability) for Thu 7-9 PM",
  "tenure_discount": 0.1,
  "breakdown": [
    {"slot": "18:00-21:00", "risk": 75, "premium": 108},
    {"slot": "21:00-23:00", "risk": 68, "premium": 72}
  ]
}
```

---

## 4. ML Model Responsibilities

### 4.1 Model: LightGBM Disruption Predictor

**Input Features (12 features):**

| Feature | Type | Source |
|---------|------|--------|
| `zone_flood_risk` | Integer (0-100) | `zones` table |
| `zone_traffic_risk` | Integer (0-100) | `zones` table |
| `zone_store_risk` | Integer (0-100) | `zones` table |
| `day_of_week` | Integer (0-6) | Derived |
| `hour` | Integer (0-23) | Derived |
| `is_weekend` | Boolean | Derived |
| `is_monsoon` | Boolean | Jun-Sep |
| `rider_tenure_days` | Integer | `riders` table |
| `rider_avg_earnings` | Float | `rider_zone_baselines` |
| `rider_order_consistency` | Float | Coefficient of variation |
| `forecast_rainfall` | Float | Weather API / mock |
| `forecast_aqi` | Integer | Weather API / mock |

**Output:**
| Output | Type |
|--------|------|
| `disruption_probability` | Float (0-1) |
| `expected_earnings` | Float |
| `risk_band` | low / medium / high / critical |

### 4.2 Training Pipeline

```
backend/ml/
├── training/
│   ├── generate_synthetic_data.py   # Generate ~50,000 synthetic records
│   └── train_model.py              # Train LightGBM model
├── model_artifacts/
│   ├── risk_model.pkl               # Trained model
│   └── feature_names.json           # Feature order
└── serve.py                         # FastAPI model serving (port 8001)
```

### 4.3 Premium Calculation Formula

```
base_premium = get_base_premium(risk_band)
    # low: ₹50, medium: ₹100, high: ₹150, critical: ₹200

tenure_discount = min(rider_tenure_days / 365, 0.15)  # Max 15%

tier_multiplier = {essential: 0.7, balanced: 1.0, max_protect: 1.3}

slot_premium = base_premium × (1 - tenure_discount) × tier_multiplier

total_premium = sum(slot_premiums for each covered slot)
```

### 4.4 Plan Tiers

| Plan | Coverage % | Coverage Limit (of baseline) | Target |
|------|-----------|-----|--------|
| Essential | 70% | 70% of weekly baseline earnings | Budget riders |
| Balanced | 80% | 80% of weekly baseline earnings | Standard |
| Max Protect | 90% | 90% of weekly baseline earnings | Peak season |

---

## 5. Dependencies on Other Devs

| You Call | Owned By | Contract | When |
|----------|----------|----------|------|
| `riders` table | Dev 1 | Read rider profile for premium calc | Day 3+ |
| `zones` table | Dev 1 | Read zone risk scores | Day 3+ |
| `rider_zone_baselines` | Dev 1 | Read earnings baselines | Day 5+ |
| Auth middleware | Dev 1 | `from shared.auth import get_current_rider` | Day 2+ |

---

## 6. Other Devs Depend on You

| Consumer | What They Need | Deadline |
|----------|---------------|----------|
| **Dev 1** (Rider) | `POST /api/risk/premium` for onboarding quotes | Day 5 |
| **Dev 3** (Triggers) | `policies` table to find insured riders in a zone | Day 5 |
| **Dev 4** (Claims) | `policies` table for coverage limit + payout calc | Day 5 |
| **Dev 4** (Claims) | `coverage_used` tracking to enforce weekly limits | Day 7 |

---

## 7. File Structure You Own

```
backend/
├── policy_service/
│   ├── __init__.py
│   ├── router.py          # All /api/policies/* endpoints
│   ├── service.py          # Policy lifecycle logic
│   ├── models.py           # SQLAlchemy ORM (policies, micro_slots)
│   └── schemas.py          # Pydantic models
├── premium_service/
│   ├── __init__.py
│   ├── router.py           # /api/risk/premium endpoint
│   ├── service.py          # Premium calculation logic
│   └── schemas.py          # ML input/output models
├── ml/
│   ├── Dockerfile
│   ├── serve.py            # Model serving API (port 8001)
│   ├── model_artifacts/
│   │   ├── risk_model.pkl
│   │   └── feature_names.json
│   └── training/
│       ├── generate_synthetic_data.py
│       └── train_model.py
```

---

## 8. Day-by-Day Plan

| Day | Task | Deliverable |
|-----|------|-------------|
| **1** | FastAPI skeleton for policy routes | Policy router mounted |
| **2** | Zone baseline generation, micro_slot seed data | Zone risk data populated |
| **3** | Policy ORM model, basic CRUD | `POST /api/policies` works |
| **4** | Quote endpoint with static pricing | `GET /api/policies/quote` returns 3 tiers |
| **5** | Policy creation + activation flow | Full policy purchase works |
| **6** | Policy renewal logic | Renewal with recalculated premium |
| **7** | **INTEGRATION** with Dev 1 (auth → policy creation) | Auth + Policy E2E |
| **8** | ML synthetic data generation + model training | `risk_model.pkl` exists |
| **9** | Premium calc with ML model, **INTEGRATION** | Dynamic pricing works |
| **10** | Policy cancellation, coverage tracking | Coverage used/remaining tracked |
| **11** | End-to-end test with all services | Policy lifecycle complete |
| **12** | PWA policy selection UI | UI connected |
| **13** | PWA polish, integration fixes | Stable |
| **14** | Demo final | Demo-ready |

---

## 9. Error Codes You Handle

| Code | HTTP | Description |
|------|------|-------------|
| `NO_ACTIVE_POLICY` | 400 | No active policy found for rider |
| `DUPLICATE_POLICY` | 409 | Policy already exists for this week |
| `POLICY_NOT_FOUND` | 404 | Policy ID not found |
| `COVERAGE_EXHAUSTED` | 400 | Weekly coverage limit reached |
| `INVALID_TIER` | 400 | Tier must be essential/balanced/max_protect |
| `POLICY_EXPIRED` | 400 | Cannot renew an expired policy |

---

## 10. Acceptance Criteria

- [ ] 3-tier quotes returned with per-slot risk breakdown
- [ ] Policy created for current calendar week
- [ ] Coverage limit correctly calculated per tier (70%/80%/90% of baseline)
- [ ] Premium varies by zone (high-risk zone > low-risk zone) — **demo differentiator**
- [ ] Tenure discount applied (up to 15%)
- [ ] ML model trained on synthetic data, serves predictions
- [ ] Premium explanation in natural language
- [ ] Policy renewal recalculates premium
- [ ] Policy cancellation sets status = cancelled
- [ ] `coverage_used` incremented when claims are paid

---

## 11. User Stories Covered

| ID | Story |
|----|-------|
| US-05 | View 3 policy tiers |
| US-06 | Purchase a weekly policy |
| US-07 | View active policy |
| US-08 | Renew policy for next week |
| US-09 | See dynamic premium |
| US-10 | Premiums differ by zone |

---

## 12. Demo Responsibility

You own **[0:30–1:00]** of the demo video:
> View 3 tiers → show high-risk vs low-risk premium difference → Select Balanced → Pay via UPI → Policy activated → View coverage dashboard

**Key demo moment:** Show that Koramangala (high-risk) has higher premium than a low-risk zone. This is what judges care about.
