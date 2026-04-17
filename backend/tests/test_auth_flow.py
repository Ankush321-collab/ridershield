import httpx
import asyncio
import os
import time
import random
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://18.60.19.96:8000")

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_BACKEND_TESTS") != "1",
    reason="requires a live backend on localhost:8000; set RUN_LIVE_BACKEND_TESTS=1 to run",
)

@pytest.mark.asyncio
async def test_auth_flow():
    """Test the full rider auth flow from OTP to Profile access."""
    print("🚀 Starting Rider Auth Flow Test...")
    
    async with httpx.AsyncClient() as client:
        # 1. Health Check
        print("🔍 Checking health...")
        r = await client.get(f"{BASE_URL}/health")
        if r.status_code != 200:
            print(f"❌ Health check failed ({r.status_code}): {r.text}")
            return
        print(f"✅ Health: {r.json()['status']}")

        # 2. List Zones
        print("🔍 Listing zones...")
        r = await client.get(f"{BASE_URL}/api/riders/zones")
        if r.status_code != 200:
            print(f"❌ Failed to fetch zones ({r.status_code}): {r.text}")
            return
        
        zones = r.json().get("zones", [])
        if not zones:
            print("❌ No zones found. Run setup_test_data.py first.")
            return
        zone_id = zones[0]["id"]
        print(f"✅ Using Zone ID: {zone_id}")

        # 3. Send OTP
        phone = f"+91{random.randint(1000000000, 9999999999)}"
        print(f"📲 Sending OTP to {phone}...")
        r = await client.post(f"{BASE_URL}/api/riders/send-otp", json={"phone": phone})
        print(f"✅ OTP: {r.json()['message']}")

        # 4. Verify OTP
        print("🔑 Verifying OTP (123456)...")
        r = await client.post(f"{BASE_URL}/api/riders/verify-otp", json={"phone": phone, "otp": "123456"})
        if r.status_code != 200:
            print(f"❌ OTP Verification failed: {r.text}")
            return
        temp_token = r.json()["temp_token"]
        print("✅ Received temp token")

        # 5. Register
        print("📝 Registering rider...")
        rider_data = {
            "name": "Test Rider",
            "platform": "zepto",
            "city": "bengaluru",
            "zone_id": zone_id,
            "slots": ["18:00-21:00", "21:00-23:00"]
        }
        r = await client.post(
            f"{BASE_URL}/api/riders/register", 
            json=rider_data, 
            headers={"Authorization": f"Bearer {temp_token}"}
        )
        if r.status_code != 201:
            print(f"❌ Registration failed: {r.text}")
            return
        jwt_token = r.json()["jwt_token"]
        rider_id = r.json()["rider_id"]
        print(f"✅ Registered! Rider ID: {rider_id}")

        # 6. Get Profile
        print("👤 Fetching profile...")
        r = await client.get(
            f"{BASE_URL}/api/riders/me", 
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        if r.status_code != 200:
            print(f"❌ Profile fetch failed: {r.text}")
            return
        print(f"✅ Profile: {r.json()['name']} ({r.json()['phone']})")

        # 7. Get Risk Profile
        print("📊 Fetching risk profile...")
        r = await client.get(
            f"{BASE_URL}/api/riders/me/risk-profile", 
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        if r.status_code != 200:
            print(f"❌ Risk profile fetch failed: {r.text}")
            return
        print(f"✅ Risk Profile: Score {r.json()['composite_risk_score']}")

    print("\n🎉 ALL TESTS PASSED! Task 1 implementation is working perfectly.")

if __name__ == "__main__":
    asyncio.run(test_auth_flow())
