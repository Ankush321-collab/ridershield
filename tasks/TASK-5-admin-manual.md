# TASK-5: Admin Service + Manual Claims + Spam Detection

**Owner:** Developer 5  
**Module:** Admin Dashboard Backend + Manual Claim Submission + Geo-Validation + Spam Detection  
**Priority:** P1 (Manual fallback + admin review — completes the product story)

---

## 1. Ownership Summary

You own the **manual claim fallback** and **admin review pipeline**. When auto-triggers don't catch a disruption, riders submit manual claims through your endpoints. You validate them with geo-tagging, weather/traffic corroboration, and spam scoring. Admins then approve or reject from a review queue you provide.

**You are responsible for:**
- Manual claim submission endpoint (with photo upload)
- EXIF GPS extraction from uploaded photos
- Geo-validation (photo GPS vs rider telemetry)
- Weather + traffic corroboration checks
- Spam score calculation (0–100)
- Auto-reject if spam ≥ 70
- Admin endpoints: list queue, approve, reject
- Admin authentication (separate from rider auth)

---

## 2. Database Tables You Own

### `manual_claims`
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
    review_status VARCHAR(20) DEFAULT 'pending',
    reviewer_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP
);
```

---

## 3. API Endpoints You Build

### `POST /api/claims/manual`
Submit manual claim with geo-tagged photo.  
**Headers:** `Authorization: Bearer {jwt_token}`  
**Content-Type:** `multipart/form-data`

```
disruption_type: traffic
description: Road work causing gridlock
incident_time: 2026-03-30T19:30:00Z
photo: <file upload>
latitude: 12.9352
longitude: 77.6245
```

**Response (201):**
```json
{
  "claim_id": "mcl_001", "rider_id": "rd_001", "type": "manual",
  "disruption_type": "traffic", "status": "under_review", "spam_score": 25,
  "geo_validation": {
    "photo_gps": {"lat": 12.9352, "lon": 77.6245},
    "telemetry_gps": {"lat": 12.9355, "lon": 77.6248},
    "distance_m": 45, "valid": true
  },
  "corroboration": {
    "weather_match": true, "traffic_match": true, "known_disruption": false
  }
}
```

**Pipeline:**
1. Save photo to local FS / S3
2. Extract EXIF GPS + timestamp from photo
3. Compare photo GPS vs rider telemetry → `geo_valid` + `gps_distance_m`
4. Query Dev 3's `weather_data` for corroboration
5. Query Dev 3's traffic mock for corroboration
6. Calculate spam score
7. If `spam_score >= 70`: auto-reject
8. If `spam_score < 70`: call Dev 4's `process_manual_claim()` → status = `under_review`

### `GET /api/claims/manual/{claim_id}`
```json
{
  "claim_id": "mcl_001", "status": "approved", "payout_amount": 380,
  "reviewed_at": "2026-03-30T20:30:00Z",
  "reviewer_notes": "Geo-validation passed, traffic corroboration confirmed"
}
```

### `GET /api/admin/claims` (Admin)
List all auto claims. **Headers:** `Authorization: Bearer {admin_jwt_token}`
```json
{
  "claims": [
    { "claim_id": "clm_001", "rider_id": "rd_001", "type": "auto",
      "income_loss": 540, "payout_amount": 540, "fraud_score": 15, "status": "paid" }
  ]
}
```

### `GET /api/admin/claims/manual` (Admin)
List manual claims sorted by spam score. **Query:** `?sort=spam_score&order=asc`
```json
{
  "claims": [
    { "claim_id": "mcl_001", "rider_id": "rd_001", "disruption_type": "traffic",
      "spam_score": 25, "status": "under_review",
      "geo_validation": {"valid": true, "distance_m": 45},
      "corroboration": {"weather_match": true, "traffic_match": true} }
  ]
}
```

### `POST /api/admin/claims/{claim_id}/approve`
```json
{ "claim_id": "mcl_001", "status": "approved", "payout_amount": 380, "payout_id": "pout_001" }
```
Calls Dev 4's `approve_manual_claim()` → creates payout.

### `POST /api/admin/claims/{claim_id}/reject`
**Request:** `{ "reason": "Location mismatch: 2.3km from declared zone" }`
```json
{ "claim_id": "mcl_001", "status": "rejected", "reason": "..." }
```

---

## 4. Spam Score Calculation

```python
def calculate_spam_score(claim, weather_data, traffic_data):
    score = 0
    
    # Location mismatch (35% weight)
    if claim.gps_distance_m > 500:
        score += 35
    
    # Time anomaly (25% weight) — EXIF timestamp vs incident_time
    time_delta = abs((claim.photo_timestamp - claim.incident_time).total_seconds() / 60)
    if time_delta > 30:
        score += 25
    
    # Weather mismatch (20% weight)
    if claim.disruption_type == "weather":
        if weather_data.rainfall_mm < 7.6 and weather_data.wind_kmh < 40:
            score += 20
    
    # Traffic mismatch (20% weight)
    if claim.disruption_type == "traffic":
        if traffic_data.congestion_index < 70:
            score += 20
    
    return min(score, 100)
```

**Rule:** `spam_score >= 70` → auto-reject. `< 70` → queue for admin.

---

## 5. Geo-Validation

```python
from math import radians, sin, cos, sqrt, atan2

def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """Returns distance in meters between two GPS points"""
    R = 6371000  # Earth radius in meters
    # ... standard haversine formula
    return distance_m

# Flag if distance > 500m
geo_valid = (distance_m <= 500)
```

---

## 6. Dependencies

| You Call | Owned By | What |
|----------|----------|------|
| `weather_data` table | Dev 3 | Weather corroboration |
| Traffic mock data | Dev 3 | Traffic corroboration |
| `process_manual_claim()` | Dev 4 | Create claim record |
| `approve_manual_claim()` | Dev 4 | Trigger payout on approve |
| `policies` table | Dev 2 | Check active policy, rate limit |
| Auth middleware | Dev 1 | `get_current_rider`, `require_admin` |

### Others Depend on You
No other dev depends on you directly. You are the terminal node.

---

## 7. File Structure

```
backend/
├── admin_service/
│   ├── router.py       # /api/admin/* endpoints
│   ├── service.py      # Admin review logic
│   └── schemas.py
├── manual_claims/
│   ├── router.py       # /api/claims/manual
│   ├── service.py      # Submission pipeline
│   ├── models.py       # manual_claims ORM
│   ├── geo_validation.py   # Haversine + EXIF extraction
│   ├── spam_detection.py   # Spam score calculation
│   ├── schemas.py
│   └── photo_handler.py    # File upload + EXIF
```

---

## 8. Day-by-Day Plan

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Basic HTML admin UI skeleton | Admin page loads |
| 2 | Seed data script | Demo data imported |
| 3 | Zone risk data seeding | Risk data available |
| 4 | Admin UI layout, manual claim model | ORM ready |
| 5 | Manual claim submission endpoint | Photo upload works |
| 6 | EXIF extraction + geo-validation | GPS comparison works |
| 7 | Geo-validation + haversine distance | Distance calculated |
| 8 | Spam score calculation | Score computed correctly |
| 9 | Photo upload handling, corroboration queries | Full pipeline |
| 10 | Admin approve/reject endpoints | Admin actions work |
| 11 | Rate limiting (1 manual claim/week) | Limits enforced |
| 12-14 | PWA admin UI, polish, demo | Demo-ready |

---

## 9. Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `MANUAL_CLAIM_LIMIT` | 400 | 1 manual claim per policy week |
| `NO_ACTIVE_POLICY` | 400 | No active policy |
| `PHOTO_REQUIRED` | 400 | Photo not provided |
| `INVALID_DISRUPTION_TYPE` | 400 | Type not recognized |
| `CLAIM_ALREADY_REVIEWED` | 400 | Already approved/rejected |
| `ADMIN_UNAUTHORIZED` | 403 | Not an admin |

---

## 10. Acceptance Criteria

- [x] Manual claim submits with photo upload
- [x] EXIF GPS extracted from photo
- [x] Haversine distance calculated (>500m flagged)
- [x] Weather + traffic corroboration queried
- [x] Spam score calculated correctly
- [x] Auto-reject at spam ≥ 70
- [x] Admin queue sorted by spam score (ascending)
- [x] Admin approve triggers payout via Dev 4
- [x] Admin reject stores reason + notifies rider
- [x] Rate limit: 1 manual claim per policy week
- [x] Photo stored to local FS with path in DB

## 11. User Stories: US-13, US-14, US-15, US-16

## 12. Demo: [1:30–2:00] — Manual claim + photo → admin queue → approve → payout
