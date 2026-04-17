# TASK-4: Claims Service + Payout Service + Fraud Detection

**Owner:** Developer 4  
**Module:** Claims Engine + Payout Processing + Basic Fraud  
**Priority:** P0 (No claims = no payouts = no product)

---

## 1. Ownership Summary

You own the **money flow**. When a disruption happens, you calculate how much the rider lost, verify it's legitimate, and send the payout. You handle both auto-claims (triggered by Dev 3's DisruptionEvents) and the processing pipeline for manual claims (submitted via Dev 5's form).

**You are responsible for:**
- Auto-claim creation from DisruptionEvents
- Income gap calculation (expected − actual = loss)
- Payout calculation: `min(income_loss, coverage_limit)`
- Basic fraud check (GPS + peer comparison)
- Payout record creation + mock UPI processing
- Claims listing for riders
- Coverage tracking (update `coverage_used` on Dev 2's policies)

---

## 2. Database Tables You Own

### `claims`
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
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);
```

### `payouts`
```sql
CREATE TABLE payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id),
    rider_id UUID NOT NULL REFERENCES riders(id),
    amount INTEGER NOT NULL,
    method VARCHAR(20) DEFAULT 'upi',
    upi_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    reference_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

---

## 3. API Endpoints You Build

### `GET /api/claims`
List rider's claims. **Headers:** `Authorization: Bearer {jwt_token}`
```json
{
  "claims": [
    { "claim_id": "clm_001", "type": "auto", "disruption_event_id": "de_001",
      "income_loss": 540, "payout_amount": 540, "status": "paid",
      "created_at": "2026-03-30T15:10:00Z" }
  ]
}
```

### `GET /api/claims/{claim_id}`
Full claim details with breakdown.
```json
{
  "claim_id": "clm_001", "rider_id": "rd_001", "type": "auto",
  "disruption_event_id": "de_001", "policy_id": "pol_001",
  "income_loss": 540, "expected_earnings": 720, "actual_earnings": 180,
  "payout_amount": 540, "fraud_score": 15, "status": "paid",
  "created_at": "2026-03-30T15:10:00Z", "paid_at": "2026-03-30T15:12:00Z"
}
```

### `GET /api/payouts`
List rider's payouts.
```json
{
  "payouts": [
    { "payout_id": "pout_001", "claim_id": "clm_001", "amount": 540,
      "method": "upi", "upi_id": "arjun@oksbi", "status": "completed",
      "created_at": "2026-03-30T15:12:00Z" }
  ]
}
```

---

## 4. Auto-Claims Pipeline

When Dev 3 creates a DisruptionEvent, you run this pipeline:

```
DisruptionEvent → Find insured riders in zone → Filter: online + in-zone
→ Calculate income gap per rider → Fraud check → Create claim → Create payout
```

### Income Gap Calculation
```python
def calculate_income_gap(rider_id, slot_time):
    baseline = get_baseline(rider_id, slot_time)      # From rider_zone_baselines
    actual = get_actual_earnings(rider_id, slot_time)  # From platform_snapshots
    return baseline - actual

# Example:
# Expected: 12 orders/hr × 4 hrs × ₹15 = ₹720
# Actual: 3 orders/hr × 4 hrs × ₹15 = ₹180
# Loss = ₹540
```

### Payout Calculation
```python
payout = min(income_loss, policy.coverage_limit - policy.coverage_used)
```

### Basic Fraud Check (Auto Claims)

| Check | Rule | Action |
|-------|------|--------|
| GPS Consistency | Rider GPS in zone at disruption time | Required |
| Peer Comparison | Rider drop vs peer average | Flag if >2x peers |
| Baseline Validity | >= 1 week baseline history | Use zone median if not |
| Duplicate Claim | Same disruption + same rider already paid | Reject |

---

## 5. Manual Claims Processing

Dev 5 submits manual claims via `POST /api/claims/manual`. You provide the **processing pipeline** they call:

```python
# Exported function for Dev 5 to call
async def process_manual_claim(claim_data: ManualClaimInput) -> ClaimResult:
    """
    1. Calculate income gap
    2. Run fraud score (imported from Dev 5's spam detection)
    3. If spam_score >= 70: auto-reject
    4. If spam_score < 70: status = 'under_review'
    5. Create claim record
    """
```

When Dev 5's admin approves a manual claim, you handle:
```python
async def approve_manual_claim(claim_id: UUID) -> PayoutResult:
    """Create payout record + process mock UPI"""
```

---

## 6. Mock UPI Payout

```python
async def process_upi_payout(rider_id, amount, upi_id):
    """Simulated instant UPI credit — always succeeds"""
    payout = Payout(
        claim_id=claim_id,
        rider_id=rider_id,
        amount=amount,
        method="upi",
        upi_id=upi_id,
        status="completed",
        reference_id=f"UPI-{uuid4().hex[:12].upper()}",
        completed_at=datetime.utcnow()
    )
    # Update policy coverage_used
    policy.coverage_used += amount
    return payout
```

---

## 7. Dependencies

| You Call | Owned By | What |
|----------|----------|------|
| `disruption_events` | Dev 3 | Trigger for auto-claims |
| `platform_snapshots` | Dev 3 | Actual rider earnings |
| `policies` table | Dev 2 | Coverage limit + used |
| `rider_zone_baselines` | Dev 1 | Expected earnings baseline |
| `riders` table | Dev 1 | Rider profile + UPI ID |
| Auth middleware | Dev 1 | `get_current_rider` |

### Others Depend on You

| Consumer | What They Need | Deadline |
|----------|---------------|----------|
| **Dev 5** (Admin) | `process_manual_claim()`, `approve_manual_claim()` | Day 7 |
| **Dev 2** (Policy) | Coverage used updates | Day 8 |

---

## 8. File Structure

```
backend/
├── claims_service/
│   ├── router.py       # /api/claims/*, /api/payouts/*
│   ├── service.py      # Auto-claim pipeline, income gap calc
│   ├── models.py       # claims, payouts ORM
│   ├── schemas.py
│   └── fraud.py        # Basic fraud rules (auto claims)
├── payout_service/
│   ├── service.py      # Mock UPI processing
│   └── schemas.py
```

---

## 9. Day-by-Day Plan

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | PostgreSQL connection, claims model | ORM models ready |
| 2 | Seed data script | Demo data imported |
| 3 | Claims CRUD endpoints | List/get claims work |
| 4 | Income estimation logic | Gap calculation correct |
| 5 | Auto-claim creation pipeline | Pipeline processes events |
| 6 | Payout processing (mock UPI) | Payouts created |
| 7 | **INTEGRATION** with Dev 3 (trigger → claim → payout) | E2E auto works |
| 8 | Basic fraud check (GPS + peer) | Fraud scores calculated |
| 9 | Manual claim processing function (for Dev 5) | Function exported |
| 10 | Coverage tracking, edge cases | Limits enforced |
| 11 | Full E2E test | All flows pass |
| 12-14 | PWA claims UI, polish, demo | Demo-ready |

---

## 10. Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `DUPLICATE_CLAIM` | 400 | Already claimed for this disruption |
| `COVERAGE_EXHAUSTED` | 400 | Weekly limit reached |
| `NO_ACTIVE_POLICY` | 400 | No policy for this rider |
| `CLAIM_NOT_FOUND` | 404 | Claim ID not found |
| `PAYOUT_FAILED` | 500 | UPI processing failed |

---

## 11. Acceptance Criteria

- [x] Auto-claim created from DisruptionEvent with correct income gap
- [x] Payout = `min(income_loss, coverage_remaining)`
- [x] Fraud check runs on all auto-claims
- [x] Duplicate claims rejected
- [x] Coverage used tracked on policy
- [x] Manual claim processing function works for Dev 5
- [x] Mock UPI payout always succeeds with reference ID
- [x] Claims list shows all rider claims with status
- [x] Payout list shows all rider payouts

## 12. User Stories: US-12, US-13, US-14

## 13. Demo: [1:15–1:30] — Auto-payout credited → notification → breakdown shown
