# TASK-10: Mobile App — Rashi

**Owner:** Rashi  
**Module:** Mobile App — Claims Tab + Manual Claim Submission  
**Priority:** P0 (Demo-critical — [1:15–1:45] Payout + Manual Claim)  
**Deadline:** Today (April 3, 2026)

---

## 1. Your Scope

You own the **claims experience** — where riders see their auto-payouts and submit manual claims with photo evidence.

| Screen | Owner | File | Status |
|--------|-------|------|--------|
| **Claims Tab** | Rashi | `app/(tabs)/claims.tsx` | ⚠️ Stub — needs full build |
| **Manual Claim Tab** | Rashi | `app/(tabs)/manual-claim.tsx` | ⚠️ Stub — needs full build |
| Auth screens | Ankush | — | His scope |
| Policy + Dashboard | Chanikya | — | His scope |
| Profile | Ankush | — | His scope |

---

## 2. Tech Stack

- **Framework:** Expo SDK 54 + React Native 0.81 + TypeScript
- **Navigation:** expo-router (file-based)
- **State:** React Context (`AuthContext`)
- **API Client:** `services/api.ts` (`api` object)
- **Camera:** Use `expo-image-picker` (install needed — see setup)
- **Location:** Use `expo-location` (install needed — see setup)
- **Backend:** `http://localhost:8000`

---

## 3. Setup (Install New Dependencies)

You'll need these packages for camera + location. Run in `mobile/` directory:

```bash
npx expo install expo-image-picker expo-location
```

These are needed for the geo-tagged photo capture in manual claims.

---

## 4. Tasks Checklist

### 4.1 Claims Tab (`app/(tabs)/claims.tsx`) — Full Build

This tab shows ALL of the rider's claims (auto + manual) and payouts.

- [ ] **Fetch data on mount:**
  ```typescript
  const [claims, setClaims] = useState<any[]>([]);
  const [payouts, setPayouts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.claims.list(),
      api.payouts.list(),
    ]).then(([claimData, payoutData]) => {
      setClaims(claimData.claims || []);
      setPayouts(payoutData.payouts || []);
    }).finally(() => setLoading(false));
  }, []);
  ```

- [ ] **Tab Toggle** at top: "Claims" | "Payouts"
  ```typescript
  const [activeTab, setActiveTab] = useState<'claims' | 'payouts'>('claims');
  ```
  - Use two horizontal buttons with active state styling

- [ ] **Claims List** (when tab = "claims"):
  
  Each claim card shows:
  - **Type badge:** "🤖 Auto" (blue) or "📝 Manual" (amber)
  - **Status badge:** 
    - PAID → green
    - PENDING → amber
    - UNDER REVIEW → blue
    - REJECTED → red
    - APPROVED → green
  - **Trigger type** with emoji (weather/traffic/store/platform)
  - **Zone name**
  - **Payout amount** (large, sky-400 color): `₹540`
  - **Timestamp** (relative): "2 hours ago" or formatted date
  - **Income breakdown** (if available):
    - Expected: ₹720
    - Actual: ₹180  
    - Loss: ₹540

- [ ] **Payouts List** (when tab = "payouts"):
  
  Each payout card shows:
  - Amount (large, green)
  - Trigger type
  - Status: "Credited" ✅ or "Processing" ⏳
  - UPI Reference (monospace, small)
  - Date/time

- [ ] **Empty states:**
  - No claims: "No claims yet. You're covered — if a disruption happens, it'll appear here."
  - No payouts: "No payouts yet this week."

- [ ] **Pull-to-refresh**

- [ ] **Loading state:** Skeleton cards or spinner

---

### 4.2 Manual Claim Tab (`app/(tabs)/manual-claim.tsx`) — ⭐ DEMO CRITICAL — Full Build

This is the manual claim submission form. Judges will see this at **[1:30–1:45]**.

**Complete form with these sections:**

#### Step 1: Disruption Type Picker
- [ ] **Disruption type dropdown/chips:**
  ```typescript
  const DISRUPTION_TYPES = [
    { id: 'weather', label: 'Weather', emoji: '🌧️', desc: 'Rain, flooding, storms' },
    { id: 'traffic', label: 'Traffic', emoji: '🚗', desc: 'Congestion, road blocks' },
    { id: 'store_closure', label: 'Store Closed', emoji: '🏪', desc: 'Dark store shut down' },
    { id: 'platform_outage', label: 'Platform Down', emoji: '📱', desc: 'App not working' },
    { id: 'other', label: 'Other', emoji: '❓', desc: 'Other disruption' },
  ];
  ```
  - Show as tappable cards/chips
  - Selected = blue border + background

#### Step 2: Photo Capture
- [ ] **Camera/gallery button:**
  ```typescript
  import * as ImagePicker from 'expo-image-picker';
  import * as Location from 'expo-location';

  const takePhoto = async () => {
    // Request camera permission
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      alert('Camera permission needed');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      quality: 0.7,
      allowsEditing: false,
      exif: true,  // Include EXIF data (GPS)
    });

    if (!result.canceled) {
      setPhoto(result.assets[0]);
    }
  };

  // Also get current location separately
  const getLocation = async () => {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status === 'granted') {
      const loc = await Location.getCurrentPositionAsync({});
      setLocation(loc.coords);
    }
  };
  ```

- [ ] **Photo preview:**
  - If photo taken: show thumbnail with ✅ "Photo captured"
  - If no photo: show camera icon with "📸 Take Photo" button
  - "Retake" option to replace photo

- [ ] **Location indicator:**
  - Show current GPS coordinates (small text)
  - "📍 Location: 12.9352° N, 77.6245° E"
  - Green indicator if location available, red if denied

#### Step 3: Description
- [ ] **Text input (multiline):**
  ```tsx
  <TextInput
    style={styles.textArea}
    placeholder="Describe what happened..."
    placeholderTextColor="#64748b"
    value={description}
    onChangeText={setDescription}
    multiline
    numberOfLines={4}
    textAlignVertical="top"
  />
  ```

#### Step 4: Submit
- [ ] **Submit button:**
  ```typescript
  const handleSubmit = async () => {
    if (!disruptionType || !photo || !description) {
      alert('Please fill all fields and take a photo');
      return;
    }

    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('disruption_type', disruptionType);
      formData.append('description', description);
      
      // Append photo
      const photoUri = photo.uri;
      const filename = photoUri.split('/').pop() || 'photo.jpg';
      formData.append('photo', {
        uri: photoUri,
        name: filename,
        type: 'image/jpeg',
      } as any);

      // Append location if available
      if (location) {
        formData.append('latitude', String(location.latitude));
        formData.append('longitude', String(location.longitude));
      }

      const result = await api.manualClaims.submit(formData);
      
      // Show success
      setSubmitted(true);
      setClaimId(result.claim_id);
    } catch (err) {
      alert('Submission failed: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };
  ```

- [ ] **Success State** (after submission):
  - Show ✅ "Claim Submitted Successfully"
  - Claim ID
  - Status: "Under Review"
  - "Track your claim in the Claims tab"
  - "Submit Another" button to reset form

- [ ] **Submit button styling:**
  - Red/coral background (`#dc2626`)
  - Disabled if missing required fields (opacity 0.4)
  - Loading spinner during submission

- [ ] **Validation:**
  - Disruption type required
  - Photo required
  - Description required (min 10 chars)
  - Show inline error messages

---

## 5. Backend API Reference

### Endpoints You'll Call

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/claims` | List rider's claims (auto + manual) |
| `GET` | `/api/claims/{id}` | Claim detail |
| `GET` | `/api/payouts` | Payout history |
| `POST` | `/api/claims/manual` | Submit manual claim (FormData) |
| `GET` | `/api/claims/manual/{id}` | Check manual claim status |

### Manual Claim Submission

**POST /api/claims/manual** (multipart/form-data):
```
disruption_type: "traffic"
description: "Road work causing gridlock on main road"
photo: [binary file]
latitude: 12.9352
longitude: 77.6245
```

**Response:**
```json
{
  "claim_id": "mcl_xyz789",
  "status": "submitted",
  "spam_score": null,
  "message": "Manual claim submitted. Under review."
}
```

### Claims List Response

**GET /api/claims:**
```json
{
  "claims": [
    {
      "id": "clm_001",
      "claim_type": "auto",
      "trigger_type": "weather",
      "income_loss": 540,
      "payout_amount": 540,
      "status": "paid",
      "zone_name": "koramangala",
      "created_at": "2026-04-03T10:30:00Z"
    },
    {
      "id": "mcl_002",
      "claim_type": "manual",
      "trigger_type": "traffic",
      "status": "under_review",
      "description": "Road work...",
      "created_at": "2026-04-03T11:00:00Z"
    }
  ]
}
```

---

## 6. Design Guidelines

Same as global mobile design:

- **Background:** `#0f172a`  
- **Cards:** `#1e293b` with `#334155` border, radius 14-16
- **Claim type badges:**
  - Auto: `bg: #1d4ed8` (blue)
  - Manual: `bg: #d97706` (amber)
- **Status badges:**
  - Paid: `bg: #22c55e` (green)
  - Pending/Under Review: `bg: #f59e0b` (amber)
  - Rejected: `bg: #ef4444` (red)
- **Payout amounts:** `#38bdf8` (sky-400), large bold
- **Submit button:** `#dc2626` (red) — emphasizes urgency
- **Photo preview:** rounded corners, bordered, max 200px height

---

## 7. Coordination with Team

- **Independent work** — your screens are self-contained tabs, no dependency on Ankush/Chanikya
- **Chanikya's dashboard** has a "Report Disruption" button that navigates to your manual-claim tab — make sure the tab is ready
- **Don't modify:** `services/api.ts` or `contexts/AuthContext.tsx` without coordination

---

## 8. Demo Responsibility

You own **[1:15–1:45]** of the demo video:

| Time | What | Screen |
|------|------|--------|
| **[1:15–1:30]** | Show auto-payout notification + payout detail in Claims tab | Claims Tab |
| **[1:30–1:45]** | Tap "Manual Claim" → Select traffic → Take photo → Describe → Submit → "Under Review" | Manual Claim Tab |

**Key moments judges will see:**
1. Payout of ₹540 appearing in claims list with breakdown
2. Camera opens, photo taken with location stamp
3. Submit → claim appears as "Under Review"

---

## 9. Acceptance Criteria

- [ ] Claims tab shows real claims from backend (auto + manual)
- [ ] Claims have correct type badges and status badges
- [ ] Payouts tab shows real payout history
- [ ] Toggle between Claims/Payouts works
- [ ] Manual claim form: disruption type picker works
- [ ] Manual claim form: camera captures photo
- [ ] Manual claim form: location captured
- [ ] Manual claim form: description textarea works
- [ ] Manual claim submit sends FormData to API correctly
- [ ] Success state shows claim ID and "Under Review"
- [ ] All required field validation with inline errors
- [ ] Pull-to-refresh on claims list
- [ ] Loading/error states on all screens
- [ ] No crashes or TypeScript errors
- [ ] Dark theme consistent
