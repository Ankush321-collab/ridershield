# TASK-8: Mobile App — Ankush

**Owner:** Ankush  
**Module:** Mobile App — Auth Flow (OTP + Register + Zone + Slot) + Profile Tab  
**Priority:** P0 (Demo-critical — [0:15–0:30] Registration Flow)  
**Deadline:** Today (April 3, 2026)

---

## 1. Your Scope

You own the **onboarding flow** — the FIRST thing judges see in the demo. Registration must look polished and work end-to-end.

| Screen | Owner | File | Status |
|--------|-------|------|--------|
| **Welcome/Landing** | Ankush | `app/index.tsx` | Has basic landing |
| **OTP Screen** | Ankush | `app/(auth)/otp.tsx` | Functional — needs polish |
| **Register Screen** | Ankush | `app/(auth)/register.tsx` | Functional — needs polish |
| **Zone Select** | Ankush | `app/(auth)/zone-select.tsx` | ⚠️ **STUB — needs full build** |
| **Slot Select** | Ankush | `app/(auth)/slot-select.tsx` | ⚠️ **STUB — needs full build** |
| **Profile Tab** | Ankush | `app/(tabs)/profile.tsx` | Stub — needs API wiring |
| Policy Select/Payment | Chanikya | — | His scope |
| Dashboard Tab | Chanikya | — | His scope |
| Claims + Manual Claim | Rashi | — | Her scope |

---

## 2. Tech Stack

- **Framework:** Expo SDK 54 + React Native 0.81 + TypeScript
- **Navigation:** expo-router (file-based)
- **State:** React Context (`AuthContext`)
- **API Client:** `services/api.ts` (`api` object — already created)
- **Styling:** StyleSheet (React Native)
- **Backend:** `http://localhost:8000` (or `EXPO_PUBLIC_API_URL`)

---

## 3. Tasks Checklist

### 3.1 Welcome Screen (`app/index.tsx`) — Polish

- [ ] Make it look stunning — this is the app's first impression
- [ ] Show app name "Zylo" with shield emoji/icon
- [ ] Tagline: "Income Protection for Delivery Riders"
- [ ] Phone number input field with country code (+91)
- [ ] "Get OTP" button → calls `api.riders.sendOtp(phone)` → navigates to OTP screen
- [ ] Loading state on button during API call
- [ ] Handle errors (show alert)
- [ ] Dark theme consistent with `#0f172a` background

---

### 3.2 OTP Screen (`app/(auth)/otp.tsx`) — Polish

Already functional. Improvements needed:

- [ ] Add auto-focus on OTP input
- [ ] Add "Resend OTP" button (with 30s cooldown timer)
- [ ] Better error message styling (not just `alert()`)
- [ ] Add subtle animation when verifying (spinner or pulse)
- [ ] Ensure navigation to register screen works after verify

---

### 3.3 Register Screen (`app/(auth)/register.tsx`) — Polish

Already functional. Improvements needed:

- [ ] Platform chips should look better — add platform icons/emojis:
  - Zepto: 🟢 
  - Blinkit: 🟡
  - Swiggy: 🟠
- [ ] UPI ID field validation (basic format check)
- [ ] "Select Zone →" button navigates correctly with all params
- [ ] Keyboard dismiss on scroll

---

### 3.4 Zone Select Screen (`app/(auth)/zone-select.tsx`) — ⭐ BUILD FROM SCRATCH

This is currently a **stub**. You need to build it fully.

- [ ] **Fetch zones on mount:**
  ```typescript
  const [zones, setZones] = useState<any[]>([]);
  const [selectedZone, setSelectedZone] = useState<string | null>(null);
  
  useEffect(() => {
    api.zones.list().then(data => setZones(data.zones));
  }, []);
  ```

- [ ] **City tabs/filter** at top:
  - Show unique cities from zones list (e.g., Bengaluru, Hyderabad, Mumbai, Delhi)
  - Tap city → filter zones for that city
  - Default to first city

- [ ] **Zone cards** — for each zone show:
  - Zone name (e.g., "Koramangala")
  - City
  - Risk score with **color-coded indicator:**
    - `< 40`: Green 🟢 "Low Risk"
    - `40–70`: Yellow 🟡 "Medium Risk"  
    - `> 70`: Red 🔴 "High Risk"
  - Selected state: highlighted border (sky-400)

- [ ] **"Continue" button** at bottom:
  - Disabled until zone selected
  - On press → navigate to slot-select with zone data:
    ```typescript
    router.push({
      pathname: '/(auth)/slot-select',
      params: { ...existingParams, zone: selectedZone, zoneId: selectedZoneId }
    });
    ```

- [ ] **Loading state** while fetching zones (skeleton or spinner)

---

### 3.5 Slot Select Screen (`app/(auth)/slot-select.tsx`) — ⭐ BUILD FROM SCRATCH

This is currently a **stub**. You need to build it fully.

- [ ] **Define time slots:**
  ```typescript
  const TIME_SLOTS = [
    { id: '06:00-09:00', label: 'Early Morning', time: '6:00 AM - 9:00 AM', icon: '🌅' },
    { id: '09:00-12:00', label: 'Morning', time: '9:00 AM - 12:00 PM', icon: '☀️' },
    { id: '12:00-15:00', label: 'Afternoon', time: '12:00 PM - 3:00 PM', icon: '🌤️' },
    { id: '15:00-18:00', label: 'Evening', time: '3:00 PM - 6:00 PM', icon: '🌇' },
    { id: '18:00-21:00', label: 'Night Peak', time: '6:00 PM - 9:00 PM', icon: '🌙' },
    { id: '21:00-23:00', label: 'Late Night', time: '9:00 PM - 11:00 PM', icon: '🌃' },
  ];
  ```

- [ ] **Multi-select slot chips:**
  - Tappable cards for each slot
  - Selected = blue background, unselected = dark slate
  - Show risk level per slot (can vary — show as subtle text)
  - Allow selecting 1–4 slots

- [ ] **Selected slots counter:** "3 slots selected"

- [ ] **"Complete Registration" button:**
  - On press → call TWO API endpoints sequentially:
    ```typescript
    // 1. Register the rider
    const regResult = await api.riders.register({
      name, platform, city, zone: zoneName, 
      slots: selectedSlots, upi_id: upiId
    });
    
    // 2. Get the real JWT token and login
    const token = regResult.jwt_token;
    await login(token);  // from useAuth()
    
    // 3. Navigate to policy selection
    router.replace('/policy/select');
    ```
  - Show loading during registration
  - Handle errors gracefully

---

### 3.6 Profile Tab (`app/(tabs)/profile.tsx`) — Wire Up

- [ ] **Fetch real rider data** from `useAuth()` context (already connected)
- [ ] **Fetch risk profile** on mount:
  ```typescript
  const [riskProfile, setRiskProfile] = useState<any>(null);
  useEffect(() => {
    api.riders.getRiskProfile()
      .then(setRiskProfile)
      .catch(console.error);
  }, []);
  ```

- [ ] **Profile Card:**
  - Name (large, bold)
  - Phone
  - Platform (with emoji)
  - Zone
  - Trust Score (with progress bar/ring)

- [ ] **Risk Profile Card:**
  - Display `zone_flood_risk`, `zone_traffic_risk`
  - Income volatility indicator
  - Composite risk score (color-coded)
  - 4-week earnings (simple bar chart or list):
    ```
    Week 12: ₹4,250
    Week 11: ₹4,100
    Week 10: ₹3,800
    Week 9:  ₹4,450
    ```

- [ ] **Logout button** — already connected via `useAuth().logout`

---

## 4. Backend API Reference

### Endpoints You'll Call

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/riders/send-otp` | Send OTP `{ phone }` |
| `POST` | `/api/riders/verify-otp` | Verify OTP `{ phone, otp }` → temp_token |
| `POST` | `/api/riders/register` | Create rider → jwt_token |
| `GET` | `/api/zones` | List zones with risk scores |
| `GET` | `/api/riders/me` | Get rider profile |
| `GET` | `/api/riders/me/risk-profile` | Risk data + earnings |

---

## 5. Design Guidelines

- **Background:** `#0f172a` (slate-950)
- **Cards:** `#1e293b` (slate-800) with `#334155` border
- **Primary accent:** `#38bdf8` (sky-400) — values, highlights
- **Success:** `#22c55e` (green-500) — active states
- **Warning:** `#f59e0b` (amber-500) — risk indicators
- **Danger:** `#ef4444` (red-500) — high risk, errors
- **Text primary:** `#f8fafc` (slate-50)
- **Text secondary:** `#94a3b8` (slate-400)
- **Border radius:** 12-16 for cards, 8-10 for chips/badges
- **Padding:** 16-20 for cards, 24 for screens

---

## 6. Coordination with Team

- **Chanikya** handles Policy Select + Payment + Dashboard tab → he picks up after your slot-select navigates to `/policy/select`
- **Rashi** handles Claims tab + Manual Claim → independent screens, no dependency on you
- **All three share:** `services/api.ts` and `contexts/AuthContext.tsx` — don't modify these without telling others

---

## 7. Demo Responsibility

You own **[0:15–0:30]** of the demo video:

> **Visual:** Mobile app registration flow  
> Phone → OTP (123456) → Name + Platform → Zone (Koramangala, show risk) → Slots  
> Everything must feel **smooth and instant**

---

## 8. Acceptance Criteria

- [ ] Welcome → OTP → Register → Zone → Slot → Policy flow works end-to-end
- [ ] Zone select fetches real zones, shows risk scores color-coded
- [ ] Slot select allows multi-pick, calls register API
- [ ] Registration creates rider and returns JWT
- [ ] Profile tab shows real rider data + risk profile
- [ ] All screens have loading/error states
- [ ] No crashes or TypeScript errors
- [ ] Dark theme consistent across all screens
- [ ] Navigation flow is correct (no dead ends)
