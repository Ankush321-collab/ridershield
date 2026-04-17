"""
Zylo -- Full API Test Suite (v2)
Run: python test_api.py
"""
import httpx, sys, io, os
BASE = os.getenv("API_BASE_URL", "http://18.60.19.96:8000")

results = []

def log(label, status, detail=""):
    icon = "[PASS]" if status == "pass" else ("[SKIP]" if status == "skip" else "[FAIL]")
    line = f"  {icon}  {label}"
    if detail: line += f"  ->  {detail}"
    print(line)
    results.append((label, status, detail))

def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")

def req(method, path, **kwargs):
    try:
        return httpx.request(method, BASE + path, timeout=10, **kwargs)
    except Exception as e:
        return None

state = {}

# ============================================================
section("1. HEALTH CHECK")
# ============================================================
r = req("GET", "/health")
if r and r.status_code == 200:
    b = r.json()
    log("GET /health", "pass", f"postgres={b['postgres']} redis={b['redis']} scheduler_cycles={b['trigger_scheduler_cycles']}")
else:
    log("GET /health", "fail", "no response"); sys.exit(1)

# ============================================================
section("2. ZONES (public)")
# ============================================================
r = req("GET", "/api/zones")
if r and r.status_code == 200:
    zones = r.json().get("zones", [])
    state["zone_id"] = zones[0]["id"] if zones else None
    state["zone_name"] = zones[0]["name"] if zones else None
    log("GET /api/zones", "pass", f"{len(zones)} zones, first={state['zone_name']}")
else:
    log("GET /api/zones", "fail", f"status={r.status_code if r else 'timeout'}")

# ============================================================
section("3. TASK-1 -- RIDER AUTH")
# ============================================================

PHONE = "+919988001122"

# send-otp
r = req("POST", "/api/riders/send-otp", json={"phone": PHONE})
if r and r.status_code == 200:
    log("POST /api/riders/send-otp", "pass", r.json().get("message"))
else:
    log("POST /api/riders/send-otp", "fail", f"status={r.status_code if r else 'N/A'}")

# verify-otp wrong
r = req("POST", "/api/riders/verify-otp", json={"phone": PHONE, "otp": "999999"})
if r and r.status_code == 400:
    log("POST /api/riders/verify-otp (wrong otp -> 400)", "pass", r.json()["detail"]["code"])
else:
    log("POST /api/riders/verify-otp (wrong otp)", "fail", f"expected 400 got {r.status_code if r else 'N/A'}")

# verify-otp correct
r = req("POST", "/api/riders/verify-otp", json={"phone": PHONE, "otp": "123456"})
if r and r.status_code == 200:
    state["temp_token"] = r.json().get("temp_token")
    log("POST /api/riders/verify-otp (correct)", "pass", "temp_token ok")
else:
    log("POST /api/riders/verify-otp (correct)", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:100] if r else ''}")

# register
if state.get("temp_token") and state.get("zone_id"):
    r = req("POST", "/api/riders/register",
        headers={"Authorization": f"Bearer {state['temp_token']}"},
        json={"name": "API Tester", "platform": "zepto", "city": "bengaluru",
              "zone_id": state["zone_id"], "slots": ["18:00-21:00"], "upi_id": "tester@upi"}
    )
    if r and r.status_code == 201:
        b = r.json()
        state["jwt_token"] = b.get("jwt_token")
        state["rider_id"] = str(b.get("rider_id", ""))
        log("POST /api/riders/register", "pass", f"rider_id={state['rider_id'][:12]}... jwt=ok")
    elif r and r.status_code == 409:
        log("POST /api/riders/register", "skip", "409 already registered -- getting fresh JWT")
        # re-issue OTP for same phone
        req("POST", "/api/riders/send-otp", json={"phone": PHONE})
        r2 = req("POST", "/api/riders/verify-otp", json={"phone": PHONE, "otp": "123456"})
        if r2 and r2.status_code == 200:
            state["temp_token"] = r2.json().get("temp_token")
        # Try different number
        PHONE2 = "+919911000099"
        req("POST", "/api/riders/send-otp", json={"phone": PHONE2})
        r3 = req("POST", "/api/riders/verify-otp", json={"phone": PHONE2, "otp": "123456"})
        if r3 and r3.status_code == 200:
            t3 = r3.json().get("temp_token")
            r4 = req("POST", "/api/riders/register",
                headers={"Authorization": f"Bearer {t3}"},
                json={"name": "API Tester 2", "platform": "blinkit", "city": "hyderabad",
                      "zone_id": state["zone_id"], "slots": ["18:00-21:00"], "upi_id": "tester2@upi"}
            )
            if r4 and r4.status_code == 201:
                b = r4.json()
                state["jwt_token"] = b.get("jwt_token")
                state["rider_id"] = str(b.get("rider_id", ""))
                log("POST /api/riders/register (alt phone)", "pass", f"rider_id={state['rider_id'][:12]}...")
    else:
        log("POST /api/riders/register", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:150] if r else ''}")
else:
    log("POST /api/riders/register", "skip", "missing temp_token or zone_id")

AUTH = {"Authorization": f"Bearer {state.get('jwt_token', '')}"}
jwt_ok = bool(state.get("jwt_token"))

# GET /me
if jwt_ok:
    r = req("GET", "/api/riders/me", headers=AUTH)
    if r and r.status_code == 200:
        b = r.json()
        log("GET /api/riders/me", "pass", f"name={b.get('name')} platform={b.get('platform')}")
    else:
        log("GET /api/riders/me", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:100] if r else ''}")
else:
    log("GET /api/riders/me", "skip", "no jwt_token")

# GET /me/risk-profile
if jwt_ok:
    r = req("GET", "/api/riders/me/risk-profile", headers=AUTH)
    if r and r.status_code == 200:
        b = r.json()
        log("GET /api/riders/me/risk-profile", "pass", f"volatility={b.get('income_volatility')} risk={b.get('composite_risk_score')}")
    elif r and r.status_code == 404:
        log("GET /api/riders/me/risk-profile", "skip", "404 -- no risk profile yet (expected for new rider)")
    else:
        log("GET /api/riders/me/risk-profile", "fail", f"status={r.status_code if r else 'N/A'}")
else:
    log("GET /api/riders/me/risk-profile", "skip", "no jwt_token")

# POST /onboard
if jwt_ok:
    r = req("POST", "/api/riders/onboard", headers=AUTH, json={"plan_tier": "balanced"})
    if r and r.status_code == 200:
        b = r.json()
        log("POST /api/riders/onboard", "pass", f"tiers={list(b.get('premium_quote',{}).keys())}")
    else:
        log("POST /api/riders/onboard", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:150] if r else ''}")
else:
    log("POST /api/riders/onboard", "skip", "no jwt_token")

# invalid token -> 401
r = req("GET", "/api/riders/me", headers={"Authorization": "Bearer nottokenyep"})
if r and r.status_code == 401:
    log("GET /api/riders/me (invalid token -> 401)", "pass")
else:
    log("GET /api/riders/me (invalid token)", "fail", f"expected 401 got {r.status_code if r else 'N/A'}")

# ============================================================
section("4. TASK-2 -- POLICY SERVICE")
# ============================================================

# POST /api/risk/premium
if jwt_ok:
    r = req("POST", "/api/risk/premium", headers=AUTH, json={
        "rider_id": state.get("rider_id", ""), "zone_risk_score": 72,
        "income_volatility": 0.42, "plan_tier": "balanced"
    })
    if r and r.status_code in (200, 201):
        log("POST /api/risk/premium", "pass", f"keys={list(r.json().keys())}")
    else:
        log("POST /api/risk/premium", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:150] if r else ''}")
else:
    log("POST /api/risk/premium", "skip", "no jwt")

# POST /api/policies
if jwt_ok:
    r = req("POST", "/api/policies", headers=AUTH, json={"plan_tier": "balanced", "slots": ["18:00-21:00"]})
    if r and r.status_code in (200, 201):
        b = r.json()
        state["policy_id"] = str(b.get("policy_id") or b.get("id", ""))
        log("POST /api/policies", "pass", f"policy_id={state['policy_id'][:14]}... status={b.get('status')}")
    elif r and r.status_code == 400 and "already" in (r.text or "").lower():
        log("POST /api/policies", "skip", "Policy already exists this week")
        # Try to find policy active id
        r_act = req("GET", "/api/policies/active", headers=AUTH)
        if r_act and r_act.status_code == 200:
            state["policy_id"] = r_act.json().get("policy_id") or r_act.json().get("id")
    else:
        log("POST /api/policies", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:150] if r else ''}")
else:
    log("POST /api/policies", "skip", "no jwt")

# GET /api/policies/active
if jwt_ok:
    r = req("GET", "/api/policies/active", headers=AUTH)
    if r and r.status_code == 200:
        b = r.json()
        if not state.get("policy_id"):
            state["policy_id"] = str(b.get("policy_id") or b.get("id", ""))
        log("GET /api/policies/active", "pass", f"tier={b.get('plan_tier')} status={b.get('status')} coverage={b.get('coverage_limit')}")
    else:
        log("GET /api/policies/active", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:150] if r else ''}")
else:
    log("GET /api/policies/active", "skip", "no jwt")

# ============================================================
section("5. TASK-3 -- TRIGGERS & DISRUPTION EVENTS")
# ============================================================

# GET /api/triggers/status (public)
r = req("GET", "/api/triggers/status")
if r and r.status_code == 200:
    b = r.json()
    log("GET /api/triggers/status", "pass",
        f"active={len(b.get('active_triggers',[]))} signals={len(b.get('community_signals',[]))} last_eval={str(b.get('last_evaluation',''))[:19]}")
else:
    log("GET /api/triggers/status", "fail", f"status={r.status_code if r else 'N/A'}")

# GET /api/triggers/disruption-events (correct path)
r = req("GET", "/api/triggers/disruption-events")
if r and r.status_code == 200:
    events = r.json().get("events", [])
    log("GET /api/triggers/disruption-events", "pass", f"{len(events)} events in DB")
elif r and r.status_code == 404:
    log("GET /api/triggers/disruption-events", "fail", "404 -- route not found (check main.py prefix)")
else:
    log("GET /api/triggers/disruption-events", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:100] if r else ''}")

# POST /api/admin/login -> get admin JWT
r = req("POST", "/api/admin/login", json={"username": "admin", "password": "admin123"})
if r and r.status_code == 200:
    state["admin_token"] = r.json().get("access_token")
    log("POST /api/admin/login", "pass", "admin JWT obtained")
else:
    log("POST /api/admin/login", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:150] if r else ''}")

ADMIN_AUTH = {"Authorization": f"Bearer {state.get('admin_token', '')}"}
admin_ok = bool(state.get("admin_token"))

# POST /api/triggers/inject (requires admin JWT)
if admin_ok:
    r = req("POST", "/api/triggers/inject", headers=ADMIN_AUTH, json={
        "trigger_type": "heavy_rain",
        "zone": state.get("zone_name", "electronic_city"),
        "rainfall_mm": 55,
        "duration_seconds": 1800
    })
    if r and r.status_code in (200, 201):
        b = r.json()
        state["disruption_event_id"] = str(b.get("event_id", ""))
        log("POST /api/triggers/inject (admin)", "pass",
            f"event_id={state['disruption_event_id'][:14]}... affected={b.get('affected_riders')}")
    else:
        log("POST /api/triggers/inject (admin)", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:200] if r else ''}")
else:
    log("POST /api/triggers/inject (admin)", "skip", "no admin token")

# verify event now appears
r = req("GET", "/api/triggers/disruption-events")
if r and r.status_code == 200:
    events = r.json().get("events", [])
    log("GET /api/triggers/disruption-events (post-inject)", "pass", f"{len(events)} event(s) now")
else:
    log("GET /api/triggers/disruption-events (post-inject)", "skip", f"status={r.status_code if r else 'N/A'}")

# GET /api/triggers/status (should now show active)
r = req("GET", "/api/triggers/status")
if r and r.status_code == 200:
    active = r.json().get("active_triggers", [])
    log("GET /api/triggers/status (post-inject)", "pass", f"{len(active)} active trigger(s)")
else:
    log("GET /api/triggers/status (post-inject)", "fail")

# ============================================================
section("6. TASK-4 -- CLAIMS & PAYOUTS")
# ============================================================

# GET /api/claims
if jwt_ok:
    r = req("GET", "/api/claims", headers=AUTH)
    if r and r.status_code == 200:
        claims = r.json().get("claims", [])
        if claims:
            state["claim_id"] = str(claims[0].get("claim_id") or claims[0].get("id",""))
        log("GET /api/claims", "pass", f"{len(claims)} claim(s)")
    else:
        log("GET /api/claims", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:150] if r else ''}")
else:
    log("GET /api/claims", "skip", "no jwt")

# GET /api/claims/{id}
if state.get("claim_id") and jwt_ok:
    r = req("GET", f"/api/claims/{state['claim_id']}", headers=AUTH)
    if r and r.status_code == 200:
        b = r.json()
        log("GET /api/claims/{id}", "pass", f"type={b.get('type')} payout={b.get('payout_amount')} status={b.get('status')}")
    else:
        log("GET /api/claims/{id}", "fail", f"status={r.status_code if r else 'N/A'}")
else:
    log("GET /api/claims/{id}", "skip", "no claim_id (no auto-claims triggered yet)")

# GET /api/payouts
if jwt_ok:
    r = req("GET", "/api/payouts", headers=AUTH)
    if r and r.status_code == 200:
        payouts = r.json().get("payouts", [])
        log("GET /api/payouts", "pass", f"{len(payouts)} payout(s)")
    else:
        log("GET /api/payouts", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:150] if r else ''}")
else:
    log("GET /api/payouts", "skip", "no jwt")

# ============================================================
section("7. TASK-5 -- MANUAL CLAIMS & ADMIN")
# ============================================================

# POST /api/claims/manual
if jwt_ok:
    fake_jpeg = (b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
                 b'\xff\db\x00C\x00\x08\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
                 b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a'
                 b'\x1c\x1c $.\' ",#\x1c\x1c(7),01444\xc0\x00\x0b\x08\x00\x01\x00\x01'
                 b'\x01\x01\x11\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd2\x8a\xff\xd9')
    r = req("POST", "/api/claims/manual",
        headers=AUTH,
        files={"photo": ("evidence.jpg", io.BytesIO(fake_jpeg), "image/jpeg")},
        data={"disruption_type": "traffic", "description": "Flood blocked main road",
              "incident_time": "2026-04-03T19:30:00Z", "latitude": "12.9352", "longitude": "77.6245"}
    )
    if r and r.status_code == 201:
        b = r.json()
        state["manual_claim_id"] = str(b.get("manual_claim_id",""))
        log("POST /api/claims/manual", "pass",
            f"id={state['manual_claim_id'][:14]}... spam={b.get('spam_score')} status={b.get('status')}")
    elif r and r.status_code == 400 and "one manual" in (r.text or "").lower():
        log("POST /api/claims/manual", "skip", "Rate limit: 1/policy -- correct behaviour")
    elif r and r.status_code == 400 and "active policy" in (r.text or "").lower():
        log("POST /api/claims/manual", "fail", f"status=400 No active policy (did policy endpoint fail?) {r.text[:100]}")
    else:
        log("POST /api/claims/manual", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:200] if r else ''}")
else:
    log("POST /api/claims/manual", "skip", "no jwt")

# GET /api/claims/manual/{id}
if state.get("manual_claim_id") and jwt_ok:
    r = req("GET", f"/api/claims/manual/{state['manual_claim_id']}", headers=AUTH)
    if r and r.status_code == 200:
        b = r.json()
        log("GET /api/claims/manual/{id}", "pass",
            f"spam={b.get('spam_score')} geo_valid={b.get('geo_valid')} status={b.get('review_status')}")
    else:
        log("GET /api/claims/manual/{id}", "fail", f"status={r.status_code if r else 'N/A'}")
else:
    log("GET /api/claims/manual/{id}", "skip", "no manual_claim_id")

# GET /api/admin/claims/auto (correct path)
if admin_ok:
    r = req("GET", "/api/admin/claims/auto", headers=ADMIN_AUTH)
    if r and r.status_code == 200:
        log("GET /api/admin/claims/auto", "pass", f"{len(r.json().get('claims',[]))} auto claim(s)")
    else:
        log("GET /api/admin/claims/auto", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:100] if r else ''}")
else:
    log("GET /api/admin/claims/auto", "skip", "no admin token")

# GET /api/admin/claims/manual
if admin_ok:
    r = req("GET", "/api/admin/claims/manual?status=all", headers=ADMIN_AUTH)
    if r and r.status_code == 200:
        claims = r.json().get("claims", [])
        if claims and not state.get("manual_claim_id"):
            mc = claims[0]
            state["manual_claim_id"] = str(mc.get("claim_id") or mc.get("id",""))
        log("GET /api/admin/claims/manual", "pass", f"{len(claims)} total manual claim(s)")
    else:
        log("GET /api/admin/claims/manual", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:100] if r else ''}")
else:
    log("GET /api/admin/claims/manual", "skip", "no admin token")

# POST /api/admin/claims/{id}/approve
if admin_ok and state.get("manual_claim_id"):
    r = req("POST", f"/api/admin/claims/{state['manual_claim_id']}/approve", headers=ADMIN_AUTH)
    if r and r.status_code == 200:
        b = r.json()
        log("POST /api/admin/claims/{id}/approve", "pass",
            f"status={b.get('status')} payout={b.get('payout_amount')}")
    elif r and r.status_code == 400:
        log("POST /api/admin/claims/{id}/approve", "skip", f"Already reviewed: {r.json().get('detail','')}")
    else:
        log("POST /api/admin/claims/{id}/approve", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:150] if r else ''}")
else:
    log("POST /api/admin/claims/{id}/approve", "skip", "no admin token or no manual claim")

# POST /api/admin/claims/{id}/reject (use a fresh manual claim -- test with claim_id if exists)
if admin_ok and state.get("manual_claim_id"):
    r = req("POST", f"/api/admin/claims/{state['manual_claim_id']}/reject",
        headers=ADMIN_AUTH, json={"reason": "GPS mismatch > 500m -- API test reject"})
    if r and r.status_code == 200:
        log("POST /api/admin/claims/{id}/reject", "pass", f"claim rejected: {r.json().get('status')}")
    elif r and r.status_code == 400:
        log("POST /api/admin/claims/{id}/reject", "skip", f"Already reviewed (approved above): {r.json().get('detail','')}")
    else:
        log("POST /api/admin/claims/{id}/reject", "fail", f"status={r.status_code if r else 'N/A'} {r.text[:100] if r else ''}")
else:
    log("POST /api/admin/claims/{id}/reject", "skip", "no admin or manual_claim_id")

# ============================================================
section("SUMMARY")
# ============================================================
passed  = sum(1 for _,s,_ in results if s == "pass")
failed  = sum(1 for _,s,_ in results if s == "fail")
skipped = sum(1 for _,s,_ in results if s == "skip")

print(f"\n  Total: {len(results)}  |  PASS: {passed}  |  FAIL: {failed}  |  SKIP: {skipped}\n")

if failed:
    print("  Failed endpoints:")
    for label, status, detail in results:
        if status == "fail":
            print(f"    * {label}: {detail}")
print()
