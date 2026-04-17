# TASK-7: Admin Dashboard — Charmi

**Owner:** Charmi  
**Module:** Admin Dashboard — Auto Claims + Manual Claims Review  
**Priority:** P0 (Demo-critical — [1:45–1:55] Admin Review)  
**Deadline:** Today (April 3, 2026)

---

## 1. Your Scope

You own the **two claims pages** — the heart of the admin dashboard where claims are viewed, reviewed, approved, and rejected.

| Page | Owner | Status |
|------|-------|--------|
| **Auto Claims (/claims)** | Charmi | Stubbed — needs real API data + filtering |
| **Manual Claims (/manual-claims)** | Charmi | Stubbed — needs real API data + approve/reject |
| Layout + Overview | Pankaj | He handles this |
| Triggers | Pankaj | He handles this |

---

## 2. Prerequisites (Wait for Pankaj)

Before you start wiring API calls, Pankaj will create:
1. **`src/lib/types.ts`** — shared TypeScript types
2. **Updated `src/lib/api.ts`** — any missing endpoints

You can start **designing the UI** immediately while waiting. Once types are ready, wire up the API.

---

## 3. Tech Stack

- **Framework:** Next.js 16 + React 19 + TypeScript
- **Styling:** Tailwind CSS v4
- **API Client:** `src/lib/api.ts` (`adminApi`)
- **Backend:** `http://localhost:8000`

---

## 4. Tasks Checklist

### 4.1 Auto Claims Page (`src/app/claims/page.tsx`)

This page shows ALL automatically generated claims from trigger events.

- [ ] **Add `'use client'` directive** at top of file

- [ ] **Fetch data on mount:**
  ```typescript
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    adminApi.claims.listAll()
      .then(data => setClaims(data.claims))
      .finally(() => setLoading(false));
  }, []);
  ```

- [ ] **Filter Bar** (above table):
  - Status filter: All | Pending | Approved | Paid | Rejected
  - Trigger type filter: All | Weather | Traffic | Store | Platform | Regulatory
  - Design as pill/chip buttons (active = solid color)

- [ ] **Claims Table** (already scaffolded — wire up real data):
  | Column | Source | Format |
  |--------|--------|--------|
  | Claim ID | `claim.id` | First 8 chars, monospace |
  | Rider | `claim.rider_name` | Text |
  | Trigger | `claim.trigger_type` | Emoji + label (map below) |
  | Income Loss | `claim.income_loss` | `₹{amount}` in red |
  | Payout | `claim.payout_amount` | `₹{amount}` in green |
  | Fraud Score | `claim.fraud_score` | Number with color (< 30 green, 30-70 yellow, >70 red) |
  | Status | `claim.status` | Badge (green=paid, yellow=pending, red=rejected) |

- [ ] **Trigger type emoji map:**
  ```typescript
  const TRIGGER_EMOJI: Record<string, string> = {
    weather: '🌧️ Heavy Rain',
    traffic: '🚗 Traffic',
    store_closure: '🏪 Store Closed',
    platform_outage: '📱 Platform Down',
    regulatory: '🚫 Regulatory',
  };
  ```

- [ ] **Status badge colors:**
  ```typescript
  const STATUS_COLORS: Record<string, string> = {
    pending: 'bg-amber-900 text-amber-300',
    approved: 'bg-blue-900 text-blue-300',
    paid: 'bg-emerald-900 text-emerald-300',
    rejected: 'bg-red-900 text-red-300',
  };
  ```

- [ ] **Empty state:** "No claims found" centered message
- [ ] **Loading state:** Skeleton rows or spinner
- [ ] **Summary stats above table:** Total claims count, Total payouts sum, Average fraud score

---

### 4.2 Manual Claims Review Page (`src/app/manual-claims/page.tsx`) — DEMO CRITICAL ⭐

This is the **KEY demo page** — [1:45–1:55] of the demo video. Judges will see you approve a manual claim here.

- [ ] **Add `'use client'` directive** at top of file

- [ ] **Fetch manual claims:**
  ```typescript
  const [claims, setClaims] = useState<ManualClaim[]>([]);
  useEffect(() => {
    adminApi.claims.listManual('spam_score', 'asc')
      .then(data => setClaims(data.claims));
  }, []);
  ```

- [ ] **Claim Cards** (one per claim — NOT a table, use cards for richer display):
  
  Each card has:
  
  **Header Row:**
  - Claim ID + Disruption type (bold, left)
  - Spam score badge (right): `Spam: {score}/100`
    - Score < 30: green badge (low risk)
    - Score 30-70: yellow badge (medium risk)  
    - Score ≥ 70: red badge (auto-rejected)

  **Rider Info:**
  - Rider name • Zone • Submission time

  **Description:**
  - Rider's written description (italic, quoted)

  **Photo Evidence:**
  - Display the photo from `claim.photo_url` 
  - If photo URL exists: `<img>` with rounded corners, max-height 200px
  - If no photo: "No photo attached" placeholder

  **Validation Grid (3 columns):**
  | Geo-Validation | Weather | Traffic |
  |----------------|---------|---------|
  | ✅ 45m match | ✅ Matches | ✅ High congestion |
  
  - Green ✅ if match=true, Red ❌ if match=false
  - Show detail text below the icon

  **Action Buttons:**
  - ✅ **Approve** (green button) → calls `adminApi.claims.approve(claimId)`
  - ❌ **Reject** (red button) → shows reason input → calls `adminApi.claims.reject(claimId, reason)`

- [ ] **Approve Flow:**
  ```typescript
  const handleApprove = async (claimId: string) => {
    try {
      await adminApi.claims.approve(claimId);
      // Remove from list or update status
      setClaims(prev => prev.filter(c => c.id !== claimId));
      // Show success toast/notification
    } catch (err) {
      alert('Failed to approve: ' + err.message);
    }
  };
  ```

- [ ] **Reject Flow:**
  - Click Reject → show inline text input for reason
  - Confirm → call `adminApi.claims.reject(claimId, reason)`
  - Remove from list after success

- [ ] **Sorting:** Already sorted by spam_score ascending (low risk first — meant to fast-track legitimate claims)

- [ ] **Empty state:** "🎉 No pending manual claims — all caught up!"

- [ ] **Auto-rejected indicator:** If spam_score ≥ 70, show a red "Auto-Rejected" badge instead of action buttons

---

## 5. Backend API Reference

### Endpoints You'll Call

| Method | Endpoint | Purpose | Response Shape |
|--------|----------|---------|----------------|
| `GET` | `/api/admin/claims` | All auto claims | `{ claims: [...] }` |
| `GET` | `/api/admin/claims/manual?sort=spam_score&order=asc` | Manual claims sorted | `{ claims: [...] }` |
| `POST` | `/api/admin/claims/{id}/approve` | Approve → payout | `{ message, payout_id }` |
| `POST` | `/api/admin/claims/{id}/reject` | Reject with reason | `{ message }` |

### Example API Responses

**GET /api/admin/claims:**
```json
{
  "claims": [
    {
      "id": "clm_abc123",
      "rider_id": "rd_001",
      "rider_name": "Arjun Kumar",
      "claim_type": "auto",
      "trigger_type": "weather",
      "income_loss": 540,
      "payout_amount": 540,
      "fraud_score": 15,
      "status": "paid",
      "created_at": "2026-04-03T10:30:00Z"
    }
  ]
}
```

**GET /api/admin/claims/manual:**
```json
{
  "claims": [
    {
      "id": "mcl_xyz789",
      "rider_name": "Arjun Kumar",
      "trigger_type": "traffic",
      "description": "Road work causing gridlock on main road",
      "photo_url": "/uploads/photos/mcl_xyz.jpg",
      "spam_score": 25,
      "geo_validation": { "match": true, "distance_m": 45 },
      "weather_corroboration": { "match": true, "details": "Light rain confirmed" },
      "traffic_corroboration": { "match": true, "details": "High congestion detected" },
      "status": "pending",
      "created_at": "2026-04-03T11:00:00Z"
    }
  ]
}
```

---

## 6. Design Guidelines

- **Theme:** Dark mode (already set up in layout)
- **Cards:** `bg-slate-900 border border-slate-800 rounded-xl p-6 mb-4`
- **Table rows:** `border-b border-slate-800/50 hover:bg-slate-800/30` transition
- **Status badges:** Rounded-full, small text, colored bg
- **Buttons:**
  - Approve: `bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2.5 rounded-lg`
  - Reject: `bg-red-600 hover:bg-red-500 text-white px-6 py-2.5 rounded-lg`
- **Loading:** Use a pulsing skeleton or simple spinner
- **Animations:** Add `transition-all duration-300` on cards for smooth remove after approve/reject

---

## 7. Important Notes

1. **Photo URLs:** The backend serves photos at `http://localhost:8000/uploads/photos/{filename}`. Use `API_BASE + photo_url` for the image `src`.

2. **Spam score thresholds:**
   - `< 30` → Green (low risk, likely legitimate)
   - `30–69` → Yellow (needs review)
   - `≥ 70` → Red (auto-rejected by system)

3. **Response field names** may vary slightly from the types — inspect the actual API response and adapt. Common pattern:
   - Backend uses `snake_case` (e.g., `fraud_score`, `payout_amount`)
   - You may need to map these in your component

4. **Coordinate with Pankaj** on the types file — if his types don't match backend response, adapt locally.

---

## 8. Demo Responsibility

You own **[1:45–1:55]** of the demo video:

> **Visual:** Admin dashboard — Manual Claims page  
> **Action 1:** Admin sees claim queue with spam scores  
> **Action 2:** View evidence — photo + geo-validation (✅) + weather (✅)  
> **Action 3:** Click "Approve" → payout triggered  
> **Voiceover:** "Corroborated claims are fast-tracked..."

**Make sure:**
- At least 1 manual claim is visible with real data
- Validate sections show green checkmarks
- Approve button works and claim disappears from list
- The whole flow looks smooth and instant

---

## 9. Acceptance Criteria

- [ ] Auto Claims page shows real claims from backend
- [ ] Claims table has working status filters
- [ ] Manual Claims page shows pending claims sorted by spam score
- [ ] Each manual claim card shows: description, photo, geo-validation, weather, traffic
- [ ] Approve button works — calls API → removes claim from list
- [ ] Reject button works — shows reason input → calls API → removes claim
- [ ] Spam score badges are color-coded correctly
- [ ] Loading states on both pages
- [ ] Error handling with user-friendly messages
- [ ] No TypeScript errors
- [ ] UI matches dark theme design system
