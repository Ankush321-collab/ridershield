# TASK-6: Admin Dashboard — Pankaj (Lead)

**Owner:** Pankaj  
**Module:** Admin Dashboard — Core Architecture + Overview + Triggers  
**Priority:** P0 (Demo-critical — [0:45–1:15] + [1:55–2:00])  
**Deadline:** Today (April 3, 2026)

---

## 1. Your Scope

You handle the **core dashboard architecture** and the **most demo-critical pages**. Charmi handles Claims pages.

| Page | Owner | Status |
|------|-------|--------|
| **Layout + Sidebar** | Pankaj | Scaffolded — needs polish + active nav state |
| **Overview (/)** | Pankaj | Stubbed — needs real API data |
| **Triggers (/triggers)** | Pankaj | Stubbed — needs inject + live status |
| Auto Claims (/claims) | Charmi | Stubbed |
| Manual Claims (/manual-claims) | Charmi | Stubbed |

---

## 2. Tech Stack

- **Framework:** Next.js 16 + React 19 + TypeScript
- **Styling:** Tailwind CSS v4
- **API Client:** `src/lib/api.ts` (`adminApi` — already created)
- **Backend:** `http://localhost:8000` (FastAPI)

---

## 3. Tasks Checklist

### 3.1 Core Architecture (Do First — Charmi depends on this)

- [ ] **Create shared types file** `src/lib/types.ts`
  ```typescript
  export interface Claim {
    id: string;
    rider_id: string;
    rider_name?: string;
    claim_type: 'auto' | 'manual';
    trigger_type: string;
    income_loss: number;
    payout_amount: number;
    fraud_score: number;
    status: 'pending' | 'approved' | 'rejected' | 'paid';
    created_at: string;
  }

  export interface ManualClaim extends Claim {
    description: string;
    photo_url: string;
    spam_score: number;
    geo_validation: { match: boolean; distance_m: number };
    weather_corroboration: { match: boolean; details: string };
    traffic_corroboration: { match: boolean; details: string };
  }

  export interface TriggerStatus {
    trigger_type: string;
    zone: string;
    severity: string;
    active: boolean;
    started_at: string;
    details: Record<string, any>;
  }

  export interface DashboardStats {
    total_claims: number;
    pending_review: number;
    active_triggers: number;
    loss_ratio: number;
  }
  ```

- [ ] **Add `use client` directive** to all pages that use `useState`/`useEffect` (Next.js App Router requirement)

- [ ] **Update `src/lib/api.ts`** — add missing endpoints:
  ```typescript
  // Add to AdminApiClient:
  stats = {
    overview: () => this.request<DashboardStats>('GET', '/api/admin/dashboard'),
  };
  
  // Add to triggers:
  triggers = {
    getStatus: () => this.request<any>('GET', '/api/triggers/status'),
    getDisruptionEvents: (zone?: string) => {
      const params = zone ? `?zone=${zone}` : '';
      return this.request<any>('GET', `/api/triggers/disruption-events${params}`);
    },
    inject: (data: { trigger_type: string; zone: string; rainfall_mm?: number; duration_seconds?: number }) =>
      this.request<any>('POST', '/api/triggers/inject', data),
  };
  ```

- [ ] **Polish sidebar layout** (`src/app/layout.tsx`):
  - Add active nav state highlighting (use `usePathname()`)
  - Add "Zylo" logo/branding
  - Add system status indicator (green/red dot from `/health`)
  - Make sidebar responsive

---

### 3.2 Overview Page (`src/app/page.tsx`) — DEMO CRITICAL

Replace static values with real API data:

- [ ] Fetch real stats on page load:
  - **Total Claims:** `GET /api/admin/claims` → count
  - **Pending Review:** `GET /api/admin/claims/manual?sort=spam_score&order=asc` → filter status=pending → count
  - **Active Triggers:** `GET /api/triggers/status` → count active
  - **Loss Ratio:** Calculate from claims data or add a backend endpoint

- [ ] **Stats Grid Cards** (4 cards — already designed):
  - Total Claims (with trend arrow)
  - Pending Manual Claims
  - Active Triggers
  - Loss Ratio (payouts / premiums)

- [ ] **Recent Activity Feed** — show last 5 claims (auto + manual) with:
  - Rider name
  - Trigger type (emoji + label)
  - Payout amount
  - Timestamp (relative — "2 hours ago")
  - Status badge (color-coded)

- [ ] **Active Disruptions Widget** — if any triggers active, show:
  - Zone name
  - Trigger type
  - Duration
  - Affected riders count

- [ ] **Auto-refresh** every 30 seconds (`setInterval` + cleanup)

---

### 3.3 Triggers Page (`src/app/triggers/page.tsx`) — DEMO CRITICAL

This page is where you **inject disruptions during the demo** ([1:00–1:15]).

- [ ] **Demo Injection Panel** (top of page, highlighted border):
  - Zone selector dropdown (fetch from `GET /api/zones`)
  - 5 trigger type buttons:
    - 🌧️ Heavy Rain (inject with `rainfall_mm: 60`)
    - 🚗 Traffic Jam (inject with `congestion_score: 90`)
    - 🏪 Store Closed
    - 📱 Platform Down
    - 🚫 Regulatory
  - On click → call `POST /api/triggers/inject` with payload
  - Show success toast/notification
  - Show loading spinner during injection

- [ ] **Active Triggers List** (real-time from `GET /api/triggers/status`):
  - For each active trigger show:
    - Trigger type (emoji + label)
    - Zone name
    - Severity level (color-coded badge)
    - Started at (time ago)
    - Duration
  - Empty state: "No active disruptions"

- [ ] **Disruption Event History** (table):
  - Fetch from `GET /api/triggers/disruption-events`
  - Columns: Time | Zone | Trigger Type | Severity | Affected Riders | Claims Generated
  - Sort by most recent first
  - Paginate if needed

- [ ] **Auto-refresh** every 10 seconds (triggers page is real-time critical)

---

## 4. Backend API Reference

### Endpoints You'll Call

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/health` | System status |
| `GET` | `/api/zones` | Zone list for dropdowns |
| `GET` | `/api/triggers/status` | Active triggers |
| `GET` | `/api/triggers/disruption-events` | Disruption history |
| `POST` | `/api/triggers/inject` | Demo trigger injection |
| `GET` | `/api/admin/claims` | All claims list |
| `GET` | `/api/admin/claims/manual` | Manual claims queue |

### Inject Trigger Payload Examples

```json
// Heavy Rain
{ "trigger_type": "weather", "zone": "koramangala", "rainfall_mm": 60 }

// Traffic Jam  
{ "trigger_type": "traffic", "zone": "koramangala", "duration_seconds": 3600 }

// Store Closed
{ "trigger_type": "store_closure", "zone": "koramangala" }
```

---

## 5. Design Guidelines

- **Theme:** Dark mode (slate-950 bg, slate-100 text) — already set up
- **Cards:** `bg-slate-900 border border-slate-800 rounded-xl p-6`
- **Accent Colors:**
  - Sky-400 for primary values
  - Emerald-400 for success/positive
  - Amber-400 for warnings/pending
  - Red-400 for alerts/negative
- **Font Sizes:** h1=3xl bold, h2=lg bold, body=sm
- **Transitions:** Add `transition-colors` to interactive elements
- **Loading States:** Show skeleton/spinner during API fetches
- **Error States:** Show toast or inline error with retry option

---

## 6. Coordination with Charmi

- **You provide:** Types (`src/lib/types.ts`), updated API client, polished layout
- **She needs:** Your types file and API client updates before she starts wiring claims pages
- **Shared:** Both of you use `adminApi` from `src/lib/api.ts`
- **Do first:** Create types file + update API client → tell Charmi it's ready

---

## 7. Demo Responsibility

You own these demo segments on the dashboard:

| Time | Segment | What Judges See |
|------|---------|-----------------|
| **[1:00–1:15]** | Trigger injection | Click "Heavy Rain" on triggers page → system detects disruption |
| **[1:55–2:00]** | Overview metrics | Dashboard shows updated stats after claims processed |

**Make the injection feel dramatic** — add a brief animation/pulse effect when trigger fires.

---

## 8. Acceptance Criteria

- [ ] Overview page shows real stats from backend
- [ ] Overview auto-refreshes every 30s
- [ ] Trigger injection works — click button → disruption fires → claims auto-generated
- [ ] Trigger page shows active disruptions in real-time
- [ ] Disruption history table populated
- [ ] Sidebar has active nav state
- [ ] All pages have loading states (no blank screens)
- [ ] All pages have error handling
- [ ] No TypeScript errors
- [ ] UI matches dark theme design system
