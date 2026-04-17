# TASK-1: Rider Service + Authentication + OTP

**Owner:** Developer 1  
**Module:** Rider Service  
**Priority:** P0 (Critical Path — all other services depend on authenticated riders)  
**Estimated Duration:** 14 days (parallel with other devs)

---

## 1. Ownership Summary

You own the **identity layer** of Zylo. Every other service depends on your JWT tokens and rider profiles. Your module is the first thing that runs in the demo and the first thing judges see.

**You are responsible for:**
- OTP generation/verification (Redis-backed)
- Rider registration and profile management
- JWT authentication middleware (used by ALL other devs)
- Risk profile generation on onboarding
- Shared auth middleware that Dev 2–5 will import
- Docker setup + DB schema initialization (Day 1 infrastructure lead)

---

## 2. Database Tables You Own

### `riders`
```sql
CREATE TABLE riders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL,  -- zepto, blinkit, swiggy
    city VARCHAR(50) NOT NULL,
    zone_id UUID NOT NULL REFERENCES zones(id),
    upi_id VARCHAR(100),
    kyc_status VARCHAR(20) DEFAULT 'pending',  -- pending, verified, rejected
    trust_score INTEGER DEFAULT 50,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### `rider_risk_profiles`
```sql
CREATE TABLE rider_risk_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rider_id UUID UNIQUE REFERENCES riders(id),
    zone_id UUID REFERENCES zones(id),
    income_volatility DECIMAL(4, 2) DEFAULT 0,
    disruption_probability DECIMAL(4, 2) DEFAULT 0,
    four_week_earnings JSONB,  -- {"week_12": 4250, "week_11": 4100...}
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### `zones` (shared — you create it, others read from it)
```sql
CREATE TABLE zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    flood_risk_score INTEGER DEFAULT 0,
    traffic_risk_score INTEGER DEFAULT 0,
    store_risk_score INTEGER DEFAULT 0,
    composite_risk_score INTEGER DEFAULT 0,
    lat DECIMAL(10, 8),
    lon DECIMAL(11, 8)
);
```

### `rider_zone_baselines`
```sql
CREATE TABLE rider_zone_baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rider_id UUID NOT NULL REFERENCES riders(id),
    zone_id UUID NOT NULL REFERENCES zones(id),
    week VARCHAR(10) NOT NULL,
    slot_time TIME NOT NULL,
    avg_earnings INTEGER NOT NULL,
    avg_orders INTEGER NOT NULL,
    disruption_count INTEGER DEFAULT 0,
    UNIQUE(rider_id, zone_id, week, slot_time)
);
```

---

## 3. API Endpoints You Build

### 3.1 `POST /api/riders/send-otp`
Send OTP to phone number. Store mock OTP `"123456"` in Redis with 5-min TTL.

**Request:**
```json
{ "phone": "+919876543210" }
```
**Response (200):**
```json
{ "message": "OTP sent", "expires_in": 300 }
```
**Implementation:** `Redis SET otp:{phone} "123456" EX 300`

---

### 3.2 `POST /api/riders/verify-otp`
Verify OTP and return a temporary token for registration.

**Request:**
```json
{ "phone": "+919876543210", "otp": "123456" }
```
**Response (200):**
```json
{ "valid": true, "temp_token": "eyJhbG..." }
```
**Implementation:** `Redis GET otp:{phone}` → compare → `Redis DEL otp:{phone}` → issue temp JWT

---

### 3.3 `POST /api/riders/register`
Create rider profile after OTP verification.

**Headers:** `Authorization: Bearer {temp_token}`

**Request:**
```json
{
  "name": "Arjun Kumar",
  "platform": "zepto",
  "city": "bengaluru",
  "zone": "koramangala",
  "slots": ["18:00-21:00", "21:00-23:00"],
  "upi_id": "arjun@oksbi"
}
```
**Response (201):**
```json
{
  "rider_id": "rd_001",
  "name": "Arjun Kumar",
  "platform": "zepto",
  "zone": "koramangala",
  "active_policy": null,
  "trust_score": 85,
  "jwt_token": "eyJhbG..."
}
```

---

### 3.4 `POST /api/riders/onboard`
Generate earnings baseline and get premium quote. Calls **Dev 2's** `POST /api/risk/premium` internally.

**Headers:** `Authorization: Bearer {jwt_token}`

**Request:**
```json
{
  "typical_slots": ["18:00-21:00", "21:00-23:00"],
  "plan_tier": "balanced"
}
```
**Response (200):**
```json
{
  "risk_profile": {
    "zone_risk_score": 72,
    "income_volatility": "high",
    "disruption_probability": 0.65,
    "explanation": "Monsoon season + high-traffic zone"
  },
  "premium_quote": {
    "essential": {"weekly": 120, "coverage": "70%"},
    "balanced": {"weekly": 180, "coverage": "80%"},
    "max_protect": {"weekly": 250, "coverage": "90%"}
  },
  "slot_breakdown": [
    {"slot": "18:00-21:00", "expected_earnings": 360, "risk_score": 75},
    {"slot": "21:00-23:00", "expected_earnings": 240, "risk_score": 68}
  ]
}
```

---

### 3.5 `GET /api/riders/me`
Return authenticated rider profile.

**Headers:** `Authorization: Bearer {jwt_token}`

**Response (200):**
```json
{
  "rider_id": "rd_001",
  "name": "Arjun Kumar",
  "phone": "+919876543210",
  "platform": "zepto",
  "city": "bengaluru",
  "zone": "koramangala",
  "kyc_status": "verified",
  "trust_score": 85,
  "policy_week": "2026-W13"
}
```

---

### 3.6 `GET /api/riders/me/risk-profile`
Return rider's zone risk + earnings volatility.

**Headers:** `Authorization: Bearer {jwt_token}`

**Response (200):**
```json
{
  "zone_flood_risk": 65,
  "zone_traffic_risk": 78,
  "income_volatility": 0.42,
  "composite_risk_score": 72,
  "four_week_earnings": {
    "week_12": 4250, "week_11": 4100,
    "week_10": 3800, "week_9": 4450
  },
  "avg_per_slot": {
    "18:00-21:00": 360,
    "21:00-23:00": 240
  }
}
```

---

### 3.7 `GET /api/zones`
List available zones (public endpoint).

**Response (200):**
```json
{
  "zones": [
    {"id": "zn_001", "name": "koramangala", "city": "bengaluru", "risk_score": 72},
    {"id": "zn_002", "name": "gachibowli", "city": "hyderabad", "risk_score": 65}
  ]
}
```

---

### 3.8 `GET /health`
Health check endpoint for all services.

**Response (200):**
```json
{
  "status": "healthy",
  "postgres": "connected",
  "redis": "connected",
  "timestamp": "2026-03-30T15:00:00Z"
}
```

---

## 4. Shared Modules You Provide to Other Devs

### 4.1 Auth Middleware (`shared/auth.py`)
```python
# Every other developer imports this
from shared.auth import get_current_rider, require_admin

@router.get("/api/policies/active")
async def get_active_policy(rider = Depends(get_current_rider)):
    ...
```

### 4.2 Shared Schemas (`shared/schemas.py`)
```python
class RiderBase(BaseModel):
    id: UUID
    phone: str
    name: str
    platform: str
    zone_id: UUID

class TokenData(BaseModel):
    rider_id: UUID
    role: str  # "rider" | "admin"
```

### 4.3 Database Session (`shared/database.py`)
```python
# Provide SQLAlchemy session factory for all devs
from shared.database import get_db
```

---

## 5. Dependencies on Other Devs

| You Call | Owned By | Contract | When |
|----------|----------|----------|------|
| `POST /api/risk/premium` | Dev 2 (ML/Premium) | During `/onboard` to get premium quote | Day 5+ |

---

## 6. Other Devs Depend on You

| Consumer | What They Need | Deadline |
|----------|---------------|----------|
| **Dev 2** (Policy) | `get_current_rider` middleware, `riders` table | Day 3 |
| **Dev 3** (Triggers) | `riders` table, zone data, rider online status | Day 3 |
| **Dev 4** (Claims) | `riders` table, `rider_zone_baselines`, auth middleware | Day 3 |
| **Dev 5** (Admin) | `require_admin` middleware, rider profiles | Day 4 |
| **ALL** | JWT auth middleware, DB session factory, shared schemas | Day 2 |

---

## 7. Infrastructure Responsibilities (Day 1)

You are the **infrastructure lead**. On Day 1, you set up:

- [x] `docker-compose.yml` — PostgreSQL (TimescaleDB), Redis, Backend, ML Service, Scheduler
- [x] `.env.example` with all environment variables
- [x] Database migration script (`init.sql`) with ALL tables (coordinate with Dev 2–5)
- [x] Seed data script — 20 riders across 4 cities, zone data, baselines
- [x] FastAPI app skeleton (`main.py`) with CORS, router mounting, error handlers
- [x] `shared/` directory with `auth.py`, `database.py`, `schemas.py`
- [x] `requirements.txt` with all Python dependencies

---

## 8. File Structure You Own

```
backend/
├── main.py                          # FastAPI app entry (you create skeleton)
├── requirements.txt                  # All dependencies
├── Dockerfile
├── shared/
│   ├── __init__.py
│   ├── auth.py                      # JWT middleware (get_current_rider, require_admin)
│   ├── database.py                  # SQLAlchemy engine + session
│   ├── schemas.py                   # Shared Pydantic models
│   └── config.py                    # Settings from .env
├── rider_service/
│   ├── __init__.py
│   ├── router.py                    # All /api/riders/* endpoints
│   ├── service.py                   # Business logic
│   ├── models.py                    # SQLAlchemy ORM models (riders, risk_profiles)
│   └── schemas.py                   # Request/response Pydantic models
├── seeds/
│   ├── seed_zones.py                # Zone seed data
│   ├── seed_riders.py               # 20 demo riders
│   └── seed_baselines.py            # Earnings baselines
└── migrations/
    └── init.sql                     # Full DB schema (all tables)
```

---

## 9. Day-by-Day Plan

| Day | Task | Deliverable |
|-----|------|-------------|
| **1** | Docker setup, DB schema, FastAPI skeleton | `docker-compose up` works, `/health` returns OK |
| **2** | Rider model + CRUD, shared auth module | `shared/auth.py` available for other devs |
| **3** | OTP + Redis flow | Send/verify OTP works end-to-end |
| **4** | JWT auth + registration endpoint | Registration flow complete with JWT |
| **5** | Registration + onboard flow (calls Dev 2 premium API) | Full onboard returns risk profile + quote |
| **6** | Integration test with Dev 2 (policy creation after auth) | Auth → Policy flow works |
| **7** | Risk profile endpoint, zone listing | `/me/risk-profile` and `/zones` working |
| **8** | Seed data: 20 riders, 4 cities, baselines | Demo data loaded |
| **9** | Edge cases: expired OTP, duplicate phone, invalid token | Error handling complete |
| **10** | Model tuning, trust score logic | Trust score updates on activity |
| **11** | End-to-end test: register → onboard → policy → dashboard | Full rider journey works |
| **12** | PWA registration UI (coordinate with frontend) | UI connected to APIs |
| **13** | Integration polish, bug fixes | All integration points stable |
| **14** | Demo final, documentation | Demo-ready |

---

## 10. Error Codes You Handle

| Code | HTTP | Description |
|------|------|-------------|
| `INVALID_OTP` | 400 | OTP verification failed |
| `OTP_EXPIRED` | 400 | OTP TTL exceeded (5 min) |
| `RIDER_NOT_FOUND` | 404 | Rider ID not found |
| `DUPLICATE_PHONE` | 409 | Phone already registered |
| `INVALID_ZONE` | 400 | Zone does not exist |
| `INVALID_PLATFORM` | 400 | Platform not in [zepto, blinkit, swiggy] |
| `TOKEN_EXPIRED` | 401 | JWT token expired |
| `TOKEN_INVALID` | 401 | JWT verification failed |

---

## 11. Acceptance Criteria

- [x] OTP flow works: send → verify → get temp token
- [x] Registration creates rider record with correct zone linkage
- [x] JWT token returned on registration, verified on all protected endpoints
- [x] `/me` returns correct profile
- [x] `/me/risk-profile` returns zone risk + earnings data
- [x] `/zones` returns all seeded zones
- [x] `/health` checks Postgres + Redis connectivity
- [x] Auth middleware importable by Dev 2–5 via `from shared.auth import get_current_rider`
- [x] 20 riders seeded across 4 cities for demo
- [x] All error codes return proper JSON format
- [x] Redis fallback works if connection drops (in-memory cache)

---

## 12. User Stories Covered

| ID | Story | Status |
|----|-------|--------|
| US-01 | Register with phone number | Your scope |
| US-02 | Link delivery platform | Your scope |
| US-03 | Select working zone and time slots | Your scope |
| US-04 | See risk profile with explanation | Your scope |

---

## 13. Demo Responsibility

You own **[0:15–0:30]** of the demo video:
> PWA → Enter phone → OTP → Verify → Link Zepto → Select Koramangala → Select slots → See risk profile

**Make sure it looks smooth and instant.**
