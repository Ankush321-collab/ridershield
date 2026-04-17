#!/usr/bin/env python3
"""
GuideWire Full-Stack Smoke Test
Tests complete end-to-end workflows across backend, admin, and rider dashboards
"""

import httpx
import json
import uuid
import time
from datetime import datetime, timedelta

import os
BASE_URL = os.getenv("API_BASE_URL", "http://18.60.19.96:8000")
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# Track test metrics
metrics = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "errors": []
}

def log_test(name, status, details=""):
    """Log test result"""
    metrics["total"] += 1
    if status:
        metrics["passed"] += 1
        print(f"  [PASS] {name}")
    else:
        metrics["failed"] += 1
        print(f"  [FAIL] {name}")
        metrics["errors"].append(f"{name}: {details}")
    if details and status:
        print(f"    {details}")

def section(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}")

# ─────────────────────────────────────────────────────────────────
# PHASE 1: ADMIN SETUP & VALIDATION
# ─────────────────────────────────────────────────────────────────

section("PHASE 1: ADMIN SETUP & VALIDATION")

print("\n[1.1] Admin Authentication")
admin_token = None
try:
    r = httpx.post(f"{BASE_URL}/api/admin/login",
                   json={"username": ADMIN_USER, "password": ADMIN_PASS})
    if r.status_code == 200:
        admin_token = r.json()["access_token"]
        log_test("Admin login", True, f"Token: {admin_token[:30]}...")
    else:
        log_test("Admin login", False, f"Status: {r.status_code}")
except Exception as e:
    log_test("Admin login", False, str(e))

print("\n[1.2] Zone Verification")
zones = []
try:
    r = httpx.get(f"{BASE_URL}/api/riders/zones")
    if r.status_code == 200:
        zones = r.json().get("zones", [])
        log_test("Fetch zones", True, f"Count: {len(zones)} zones")
    else:
        log_test("Fetch zones", False, f"Status: {r.status_code}")
except Exception as e:
    log_test("Fetch zones", False, str(e))

print("\n[1.3] Trigger Status Baseline")
try:
    r = httpx.get(f"{BASE_URL}/api/triggers/status")
    if r.status_code == 200:
        data = r.json()
        active = len(data.get("active_triggers", []))
        log_test("Get trigger status", True, f"Active: {active} triggers")
        baseline_triggers = active
    else:
        log_test("Get trigger status", False, f"Status: {r.status_code}")
        baseline_triggers = 0
except Exception as e:
    log_test("Get trigger status", False, str(e))
    baseline_triggers = 0

# ─────────────────────────────────────────────────────────────────
# PHASE 2: COMPLETE RIDER JOURNEY (Auth → Policy → Claim → Payout)
# ─────────────────────────────────────────────────────────────────

section("PHASE 2: COMPLETE RIDER JOURNEY")

rider_id = None
jwt_token = None
policy_id = None
claim_id = None

print("\n[2.1] Rider Registration & Auth")
phone = f"+9199{str(uuid.uuid4().int)[:8]}"
print(f"  Using phone: {phone}")

try:
    # Send OTP
    r = httpx.post(f"{BASE_URL}/api/riders/send-otp",
                   json={"phone": phone})
    log_test("Send OTP", r.status_code == 200)

    # Verify OTP
    r = httpx.post(f"{BASE_URL}/api/riders/verify-otp",
                   json={"phone": phone, "otp": "123456"})
    if r.status_code == 200:
        temp_token = r.json()["temp_token"]
        log_test("Verify OTP", True, f"Temp token received")

        # Register rider
        zone_id = zones[0]["id"] if zones else str(uuid.uuid4())
        rider_data = {
            "name": f"Smoke Test Rider {uuid.uuid4().hex[:8]}",
            "platform": "zepto",
            "city": "bengaluru",
            "zone_id": zone_id,
            "slots": ["18:00-21:00", "21:00-23:00"],
            "upi_id": f"smoketest{uuid.uuid4().hex[:6]}@okaxis",
        }

        r = httpx.post(
            f"{BASE_URL}/api/riders/register",
            json=rider_data,
            headers={"Authorization": f"Bearer {temp_token}"},
        )
        if r.status_code == 201:
            rider_id = r.json()["rider_id"]
            jwt_token = r.json()["jwt_token"]
            log_test("Register rider", True, f"ID: {rider_id[:20]}...")
        else:
            log_test("Register rider", False, f"Status: {r.status_code}, {r.text[:100]}")
    else:
        log_test("Verify OTP", False, f"Status: {r.status_code}")
except Exception as e:
    log_test("Auth flow", False, str(e))

print("\n[2.2] Rider Profile & Risk Assessment")
if jwt_token:
    try:
        # Get profile
        r = httpx.get(f"{BASE_URL}/api/riders/me",
                     headers={"Authorization": f"Bearer {jwt_token}"})
        if r.status_code == 200:
            profile = r.json()
            log_test("Get rider profile", True, f"Name: {profile.get('name')}")
        else:
            log_test("Get rider profile", False, f"Status: {r.status_code}")

        # Get risk profile
        r = httpx.get(f"{BASE_URL}/api/riders/me/risk-profile",
                     headers={"Authorization": f"Bearer {jwt_token}"})
        if r.status_code == 200:
            risk = r.json()
            log_test("Get risk profile", True, f"Score: {risk.get('risk_score')}")
        else:
            log_test("Get risk profile", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Profile fetch", False, str(e))

print("\n[2.3] Onboarding & Premium Quote")
if jwt_token:
    try:
        r = httpx.post(
            f"{BASE_URL}/api/riders/onboard",
            json={"plan_tier": "balanced", "typical_slots": ["18:00-21:00", "21:00-23:00"]},
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        if r.status_code == 200:
            quote = r.json()
            log_test("Get premium quote", True, f"Tiers: {len(quote.get('tiers', []))} available")
        else:
            log_test("Get premium quote", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Onboarding", False, str(e))

print("\n[2.4] Policy Purchase")
if jwt_token and zones:
    try:
        policy_data = {
            "tier": "balanced",
            "zone_id": zones[0]["id"],
            "custom_slots": ["18:00-21:00"],
            "premium_override": None
        }
        r = httpx.post(
            f"{BASE_URL}/api/policies",
            json=policy_data,
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        if r.status_code == 201:
            policy_id = r.json()["policy_id"]
            log_test("Create policy (POST)", True, f"ID: {policy_id[:20]}...")
        else:
            log_test("Create policy (POST)", False, f"Status: {r.status_code}, {r.text[:150]}")
    except Exception as e:
        log_test("Policy purchase", False, str(e))

print("\n[2.5] Verify Active Policy")
if jwt_token:
    try:
        r = httpx.get(f"{BASE_URL}/api/policies/active",
                     headers={"Authorization": f"Bearer {jwt_token}"})
        if r.status_code == 200:
            active_policy = r.json()
            coverage = active_policy.get("coverage_amount")
            log_test("Get active policy", True, f"Coverage: {coverage}")
        else:
            log_test("Get active policy", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Get active policy", False, str(e))

# ─────────────────────────────────────────────────────────────────
# PHASE 3: TRIGGER EVENT & AUTO CLAIM GENERATION
# ─────────────────────────────────────────────────────────────────

section("PHASE 3: TRIGGER EVENT & AUTO CLAIM GENERATION")

print("\n[3.1] Inject Disruption Event")
if admin_token and zones:
    try:
        zone_name = zones[0]["name"]
        event_data = {
            "trigger_type": "heavy_rain",
            "zone": zone_name,
            "duration_seconds": 1800,
            "rainfall_mm": 55.0
        }
        r = httpx.post(
            f"{BASE_URL}/api/triggers/inject",
            json=event_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        if r.status_code in [200, 201]:
            event_id = r.json()["event_id"]
            log_test("Inject disruption event", True, f"ID: {event_id[:20]}...")
        else:
            log_test("Inject disruption event", False, f"Status: {r.status_code}, Body: {r.text[:100]}")
    except Exception as e:
        log_test("Inject event", False, str(e))

print("\n[3.2] Wait for Auto Claim Generation")
time.sleep(3)  # Wait for trigger evaluation
try:
    r = httpx.get(f"{BASE_URL}/api/claims",
                 headers={"Authorization": f"Bearer {jwt_token}"})
    if r.status_code == 200:
        claims = r.json().get("data", [])
        log_test("Fetch claims", True, f"Count: {len(claims)} claims")
        if claims:
            claim_id = claims[0]["id"]
except Exception as e:
    log_test("Fetch claims", False, str(e))

print("\n[3.3] Verify Claim Details")
if jwt_token and claim_id:
    try:
        r = httpx.get(f"{BASE_URL}/api/claims/{claim_id}",
                     headers={"Authorization": f"Bearer {jwt_token}"})
        if r.status_code == 200:
            claim = r.json()
            status = claim.get("status")
            payout = claim.get("payout_amount")
            log_test("Get claim details", True, f"Status: {status}, Payout: {payout}")
        else:
            log_test("Get claim details", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Get claim", False, str(e))

# ─────────────────────────────────────────────────────────────────
# PHASE 4: MANUAL CLAIM SUBMISSION
# ─────────────────────────────────────────────────────────────────

section("PHASE 4: MANUAL CLAIM SUBMISSION")

manual_claim_id = None
if jwt_token:
    try:
        print("\n[4.1] Submit Manual Claim")
        # Create a temporary test image file
        import io
        test_image = io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDAT\x08\x99c\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')

        form_data = {
            "disruption_type": "heavy_rain",
            "description": "Heavy rain during delivery shift, multiple orders affected",
            "incident_time": (datetime.utcnow() - timedelta(minutes=30)).isoformat() + "Z",
            "latitude": 12.9716 + (uuid.uuid4().int % 100 / 10000),
            "longitude": 77.5946 + (uuid.uuid4().int % 100 / 10000),
        }

        files = {
            "photo": ("test_claim.png", test_image, "image/png")
        }

        r = httpx.post(
            f"{BASE_URL}/api/claims/manual",
            data=form_data,
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        if r.status_code == 201:
            payload = r.json()
            manual_claim_id = payload.get("manual_claim_id") or payload.get("id")
            spam_score = payload.get("spam_score", 0)
            log_test("Submit manual claim", True, f"ID: {manual_claim_id[:20]}..., Spam: {spam_score}")
        else:
            log_test("Submit manual claim", False, f"Status: {r.status_code}, {r.text[:100]}")
    except Exception as e:
        log_test("Manual claim submission", False, str(e))

print("\n[4.2] Verify Manual Claim in Admin History")
if admin_token:
    try:
        r = httpx.get(f"{BASE_URL}/api/admin/claims/manual?status=all",
                     headers={"Authorization": f"Bearer {admin_token}"})
        if r.status_code == 200:
            manual_claims = r.json().get("claims", [])
            log_test("Admin: List manual claims", True, f"Count: {len(manual_claims)} total")
        else:
            log_test("Admin: List manual claims", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Admin: Fetch manual claims", False, str(e))

# ─────────────────────────────────────────────────────────────────
# PHASE 5: ADMIN CLAIMS REVIEW WORKFLOW
# ─────────────────────────────────────────────────────────────────

section("PHASE 5: ADMIN CLAIMS REVIEW WORKFLOW")

print("\n[5.1] Admin: Fetch Auto Claims for Review")
if admin_token:
    try:
        r = httpx.get(f"{BASE_URL}/api/admin/claims/auto",
                     headers={"Authorization": f"Bearer {admin_token}"})
        if r.status_code == 200:
            auto_claims = r.json().get("data", [])
            log_test("Admin: List auto claims", True, f"Count: {len(auto_claims)} total")
        else:
            log_test("Admin: List auto claims", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Admin: Fetch auto claims", False, str(e))

print("\n[5.2] Admin: Override Manual Claim")
if admin_token and manual_claim_id:
    try:
        r = httpx.post(
            f"{BASE_URL}/api/admin/claims/{manual_claim_id}/approve",
            json={"reviewer_notes": "Smoke test approval - weather verification passed"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        if r.status_code == 200:
            approved = r.json()
            status = approved.get("status")
            log_test("Admin: Approve claim", True, f"Override status: {status}")
        else:
            log_test("Admin: Approve claim", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Admin: Approve claim", False, str(e))

print("\n[5.3] Admin: Rejection Flow (Alternative)")
print("  (Skipped - claim already approved above)")

# ─────────────────────────────────────────────────────────────────
# PHASE 6: PAYOUT VERIFICATION & COVERAGE ACCOUNTING
# ─────────────────────────────────────────────────────────────────

section("PHASE 6: PAYOUT VERIFICATION & COVERAGE ACCOUNTING")

print("\n[6.1] Fetch Payouts")
if jwt_token:
    try:
        r = httpx.get(f"{BASE_URL}/api/payouts",
                     headers={"Authorization": f"Bearer {jwt_token}"})
        if r.status_code == 200:
            payouts = r.json().get("data", [])
            total = sum([p.get("amount", 0) for p in payouts])
            log_test("Fetch payouts", True, f"Count: {len(payouts)}, Total: {total}")
        else:
            log_test("Fetch payouts", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Fetch payouts", False, str(e))

print("\n[6.2] Verify Payout Status")
if jwt_token:
    try:
        r = httpx.get(f"{BASE_URL}/api/payouts",
                     headers={"Authorization": f"Bearer {jwt_token}"})
        if r.status_code == 200:
            payouts = r.json().get("data", [])
            statuses = set([p.get("status") for p in payouts])
            log_test("Payout statuses", True, f"Types: {statuses}")
        else:
            log_test("Payout statuses", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Payout statuses", False, str(e))

print("\n[6.3] Coverage Accounting Check")
if jwt_token:
    try:
        r = httpx.get(f"{BASE_URL}/api/policies/active",
                     headers={"Authorization": f"Bearer {jwt_token}"})
        if r.status_code == 200:
            policy = r.json()
            original = policy.get("coverage_amount", 0)
            remaining = policy.get("remaining_coverage", original)
            log_test("Coverage amount", True, f"Original: {original}, Remaining: {remaining}")
        else:
            log_test("Coverage amount", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Coverage accounting", False, str(e))

# ─────────────────────────────────────────────────────────────────
# PHASE 7: POLICY MANAGEMENT & RENEWAL
# ─────────────────────────────────────────────────────────────────

section("PHASE 7: POLICY MANAGEMENT & RENEWAL")

print("\n[7.1] Check Current Policy Status")
if jwt_token:
    try:
        r = httpx.get(f"{BASE_URL}/api/policies/active",
                     headers={"Authorization": f"Bearer {jwt_token}"})
        if r.status_code == 200:
            policy = r.json()
            tier = policy.get("tier")
            status = policy.get("status")
            log_test("Policy status", True, f"Tier: {tier}, Status: {status}")
        else:
            log_test("Policy status", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Policy status", False, str(e))

print("\n[7.2] Test Policy Renewal (Advanced)")
if jwt_token and policy_id:
    try:
        r = httpx.put(
            f"{BASE_URL}/api/policies/{policy_id}/renew",
            json={"new_tier": "balanced"},
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        if r.status_code == 200:
            renewed = r.json()
            log_test("Renew policy", True, f"New tier: {renewed.get('tier')}")
        else:
            log_test("Renew policy", False, f"Status: {r.status_code}")
    except Exception as e:
        log_test("Renew policy", False, str(e))
else:
    print("  [SKIP] Policy renewal - no policy_id available")

# ─────────────────────────────────────────────────────────────────
# PHASE 8: FINAL VALIDATION & REPORTING
# ─────────────────────────────────────────────────────────────────

section("PHASE 8: FINAL VALIDATION & REPORTING")

print("\n[8.1] Health Check")
try:
    r = httpx.get(f"{BASE_URL}/health")
    if r.status_code == 200:
        health = r.json()
        postgres = health.get("postgres")
        redis = health.get("redis")
        log_test("System health", postgres == "connected" and redis == "connected",
                f"PostgreSQL: {postgres}, Redis: {redis}")
    else:
        log_test("System health", False, f"Status: {r.status_code}")
except Exception as e:
    log_test("System health", False, str(e))

print("\n[8.2] Trigger Evaluation Count")
try:
    r = httpx.get(f"{BASE_URL}/api/triggers/status")
    if r.status_code == 200:
        data = r.json()
        active = len(data.get("active_triggers", []))
        log_test("Active triggers", True, f"Count: {active}")
    else:
        log_test("Active triggers", False, f"Status: {r.status_code}")
except Exception as e:
    log_test("Active triggers", False, str(e))

# ─────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────

section("SMOKE TEST SUMMARY")

pass_rate = (metrics["passed"] / metrics["total"] * 100) if metrics["total"] > 0 else 0

print(f"\nTotal Tests: {metrics['total']}")
print(f"Passed: {metrics['passed']}")
print(f"Failed: {metrics['failed']}")
print(f"Pass Rate: {pass_rate:.1f}%")

if metrics["failed"] > 0:
    print(f"\nFailed Tests:")
    for error in metrics["errors"]:
        print(f"  • {error}")

print("\n" + "="*70)
if pass_rate >= 95:
    print(" SMOKE TEST: PASSED [OK] - Ready for production")
elif pass_rate >= 80:
    print(" SMOKE TEST: PASSED (with warnings) - Minor issues found")
else:
    print(" SMOKE TEST: FAILED [CRITICAL] - Issues detected")
print("="*70 + "\n")

# Export metrics
with open("smoke_test_results.json", "w") as f:
    json.dump({
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total": metrics["total"],
            "passed": metrics["passed"],
            "failed": metrics["failed"],
            "pass_rate": pass_rate
        },
        "errors": metrics["errors"]
    }, f, indent=2)

print(f"Results saved to: smoke_test_results.json")

exit(0 if metrics["failed"] == 0 else 1)
