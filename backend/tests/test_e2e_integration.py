import io
import asyncio
import httpx
import uuid
from datetime import datetime, timezone

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from main import app

BASE_URL = "http://test"


async def run_e2e_test():
    print("=========================================")
    print(" STARTING FULL E2E INTEGRATION TEST ")
    print("=========================================")

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
        from shared.database import init_db, close_db
        from seeds.seed_zones import seed as seed_zones

        await init_db()
        await seed_zones()
        try:
            print("\n1. Health Check & Zone Fetching...")
            r = await client.get(f"{BASE_URL}/health")
            assert r.status_code == 200, f"Health check failed: {r.text}"

            r = await client.get(f"{BASE_URL}/api/riders/zones")
            zones = r.json().get("zones", [])
            assert len(zones) > 0, "No zones available in DB"
            zone_id = zones[0]["id"]
            print(f"   Fetched Zone: {zones[0]['name']}")

            print("\n2. Executing Rider Auth Flow...")
            phone = f"+9199{str(uuid.uuid4().int)[:8]}"

            await client.post(f"{BASE_URL}/api/riders/send-otp", json={"phone": phone})
            r = await client.post(f"{BASE_URL}/api/riders/verify-otp", json={"phone": phone, "otp": "123456"})
            temp_token = r.json()["temp_token"]

            rider_data = {
                "name": "E2E Test Rider",
                "platform": "zepto",
                "city": "bengaluru",
                "zone_id": zone_id,
                "slots": ["18:00-21:00", "21:00-23:00"],
                "upi_id": "e2e@okaxis",
            }
            r = await client.post(
                f"{BASE_URL}/api/riders/register",
                json=rider_data,
                headers={"Authorization": f"Bearer {temp_token}"},
            )
            assert r.status_code == 201, f"Registration failed: {r.text}"

            jwt_token = r.json()["jwt_token"]
            print(f"   Rider registered: {r.json()['rider_id']}")

            print("\n3. Rider Onboarding & Premium Quote Fetch...")
            r = await client.post(
                f"{BASE_URL}/api/riders/onboard",
                json={"plan_tier": "balanced", "typical_slots": ["18:00-21:00", "21:00-23:00"]},
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
            assert r.status_code == 200, f"Onboarding quote fetch failed: {r.text}"
            print(f"   Received quote breakdown: {r.json().keys()}")

            print("\n4. Policy Generation...")
            r = await client.post(
                f"{BASE_URL}/api/policies",
                json={
                    "plan_tier": "balanced",
                    "payment_method": "upi",
                    "upi_id": "e2e@okaxis",
                    "slots": ["18:00-21:00", "21:00-23:00"],
                },
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
            assert r.status_code == 201, f"Policy creation failed: {r.text}"
            policy_id = r.json()["policy_id"]
            print(f"   Policy created: {policy_id}")

            print("\n5. Validating Renewal Scheduling Semantics...")
            r = await client.put(
                f"{BASE_URL}/api/policies/{policy_id}/renew",
                json={"plan_tier": "max_protect"},
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
            assert r.status_code == 200, f"Renewal failed: {r.text}"
            renewal = r.json()
            assert renewal["policy_id"] != policy_id, "Renewal should create a distinct next-week policy"

            r = await client.get(f"{BASE_URL}/api/policies/active", headers={"Authorization": f"Bearer {jwt_token}"})
            assert r.status_code == 200, f"Active policy lookup failed after renewal: {r.text}"
            active_policy_after_renew = r.json()
            assert active_policy_after_renew["policy_id"] == policy_id, "Current-week active policy was replaced by renewal"
            print(f"   Renewal queued for {renewal['week']} while current policy stays active")

            print("\n6. Submitting Manual Claim...")
            dummy_img = io.BytesIO(b"fake_image_bytes")
            fake_photo = ("evidence.jpg", dummy_img, "image/jpeg")
            claim_data = {
                "disruption_type": "heavy_rain",
                "description": "Flood test",
                "incident_time": datetime.now(timezone.utc).isoformat(),
                "latitude": str(12.9716),
                "longitude": str(77.5946),
            }
            r = await client.post(
                f"{BASE_URL}/api/claims/manual",
                data=claim_data,
                files={"photo": fake_photo},
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
            assert r.status_code == 201, f"Failed to submit manual claim: {r.text}"
            manual_claim_id = r.json()["manual_claim_id"]
            print(f"   Submitted manual claim: {manual_claim_id}")

            print("\n7. Admin Authentication...")
            r = await client.post(f"{BASE_URL}/api/admin/login", json={"username": "admin", "password": "admin123"})
            assert r.status_code == 200, "Admin login failed"
            admin_token = r.json()["access_token"]

            print("\n8. Validating Automated Claim Decision...")
            r = await client.get(f"{BASE_URL}/api/claims", headers={"Authorization": f"Bearer {jwt_token}"})
            final_claim = r.json().get("claims", [])[0]
            assert final_claim["status"] in {"paid", "rejected"}, f"Unexpected claim status: {final_claim['status']}"
            print(f"   Automated decision: {final_claim['status']} payout={final_claim['payout_amount']}")

            print("\n9. Admin Reviewing Historical Manual Claims...")
            r = await client.get(
                f"{BASE_URL}/api/admin/claims/manual?status=all",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            claims_history = r.json().get("claims", [])
            target_mc = next((c for c in claims_history if c["id"] == manual_claim_id), None)
            assert target_mc is not None, "Manual claim not found in admin history"
            assert target_mc["review_status"] in {"approved", "rejected"}
            print(f"   Claim history status: {target_mc['review_status']}")
        finally:
            await close_db()

    print("\n=========================================")
    print(" ALL SYSTEMS FUNCTIONAL & INTEGRITY OK ")
    print("=========================================\n")


if __name__ == "__main__":
    asyncio.run(run_e2e_test())
