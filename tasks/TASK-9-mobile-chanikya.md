# TASK-9: Mobile App — Chanikya

**Owner:** Chanikya  
**Module:** Mobile App — Policy Flow + Dashboard Tab  
**Priority:** P0 (Demo-critical — [0:30–1:00] Policy + Dashboard)  
**Deadline:** Today (April 3, 2026)

---

## 1. Your Scope

You own the **policy purchase flow** and the **main dashboard tab** — what the rider sees after onboarding and during daily use.

| Screen | Owner | File | Status |
|--------|-------|------|--------|
| **Policy Select** | Chanikya | `app/policy/select.tsx` | Stubbed with fake data — needs API |
| **Payment Screen** | Chanikya | `app/policy/payment.tsx` | Stubbed with fake data — needs API |
| **Dashboard Tab** | Chanikya | `app/(tabs)/index.tsx` | Stubbed — needs real data |
| Auth screens | Ankush | — | His scope |
| Claims + Manual | Rashi | — | Her scope |
| Profile | Ankush | — | His scope |

---

## 2. Tech Stack

- **Framework:** Expo SDK 54 + React Native 0.81 + TypeScript
- **Navigation:** expo-router (file-based)
- **State:** React Context (`AuthContext`)
- **API Client:** `services/api.ts` (`api` object)
- **Backend:** `http://localhost:8000`

---

## 3. Tasks Checklist

### 3.1 Policy Select Screen (`app/policy/select.tsx`) — ⭐ DEMO CRITICAL

Currently shows hardcoded tiers. Wire up real premium data.

- [ ] **Fetch premium quote on mount:**
  ```typescript
  const { rider } = useAuth();
  const [tiers, setTiers] = useState<any>(null);
  const [selectedTier, setSelectedTier] = useState<string>('balanced');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Use rider's slots and city to get real pricing
    const slots = rider?.slots?.join(',') || '18:00-21:00,21:00-23:00';
    const city = rider?.city || 'bengaluru';
    
    api.policies.getQuote(slots, city)
      .then(data => setTiers(data))
      .finally(() => setLoading(false));
  }, []);
  ```

- [ ] **Three tier cards** with REAL pricing from API:
  
  Each card shows:
  - Tier name (Essential / Balanced / Max Protect)
  - Emoji icon (🔵 / 🟢 / 🟡)
  - **Real weekly price** from API (e.g., ₹120/week)
  - Coverage percentage (70% / 80% / 90%)
  - Max payout per event
  - **"RECOMMENDED"** badge on Balanced tier
  - Selected state = highlighted border

- [ ] **Zone risk comparison** — show a note:
  > "Your zone (Koramangala) has a risk score of 72/100. Premiums are personalized based on zone risk."
  
  This demonstrates the **premium differentiation** judges want to see.

- [ ] **Slot breakdown** (if API provides):
  - Show per-slot expected earnings + risk
  - e.g., "6-9 PM: ₹360 expected, Risk 75/100"

- [ ] **"Continue to Payment →" button:**
  - Passes selected tier to payment screen
  ```typescript
  router.push({
    pathname: '/policy/payment',
    params: { tier: selectedTier, price: selectedPrice }
  });
  ```

- [ ] **Loading state** while fetching quote (skeleton cards)

---

### 3.2 Payment Screen (`app/policy/payment.tsx`) — ⭐ DEMO CRITICAL

Currently has hardcoded values. Wire up real payment.

- [ ] **Read tier from params:**
  ```typescript
  const { tier, price } = useLocalSearchParams<{ tier: string; price: string }>();
  ```

- [ ] **Premium Summary Card:**
  - Plan name (from params)
  - Coverage week (e.g., "2026-W14")
  - Coverage percentage
  - Number of slots covered
  - Divider line
  - **Total price** (large, bold, sky-400 color)

- [ ] **UPI Payment Section:**
  - Show rider's UPI ID (from `useAuth()`)
  - "Pay via UPI" button with 💳 icon
  - Mock payment simulation:
    ```typescript
    const handlePay = async () => {
      setProcessing(true);
      try {
        const result = await api.policies.create({
          plan_tier: tier,
          payment_method: 'upi',
          upi_id: rider?.upi_id || 'demo@oksbi',
        });
        
        // Show success state briefly
        setSuccess(true);
        setTimeout(() => {
          router.replace('/(tabs)');  // Go to dashboard
        }, 1500);
      } catch (err) {
        alert('Payment failed: ' + err.message);
      } finally {
        setProcessing(false);
      }
    };
    ```

- [ ] **Success Animation:**
  - After payment: show ✅ "Payment Successful! Policy Activated"
  - Brief green checkmark animation  
  - Auto-navigate to dashboard after 1.5s

- [ ] **Processing state:** Show "Processing..." with spinner while API call is in progress

---

### 3.3 Dashboard Tab (`app/(tabs)/index.tsx`) — ⭐ DEMO CRITICAL

This is the **main screen** riders see daily. Currently shows hardcoded data.

- [ ] **Fetch data on mount:**
  ```typescript
  const { rider } = useAuth();
  const [policy, setPolicy] = useState<any>(null);
  const [triggers, setTriggers] = useState<any>(null);
  const [payouts, setPayouts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.policies.getActive().catch(() => null),
      api.triggers.getStatus().catch(() => null),
      api.payouts.list().catch(() => ({ payouts: [] })),
    ]).then(([policyData, triggerData, payoutData]) => {
      setPolicy(policyData);
      setTriggers(triggerData);
      setPayouts(payoutData?.payouts || []);
    }).finally(() => setLoading(false));
  }, []);
  ```

- [ ] **Greeting Header:**
  - "Hey, {rider.name} 👋" (real name from auth context)
  - Status line: "Your coverage is active" (green) or "No active policy" (amber)

- [ ] **Active Policy Card** (if policy exists):
  - Plan tier badge (ESSENTIAL / BALANCED / MAX PROTECT)
  - Coverage amount: `₹{max_coverage}`
  - Hours remaining this week
  - Coverage used (amount claimed so far)
  - Expiry date
  - If no policy: Show "Get Protected" CTA card → navigates to `/policy/select`

- [ ] **Disruption Alerts Card:**
  - Fetch from `api.triggers.getStatus()`
  - If active trigger in rider's zone:
    - Show alert with trigger type emoji + description
    - "🌧️ Heavy Rain detected in Koramangala"
    - Amber/red border for urgency
  - If no alerts: "✅ No active disruptions in your zone"

- [ ] **Recent Payouts Section:**
  - Fetch from `api.payouts.list()`
  - Show last 3-5 payouts:
    - Trigger type emoji + label
    - Payout amount (large, sky-400)
    - Date/time
    - UPI reference (if available)
  - If no payouts: "No payouts yet this week"

- [ ] **Action Buttons:**
  - "View / Renew Policy" → `/policy/select` (already exists)
  - "Report Disruption" → `/(tabs)/manual-claim` (navigates to Rashi's screen)

- [ ] **Pull-to-refresh** (RefreshControl on ScrollView):
  ```typescript
  <ScrollView
    refreshControl={
      <RefreshControl refreshing={refreshing} onRefresh={onRefresh} 
        tintColor="#38bdf8" />
    }
  >
  ```

---

## 4. Backend API Reference

### Endpoints You'll Call

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/policies/quote?slots=...&city=...` | Get 3-tier pricing |
| `POST` | `/api/policies` | Create/purchase policy |
| `GET` | `/api/policies/active` | Get active policy info |
| `PUT` | `/api/policies/{id}/renew` | Renew policy |
| `GET` | `/api/triggers/status` | Check active disruptions |
| `GET` | `/api/payouts` | Get payout history |

### Example Responses

**GET /api/policies/quote:**
```json
{
  "essential": { "weekly": 120, "coverage_pct": 70, "max_payout": 2016 },
  "balanced": { "weekly": 180, "coverage_pct": 80, "max_payout": 2304 },
  "max_protect": { "weekly": 250, "coverage_pct": 90, "max_payout": 2592 },
  "zone_risk_score": 72,
  "slot_breakdown": [
    { "slot": "18:00-21:00", "expected_earnings": 360, "risk_score": 75 },
    { "slot": "21:00-23:00", "expected_earnings": 240, "risk_score": 68 }
  ]
}
```

**POST /api/policies:**
```json
{
  "policy_id": "pol_abc123",
  "plan_tier": "balanced",
  "premium_paid": 180,
  "coverage_week": "2026-W14",
  "status": "active"
}
```

**GET /api/payouts:**
```json
{
  "payouts": [
    {
      "id": "pay_001",
      "amount": 540,
      "trigger_type": "weather",
      "status": "credited",
      "upi_reference": "UPI123456",
      "created_at": "2026-04-03T10:30:00Z"
    }
  ]
}
```

---

## 5. Design Guidelines

Same as global mobile design:

- **Background:** `#0f172a`  
- **Cards:** `#1e293b` with `#334155` border, radius 16
- **Accent:** `#38bdf8` (sky) for values, `#22c55e` (green) for positive, `#f59e0b` (amber) for warnings
- **Text:** `#f8fafc` primary, `#94a3b8` secondary
- **Buttons:** Blue (`#2563eb`) for primary, Green (`#22c55e`) for payment
- **Spacing:** 20px screen padding, 12-16px card padding, 14-16px gaps

---

## 6. Coordination with Team

- **Ankush** → his slot-select screen navigates to your `/policy/select`. Make sure you read params correctly OR fetch independently.
- **Rashi** → Dashboard has a "Report Disruption" button that navigates to her `manual-claim` tab.
- **Don't modify:** `services/api.ts` or `contexts/AuthContext.tsx` without telling Ankush.

---

## 7. Demo Responsibility

You own **[0:30–1:00]** of the demo video:

| Time | What | Screen |
|------|------|--------|
| **[0:30–0:45]** | Select Balanced plan, show hi/lo risk zone pricing | Policy Select |
| **[0:45–0:50]** | Pay via UPI mock | Payment |
| **[0:50–1:00]** | Dashboard: active policy, risk forecast, "system monitors in background" | Dashboard Tab |

---

## 8. Acceptance Criteria

- [ ] Policy select shows real prices from backend (3 tiers)
- [ ] Zone risk score visible on policy select (demo differentiator!)
- [ ] Payment calls `api.policies.create()` → policy created
- [ ] Payment shows success animation → navigates to dashboard
- [ ] Dashboard shows real active policy data
- [ ] Dashboard shows disruption alerts (if any active)
- [ ] Dashboard shows recent payouts list
- [ ] Dashboard has pull-to-refresh
- [ ] "No policy" state shows CTA to purchase
- [ ] All screens have loading/error states
- [ ] No crashes or TypeScript errors
- [ ] No hardcoded dummy data remains (remove `TODO` placeholders)
