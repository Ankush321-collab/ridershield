# Zylo — Technical Requirements Document (TRD)

**Version:** 1.0  
**Project:** Zylo — Parametric Income Protection System  
**Date:** March 30, 2026  
**Authors:** Software Architecture Team  
**Context:** Hackathon project for 5 developers

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Module Breakdown](#2-module-breakdown)
3. [Service Design](#3-service-design)
4. [API Design](#4-api-design)
5. [Database Design](#5-database-design)
6. [Data Flow](#6-data-flow)
7. [ML Integration](#7-ml-integration)
8. [Trigger System Design](#8-trigger-system-design)
9. [Claims Engine](#9-claims-engine)
10. [Fraud Detection](#10-fraud-detection)
11. [Integration Plan](#11-integration-plan)
12. [Deployment Setup](#12-deployment-setup)
13. [Development Plan](#13-development-plan)
14. [Error Handling](#14-error-handling--edge-cases)
15. [Demo Strategy](#15-demo-strategy)

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                          RIDER MOBILE APP (PWA)                         │
│  Onboarding │ Policy Dashboard │ Manual Claim │ Notifications           │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │ HTTPS / REST API
┌─────────────────────────────────────▼───────────────────────────────────┐
│                      API GATEWAY (FastAPI)                               │
│  CORS │ Authentication (JWT) │ Rate Limiting │ Request Validation         │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
        ┌──────────────┬──────────────┼──────────────┬──────────────┐
        │             │             │            │             │
   ┌────▼────┐  ┌────▼────┐ ┌────▼────┐ ┌──▼──┐  ┌────▼────┐
   │Rider   │  │Policy   │ │Trigger  │  │Claims│  │ Payout  │
   │Service │  │Service │ │Service  │  │Svc   │  │ Service │
   └────┬────┘  └────┬────┘ └────┬────┘ └──┬──┘  └────┬────┘
        │             │             │          │            │
   ┌────▼─────────────▼─────────────▼───────────▼────────────▼──────┐
   │                  ML SERVICE (LightGBM)                         │
   │  Risk Model │ Premium Calculator │ Spam Detector          │
   └────────────────────────┬────────────────────────────────┘
                           │
     ┌──────────────���──────┼─────────────────────┐
     │                   │                    │
┌────▼────┐       ┌────▼────┐        ┌────▼────┐
│PostgreSQL│       │ Redis   │        │  S3 /   │
│  +TSDB  │       │ (Cache) │        │  Local  │
└─────────┘       └─────────┘        └─────────┘
```

### 1.2 Component Diagram Explanation

| Component | Responsibility | Tech |
|-----------|--------------|------|
| Mobile App (PWA) | Rider UI: registration, policy mgmt, manual claims | React/Next.js |
| API Gateway | Auth, validation, routing, rate limiting | FastAPI |
| Rider Service | OTP, registration, KYC, profile mgmt | FastAPI + Redis |
| Policy Service | Plan selection, policy lifecycle | FastAPI + PostgreSQL |
| Risk/Premium Service | ML model, premium calculation | Python + LightGBM |
| Trigger Service | Monitor APIs, evaluate triggers, detect disruptions | FastAPI + Scheduler |
| Claims Service | Auto/manual claims, income gap calc | FastAPI + PostgreSQL |
| Fraud Service | Geo-validation, spam detection | FastAPI + Rules |
| Payout Service | Payment processing | FastAPI |
| Admin Service | Review queue, approve/reject | FastAPI + PostgreSQL |
| PostgreSQL | Core relational data | PostgreSQL 15 |
| TimescaleDB | Time-series (weather, earnings) | TimescaleDB extension |
| Redis | OTP cache, session, rate limiting | Redis 7 |
| File Storage | Geo-tagged photos | Local FS / S3 |

### 1.3 External Integrations

| API | Purpose | Implementation |
|-----|--------|----------------|
| OpenWeatherMap | Weather data (rainfall, AQI, temp) | REST API (polled every 5 min) |
| Google Maps / TomTom | Traffic congestion data | REST API (mocked for prototype) |
| Platform Simulator | Store status, order data | Internal mock module |
| UPI / Razorpay | Payment processing | Mock adapter |

---

## 2. Module Breakdown

### 2.1 Team Assignment (5 Developers)

| Developer | Primary Modules | Secondary Support |
|----------|-----------------|-------------------|
| Dev 1 | Rider Service + Auth + OTP | Redis integration |
| Dev 2 | Policy Service + Policy Lifecycle | Premium API |
| Dev 3 | Trigger Service + Data Collection | External API polling |
| Dev 4 | Claims Service + Payout + Fraud | Income estimation |
| Dev 5 | Admin Service + Manual Claims | Geo-validation, spam detection |

### 2.2 Independent Module Contracts

Each developer builds their module as an independent FastAPI router. All contracts are defined in Section 4 (API Design) to enable parallel development and integration testing.

---

## 3. Service Design

### 3.1 Rider Service

**Purpose:** Manage rider registration, authentication, and profile.

**Responsibilities:**
- OTP generation and validation (Redis-backed, 5-minute expiry)
- Rider registration with KYC (name, phone, platform, zone, slots)
- JWT token issuance and refresh
- Risk profile generation upon onboarding

**Flow:**
```
POST /api/riders/send-otp → Redis SET phone:otp "123456" TTL 300
POST /api/riders/verify-otp → Redis GET phone:otp → DELETE
POST /api/riders/register → Create rider profile + risk profile
POST /api/riders/onboard → Generate earnings baseline + return premium quote
GET /api/riders/me → Return authenticated rider profile
GET /api/riders/me/risk-profile → Return zone risk + volatility
```

### 3.2 Policy Service

**Purpose:** Manage insurance policy lifecycle.

**Responsibilities:**
- Quote generation (3 tiers: Essential, Balanced, Max Protect)
- Policy creation for calendar week
- Policy renewal with recalculated premium
- Policy cancellation
- Coverage status tracking (slots covered, hours remaining)

**Plan Tiers:**

| Plan | Coverage % | Best For |
|------|----------|---------|
| Essential | 70% baseline | Budget riders |
| Balanced | 80% baseline | Standard workers |
| Max Protect | 90% baseline | Peak season |

### 3.3 Risk/Premium Service

**Purpose:** ML-driven premium calculation.

**Responsibilities:**
- LightGBM model for disruption probability
- Zone-level risk scoring
- Premium calculation with explanation
- Tenure discount application
- Plan tier multiplier

**Output:**
- Risk score (0-100)
- 3-tier pricing with slot breakdown
- Explanation: "Premium higher due to monsoon forecast for Thu 7-9 PM in Zone 13"

### 3.4 Trigger Service

**Purpose:** Detect disruptions via external data sources.

**Responsibilities:**
- Poll external APIs every 5 minutes
- Evaluate 5 trigger conditions
- Create DisruptionEvent records
- Detect community signal (mass order collapse)
- Prevent duplicate payouts (single event per slot)

**Triggers:**

| # | Trigger | Threshold | Source |
|---|--------|----------|--------|
| 1 | Heavy Rain | > 40mm/1hr | OpenWeatherMap |
| 2 | Traffic Congestion | > 80/100 for 60+ min | Google Maps (mock) |
| 3 | Dark Store Closed | store_status = CLOSED | Platform Simulator |
| 4 | Platform Outage | platform_status = DOWN | Platform Simulator |
| 5 | Curfew | curfew_active = TRUE | Mock data |

### 3.5 Claims Service

**Purpose:** Process auto and manual claims.

**Responsibilities:**
- Auto claims: on DisruptionEvent → identify insured riders → calculate income gap → payout
- Manual claims: receive rider submission → validate photo → run spam detection → queue for review
- Income estimation using rolling baseline
- Payout calculation: min(income loss, weekly coverage limit)

### 3.6 Fraud/Validation Service

**Purpose:** Detect fraudulent claims.

**Responsibilities:**
- GPS consistency check (photo EXIF vs. telemetry)
- Peer comparison (rider vs. zone peers)
- Time anomaly detection
- Weather/traffic corroboration
- Composite spam score (0-100)

---

## 4. API Design

### 4.1 Authentication Endpoints

#### POST /api/riders/send-otp
Send OTP to phone number.

**Request:**
```json
{
  "phone": "+919876543210"
}
```

**Response (200):**
```json
{
  "message": "OTP sent",
  "expires_in": 300
}
```

#### POST /api/riders/verify-otp
Verify OTP and create temp session.

**Request:**
```json
{
  "phone": "+919876543210",
  "otp": "123456"
}
```

**Response (200):**
```json
{
  "valid": true,
  "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### POST /api/riders/register
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
  "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### POST /api/riders/onboard
Generate earnings baseline and get premium quote.

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

#### GET /api/riders/me
Get authenticated rider profile.

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

#### GET /api/riders/me/risk-profile
Get rider's risk profile.

**Headers:** `Authorization: Bearer {jwt_token}`

**Response (200):**
```json
{
  "zone_flood_risk": 65,
  "zone_traffic_risk": 78,
  "income_volatility": 0.42,
  "composite_risk_score": 72,
  "four_week_earnings": {
    "week_12": 4250,
    "week_11": 4100,
    "week_10": 3800,
    "week_9": 4450
  },
  "avg_per_slot": {
    "18:00-21:00": 360,
    "21:00-23:00": 240
  }
}
```

---

### 4.2 Policy Endpoints

#### GET /api/policies/quote
Get dynamic premium quotes for all 3 tiers.

**Headers:** `Authorization: Bearer {jwt_token}`

**Request Query:** `?slots=18:00-21:00,21:00-23:00&city=bengaluru`

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

#### POST /api/policies
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

#### GET /api/policies/active
Get active policy.

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

#### GET /api/policies/{policy_id}
Get policy details.

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

#### PUT /api/policies/{policy_id}/renew
Renew policy for next week.

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

#### DELETE /api/policies/{policy_id}
Cancel policy.

**Headers:** `Authorization: Bearer {jwt_token}`

**Response (204):** No content

---

### 4.3 ML/Premium Endpoints

#### POST /api/risk/premium
Calculate premium with ML model.

**Headers:** `Authorization: Bearer {jwt_token}`

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

### 4.4 Trigger & Disruption Endpoints

#### GET /api/triggers/status
Get live trigger status.

**Response (200):**
```json
{
  "active_triggers": [
    {
      "trigger_id": "tr_001",
      "type": "heavy_rain",
      "zone": "gachibowli",
      "threshold": "52mm/1hr",
      "active_since": "2026-03-30T15:05:00Z",
      "affected_riders": 12
    }
  ],
  "community_signals": [],
  "last_evaluation": "2026-03-30T15:05:00Z"
}
```

#### GET /api/disruption-events
List disruption events.

**Headers:** `Authorization: Bearer {jwt_token}`

**Query:** `?zone=koramangala&from=2026-03-30T00:00:00Z`

**Response (200):**
```json
{
  "events": [
    {
      "event_id": "de_001",
      "trigger_type": "heavy_rain",
      "zone": "gachibowli",
      "slot": "15:00-15:30",
      "severity": "high",
      "created_at": "2026-03-30T15:05:00Z"
    }
  ]
}
```

---

### 4.5 Claims Endpoints

#### GET /api/claims
List rider's claims.

**Headers:** `Authorization: Bearer {jwt_token}`

**Response (200):**
```json
{
  "claims": [
    {
      "claim_id": "clm_001",
      "type": "auto",
      "disruption_event_id": "de_001",
      "income_loss": 540,
      "payout_amount": 540,
      "status": "paid",
      "created_at": "2026-03-30T15:10:00Z"
    }
  ]
}
```

#### GET /api/claims/{claim_id}
Get claim details.

**Headers:** `Authorization: Bearer {jwt_token}`

**Response (200):**
```json
{
  "claim_id": "clm_001",
  "rider_id": "rd_001",
  "type": "auto",
  "disruption_event_id": "de_001",
  "policy_id": "pol_001",
  "income_loss": 540,
  "expected_earnings": 720,
  "actual_earnings": 180,
  "payout_amount": 540,
  "fraud_score": 15,
  "status": "paid",
  "created_at": "2026-03-30T15:10:00Z",
  "paid_at": "2026-03-30T15:12:00Z"
}
```

#### POST /api/claims/manual
Submit manual claim with geo-tagged photo.

**Headers:** `Authorization: Bearer {jwt_token}`

**Request (multipart/form-data):**
```
disruption_type: traffic
description: Road work causing gridlock on main road
incident_time: 2026-03-30T19:30:00Z
photo: <file upload>
latitude: 12.9352
longitude: 77.6245
```

**Response (201):**
```json
{
  "claim_id": "mcl_001",
  "rider_id": "rd_001",
  "type": "manual",
  "disruption_type": "traffic",
  "status": "under_review",
  "spam_score": 25,
  "geo_validation": {
    "photo_gps": {"lat": 12.9352, "lon": 77.6245},
    "telemetry_gps": {"lat": 12.9355, "lon": 77.6248},
    "distance_m": 45,
    "valid": true
  },
  "corroboration": {
    "weather_match": true,
    "traffic_match": true,
    "known_disruption": false
  },
  "created_at": "2026-03-30T19:45:00Z"
}
```

#### GET /api/claims/manual/{claim_id}
Check manual claim status.

**Headers:** `Authorization: Bearer {jwt_token}`

**Response (200):**
```json
{
  "claim_id": "mcl_001",
  "status": "approved",
  "payout_amount": 380,
  "reviewed_at": "2026-03-30T20:30:00Z",
  "reviewer_notes": "Geo-validation passed, traffic corroboration confirmed"
}
```

---

### 4.6 Admin Endpoints

#### GET /api/admin/claims
List all auto claims for admin.

**Headers:** `Authorization: Bearer {admin_jwt_token}`

**Response (200):**
```json
{
  "claims": [
    {
      "claim_id": "clm_001",
      "rider_id": "rd_001",
      "type": "auto",
      "income_loss": 540,
      "payout_amount": 540,
      "fraud_score": 15,
      "status": "paid"
    }
  ]
}
```

#### GET /api/admin/claims/manual
List manual claims for review.

**Headers:** `Authorization: Bearer {admin_jwt_token}`

**Query:** `?sort=spam_score&order=asc`

**Response (200):**
```json
{
  "claims": [
    {
      "claim_id": "mcl_001",
      "rider_id": "rd_001",
      "disruption_type": "traffic",
      "spam_score": 25,
      "status": "under_review",
      "geo_validation": {"valid": true, "distance_m": 45},
      "corroboration": {"weather_match": true, "traffic_match": true},
      "submitted_at": "2026-03-30T19:45:00Z"
    }
  ]
}
```

#### POST /api/admin/claims/{claim_id}/approve
Approve manual claim.

**Headers:** `Authorization: Bearer {admin_jwt_token}`

**Response (200):**
```json
{
  "claim_id": "mcl_001",
  "status": "approved",
  "payout_amount": 380,
  "payout_id": "pout_001"
}
```

#### POST /api/admin/claims/{claim_id}/reject
Reject manual claim.

**Headers:** `Authorization: Bearer {admin_jwt_token}`

**Request:**
```json
{
  "reason": "Location mismatch: photo taken 2.3km from rider's declared zone"
}
```

**Response (200):**
```json
{
  "claim_id": "mcl_001",
  "status": "rejected",
  "reason": "Location mismatch: photo taken 2.3km from rider's declared zone"
}
```

---

### 4.7 Payout Endpoints

#### GET /api/payouts
List rider's payouts.

**Headers:** `Authorization: Bearer {jwt_token}`

**Response (200):**
```json
{
  "payouts": [
    {
      "payout_id": "pout_001",
      "claim_id": "clm_001",
      "amount": 540,
      "method": "upi",
      "upi_id": "arjun@oksbi",
      "status": "completed",
      "created_at": "2026-03-30T15:12:00Z"
    }
  ]
}
```

---

### 4.8 Health & Utility Endpoints

#### GET /health
Health check for all services.

**Response (200):**
```json
{
  "status": "healthy",
  "postgres": "connected",
  "redis": "connected",
  "timestamp": "2026-03-30T15:00:00Z"
}
```

#### GET /api/zones
List available zones.

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

## 5. Database Design

### 5.1 Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   riders    │       │  policies   │       │   claims    │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)    │◄──────│ rider_id    │◄──────│ rider_id   │
│ phone      │       │ policy_id   │       │ policy_id  │
│ name       │       │ plan_tier   │       │ disruption│
│ platform   │       │ week       │       │ income_loss│
│ zone_id    │       │ premium   │       │ payout    │
│ upi_id    │       │ status    │       │ status   │
│ trust_score│       │ created   │       │ created  │
│ kyc_status│       │ expires   │       │ fraud_score│
└─────┬───���─���┘       └─────┬──────┘       └─────┬──────┘
      │                    │                    │
      │    ┌─────────────┴─────────────┐      │
      │    │                        │      │
      ▼    ▼                        ▼      ▼
┌──────────────────┐    ┌──────────────────┐
│ disruption_     │    │    payouts      │
│ events         │    ├──────────────────┤
├──────────────────┤    │ payout_id      │
│ event_id        │◄───│ claim_id      │
│ trigger_type   │    │ amount       │
│ zone_id       │    │ upi_id       │
│ slot         │    │ status       │
│ severity    │    │ created     │
│ created     │    └──────────────┘
└──────────────┘

┌──────────────────┐    ┌──────────────────┐
│ rider_zone_       │    │    micro_slots    │
│ baselines       │    ├──────────────────┤
├──────────────────┤    │ slot_id          │
│ rider_id        │───►│ zone_id         │
│ zone_id        │    │ time_start      │
│ week          │    │ time_end       │
│ avg_earnings  │    │ expected_earn  │
│ order_count   │    │ disruption_prob│
└───────────────┘    └──────────────────┘
```

### 5.2 Table Definitions

#### riders
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

#### policies
```sql
CREATE TABLE policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rider_id UUID NOT NULL REFERENCES riders(id),
    plan_tier VARCHAR(20) NOT NULL,  -- essential, balanced, max_protect
    week VARCHAR(10) NOT NULL,  -- 2026-W13
    premium INTEGER NOT NULL,
    coverage_limit INTEGER NOT NULL,
    coverage_pct INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'active',  -- active, cancelled, expired
    slots_covered TEXT[],  -- Array of slot strings
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    UNIQUE(rider_id, week));
```

#### claims
```sql
CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rider_id UUID NOT NULL REFERENCES riders(id),
    policy_id UUID NOT NULL REFERENCES policies(id),
    disruption_event_id UUID REFERENCES disruption_events(id),
    type VARCHAR(20) NOT NULL,  -- auto, manual
    disruption_type VARCHAR(50),
    income_loss INTEGER NOT NULL,
    expected_earnings INTEGER NOT NULL,
    actual_earnings INTEGER NOT NULL,
    payout_amount INTEGER NOT NULL,
    fraud_score INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected, paid
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP));
```

#### manual_claims
```sql
CREATE TABLE manual_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rider_id UUID NOT NULL REFERENCES riders(id),
    policy_id UUID NOT NULL REFERENCES policies(id),
    disruption_type VARCHAR(50) NOT NULL,
    description TEXT,
    incident_time TIMESTAMP NOT NULL,
    photo_path VARCHAR(500),
    photo_exif_lat DECIMAL(10, 8),
    photo_exif_lon DECIMAL(11, 8),
    telemetry_lat DECIMAL(10, 8),
    telemetry_lon DECIMAL(11, 8),
    gps_distance_m INTEGER,
    spam_score INTEGER DEFAULT 0,
    geo_valid BOOLEAN DEFAULT false,
    weather_match BOOLEAN,
    traffic_match BOOLEAN,
    review_status VARCHAR(20) DEFAULT 'pending',  -- pending, under_review, approved, rejected
    reviewer_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP));
```

#### disruption_events
```sql
CREATE TABLE disruption_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_type VARCHAR(50) NOT NULL,
    zone_id UUID NOT NULL REFERENCES zones(id),
    slot_start TIMESTAMP NOT NULL,
    slot_end TIMESTAMP NOT NULL,
    severity VARCHAR(20) NOT NULL,  -- low, medium, high, critical
    data_json JSONB,  -- Raw trigger data
    created_at TIMESTAMP DEFAULT NOW());
```

#### payouts
```sql
CREATE TABLE payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id),
    rider_id UUID NOT NULL REFERENCES riders(id),
    amount INTEGER NOT NULL,
    method VARCHAR(20) DEFAULT 'upi',
    upi_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    reference_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP));
```

#### rider_zone_baselines
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
    UNIQUE(rider_id, zone_id, week, slot_time));
```

#### micro_slots
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
    store_risk_score INTEGER);
```

#### zones
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
    lon DECIMAL(11, 8));
```

#### rider_risk_profiles
```sql
CREATE TABLE rider_risk_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rider_id UUID UNIQUE REFERENCES riders(id),
    zone_id UUID REFERENCES zones(id),
    income_volatility DECIMAL(4, 2) DEFAULT 0,
    disruption_probability DECIMAL(4, 2) DEFAULT 0,
    four_week_earnings JSONB,  -- {"week_12": 4250, "week_11": 4100...}
    updated_at TIMESTAMP DEFAULT NOW());
```

#### weather_data (TimescaleDB hypertable)
```sql
CREATE TABLE weather_data (
    time TIMESTAMPTZ NOT NULL,
    zone_id UUID NOT NULL,
    temperature DECIMAL(5, 2),
    rainfall_mm DECIMAL(6, 2),
    aqi INTEGER,
    humidity INTEGER,
    wind_speed DECIMAL(5, 2),
    PRIMARY KEY (time, zone_id));
SELECT create_hypertable('weather_data', 'time');
```

#### platform_snapshots (TimescaleDB hypertable)
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
    PRIMARY KEY (time, rider_id));
SELECT create_hypertable('platform_snapshots', 'time');
```

---

## 6. Data Flow

### 6.1 Registration → Policy Flow

```
Rider               Rider Service         Policy Service       Database
  │                      │                     │                │
  ├──send-otp───────────► │                     │                │
  │                      ├──Redis SET─────────► │                │
  │◄─────OTP sent────── │                     │                │
  │                      │                     │                │
  ├──verify-otp───────► │                     │                │
  │                      ├──Redis GET────────► │                │
  │◄────valid────────── │                     │                │
  │                      │                     │                │
  ├──register──────────► │                     │                │
  │                      ├──INSERT rider───►│                │
  │◄────JWT─────────── │                     │                │
  │                      │                     │                │
  ├──onboard──────────► │                     │                │
  │                      │──Calc baseline──►│                │
  │                      │◄─Premium quote──│                │
  │◄──Quote + profile──│                     │                │
  │                      │                     │                │
  ├──POST /policies───►│                     │                │
  │                      │──INSERT policy──►│                │
  │◄──Policy active────│                     │                │
```

### 6.2 Active Policy → Trigger → Claim → Payout

```
Data Collector      Trigger Service      Claims Service      Payout Service
    │                    │                  │                  │
    ├──poll weather─────►│                  │                  │
    ├──poll traffic─────►│                  │                  │
    ├──poll store───────►│                  │                  │
    │                   │                  │                  │
    │                   ├──evaluate triggers│                  │
    │                   │                  │                  │
    │                   │──threshold met───►│                  │
    │                   │◄──trigger fire───│                  │
    │                   │                  │                  │
    │                   ├──CREATE event───►│                  │
    │                   │                  │                  │
    │                   │                  ├────identify riders│
    │                   │                  │◄──insured list──│
    │                   │                  │                  │
    │                   │                  ├───calculate gap│
    │                   │                  │◄──income loss───│                  │
    │                   │                  │                  │
    │                   │                  ├───fraud check──►│
    │                   │                  │◄──score: 15────│                  │
    │                   │                  │                  │
    │                   │                  ├──CREATE claim───►│
    │                   │                  │◄──claim created                  │
    │                   │                  │                  │
    │                   │                  │──CREATE payout►│
    │                   │                  │◄──payout ok───│
    │                   │                  │                  │
    │                   │                  │──process UPI──►│
    │                   │                  │◄── credited───│
    │                   │                  │                  │
    │                   │                  │◄─Payout complete
```

### 6.3 Manual Claim Flow

```
Rider               Claims Service        Fraud Service       Admin Service
  │                      │                  │                  │
  ├──POST manual claim────►│                  │                  │
  │   + photo            │                  │                  │
  │                      │                  │                  │
  │                      ├──extract EXIF───►│                  │
  │                      │◄──gps coords────│                  │
  │                      │                  │                  │
  │                      ├──compare GPS────────────────►
  │                      │◄──distance: 45m─│                  │
  │                      │                  │                  │
  │                      ├──query weather►│                  │
  │                      │◄──match────────│                  │
  │                      │                  │                  │
  │                      ├──query traffic►│                  │
  │                      │◄──match─────────│                  │
  │                      │                  │                  │
  │                      ├──spam score────►│                  │
  │                      │◄──score: 25────│                  │
  │                      │                  │                  │
  │                      ├──CREATE claim───►│                  │
  │◄──claim submitted───│                  │                  │
  │                      │                  │                  │
  │                      │                  │──GET queue─────►
  │                      │                  │◄──sorted list───
  │                      │                  │                  │
  │                      │                  │──approve────────►
  │                      │                  │                  │
  │                      │                  │──CREATE payout►│
  │                      │                  │◄──complete─────
```

---

## 7. ML Integration

### 7.1 Model: Risk/Premium Predictor

**Model Type:** LightGBM Gradient Boosting

**Training Data Generation:**
- ~50,000 synthetic records
- Features: zone risk, earnings history, demand, tenure, weather forecast, time-of-day

### 7.2 Input Features

| Feature | Type | Description |
|---------|------|-------------|
| zone_flood_risk | Integer (0-100) | Historical flood risk of zone |
| zone_traffic_risk | Integer (0-100) | Traffic congestion risk |
| zone_store_risk | Integer (0-100) | Dark store disruption risk |
| day_of_week | Integer (0-6) | Day of week |
| hour | Integer (0-23) | Hour of day |
| is_weekend | Boolean | Weekend indicator |
| is_monsoon | Boolean | Monsoon season (Jun-Sep) |
| rider_tenure_days | Integer | Days since registration |
| rider_avg_earnings | Float | 4-week average earnings |
| rider_order_consistency | Float | Order count CV |
| forecast_rainfall | Float | Weather forecast mm |
| forecast_aqi | Integer | Air quality index |

### 7.3 Output

| Output | Type | Description |
|--------|------|-------------|
| disruption_probability | Float (0-1) | Probability of earnings disruption |
| expected_earnings | Float | Expected earnings for slot |
| risk_band | String | low/medium/high/critical |

### 7.4 Model Call Flow

```python
# In premium_service.py
def calculate_premium(zone_id, slots, rider_tenure, rider_avg_earnings):
    # Collect features
    features = collect_features(zone_id, slots, rider_tenure, rider_avg_earnings)
    
    # Load model
    model = joblib.load("backend/ml/model_artifacts/risk_model.pkl")
    
    # Predict
    disruption_prob = model.predict_proba(features)[:, 1][0]
    risk_band = map_prob_to_band(disruption_prob)
    
    # Calculate premium
    base_premium = get_base_premium(risk_band)
    tenure_discount = calculate_tenure_discount(rider_tenure)
    final_premium = base_premium * (1 - tenure_discount)
    
    return {
        "risk_score": int(disruption_prob * 100),
        "disruption_probability": disruption_prob,
        "premium": final_premium,
        "explanation": f"Premium based on {risk_band} risk band"
    }
```

### 7.5 Model Artifacts Location

```
backend/
  ml/
    model_artifacts/
      risk_model.pkl
      feature_names.json
    training/
      generate_synthetic_data.py
      train_model.py
```

---

## 8. Trigger System Design

### 8.1 Trigger Rules

| # | Trigger | Condition | Data Source |
|---|---------|-----------|-------------|
| 1 | Heavy Rain | rainfall_mm > 40 in 1hr | OpenWeatherMap |
| 2 | Traffic Congestion | congestion_index > 80 for 60+ min | Google Maps (mock) |
| 3 | Dark Store Closure | store_status = CLOSED | Platform Simulator |
| 4 | Platform Outage | platform_status = DOWN | Platform Simulator |
| 5 | Regulatory | curfew_active = TRUE | Mock data |

### 8.2 Evaluation Cycle

```
┌─────────────────────────────────────────────────────┐
│              Background Scheduler                   │
│                 (every 5 minutes)                   │
└─────────────────────────────────────────────────────┘
                         │
         ┌──────────────┴──────────────┐
         │                             │
    ┌────▼────┐                  ┌────▼────┐
    │ Poll    │                  │ Poll    │
    │Weather │                  │Traffic │
    └────┬────┘                  └────┬────┘
         │                             │
    ┌────▼────┐                  ┌────▼────┐
    │ Poll    │                  │ Poll    │
    │Platform│                  │Community│
    │ Store  │                  │ Signal │
    └────┬────┘                  └────┬────┘
         │                             │
         └──────────────┬──────────────┘
                        │
                 ┌──────▼──────┐
                 │ Evaluate   │
                 │ Triggers   │
                 └──────┬──────┘
                        │
            ┌───────────┼───────────┐
            │           │           │
       ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
       │Trigger 1│ │Trigger N│ │ No      │
       │ TRUE    │ │ TRUE    │ │Trigger │
       └��─��─┬────┘ └────┬────┘ └────┬────┘
            │           │           │
            └───────────┼───────────┘
                        │
                 ┌─────▼─────┐
                 │ Merge to  │
                 │ Single   │
                 │ Event   │
                 └─────┬─────┘
                       │
                ┌─────▼─────┐
                │Create    │
                │Disruption│
                │Event    │
                └─────────┘
```

### 8.3 Three-Factor Validation

A disruption event is created only when ALL 3 conditions are met:

1. **Trigger Condition TRUE:** External API trigger threshold is met
2. **Rider Online & In-Zone:** Rider GPS confirms presence + platform shows online status
3. **Earnings Below Baseline:** Actual earnings < model-predicted baseline

### 8.4 Implementation

```python
# In trigger_service.py
async def evaluate_triggers():
    # Poll all data sources
    weather_data = await poll_weather()
    traffic_data = await poll_traffic()
    platform_data = await poll_platform()
    
    # Evaluate each trigger zone
    for zone in zones:
        # Check trigger 1: Heavy rain
        if weather_data[zone.id].rainfall_mm > 40:
            await create_disruption_event(
                trigger_type="heavy_rain",
                zone_id=zone.id,
                severity="high",
                data={"rainfall_mm": weather_data[zone.id].rainfall_mm}
            )
        
        # Check trigger 2: Traffic congestion
        if traffic_data[zone.id].congestion_index > 80:
            if traffic_data[zone.id].duration_min >= 60:
                await create_disruption_event(
                    trigger_type="traffic_congestion",
                    zone_id=zone.id,
                    severity="medium",
                    data={"congestion": traffic_data[zone.id].congestion_index}
                )
        
        # ... other triggers
        
        # Check community signal (mass order collapse)
        zone_riders = await get_zone_riders(zone.id)
        affected_count = sum(1 for r in zone_riders 
                          if r.order_rate_drop_pct > 70)
        if affected_count / len(zone_riders) > 0.7:
            await create_disruption_event(
                trigger_type="community_signal",
                zone_id=zone.id,
                severity="high",
                data={"affected_pct": affected_count/len(zone_riders)}
            )
```

---

## 9. Claims Engine

### 9.1 Auto Claims Logic

```
DisruptionEvent Created
         │
         ▼
┌─────────────────┐
│ Find Insured    │──► Get ALL riders with active policy in zone
│ Riders in Zone │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Filter: Online  │──► Platform shows rider_status = ONLINE
│ + In Zone       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Calculate       │──► income_loss = expected - actual
│ Income Gap     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fraud Check    │──► GPS + peer comparison
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Create Claim   │
│ + Payout       │
└──────────��─��────┘
```

### 9.2 Auto Claims Calculation

```python
def calculate_auto_claim(rider, disruption_event, policy):
    # Get baseline earnings
    baseline = get_baseline(rider.id, disruption_event.slot_time)
    
    # Get actual earnings from platform snapshot
    actual = get_actual_earnings(rider.id, disruption_event.slot_time)
    
    # Calculate loss
    income_loss = baseline - actual
    
    # Apply coverage limit
    payout = min(income_loss, policy.coverage_limit)
    
    return {
        "rider_id": rider.id,
        "disruption_event_id": disruption_event.id,
        "policy_id": policy.id,
        "expected_earnings": baseline,
        "actual_earnings": actual,
        "income_loss": income_loss,
        "payout_amount": payout,
        "status": "pending"
    }
```

### 9.3 Manual Claims Flow

1. Rider submits: disruption type + description + geo-tagged photo + incident time
2. System extracts EXIF GPS from photo
3. System compares photo GPS vs. rider telemetry GPS → geo_validation
4. System queries weather API for photo location/time → weather_match
5. System queries traffic API for photo location/time → traffic_match
6. System computes spam_score from all signals
7. If spam_score >= 70: auto-reject
8. If spam_score < 70: queue for admin review

### 9.4 Payout Calculation

```
Expected Income = avg_orders_per_hr × disrupted_hrs × ₹per_order
Actual Income   = actual_orders × ₹per_order
Income Loss    = Expected - Actual
Payout        = min(Income Loss, Weekly Coverage Limit)
```

Example:
- Expected: 12 orders/hr × 4 hrs × ₹15 = ₹720
- Actual: 3 orders/hr × 4 hrs × ₹15 = ₹180
- Income Loss: ₹720 - ₹180 = ₹540
- Coverage Limit (80% of ₹3600): ₹2880
- Payout: min(₹540, ₹2880) = **₹540**

---

## 10. Fraud Detection

### 10.1 Auto Claims (Basic Rules)

| Check | Rule | Action |
|-------|------|--------|
| GPS Consistency | Rider GPS in zone at time of disruption | Required |
| Peer Comparison | Rider earnings drop vs. peer average | Flag if >2x peers |
| Baseline Validity | Rider has >= 1 week baseline history | Use zone median if not |
| Duplicate Claim | Same disruption, same rider, already paid | Reject |

### 10.2 Manual Claims (Spam Detection)

| Signal | Detection | Weight |
|--------|-----------|--------|
| Location Mismatch | Photo GPS vs. telemetry GPS > 500m | High |
| Time Anomaly | EXIF timestamp vs. incident time > 30 min | Medium |
| Weather Mismatch | Claim weather but API shows benign | Medium |
| Traffic Mismatch | Claim traffic but API shows low congestion | Medium |
| Known Disruption | Matching DisruptionEvent exists | Negative (-) |

**Spam Score Calculation:**
```
spam_score = (
    location_mismatch × 0.35 +
    time_anomaly × 0.25 +
    weather_mismatch × 0.20 +
    traffic_mismatch × 0.20
)

Auto-reject if spam_score >= 70
Queue for review if spam_score < 70
```

### 10.3 Implementation

```python
def calculate_spam_score(manual_claim, weather_data, traffic_data):
    score = 0
    
    # Location mismatch (high weight)
    if manual_claim.gps_distance_m > 500:
        score += 35
    
    # Time anomaly (medium weight)
    time_delta = abs(
        (manual_claim.photo_timestamp - manual_claim.incident_time)
        .total_seconds() / 60
    )
    if time_delta > 30:
        score += 25
    
    # Weather mismatch (medium weight)
    if manual_claim.disruption_type == "weather":
        if weather_data.rainfall_mm < 7.6 and weather_data.wind_kmh < 40:
            score += 20
    
    # Traffic mismatch (medium weight)
    if manual_claim.disruption_type == "traffic":
        if traffic_data.congestion_index < 70:
            score += 20
    
    return min(score, 100)
```

---

## 11. Integration Plan

### 11.1 Module Connection Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY                                 │
│                    (FastAPI + CORS + Auth)                        │
└────────────────────────────────────────────────────────────────────┘
         │      │      │      │      │      │      │      │
    ┌────┘      │      │      │      │      │      └────┐
    │           │      │      │      │      │           │
┌───▼───┐  ┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│Rider  │  │Policy │ │ Risk  │ │Trigger│ │Claims│ │Admin │
│Service│  │Service│ │Service│ │Service│ │Service│ │Service│
└───┬───┘  └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
    │          │        │        │        │        │        │
    │    ┌────┴────────┴────────┘        │    ┌────┴────┐
    │    │                               │         │
    │    │         ML SERVICE           │         │
    │    │    (LightGBM + Premium)      │         │
    │    │                           │         │
    │    └────────────┬──────────────┘         │
    │                 │                       │
    │    ┌────────────┼────────────┐          │
    │    │           │            │          │
┌───▼───┐      ┌───▼───┐   ┌───▼───┐   ┌───▼───┐
│PostgreSQL│     │Redis │   │S3/FS │   │TimescaleDB│
└────────┘     └──────┘   └──────┘   └────────┘
```

### 11.2 API Contracts Between Modules

| From | To | Contract | Method |
|------|----|----------|--------|
| Rider Service | Policy Service | GET /api/policies/quote | HTTP |
| Policy Service | Risk Service | POST /api/risk/premium | HTTP |
| Claims Service | Fraud Service | calculate_spam_score() | Function |
| Claims Service | Payout Service | create_payout() | Function |
| Trigger Service | Claims Service | DisruptionEvent created | Event/Kafka |
| Admin Service | Claims Service | approve/reject claim | HTTP |

### 11.3 Shared Data Contracts

All modules share these common models:

```python
# shared/schemas.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class RiderBase(BaseModel):
    id: UUID
    phone: str
    name: str
    platform: str
    zone_id: UUID
    
class PolicyBase(BaseModel):
    id: UUID
    rider_id: UUID
    plan_tier: str
    week: str
    premium: int
    status: str
    
class DisruptionEventBase(BaseModel):
    id: UUID
    trigger_type: str
    zone_id: UUID
    slot_start: datetime
    severity: str
    
class ClaimBase(BaseModel):
    id: UUID
    rider_id: UUID
    policy_id: UUID
    type: str
    income_loss: int
    payout_amount: int
    status: str
```

---

## 12. Deployment Setup

### 12.1 Docker Services

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: timescale/timescale:latest-pg15
    environment:
      POSTGRES_USER: zylo
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: zylo
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U zylo"]
      interval: 10s
      timeout: 5s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OPENWEATHERMAP_API_KEY=${OPENWEATHERMAP_API_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  ml_service:
    build: ./backend/ml
    ports:
      - "8001:8001"
    environment:
      - MODEL_PATH=/app/model_artifacts/risk_model.pkl
    volumes:
      - ./backend/ml:/app

  scheduler:
    build: ./backend
    command: python -m trigger_service.scheduler
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - postgres

volumes:
  postgres_data:
  redis_data:
```

### 12.2 Environment Variables

```bash
# .env.example

# Database
DATABASE_URL=postgresql://zylo:password@postgres:5432/zylo

# Redis
REDIS_URL=redis://:@redis:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# External APIs
OPENWEATHERMAP_API_KEY=your-api-key
GOOGLE_MAPS_API_KEY=your-api-key

# App Settings
DEBUG=true
LOG_LEVEL=INFO

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme
```

### 12.3 Quick Start (Local)

```bash
# Clone and start
git clone https://github.com/your-team/zylo.git
cd zylo

# Copy environment template
cp .env.example .env

# Start all services
docker-compose up -d

# Check health
curl http://localhost:8000/health

# Open API docs
# http://localhost:8000/docs
```

### 12.4 Production Deployment (AWS)

For production-grade deployment on AWS (EC2, RDS, ElastiCache, ALB, ASG, CI/CD), follow the step-by-step instructions in the:

👉 **[Incremental AWS Deployment Guide](AWS_DEPLOYMENT_GUIDE.md)**


---

## 13. Development Plan

### 13.1 Day-wise Plan (14 Days)

| Day | Developer 1 | Developer 2 | Developer 3 | Developer 4 | Developer 5 |
|-----|-------------|-------------|-------------|-------------|------------|
| **1** | Docker setup + DB schema | FastAPI skeleton | External API clients | PostgreSQL connection | Basic HTML UI |
| **2** | Rider model + CRUD | Zone baseline generation | Weather API polling | Platform simulator | Seed data script |
| **3** | OTP + Redis | Policy model | Traffic API mock | Seed data import | Zone risk data |
| **4** | JWT auth | Quote endpoint | Trigger scheduler | Claims model | Admin UI |
| **5** | Registration flow | Policy creation | Evaluate triggers | Income estim. | Claim review UI |
| **6** | Integration test | Policy renewal | Disruption events | Auto payouts | Bootstrap check |
| **7** | Manual claim API | Policy status | **INTEGRATION** | Payout processing | Geo-validation |
| **8** | Risk model train | Coverage tracking | 5 triggers work | Spam detection | Review queue |
| **9** | Premium calc | **INTEGRATION** | Community signal | Fraud check | Photo upload |
| **10** | Model tuning | Policy cancel | Trigger fix | Manual flow | Admin approve |
| **11** | Edge cases | End-to-end test | **INTEGRATION** | Edge cases | Demo prep |
| **12** | PWA registration | PWA policy | PWA triggers | PWA claims | PWA admin |
| **13** | **INTEGRATION** | PWA polish | PWA polish | Demo run | Demo run |
| **14** | Demo final | Demo final | Demo final | Demo final | Demo final |

### 13.2 Integration Checkpoints

| Day | Checkpoint | Validation |
|-----|------------|------------|
| **Day 3** | DB ready | All tables created, seed data inserted |
| **Day 5** | Auth works | Rider can register, login, get policy |
| **Day 7** | Triggers fire | Simulated disruption creates claim |
| **Day 9** | Auto payout | Zero-touch payout flow complete |
| **Day 11** | Full E2E | Registration → Policy → Trigger → Payout |
| **Day 13** | Demo ready | Working demo with all features |

---

## 14. Error Handling & Edge Cases

### 14.1 Error Responses

All API errors follow this format:

```json
{
  "error": {
    "code": "ERR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

### 14.2 Common Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| INVALID_OTP | 400 | OTP verification failed |
| OTP_EXPIRED | 400 | OTP expired (5 min TTL) |
| RIDER_NOT_FOUND | 404 | Rider ID not found |
| POLICY_NOT_FOUND | 404 | Policy not found |
| NO_ACTIVE_POLICY | 400 | No active policy for rider |
| DUPLICATE_CLAIM | 400 | Claim already exists for this disruption |
| COVERAGE_EXHAUSTED | 400 | Weekly coverage limit reached |
| MANUAL_CLAIM_LIMIT | 400 | 1 manual claim per policy week |
| INSUFFICIENT_TRUST | 403 | Trust score below threshold |

### 14.3 Edge Cases

| Scenario | Handling |
|----------|----------|
| Rider has no baseline history | Use zone median baseline |
| Network failure during claim | Save as pending, retry on reconnect |
| Multiple triggers same slot | Merge to single DisruptionEvent |
| Duplicate claim submission | Reject with error message |
| Photo upload fails | Return error, allow retry |
| External API timeout | Use cached data, log warning |
| Redis failure | Fall back to in-memory cache |
| Database connection lost | Retry with exponential backoff |

### 14.4 Logging

```python
# Standard log format
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger("zylo")

# Usage
logger.info(f"Rider {rider_id} registered successfully")
logger.warning(f"Weather API timeout, using cached data")
logger.error(f"Failed to create payout for claim {claim_id}")
```

---

## 15. Demo Strategy

### 15.1 Simulated Disruption Triggers

For demo purposes, inject disruptions programmatically:

```python
# Demo: Inject heavy rain trigger
POST /api/triggers/inject
{
  "trigger_type": "heavy_rain",
  "zone": "gachibowli",
  "rainfall_mm": 52,
  "duration_seconds": 1800
}
```

### 15.2 Demo Script

**Step 1: Registration (2 min)**
- Open PWA
- Enter phone: +919876543210
- OTP sent (use 123456)
- Verify OTP
- Enter name, platform (Zepto), zone (Koramangala)
- Complete registration → get JWT

**Step 2: Policy Management (1 min)**
- View risk profile
- Select Balanced plan
- Pay premium via UPI
- View active policy

**Step 3: Dynamic Premium (30 sec)**
- View premium breakdown
- See risk explanation

**Step 4: Auto Claim (30 sec)**
- Admin injects heavy rain in rider's zone
- Wait 5 minutes for trigger evaluation
- Check claims → auto claim created
- Check payouts → payout credited

**Step 5: Manual Claim (30 sec)**
- Disruption not detected by system
- Rider submits manual claim + photo
- Check claim status → approved

**Step 6: Admin Review (15 sec)**
- View manual claim queue
- Approve claim

### 15.3 Demo Data

Pre-seed 20 riders across 4 cities:
- Bengaluru: Koramangala, Indiranagar, Whitefield
- Hyderabad: Gachibowli, Jubilee Hills
- Mumbai: Andheri West, Borivali
- Delhi: Rajouri Garden, Dwarka

Each rider has:
- 4-week earnings baseline
- Active policy for current week
- Pre-loaded UPI ID

---

## Appendix: Quick Reference

### A. Key Endpoints Summary

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| /api/riders/send-otp | POST | No | Send OTP |
| /api/riders/verify-otp | POST | No | Verify OTP |
| /api/riders/register | POST | Temp | Create rider |
| /api/riders/me | GET | JWT | Get profile |
| /api/policies/quote | GET | JWT | Get quotes |
| /api/policies | POST | JWT | Create policy |
| /api/policies/active | GET | JWT | Get active policy |
| /api/risk/premium | POST | JWT | Calculate premium |
| /api/claims | GET | JWT | List claims |
| /api/claims/manual | POST | JWT | Submit manual |
| /api/admin/claims/manual | GET | Admin | Review queue |
| /api/admin/claims/{id}/approve | POST | Admin | Approve |
| /health | GET | No | Health check |

### B. Database Connection

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://zylo:password@localhost:5432/zylo"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### C. Redis Connection

```python
import redis

r = redis.Redis(host='localhost', port=6379, db=0)

# OTP storage
r.setex(f"otp:{phone}", 300, "123456")  # 5 min TTL
otp = r.get(f"otp:{phone}")
```

### D. JWT Token Generation

```python
from jose import jwt

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

---

**End of TRD**