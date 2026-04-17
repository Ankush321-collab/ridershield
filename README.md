# Zylo — Parametric Income Protection for Q-Commerce Riders

> **Automatic income protection for delivery riders.**  
> When rain, gridlock, GPS glitches, or platform failures kill your earnings —  
> Zylo detects it and pays you. No claims. No paperwork. No waiting.  
> And when a disruption slips through undetected, riders can submit a geo-tagged manual claim —
> evaluated against real weather, traffic, and location data in minutes, not weeks.

---
![alt text](system-design.png)

## Table of Contents

1. [Problem Statement](#1-problem-statement)  
2. [Persona & Scenarios](#2-persona--scenarios)  
3. [Application Workflow](#3-application-workflow)  
4. [Weekly Premium Model](#4-weekly-premium-model)  
5. [Parametric Triggers](#5-parametric-triggers)  
   - 5.4 [Manual Claim Request (Fallback)](#54-manual-claim-request-fallback-for-undetected-disruptions)  
6. [Platform Choice — Mobile-First PWA](#6-platform-choice--mobile-first-pwa)  
7. [AI/ML Integration](#7-aiml-integration)  
8. [System Architecture](#8-system-architecture)  
9. [Tech Stack](#9-tech-stack)  
10. [Platform Data Simulation](#10-platform-data-simulation)  
11. [Development Plan](#11-development-plan)  
12. [Phase 2 — What's Built](#12-phase-2--whats-built)  
13. [Adversarial Defense & Anti-Spoofing Strategy](#13-adversarial-defense--anti-spoofing-strategy)  
14. [Regulatory Compliance & Insurance Sense](#regulatory-compliance--insurance-sense)  

---

## 1. Problem Statement

India's quick-commerce sector (~$11.5B, growing rapidly) runs on an invisible workforce of
delivery partners operating for Blinkit, Zepto, and Swiggy Instamart. These riders:

- Earn **₹15,000–₹25,000/month**, entirely per-delivery — no fixed salary, no employer safety net.
- Lose **20–30% of monthly income** to external disruptions completely outside their control.
- Operate in hyper-local 2–5 km zones around dark stores, making them acutely sensitive to
  micro-level disruptions — a flooded underpass, a GPS glitch, a store outage.
- Function on **weekly cash flow cycles**, servicing debt on phones and bikes bought to do
  the job.

Traditional indemnity insurance structurally fails here:

| Problem | Why Traditional Insurance Fails |
|---|---|
| No fixed salary | Can't underwrite a variable daily income |
| Manual claims | Riders can't wait 30 days; they need money this week |
| Asset focus | Insurance covers vehicle damage, not lost earnings |
| Proof burden | "It rained and I lost orders" is not provable to a claims adjuster |

**Parametric insurance solves all of this.** Instead of proving a loss, the system uses
measurable, objective data signals (rainfall mm, congestion index, store status) as automatic
triggers. If the data says it happened, you get paid. Period.

**Coverage scope (DEVTrails mandate strictly followed):** Income loss from external disruptions
only. Health, life, vehicle damage, and accidents are explicitly excluded.

---

## 2. Persona & Scenarios

### Primary Persona — Arjun, 24, Q-Commerce Rider, Bengaluru

- Works for Zepto from 2 dark stores in Indiranagar/Koramangala.
- Typical pattern: evening peaks (6–11 PM), weekend mornings (8–11 AM).
- Earns ~₹18,000/month. Weekly payout from Zepto every Monday.
- Operates within a 3-km radius. Income collapses if his zone, his dark store, or the
  platform has issues.
- Pain points: monsoon flooding, GPS drift in high-rises, dark store queues, sudden
  political rallies blocking his route.

---

### Scenario 1: Heavy Rain + Flooding — Rohit, Hyderabad

**Context:** Rohit averages 12 orders/hr (₹15/order). Tuesday 3–7 PM, heavy rain hits Gachibowli.

| Step | Action |
|---|---|
| 3:05 PM | OpenWeatherMap reports 52mm rainfall in Gachibowli (threshold: 40mm) |
| 3:06 PM | Trigger Service fires a disruption event for Zone: Gachibowli |
| 3:07 PM | Claims Service identifies Rohit as an insured, online rider in this zone |
| 3:08 PM | Income Estimator: Expected ₹720 (12 × 4hrs × ₹15), Actual ₹180 (3 orders/hr) |
| 3:09 PM | Fraud Service: GPS confirms Rohit is in zone ✓, peer earnings confirm disruption ✓ |
| 3:10 PM | **Payout ₹540 sent to Rohit's UPI wallet** |

Rohit gets a push notification with a full breakdown. He did nothing except stay online.

---

### Scenario 2: GPS Multipath Shadowban — Ankush, Noida

**Context:** Ankush is delivering in DLF Cyber Hub, Gurugram — a dense urban canyon of
high-rises that causes GPS multipath interference. His location drifts on the Zepto map;
the platform algorithm interprets this as route deviation and shadowbans him for 2 hours.
He loses ₹400 in that shift. Traditional insurance: useless. Zylo:

| Step | Action |
|---|---|
| System detects | Ankush's order allocation drops to 0 while peers in the same zone earn normally |
| Community Signal | Only Ankush affected → individual signal, not zone-wide |
| Platform API | "Rider active = TRUE, orders dispatched = 0 for 120 min" → trigger fires |
| Fraud check | GPS signal verified as unstable (multipath flag from telemetry), not spoofing |
| **Payout** | ₹380 credited (income gap for 2 disrupted slots) |

---

### Scenario 3: Community Signal — 45 Riders, Andheri West, Mumbai

**Context:** Sunday evening. A water main breaks, flooding 3 streets near a cluster of dark
stores. No weather API picks it up. No traffic event is logged. But:

- 82% of 45 riders in the zone report an order collapse in the same 30-minute slot.
- Community Signal Agent fires: threshold crossed (>70% of zone riders affected).
- All 45 insured riders receive individual claim calculations based on their own baselines.
- **Payouts distributed in batch — no API triggered it. The rider community was the sensor.**

---

### Scenario 4: Dark Store Outage — Priya, Delhi

**Context:** Priya's primary dark store in Rajouri Garden shuts unexpectedly (equipment
failure) from 10 AM–2 PM. No orders dispatch. 4 hours, zero income.

- Platform API: `store_status = CLOSED` → trigger fires automatically.
- Income gap: Expected ₹300 (10 orders/hr × ₹7.5/order × 4hrs), Actual ₹0.
- GPS: Priya is near the store, confirms she was working. Fraud check passes.
- **Payout: ₹300.**

---

### Scenario 5: Fraud Attempt — No Payout

**Context:** A rider stays home on a sunny, normal-traffic day and hopes for a payout.

- No parametric triggers fire for their zone.
- GPS shows they were not in the delivery zone.
- Peer riders in the same zone earned normally.
- **Result: No disruption event, no claim, no payout.** Parametric triggers cannot be
  gamed without an actual external event in the zone.

### Scenario 6: Manual Claim — Undetected Local Disruption — Ravi, Pune

**Context:** Heavy road-work near Ravi's usual zone creates a 2-hour gridlock, but it is too
localised to breach the zone-wide congestion trigger threshold.  No disruption event fires
automatically.

- Ravi opens the app, taps **"Disruption not detected? Request Manual Claim"**.
- He selects disruption type **Traffic** and writes a brief description of the road-work.
- He takes a **geo-tagged photo** of the blocked road from his location.
- The app records his GPS coordinates and the photo's EXIF timestamp, then submits both.
- The system cross-checks:
  - **Geo-tag vs telemetry:** Photo GPS matches Ravi's live app location — ✅ no mismatch.
  - **EXIF timestamp vs incident time:** Photo taken within 5 minutes of the declared incident — ✅ no anomaly.
  - **Traffic data:** Third-party traffic API confirms congestion index 72/100 at that coordinate at that time — ✅ corroborated.
  - **Weather data:** Clear sky, no weather disruption — ✅ not a weather claim.
  - **Spam score:** 0 / 100 — genuine claim.
- Claim is fast-tracked to the admin review queue with a "low fraud risk" badge.
- **Result: Manual claim approved within 4 hours; income gap credited via UPI.**

---

## 3. Application Workflow

```mermaid
flowchart TD
    A[Rider Onboards] --> B[Selects Weekly Cover] --> C[Premium Paid via UPI]
    C --> D[Policy Activated for Calendar Week]
    D --> E[Background: Data Collector polls APIs every 5 min]
    E --> F1[Weather]
    E --> F2[Traffic]
    E --> F3[Platform/Store]
    E --> F4[Others]
    F1 & F2 & F3 & F4 --> G[Trigger Service evaluates zone × slot × rider status]
    G --> H{Disruption Detected?}
    H -- Yes --> I[Disruption Event Created]
    I --> J[Claims Service: identify insured online riders in zone]
    J --> K[Income Estimator: expected vs actual earnings]
    K --> L[Fraud Service: GPS, peer comparison, behavioural checks]
    L --> M[Payout Service: instant UPI credit]
    M --> N[Push Notification to Rider + Dashboard Update]
    H -- No --> O{Rider reports disruption manually?}
    O -- No --> P[No claim — slot closes normally]
    O -- Yes --> Q[Rider submits Manual Claim + Geo-Tagged Photo]
    Q --> R[Geo-Validation: photo GPS vs rider telemetry GPS]
    R --> S[Weather & Traffic API: corroborate claimed disruption at location/time]
    S --> T[Spam Detection: EXIF timestamp, location mismatch, peer comparison]
    T --> U{Spam Score ≥ 70?}
    U -- Yes --> V[Claim Rejected — spam flagged, rider notified]
    U -- No --> W[Manual Claim queued for Admin Review]
    W --> X{Admin Decision}
    X -- Approve --> M
    X -- Reject --> Y[Claim Rejected — reason sent to rider]
```

### Rider-Facing Steps

1. **Sign Up** — Phone + KYC, link delivery platform(s), select city and zones.
2. **Weekly Setup** — Declare typical working slots. System shows risk profile per slot
   (color-coded: green → red) and suggests 3 plan tiers.
3. **Buy Cover** — One weekly premium payment via UPI/wallet. Coverage activates immediately.
4. **Work Normally** — App monitors in the background. No rider action needed.
5. **Get Paid (Auto)** — Push notification + breakdown + UPI credit if a trigger fires automatically.
6. **Manual Claim (Fallback)** — If no automatic trigger fires but the rider experienced a real
   disruption, they can tap **"Request Manual Claim"**, select the disruption type, write a brief
   description, and take a **geo-tagged photo** of the disruption from their location.  The system
   validates the photo's GPS against the rider's live location, cross-checks weather and traffic
   data, runs spam detection, and routes low-risk claims to a fast-track admin review queue.

### Rider Dashboard

- Active coverage status (slots covered, hours remaining).
- Disruption alerts in real time.
- Claim history and payout tracking with cause breakdown (weather / traffic / platform / regulatory).
- **Manual Claim button** — visible whenever no automatic disruption fired for an active slot;
  guides the rider through photo capture, disruption-type selection, and description entry.
- Manual claim status tracker (submitted → under review → approved/rejected).
- Next-week premium forecast and risk insights.

### Admin/Insurer Dashboard

- Live disruption heatmap (zone × time).
- Loss ratio: payouts vs. premiums collected.
- Fraud alert queue and review panel.
- **Manual Claim review queue** — lists pending manual claims ranked by spam score (lowest first
  for fast approval), with photo preview, geo-validation result, weather/traffic corroboration
  summary, and one-click approve / reject.
- Next-week risk projections per micro-zone.

---

## 4. Weekly Premium Model

### Why Weekly?

- Riders are paid weekly by platforms. A weekly insurance cycle is a natural fit — no
  mismatch in cash flows.
- Weekly pricing allows dynamic adjustment per season, zone risk, and forecast.
- Riders who take a week off simply don't buy cover. No wasted money.

### Micro-Slot Logic (Internal)

The product appears simple to the rider (one weekly plan, one price) but internally prices at
**30–60 minute micro-slot granularity**:

- Working time is broken into slots (e.g., 7:00–7:30 AM, 7:30–8:00 AM, …).
- For each slot we estimate:
  - **Expected earnings** under normal conditions for that rider, zone, and time.
  - **Disruption probability** — chance that external conditions push earnings below the
    guaranteed floor.
- Aggregate risk across all planned slots → weekly pure premium + admin load.

**Why this matters:** An evening-only rider in a monsoon-prone zone pays a fair price. A
morning rider in a low-disruption suburb pays less. Coverage is personalised and explainable.

### Three Plan Tiers (Rider-Facing)

| Plan | Coverage Scope | Guaranteed Earnings | Best For |
|---|---|---|---|
| **Essential** | High-risk slots only (e.g., monsoon evenings) | 70% of baseline | Budget-conscious riders |
| **Balanced** | All usual working hours | 80% of baseline | Standard weekly workers |
| **Max Protect** | Usual + optional late/early slots | 90% of baseline | Heavy-duty riders, peak season |

### Illustrative Pricing

| Zone Risk | Example | Weekly Premium |
|---|---|---|
| Low (score 0–25) | Dry-season Pune suburb | ₹20–₹35 |
| Medium (score 26–50) | Normal Hyderabad zone | ₹50–₹80 |
| High (score 51–75) | Mumbai pre-monsoon zone | ₹80–₹120 |
| Very High (76–100) | Coastal zone during cyclone season | ₹120–₹150 |

Premiums remain within a micro-insurance bracket to maximise adoption among riders
earning ₹15,000–₹25,000/month.

### Payout Calculation

```

Expected Income = avg_orders_per_hr × disrupted_hrs × ₹_per_order
Actual Income   = actual_orders × ₹_per_order
Income Loss     = Expected − Actual
Payout          = min(Income Loss, Weekly Coverage Limit)

```

Baselines are set per rider using 4-week rolling historical averages, adjusted for zone,
day-of-week, and slot time. New riders use zone-level medians until personal history builds.

---

## 5. Parametric Triggers

A parametric trigger is a measurable, objective condition that fires automatically — no
human judgment, no claim form.

### 5.1 Baseline Triggers

| Category | Trigger | Threshold | Data Source |
|---|---|---|---|
| **Weather** | Rainfall intensity | > 40mm in 1hr in rider's zone | OpenWeatherMap / IMD |
| **Weather** | Heat index | Wet-bulb temp > 32°C or air temp > 42°C | OpenWeatherMap |
| **Air Quality** | AQI breach | > 300 (hazardous) or GRAP Stage 3/4 active | OpenAQ / CPCB |
| **Traffic** | Congestion index | > 80/100 sustained for 60+ min | Google Maps / TomTom |
| **Traffic** | Road closure | `road_blocked = TRUE` near dark store | Traffic APIs |
| **Store** | Dark store closed | `store_status = CLOSED` | Platform API (simulated) |
| **Store** | Inventory stockout | `stock_level = CRITICAL` | Platform API (simulated) |
| **Platform** | App / API outage | `platform_status = DOWN` in zone | Platform status API |
| **Regulatory** | Curfew / ban | `curfew_active = TRUE` | News feed / govt portal |
| **Community Signal** | Mass order collapse | > 70% riders in zone see simultaneous drop | Internal rider data |

### 5.2 Out-of-the-Box Triggers (Our Differentiators)

These cover uniquely Indian urban frictions no competitor insures:

| Trigger | Mechanism |
|---|---|
| **Urban Canyon GPS Multipath** | High-rises cause GPS drift → platform shadowbans rider. Detected via order-allocation anomaly + telemetry instability flags. |
| **Unpaid Dark Store Wait Time** | Chronic pickup queues due to inventory or billing issues. Triggered when dispatch delay > 5 min SLA across multiple riders at same store. |
| **Gated Community / RWA Frictions** | Elevator bans, MyGate delays, late-night entry curfews. Detected via delivery time anomaly + geo-fence status. |
| **VIP Convoy / Spontaneous Civic Events** | Sudden arterial blockades trapping entire local fleets. Detected via speed-anomaly and traffic graph propagation. |
| **Algorithmic Visibility Shock** | Platform A/B tests or throttling suddenly reduce order allocation. Detected via peer-comparison ratio (rider orders vs zone orders). |
| **GRAP-mandated vehicle bans** | Government mandates barring specific vehicle classes in high-AQI conditions. Linked to official GRAP stage APIs. |
| **Warehouse / Supply Chain Cascade** | Upstream warehouse failure causing simultaneous multi-store stockouts. Detected via synchronized `no-slots` across dependent stores. |

### 5.3 Trigger Decision Logic

A claim is auto-initiated only when **all three conditions are met**:

1. A configured trigger condition is TRUE for the rider's zone and time slot.
2. The rider's GPS / platform status confirms they were **online and in-zone**.
3. Actual earnings fall **below the model-predicted baseline band** for those conditions.

Multiple simultaneous triggers (rain + traffic + store outage) count as **one disruption event**
— no double-payouts per slot.

> **When none of the above conditions are met** but the rider believes they experienced a genuine
> disruption, they can initiate a rider-led **Manual Claim** — see [Section 5.4](#54-manual-claim-request-fallback-for-undetected-disruptions) below.

---

### 5.4 Manual Claim Request (Fallback for Undetected Disruptions)

When the automatic trigger system does **not** fire — either because the disruption is too
localised, too brief, or falls below the zone-wide threshold — a rider on an active policy can
request a manual claim.

#### How it works

1. **Rider taps "Request Manual Claim"** in the app during or immediately after the disruption
   window.
2. **Selects disruption type:** Weather / Traffic / Store Closed / Platform Issue / Other.
3. **Writes a brief description** (minimum 10 characters) explaining what happened.
4. **Takes a geo-tagged photo** of the disruption (flooded road, blocked route, closed store
   shutter, etc.).  The mobile app embeds the device GPS coordinates and timestamp in the photo's
   EXIF metadata and also records them independently from the device location service.

#### Evidence evaluation

The system automatically evaluates four dimensions of the submitted evidence:

| Check | What is verified | Positive outcome |
|---|---|---|
| **Weather corroboration** | Historical weather API (OpenWeatherMap / IMD) queried for the photo's GPS coordinates and EXIF timestamp | Rainfall > 7.6 mm/hr or wind > 40 km/h confirms a weather claim |
| **Traffic corroboration** | Traffic API (Google Maps / TomTom) queried for the same location and time window | Congestion index ≥ 70/100 confirms a traffic claim |
| **Known disruption match** | System checks if a `DisruptionEvent` record already exists for that zone and time slot | Existing event corroborates the claim and reduces spam score |
| **Delivery partner narrative** | Rider's free-text description is stored and shown to the reviewer alongside weather and traffic data for holistic judgment | Supports manual review |

#### Spam / fraud detection for manual claims

Manual claims carry a higher fraud risk than automatic parametric payouts, so the system runs a
dedicated spam-detection pipeline on top of the standard fraud checks:

| Signal | How it is detected | Weight |
|---|---|---|
| **Location mismatch** | Photo's GPS (from EXIF or device) compared to rider's live telemetry GPS at the same timestamp.  Distance > 500 m → flagged. | High |
| **Time anomaly** | Photo EXIF timestamp compared to the declared incident time.  Difference > 30 min → flagged. | Medium |
| **Weather mismatch** | Rider claims weather disruption but weather API shows benign conditions at that location / time. | Medium |
| **Traffic mismatch** | Rider claims traffic disruption but traffic API shows low congestion at that location / time. | Medium |
| **Known disruption (corroborating)** | A matching `DisruptionEvent` exists in the DB — **reduces** spam score. | Negative (supports claim) |

A composite **spam score (0–100)** is computed from these signals.  Claims scoring **≥ 70** are
auto-rejected as spam; claims scoring **< 70** are routed to the admin review queue, sorted by
ascending spam score so the lowest-risk claims are reviewed first.

#### Manual claim API endpoints

```
POST  /api/claims/manual              # Rider submits manual claim + geo-tagged photo
GET   /api/claims/manual/{claim_id}   # Rider checks their claim status
GET   /api/admin/claims/manual        # Admin queue — pending manual claims, sorted by spam score
POST  /api/admin/claims/{claim_id}/approve   # Admin approves → triggers payout
POST  /api/admin/claims/{claim_id}/reject    # Admin rejects → rider notified with reason
```

---

## 6. Platform Choice — Mobile-First PWA

**We chose a Mobile-First Progressive Web App (PWA)** for Phase 1.

| Factor | Decision |
|---|---|
| **Rider behaviour** | Riders manage their entire livelihood via smartphone, between trips, at dark-store queues. Desktop is irrelevant. |
| **Avoiding app overload** | Riders already run delivery apps, maps, and payment apps. A heavy native install adds friction. A PWA installs from browser and sits on the home screen. |
| **Cross-platform coverage** | Same React Native / Next.js codebase works on Android and iOS without separate builds. |
| **Iteration speed** | PWA enables push-to-prod without app store review cycles. |
| **Backend-heavy product** | Most intelligence (triggers, ML, payouts) lives server-side. Native sensors are not critical for Phase 1. |

**Future (Phase 3+):** A native app layer or a **Guidewire Jutro Digital Platform**
integration for deeper sensor access, background telemetry, and enterprise-grade insurer UI.

---

## 7. AI/ML Integration

Our AI strategy is **honest and phased** — practical models now, advanced architectures on
a clear roadmap.

### 7.1 v1 Models (Hackathon Deliverable)

#### A. Spatio-Temporal Risk Model (Premium Calculation)

**Goal:** Predict per-slot expected earnings and disruption probability per rider.

**Inputs per micro-slot:**
- Historical earnings for that rider × zone × day × time (rolling 4 weeks).
- Zone-level weather, AQI, congestion forecast.
- Events/regulatory calendar.
- Platform signals: surge multiplier, store health, competitor rider density.
- Rider profile: tenure, rating, slot consistency.

**Model:** LightGBM / Gradient Boosting with time-of-week features.

**Outputs:**
- Expected earnings distribution for each slot.
- Disruption probability (earnings drop below threshold).
- Weekly premium suggestion per rider.

**Explainability:** "Your premium is higher this week because Thursday 7–9 PM in Zone 13
has a 65% flood probability based on monsoon forecast."

---

#### B. Parametric Trigger Calibration

**Problem:** Hard-coded thresholds (e.g., "rain > 40mm") are arbitrary and wrong for all cities.

**Solution:** Quantile regression / reliability curves trained on historical disruption data:
- Learn which *combinations* of signals correlate with severe earnings drops.
- Derive zone-specific, season-specific adaptive thresholds.
- Update as new claims data arrives — thresholds improve continuously.

---

#### C. Fraud Detection (Multi-Layer)

| Layer | Technique | What it catches |
|---|---|---|
| **Geo-consistency** | Cross-check GPS, network location, platform trip logs | Spoofing, impossible teleportation between zones |
| **Behavioural anomaly** | Isolation Forest over online/offline patterns | Riders who only go "online" during known disruption windows |
| **Peer comparison** | Counterfactual income estimator — compare to similar riders in same zone/slot | Outsized claims when peers earned normally |
| **Graph / collusion** | Network graph linking riders, devices, payout accounts | Clusters that always claim together in the same micro-zone |
| **Geo-tagged photo validation** *(manual claims only)* | Compare photo EXIF GPS + timestamp against rider telemetry; cross-check weather/traffic APIs for claimed location/time; composite spam score 0–100 | Location spoofing, backdated photos, false disruption descriptions in manual claims |

Fraud engine runs **before** every payout. Suspicious claims are flagged for review; clear
cases are rejected automatically with a logged reason.

---

### 7.2 Advanced Roadmap (Conceptual Differentiators)

Explicitly marked as future phases — these are our north star, not our hackathon demo.

| Model | Purpose | Why Advanced |
|---|---|---|
| **Offline Deep RL (Conservative Q-Learning)** | Weekly premium optimization as a sequential decision problem — balances rider affordability vs portfolio loss ratio | Requires extensive historical policy data; avoids live trial-and-error on vulnerable users |
| **Physics-Informed Graph Neural Network (PI-GNN)** | Disruption Knowledge Graph (zones, roads, stores, events, payment rails as nodes; causal edges) — propagation model predicts second-order impacts | Requires graph DB, historical propagation data, significant training |
| **Causal AI / Anomaly Transformer** | Mathematically proves causal link between external shock and wallet-level income drop using cohort telemetry | High data requirements; research-grade fraud detection |

These models represent a credible, investor-grade roadmap even if not fully shipped in the hackathon.

---

### 7.3 AI Data Flow

```mermaid
flowchart TD
    A[External APIs] --> B[Kafka]
    B --> C[Feature Store: Redis + TimescaleDB]
    C --> D[Risk Model: LightGBM]
    D --> E[Premium per slot]
    E --> F[Policy Service]
    D --> G[Trigger Service]
    G --> H[Disruption Event]
    H --> I[Income Estimator]
    I --> J[Claim Gap Calculation]
    J --> K[Fraud Model: Isolation Forest + Rules]
    K --> L[Approve / Flag / Reject]
    L --> M[Payout Service]
    M --> N[UPI Credit]
    O[Rider: Manual Claim + Geo-Tagged Photo] --> P[Geo-Validation Service]
    P --> Q[Weather & Traffic APIs: corroborate at location/time]
    Q --> R[Spam Score Calculator: location mismatch + time anomaly + data cross-check]
    R --> S{Spam Score ≥ 70?}
    S -- Yes --> T[Auto-Reject: spam flagged]
    S -- No --> U[Admin Review Queue]
    U --> V{Admin Decision}
    V -- Approve --> M
    V -- Reject --> W[Rider notified with reason]
```

---

## 8. System Architecture

```mermaid
graph TB
    subgraph RiderApp["RIDER MOBILE APP (PWA)"]
        App["Onboarding | Slot Selection | Policy | Dashboard | Alerts | Manual Claim + Photo"]
    end

    subgraph APIGateway["API GATEWAY (FastAPI)"]
        Svc1["Rider Service | Policy Service | Claims Service | Manual Claims Service | Payout Svc"]
        Svc2["Risk Service | Fraud Service | Trigger Service | Geo-Validation Service"]
    end

    subgraph DataML["Data & ML Layer"]
        PG[(PostgreSQL - Core Data)]
        Kafka["Kafka Events / Time-Series DB"]
        ML["ML Service (FastAPI) - Risk Model | Fraud Model | Spam Score"]
        FS[(File Storage - Geo-Tagged Photos)]
    end

    subgraph Collector["DATA COLLECTOR"]
        Ext["Weather | Traffic | Platform | Payments | Events | Community Sig"]
    end

    RiderApp -->|HTTPS / REST| APIGateway
    RiderApp -->|Photo Upload| FS
    APIGateway --> PG
    APIGateway --> Kafka
    APIGateway --> ML
    APIGateway --> FS
    Kafka --> Collector
```

### Core Domain Entities

- **Rider** — profile, zones, platform links, KYC status.
- **MicroSlot** — 30-min window with risk score and expected earnings.
- **Policy** — weekly coverage plan, active dates, premium paid.
- **DisruptionEvent** — zone × slot, trigger type, severity.
- **Claim** — rider × disruption, income gap, fraud status, payout amount.
- **ManualClaim** — rider-initiated claim with disruption type, description, incident coordinates,
  evaluated weather/traffic data, spam score, and review status.
- **GeoTaggedPhoto** — evidence photo for a manual claim; stores the file reference, EXIF GPS
  coordinates + timestamp, app-reported GPS coordinates, and the computed distance between them.
- **Payout** — payment record, UPI reference, status.

---

## 9. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Mobile App** | React Native + Expo | Cross-platform iOS/Android, PWA behaviour, fast prototyping |
| **Admin Dashboard** | Next.js + TypeScript + Tailwind | SSR for data tables, rapid UI, type safety |
| **API Layer** | FastAPI (Python) | Async, auto-docs, native ML model serving |
| **ML/AI** | Python, Pandas, LightGBM, scikit-learn, PyTorch | v1 models + RL/GNN roadmap |
| **Primary DB** | PostgreSQL 15 | Relational core: riders, policies, claims, payouts |
| **Time-Series** | TimescaleDB / Redis | High-frequency external signal storage and caching |
| **Event Streaming** | Apache Kafka | Decouples ingestion from trigger evaluation |
| **Push Notifications** | Firebase Cloud Messaging | Real-time rider alerts on disruptions/payouts |
| **Payments** | Razorpay test mode / UPI simulator | India-native; simulated instant payout |
| **Weather** | OpenWeatherMap + IMD | Free tier, India coverage, rainfall/AQI/temp |
| **Traffic** | Google Maps / TomTom Traffic API | Real congestion data; fallback to mocks |
| **Platform Data** | Simulated / Mocked APIs | Dark store status, order volume — simulated for prototype |
| **File Storage** | Local FS (dev) / AWS S3 (prod) | Geo-tagged photo evidence for manual claims; EXIF parsed via Pillow |
| **Infra** | Docker + Docker Compose | One-command local deploy for demo and judges |

**Guidewire Integration Path (Future):**
- PolicyCenter (APD) for policy lifecycle management.
- ClaimCenter for zero-touch claim initiation (automatic triggers) and manual claim adjudication via App Events / Webhooks.
- Jutro Digital Platform for enterprise mobile UI.
- Integration Gateway for external API orchestration.

---

## 10. Platform Data Simulation

Real-time access to delivery platform APIs (Zepto, Blinkit, Swiggy Instamart) is not
available for a prototype. This section documents exactly how the platform data layer is
simulated, what it produces, how realistic the output is, and how it plugs into the live
system workflow.

---

### 10.1 Why Simulation Is Necessary

Delivery platforms do not expose public APIs for per-rider order data, store health, or
earnings streams. Production integrations would require formal B2B partnerships, NDA-bound
data-sharing agreements, and sandboxed API credentials — none of which are feasible for a
hackathon prototype. The simulation layer provides a **functionally identical interface**:
the rest of the system consumes simulated platform events through the same contract it would
use with a real API, making the substitution transparent to every downstream service.

---

### 10.2 Simulated Parameters

The simulation covers all platform signals that the Trigger Service and Claims Service
require to operate end-to-end.

#### Rider & Order Signals

| Parameter | Description | Simulated Range / Values |
|---|---|---|
| `orders_per_hour` | Number of orders dispatched to the rider in the current slot | 0–18 orders/hr (zone- and time-dependent) |
| `order_rate_drop_pct` | Percentage fall in order rate vs. the rider's rolling 4-week average | 0–100 % |
| `rider_status` | Whether the delivery app reports the rider as online | `ONLINE` / `OFFLINE` |
| `orders_dispatched` | Running count of orders the platform sent to the rider this shift | Integer ≥ 0 |
| `orders_accepted` | Orders the rider accepted | Integer ≤ `orders_dispatched` |
| `orders_declined` | Orders declined (used to detect algorithmic suppression) | Integer ≥ 0 |
| `dispatch_latency_sec` | Time (seconds) between store ready and dispatch notification | 30–600 s (normal 60–90 s) |
| `active_navigation_events` | Count of in-app navigation events (proxy for genuine trip activity) | Integer ≥ 0 |

#### Earnings Signals

| Parameter | Description | Simulated Range / Values |
|---|---|---|
| `earnings_current_slot` | Rupee earnings in the current 30-min micro-slot | ₹0–₹300 |
| `earnings_rolling_baseline` | Rider's 4-week average earnings for the same slot type | ₹80–₹250 (seeded from persona profile) |
| `earnings_per_order` | Per-order payout including distance incentive | ₹12–₹35 |
| `surge_multiplier` | Platform surge factor active in the zone at this moment | 1.0–2.5× |
| `weekly_earnings_to_date` | Cumulative earnings so far in the active policy week | ₹0–₹4,500 |

#### Store & Inventory Signals

| Parameter | Description | Simulated Values |
|---|---|---|
| `store_status` | Operational state of the rider's primary dark store | `OPEN` / `CLOSED` / `DEGRADED` |
| `store_order_throughput` | Orders processed per hour at the store | 0–200 orders/hr |
| `stock_level` | Aggregate inventory health of the store | `NORMAL` / `LOW` / `CRITICAL` |
| `pickup_queue_depth` | Number of riders currently waiting at the store for their order | 0–25 riders |
| `avg_pickup_wait_sec` | Average time (seconds) riders are waiting at the pickup counter | 30–900 s (SLA threshold: 300 s) |
| `store_outage_reason` | Human-readable reason when `store_status = CLOSED` | `EQUIPMENT_FAILURE` / `POWER_CUT` / `MAINTENANCE` / `FLOOD` |

#### Platform Health Signals

| Parameter | Description | Simulated Values |
|---|---|---|
| `platform_status` | Whether the platform's own backend is reachable | `UP` / `DEGRADED` / `DOWN` |
| `api_error_rate_pct` | Percentage of API calls returning errors in this zone | 0–100 % |
| `shadowban_active` | Flag indicating the platform has suppressed the rider's visibility | `true` / `false` |
| `shadowban_duration_min` | Minutes the rider has been in suppressed state | 0–240 min |
| `allocation_anomaly` | Flag set when rider's allocation is ≥ 40 % below the zone median | `true` / `false` |

---

### 10.3 Simulation Approach

#### Architecture

The simulation is implemented as a **`PlatformSimulator` module** inside the
`backend/integrations/platform_simulator.py` file. It exposes the same interface as the
real platform integration adapter, so the Data Collector calls it identically whether
talking to a live API or a simulator.

```
Data Collector (polls every 5 min)
  └─► PlatformSimulator.get_rider_snapshot(rider_id, zone_id, slot_ts)
        └─► Returns: PlatformSnapshot (all parameters above, as a typed Pydantic model)
```

#### Statistical Model

Simulated values are not random noise — they are drawn from **parameterised statistical
distributions anchored to published Q-commerce benchmarks**:

| Aspect | Approach |
|---|---|
| **Baseline order rates** | Normal distribution μ = 10 orders/hr, σ = 2.5, clipped to [0, 18]. Mean adjusted per time-of-day profile (see table below). |
| **Earnings per order** | Log-normal distribution with μ = ₹18, σ = ₹5 (matches reported Zepto/Blinkit incentive structures). |
| **Store status transitions** | Markov chain: `OPEN → DEGRADED` (p = 0.02/hr), `DEGRADED → CLOSED` (p = 0.15/hr), `CLOSED → OPEN` (p = 0.30/hr). |
| **Dispatch latency** | Gamma distribution (k = 2, θ = 45 s) with a heavy tail to simulate queue spikes. |
| **Pickup queue depth** | Poisson(λ = 4) during normal hours; λ scales to 12 during inventory-stockout injection. |
| **Surge multiplier** | Discrete: 1.0× (70 %), 1.25× (15 %), 1.5× (10 %), 2.0× (4 %), 2.5× (1 %). |

#### Time-of-Day Demand Profile

Order rates are modulated by a deterministic demand curve that reflects real Q-commerce
traffic patterns in Indian metros:

| Time Window | Demand Multiplier | Typical `orders_per_hour` |
|---|---|---|
| 06:00–08:30 | 0.5× | 4–6 |
| 08:30–11:00 | 0.9× | 8–10 |
| 11:00–14:00 | 1.1× | 9–12 |
| 14:00–17:00 | 0.6× | 4–7 |
| 17:00–20:00 | 1.4× | 12–16 |
| 20:00–22:30 | 1.2× | 10–14 |
| 22:30–06:00 | 0.3× | 0–4 |

#### Disruption Injection

The simulator accepts an optional **`DisruptionScenario`** object that overrides the
baseline distributions to reproduce a named disruption type. This is how demo scenarios
(Sections 2.1–2.4) are triggered deterministically:

| Scenario Key | What Changes |
|---|---|
| `HEAVY_RAIN` | `orders_per_hour` drops to 20–35 % of baseline; `rider_status` may flip `OFFLINE` for 10 % of riders; `store_order_throughput` falls 40 %. |
| `STORE_CLOSURE` | `store_status = CLOSED`; `orders_dispatched = 0`; `stock_level = CRITICAL` for adjacent stores. |
| `PLATFORM_OUTAGE` | `platform_status = DOWN`; `api_error_rate_pct = 95–100 %`; all `orders_dispatched = 0`. |
| `GPS_SHADOWBAN` | `shadowban_active = true`; `shadowban_duration_min` ramps from 0 to 120; rider's `orders_per_hour` → 0 while zone peers remain at baseline. |
| `DARK_STORE_QUEUE` | `pickup_queue_depth` spikes to 15–25; `avg_pickup_wait_sec` exceeds 300 s SLA. |
| `ALGORITHMIC_SHOCK` | `allocation_anomaly = true`; rider's `order_rate_drop_pct` = 50–70 % while zone median is unchanged. |

#### Reproducibility & Seeding

The simulator uses a **deterministic seed** derived from `(rider_id, zone_id, iso_week)`
so that repeated test runs produce identical results. Integration tests fix the seed
explicitly; the live demo uses a rotating daily seed to generate fresh-looking data each day.

---

### 10.4 Realism Assessment

| Dimension | Realism Level | Notes |
|---|---|---|
| **Order rate magnitudes** | ✅ High | Derived from publicly reported Zepto/Blinkit rider earnings of ₹15,000–₹25,000/month back-calculated to hourly order rates. |
| **Earnings per order** | ✅ High | Matches ₹12–₹35 range reported in rider forums and investigative journalism (2023–2025). |
| **Time-of-day demand shape** | ✅ High | Demand curve modelled on publicly reported Q-commerce peak-hour patterns (dinner rush 6–9 PM, lunch 12–2 PM). |
| **Store status transitions** | ✅ Moderate–High | Markov transition probabilities calibrated to anecdotal dark-store outage frequency (1–2 closures/week per store). |
| **Surge multiplier distribution** | ✅ Moderate | Discrete distribution matches approximate Blinkit/Zepto surge structures; exact weights are estimates. |
| **Dispatch latency distribution** | ✅ Moderate | Gamma shape captures right-skew (occasional long waits); exact parameters are estimated from rider reports. |
| **GPS multipath / shadowban mechanics** | ⚠️ Approximated | Shadowban duration and allocation-drop magnitude are plausible estimates — no published ground truth for these events. |
| **Cross-rider peer comparison signals** | ✅ High | Generated by running the simulator independently for each rider in the zone and comparing outputs — structurally identical to how real peer signals would work. |
| **Platform API error patterns** | ⚠️ Approximated | Error rate during outages set to 95–100 %; real platform partial-failure patterns are more complex. |

**Bottom line:** The simulation is calibrated to be accurate enough to validate the trigger
logic, income estimation, and fraud detection algorithms. It is **not** a substitute for
real platform data for actuary-grade pricing — that requires a production pilot with a
platform partner.

---

### 10.5 Integration into the System Workflow

The simulated platform layer is a **drop-in replacement** for the real platform API adapter.
It participates in the full data pipeline without any special handling by downstream services:

```mermaid
flowchart TD
    A[Data Collector — polls every 5 min] --> B{Platform API available?}
    B -- Yes (production) --> C[Real Platform REST API\nZepto / Blinkit / Swiggy Instamart]
    B -- No (prototype / test) --> D[PlatformSimulator\nbackend/integrations/platform_simulator.py]
    C --> E[PlatformSnapshot: Pydantic model]
    D --> E
    E --> F[Kafka topic: platform.snapshots]
    F --> G[Trigger Service\nevaluates store_status, platform_status,\nallocation_anomaly, shadowban_active]
    F --> H[Feature Store: Redis + TimescaleDB\nstores earnings, order rates, surge multiplier]
    G --> I{Trigger condition met?}
    I -- Yes --> J[DisruptionEvent created]
    J --> K[Claims Service\nidentifies insured online riders in zone]
    K --> L[Income Estimator\nearnings_rolling_baseline vs earnings_current_slot]
    L --> M[Fraud Service\nGPS · peer comparison · platform trip logs]
    M --> N[Payout Service → UPI credit]
    H --> L
```

**Key integration points:**

| Service | How It Uses Platform Data |
|---|---|
| **Trigger Service** | Reads `store_status`, `platform_status`, `allocation_anomaly`, `shadowban_active`, and `api_error_rate_pct` from the Kafka topic to evaluate store-closure, outage, and algorithmic-shock triggers. |
| **Income Estimator** | Reads `earnings_current_slot`, `earnings_rolling_baseline`, `earnings_per_order`, and `surge_multiplier` from the Feature Store to calculate the income gap for payout. |
| **Community Signal Agent** | Aggregates `order_rate_drop_pct` across all zone riders to detect mass order collapses (> 70 % drop triggers community signal). |
| **Fraud Service** | Cross-references `active_navigation_events` and `orders_dispatched` with GPS telemetry to confirm the rider was genuinely active — a spoofer's delivery app shows no trip events. |
| **Dark Store Queue Trigger** | Reads `pickup_queue_depth` and `avg_pickup_wait_sec` to detect chronic unpaid wait-time disruptions (SLA breach when wait > 300 s across ≥ 3 riders at the same store). |

**Switching to a real API in production** requires only replacing the `PlatformSimulator`
with a real `PlatformAPIAdapter` that implements the same `get_rider_snapshot()` interface.
Every service above continues to work unchanged — the data contract (the `PlatformSnapshot`
Pydantic model) remains identical.

---

## 11. Development Plan

### Phase 1 — Foundation ✅

**Goal:** Working skeleton — riders onboard, buy policies, data flows in.

| Deliverable | Status | Details |
|---|---|---|
| Rider onboarding + KYC flow | ✅ Done | Name, phone, platform, zone, slot preferences |
| Policy service | ✅ Done | Weekly plan selection, premium calculation (rule-based v0), UPI mock payment |
| Weather data pipeline | ✅ Done | OpenWeatherMap polling every 5 min into TimescaleDB |
| Basic trigger rules | ✅ Done | Rain > threshold, congestion > threshold — rule-based, no ML yet |
| Database schema | ✅ Done | Riders, zones, micro-slots, policies, disruption events, claims |
| Mobile app shell | ✅ Done | Onboarding, plan selection, policy status view |

**Exit criterion:** ✅ Rider can sign up, buy cover, and the system ingests live weather data.

---

### Phase 2 — Automation & Protection [March 21 – April 4] (Weeks 3–4) ✅

> **Theme:** "Protect Your Worker"

**Goal:** Full zero-touch flow — disruption detected → claim → payout — working end-to-end.

#### Hackathon Deliverables

- **A 2-minute demo video** uploaded to a publicly accessible link.
- **Executable source code** showcasing:
  - **Registration Process**
  - **Insurance Policy Management**
  - **Dynamic Premium Calculation**
  - **Claims Management**

#### Implementation — Completed

| Deliverable | Status | Details |
|---|---|---|
| Registration process (polish) | ✅ Done | End-to-end onboarding: name, phone OTP, platform link, zone, slot preferences — fully functional and demo-ready (`backend/rider_service/`) |
| Insurance policy management | ✅ Done | Plan selection (Essential / Balanced / Max Protect), policy lifecycle (activate, view, renew, cancel), coverage status tracking (`backend/policy_service/`) |
| Dynamic premium engine | ✅ Done | LightGBM risk model on synthetic data, zone-level scoring, hyper-local risk factors, explainable premium per slot (`backend/premium_service/`, `backend/ml/`) |
| 9 automated triggers | ✅ Done | Heavy rain, extreme heat, congestion (sustained), dark-store closure, platform outage, regulatory curfew, GPS shadowban, dark-store queue SLA breach, algorithmic shock — Three-Factor Validation Gate ensures a payout fires only when trigger is true, rider is online, and earnings have genuinely dropped (`backend/trigger_service/`) |
| Community Signal agent | ✅ Done | Detects mass order collapse across zone riders (>70% affected) — runs inside the scheduler cycle alongside other trigger evaluations (`backend/trigger_service/scheduler.py`) |
| Claims automation | ✅ Done | Trigger → income gap calc → Isolation Forest fraud check → payout (zero-touch) (`backend/claims_service/`) |
| Manual claim submission | ✅ Done | Rider-facing "Request Manual Claim" flow with geo-tagged photo upload, disruption type selection, and description (`backend/manual_claims/`, mobile `manual-claim.tsx`) |
| Geo-validation service | ✅ Done | Extracts EXIF GPS from photo; compares to rider's live telemetry GPS; flags location mismatches > 500 m (`backend/manual_claims/geo_validation.py`) |
| Weather & traffic corroboration | ✅ Done | OpenWeatherMap + Google Maps queried for the photo's location/time to verify the claimed disruption type (`backend/data_collectors/weather_client.py`, `traffic_mock.py`) |
| Spam detection pipeline | ✅ Done | Composite spam score from location mismatch, time anomaly, weather/traffic cross-check; auto-rejects score ≥ 70 (`backend/manual_claims/`) |
| Admin manual-claim review queue | ✅ Done | Ranked by spam score; one-click approve/reject with corroboration summary (`admin/src/app/manual-claims/`, `backend/admin_service/`) |
| Payout service | ✅ Done | Simulated UPI wallet credit, payout history (`backend/payout_service/`) |
| Admin dashboard | ✅ Done | Overview metrics, disruption heatmap by zone, live claims feed, triggers panel, manual-claim review — built with Next.js + Tailwind (`admin/src/app/`) |
| Mobile app | ✅ Done | Full Expo/React Native app: registration, OTP, zone/slot selection, home dashboard, policy select + payment, claims history, manual claim, profile (`mobile/app/`) |
| Docker Compose | ✅ Done | Single `docker-compose up` spins up PostgreSQL/TimescaleDB, Redis, backend API, ML service, and admin dashboard (`docker-compose.yml`) |

**Exit criterion:** ✅ End-to-end flow works — registration → policy management → dynamic premium → zero-touch claim payout → manual claim fallback → admin review.

---

### Phase 3 — Scale & Optimise [April 5 – 17] (Weeks 5–6)

> **Theme:** "Perfect for Your Worker"

**Goal:** Smart, observable, pitch-ready system with advanced fraud detection, instant payouts, and intelligent dashboards.

#### Hackathon Deliverables

- **Advanced Fraud Detection:** Catch delivery-specific fraud (e.g., GPS spoofing, fake weather claims using historical data).
- **Instant Payout System (Simulated):** Integrate mock payment gateways (Razorpay test mode, Stripe sandbox, or UPI simulators) to demonstrate how the worker receives their lost wages instantly.
- **Intelligent Dashboard:**
  - **For Workers:** Earnings protected, active weekly coverage.
  - **For Insurers (Admin):** Loss ratios, predictive analytics on next week's likely weather/disruption claims.

#### Our Implementation Plan

| Deliverable | Details |
|---|---|
| Advanced fraud detection | Geo-consistency, peer comparison, Isolation Forest, behavioural autoencoder, collusion graph (Neo4j), counterfactual estimator, geo-velocity impossibility checks |
| Instant payouts (simulated) | Full Razorpay test mode / Stripe sandbox / UPI simulator with webhook reconciliation, push notification on payout via FCM |
| Rider intelligent dashboard | Earnings protected, active weekly coverage, risk alerts, claim history, next-week risk forecast, manual claim status tracker |
| Admin intelligent dashboard | Loss ratios, predictive analytics, live disruption heatmap (zone × time), fraud alert queue, payout analytics, manual claim review |
| Knowledge Graph v0 | Neo4j graph of zones, roads, stores, events — propagation logic |
| Model improvements | Temporal model upgrade (TCN/Transformer), self-calibrating thresholds |
| Final submission package | Demo + pitch deck + full repo with Docker Compose |


## 12. Phase 2 — What's Built

> **Status: Complete** — All Phase 2 deliverables are shipped and running end-to-end.

This section is a quick reference for developers, contributors, and demo reviewers: exactly
what code was produced in Phase 2, where it lives, and how to run it.

---

### Repository Layout

```
GuideWire/
├── backend/                     # FastAPI backend — all services
│   ├── rider_service/           # Registration, OTP auth, JWT, rider profiles
│   ├── policy_service/          # Policy lifecycle (buy, view, renew, cancel)
│   ├── premium_service/         # LightGBM dynamic premium engine
│   ├── trigger_service/         # Parametric trigger evaluation + scheduler
│   ├── claims_service/          # Auto-claim pipeline + Isolation Forest fraud
│   ├── payout_service/          # Simulated UPI wallet payouts
│   ├── manual_claims/           # Manual claim submission + geo-validation
│   ├── admin_service/           # Admin API (overview, manual-claim review)
│   ├── data_collectors/         # OpenWeatherMap, traffic mock, platform simulator
│   ├── ml/                      # LightGBM model training + serving (port 8001)
│   ├── shared/                  # Auth middleware, DB, Redis, config, zones
│   ├── seeds/                   # Demo seed data (riders, zones, policies, baselines)
│   ├── migrations/init.sql      # Full DB schema (PostgreSQL/TimescaleDB)
│   └── main.py                  # FastAPI app entry point (port 8000)
├── admin/                       # Next.js admin dashboard (port 3000)
│   └── src/app/
│       ├── page.tsx             # Overview: KPIs, live activity feed
│       ├── claims/              # Auto-claims list + status
│       ├── triggers/            # Live trigger panel + disruption heatmap
│       └── manual-claims/       # Manual claim review queue (approve / reject)
├── mobile/                      # Expo / React Native rider app
│   └── app/
│       ├── (auth)/              # register.tsx, otp.tsx, zone-select.tsx, slot-select.tsx
│       ├── (tabs)/              # index.tsx (home), claims.tsx, manual-claim.tsx, profile.tsx
│       └── policy/              # select.tsx (plan picker), payment.tsx
└── docker-compose.yml           # One-command full-stack local setup
```

---

### Running Locally

**Prerequisites:** Docker + Docker Compose, Node.js 18+, Expo CLI

```bash
# 1. Start infrastructure + backend
docker-compose up --build

# 2. Run admin dashboard (local development)
# Production dashboard is available at http://18.60.19.96
cd admin && npm install && npm run dev

# 3. Run mobile app (Expo)
cd mobile && npm install && npx expo start
```

The backend API is available at **http://18.60.19.96:8000** with auto-generated docs at
`/docs` (Swagger) and `/redoc`.

---

### Production Deployment (AWS)

For a detailed, step-by-step guide on how to deploy this application to AWS using a scalable and automated architecture, please refer to the:

👉 **[Incremental AWS Deployment Guide](AWS_DEPLOYMENT_GUIDE.md)**

This guide covers:
- **Phase 1**: Bare-metal deployment on a single EC2 (IP:PORT).
- **Phase 2**: Adding Nginx reverse proxy (IP:80).
- **Phase 3**: Auto Scaling and Load Balancing (ALB).
- **Phase 4**: CI/CD setup with GitHub Actions and ECR.



### Phase 2 Feature Highlights

#### Rider Mobile App (Expo / React Native)
- **Onboarding:** Phone registration → SMS OTP verification → zone + shift-slot selection
- **Policy:** Plan picker (Essential / Balanced / Max Protect) → simulated UPI payment → active policy view
- **Home Dashboard:** Active policy badge, current zone, earnings-at-risk, recent payouts
- **Claims History:** All auto and manual claims with status and payout amounts
- **Manual Claim:** Disruption type selection, description, geo-tagged photo upload, live submission status

#### Backend Services (FastAPI / Python)
- **Rider Service:** Phone/OTP auth with Redis OTP cache, JWT tokens, rider CRUD, zone assignment
- **Policy Service:** Policy lifecycle management, micro-slot risk scoring, coverage status
- **Premium Service:** LightGBM model trained on synthetic zone/slot/weather data; returns per-slot premium breakdown with feature explanations
- **Trigger Service:** 9 parametric triggers evaluated every 5 minutes via APScheduler; Three-Factor Validation Gate (trigger true + rider online + earnings drop ≥ 20%); Community Signal (>70% zone-rider order collapse)
- **Claims Service:** Auto-claim pipeline on disruption events; income gap estimator; Isolation Forest fraud scoring; auto-approve below threshold
- **Payout Service:** Wallet credit simulation; payout history API
- **Manual Claims Service:** Photo upload with EXIF GPS extraction; geo-validation (rider GPS vs photo GPS, tolerance 500 m); spam score (0–100); auto-reject ≥ 70; admin queue routing
- **Admin Service:** Overview metrics, live disruption events, manual-claim review (approve / reject with reason)
- **Data Collectors:** OpenWeatherMap client, traffic mock, platform simulator (rider/order/store/platform signals)

#### Admin Dashboard (Next.js + Tailwind)
- **Overview:** Total payouts, active policies, active disruptions, recent claim activity feed
- **Claims:** Full auto-claim list with trigger type, rider, amount, and status
- **Triggers:** Live trigger evaluation results per zone, active disruption events
- **Manual Claims:** Review queue ranked by spam score; expandable corroboration evidence; one-click approve/reject

#### ML Service (LightGBM)
- Synthetic training data generated for Indian metro zones across time-of-day profiles
- Features: zone risk score, rainfall, congestion index, time-of-day, rider history, platform signals
- Serves premium predictions at `/predict` (relative to API base)
- Falls back to rule-based pricing if ML service is unavailable

---

### Key API Endpoints (Phase 2)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/riders/register` | Register rider (phone + name) |
| `POST` | `/api/riders/verify-otp` | Verify OTP → issue JWT |
| `GET` | `/api/riders/me` | Authenticated rider profile |
| `GET` | `/api/zones` | All available zones |
| `POST` | `/api/policies/buy` | Purchase weekly policy |
| `GET` | `/api/policies/me` | Active policy for logged-in rider |
| `GET` | `/api/risk/premium` | Dynamic premium quote (ML) |
| `POST` | `/api/triggers/evaluate` | Manually trigger evaluation (demo) |
| `GET` | `/api/triggers/active` | Currently active disruption triggers |
| `GET` | `/api/claims/` | Claims for logged-in rider |
| `POST` | `/api/claims/manual` | Submit manual claim with photo |
| `GET` | `/api/payouts/` | Payout history for logged-in rider |
| `GET` | `/api/admin/overview` | Admin: platform-wide KPIs |
| `GET` | `/api/admin/manual-claims` | Admin: pending manual claim queue |
| `POST` | `/api/admin/manual-claims/{id}/approve` | Admin: approve manual claim |
| `POST` | `/api/admin/manual-claims/{id}/reject` | Admin: reject manual claim |

---

## 13. Adversarial Defense & Anti-Spoofing Strategy

> **Context:** A coordinated syndicate of 500 delivery workers organized via Telegram used
> GPS-spoofing apps to fake their presence inside a red-alert weather zone — triggering
> mass false parametric payouts and draining a platform's liquidity pool in hours.

**Core Principle:** GPS is a signal, not the source of truth. A rider is considered genuine
only when location data is consistent with OS-level location APIs, device telemetry, platform
trip logs, zone-level disruption evidence, behavioral history, and corroborating peer data.
Spoofed GPS alone can imitate "being in a bad zone" — it cannot simultaneously imitate a
realistic order history, IMU motion fingerprint, matching cell tower sequence, a real earnings
drop from a prior baseline, and a zone-wide peer impact pattern.

---

### 13.1 The Differentiation — Genuine Stranded Rider vs. GPS Spoofer

Every automatic payout requires multi-modal corroboration across the following signal stack.
No single signal can approve or reject a claim on its own.

| Signal | Genuine Stranded Rider | GPS Spoofer at Home |
|---|---|---|
| **OS Mock Location API** | `IS_FROM_MOCK_PROVIDER = FALSE` (Android); native CoreLocation source (iOS); no mock-location app running | Basic spoofing apps set this flag TRUE. Advanced tools (Magisk, virtualization containers) can mask it — treated as a heavy-weight corroborating signal, never a standalone reject ✗ |
| **GPS telemetry quality** | Degraded HDOP (> 3.0), multipath scatter, altitude jitter — consistent with rain and urban canyons | Spoofing apps inject artificially *perfect* GPS fixes. A too-perfect lock during a declared red-zone storm is a hard red flag ✗ |
| **Cell tower triangulation** | Serving cell tower IDs (CID + LAC) physically in the claimed zone; RSSI variance from movement | GPS spoofing moves the injected coordinate, not the physical tower. Home tower in a different zone = immediate flag ✗ |
| **Accelerometer / IMU** | Erratic, high-frequency vibration consistent with riding a two-wheeler on wet roads | Stationary phone shows near-zero accelerometer variance. Lightweight on-device model classifies motion state at payout time ✗ |
| **Platform trip logs** | Active order attempts, order declines, navigation events firing in the delivery app | Spoofer's delivery app is backgrounded or idle — no trip events, no order workflow activity ✗ |
| **Earnings trajectory** | Genuine drop from prior-hour earning baseline — income *was* flowing, then disruption hit | Fraudster's account shows near-zero earnings history; there is no drop to measure because there was no work ✗ |
| **Zone entry timing** | Rider was already in the zone *before* the trigger fired — shift history confirms prior presence | Ring members "teleport" into the disrupted zone at the exact moment a trigger activates. Zone-entry within < 2 minutes of trigger fire is flagged ✗ |
| **Battery drain rate** | ~15–20%/hr field drain: continuous GPS + mobile data + screen-on under thermal load | Spoofing app runs a secondary background process, producing an anomalous drain pattern distinct from both field use and normal idle ✗ |
| **IP geolocation** | Data connection routes through a cell tower ISP consistent with the claimed zone | Home WiFi or fixed residential ISP contradicts the claimed zone. A rider "in Gachibowli" connecting from a Koramangala home ISP is anomalous ✗ |
| **App session behavior** | Organic, irregular API heartbeat cadence driven by real delivery events | Automated spoofing scripts produce unnaturally metronomic, periodic API call intervals — detectable via periodicity analysis on the call-interval time series ✗ |

**Pre-Disruption Telemetry Buffer (network-drop protection):**
The rider app continuously caches the last **15 minutes** of GPS + IMU + platform activity
locally on the device. When a claim is evaluated, this buffer is uploaded alongside live data.
A rider whose buffered data shows consistent zone presence and active platform activity in the
15 minutes *before* network degraded receives full benefit-of-the-doubt — genuine presence is
proven by evidence captured before connectivity failed, not just at the moment of claim.
A spoofer has no such legitimate pre-disruption history to upload.

**Geo-Velocity Impossibility Check:**
Any rider whose GPS history shows them in Zone A at time T and Zone B (≥ 3 km away) at
T + 90 seconds — physically impossible during a red-alert event with flooded roads and gridlock
— is immediately auto-flagged. The distance and time thresholds (default: 3 km / 90 s) are
**configurable parameters**, dynamically adjusted per disruption type, zone road density, and
observed traffic conditions.

---

### 13.2 The Data — What Catches a Coordinated Fraud Ring

Individual fraud detection fails at scale. A ring of 500 acting in concert leaves a
**graph-level and behavioral signature** that is statistically unmistakable in aggregate.
The fraud engine organizes evidence into four layers:

#### Layer 1 — Device-Level Signals

| Signal | What It Catches |
|---|---|
| **OS Mock Location flag** (`IS_FROM_MOCK_PROVIDER`) | Heavy-weight corroborating input to the fraud score — never a standalone reject trigger. Always requires corroboration from at least one other signal (e.g., stationary IMU, cell tower mismatch). |
| **IMU / Accelerometer fingerprint** | A lightweight on-device ML model classifies "riding," "walking," "stationary," or "vehicle passenger" at claim time. Stationary classification contradicts an active-delivery claim. |
| **Device fingerprint clustering** | Device hardware ID (IMEI/IDFA), WiFi MAC address, and shared IP are grouped in a Neo4j graph. 500 coordinating via Telegram will share a small number of device setups — detectable even if each account appears independent. |
| **Spoofing APK fingerprint** | Multiple riders sharing the same APK hash or build fingerprint — installed on the same day a disruption is declared — is a collusion indicator. |
| **Battery anomaly** | GPS spoofing runs a persistent background process. Unusual battery consumption correlated with "in-zone" status is cross-referenced against the device model's baseline. |

#### Layer 2 — Behavioral Signals

| Signal | What It Catches |
|---|---|
| **Online/offline timing pattern** | Riders who go "online" *exclusively* during known red-alert windows and never during normal conditions are flagged by Isolation Forest as a behavioral fingerprint. |
| **Claim-to-earn ratio** | Rolling 4-week earn/claim ratio per rider. A fraudster's account with near-zero earnings history and a sudden high-value claim scores heavily in the fraud model. |
| **Zone entry timing** | Genuine riders are already in a zone before disruption begins. Fraudsters "teleport" in at the exact moment a trigger fires (threshold: < 2 min; configurable). |
| **Geo-velocity impossibility** | Rider in Zone A at T=0 and Zone B (≥ 3 km) at T+90 s during a declared red-alert event is physically impossible (thresholds configurable). |
| **Claim timing burst** | Legitimate disruptions produce staggered, organic claim arrivals (Poisson distribution). A ring submitting after a Telegram broadcast creates a sharp impulse. Poisson-rate test: > 3σ deviation from the zone's historical mean triggers a zone-level fraud hold. |

#### Layer 3 — Graph / Ring Detection

Zylo's Neo4j-based collusion graph ingests four edge types:

- **Rider → Zone** (weighted by shift frequency — zone affinity)
- **Rider → Device** (hardware fingerprint per login session)
- **Rider → PayoutAccount** (UPI VPA / bank account number)
- **Rider → ClaimEvent** (timestamped, with disruption event ID)

Three graph queries execute on every disruption event:

1. **Community detection (Louvain algorithm):** Clusters of riders who co-claim across
   multiple unrelated disruption events. Honest riders do not form tight co-claim clusters;
   a ring does. Cluster coefficient > 0.7 triggers a ring-review flag.

2. **Hub payout account detection:** Any UPI VPA or bank account receiving credits from
   ≥ 5 distinct riders in a 30-day window is flagged. Second-degree traversal also surfaces
   indirect linkage via a common third party.

3. **Simultaneous zone-entry detection:** If 50+ riders "enter" a disrupted zone within
   the same 60-second window — physically impossible during a red-alert event — the entire
   batch is held for ring-level review, not individual review.

#### Layer 4 — Zone-Level Coherence

| Signal | What It Catches |
|---|---|
| **Peer earnings cross-validation** | In a genuine disruption, *all* on-site riders (confirmed via cell towers and platform logs) show an earnings drop. Fraudsters who "appear" in the zone have no prior earning history there — no real drop to claim. |
| **Weather-earnings model ceiling** | LightGBM has a trained expectation of maximum earnings impact per rainfall/congestion level per zone per time slot. Claims requesting payouts *larger than the model's ceiling* for observed weather severity are flagged as overclaiming. |
| **Dark store activity cross-check** | If dark stores in the zone are still processing orders (`store_status = ACTIVE`, throughput > 0), disruption severity is lower than claimed — payouts are proportionally capped to observed store impact, not the claimed maximum. |
| **Zone–rider affinity score** | Fraction of a rider's past 30 shifts in the claimed zone. A low-affinity rider (< 5% of prior shifts) claiming their first-ever disruption in a zone during its only significant payout event of the month is anomalous. 200 low-affinity riders simultaneously claiming from the same zone approaches zero coincidence probability. |
| **Claim zone saturation rate** | Genuine disruptions produce 30–60% zone-claim rates, tapering as the event resolves. A coordinated ring produces 85–100% rates sustained uniformly throughout the disruption window — a signal of artificial maximization. |

---

### 13.3 The UX Balance — Tiered Response Without Punishing Honest Workers

A real rider experiencing a genuine network drop in bad weather will look superficially
similar to a spoofer: degraded GPS, weak cell signal, intermittent platform activity. The
system must not punish them. Zylo uses a **four-tier numeric fraud score system**,
not a binary approve/reject — with time-bounded SLAs on every tier.

> **Design principle:** The system fails safely. Hard on spoofers; forgiving to genuinely
> stranded workers. Claims are never rejected on GPS evidence alone.

#### Four-Tier Fraud Score Framework

| Score Band | Tier | Action | Rider-Facing Message | SLA |
|---|---|---|---|---|
| **0 – 30** | 🟢 **Auto-Approve** | Instant payout released. No friction for the rider. | *"₹540 credited to your UPI wallet. Stay safe!"* | Seconds |
| **31 – 60** | 🟡 **Soft Flag — Passive Hold** | Payout held up to 2 hours. System monitors passively: if signals resolve → auto-approve; if still ambiguous → route to human review queue, not auto-reject. | *"Your payout is being verified due to signal conditions. You'll hear back within 2 hours."* | ≤ 2 hours |
| **61 – 85** | 🟠 **Hard Flag — Self-Attestation** | Payout held. Rider submits a **5-second live geo-stamped video** (live video is orders of magnitude harder to fake than a GPS coordinate). Simultaneously routed to admin fraud queue with full multi-signal evidence brief. Admin approves or rejects with one click. | *"Your claim needs a quick check. Tap to record a 5-second video from your current location. You'll have a decision within 4 hours."* | ≤ 4 hours |
| **86 – 100** | 🔴 **Auto-Reject** | Requires convergent evidence across **at least two independent signals**: e.g., Mock Location flag TRUE *and* IMU confirms stationary, OR Mock Location flag TRUE *and* cell tower in a different zone, OR device in a confirmed payout/device graph cluster *and* zero platform trip activity. No single signal alone reaches this tier. | *"Your claim was declined. Specific reason: [e.g., 'Your phone's OS-reported location does not match GPS and your phone showed no movement during this window.']"* — never vague. Rider can appeal with human review. | Instant |

#### The Pre-Disruption Telemetry Buffer (for Network Drop Edge Cases)

Bad weather degrades GPS and cell signal simultaneously — the exact conditions that
cause legitimate disruptions. The app handles this with a pre-disruption buffer:

- Continuously caches the last **15 minutes** of GPS + IMU + platform activity **locally on
  device**, independent of network connectivity.
- On claim submission, the buffer is uploaded alongside live data.
- A rider whose buffer shows consistent zone presence and active delivery app usage in the
  15 minutes before network degradation gets automatic benefit-of-the-doubt.
- A spoofer running a script at home has no legitimate 15-minute pre-disruption history —
  their buffer shows a stationary, home-network, app-idle device.

#### Trust Score — Track Record as Corroborating Evidence

Every rider accumulates a `trust_score` (0–100) from clean claim history, platform tenure,
consistent zone activity, and on-time premium payments. A rider with `trust_score ≥ 70`
receives a score adjustment that can shift a borderline 31-score claim into the auto-approve
band — their documented history provides evidence that signal ambiguity reflects genuine
conditions, not fraud.

*Trust score cannot override zone-level burst holds.* When a zone saturation event or
> 3σ Poisson burst triggers a zone-level hold, even high-trust riders enter the Soft Flag
tier and qualify for the micro-advance, but are not auto-approved until the zone investigation
completes. This prevents a trusted account from being co-opted as ring cover.

#### Additional Protections for Honest Workers

**Emergency micro-advance:** Any rider in the Soft Flag or Hard Flag tier with a clean
90-day claim history can instantly request an advance (default: ₹200; **configurable**) through
the app. Disbursed immediately; debited from the final approved payout. If rejected, repayment
is structured as small weekly deductions (default: ₹50/week over 4 weeks; **configurable**) —
never a lump-sum demand. Balances outstanding after 90 days are written off
(**write-off threshold is configurable**, informed by real portfolio data).

**Signal decay forgiveness:** During declared "heavy rain," "flood," or "cyclone" events,
degraded GPS quality (low satellite count, high HDOP) is re-classified as *corroborating
evidence* of the claimed condition, not an anomaly flag.

**Repeated false flags trigger recalibration:** If a rider's claims are repeatedly flagged but
consistently approved on human review, the pattern is logged as a false-positive cluster and
used to retrain the model — not to penalize the rider.

**No punitive premium impact for a single flag:** Risk-score adjustments only activate after
3 confirmed-fraudulent rejections within a 90-day window, with explicit written notice before
each increment.

**Transparent audit trail:** Every flagged claim shows the rider the specific signal that
triggered it in plain language (e.g., *"The cell tower your phone connected to was in
Koramangala, not the declared zone in Gachibowli"*) — enabling a specific, actionable
rebuttal, not a blind appeal.

#### Surgical Zone Interdiction — No Collateral Damage

When a zone-level burst event triggers a hold, the system operates in three ranked passes:

1. **Pass 1 — Immediate release (score 0–30, ≥ 8/10 signals consistent):** Approved and
   paid instantly. These riders are clearly legitimate; they are never held as collateral.
2. **Pass 2 — Soft hold (score 31–60):** Held pending zone investigation, micro-advance
   available to all. Auto-resolve within 2 hours if signals clear.
3. **Pass 3 — Investigation-gated (score > 60, or confirmed graph cluster member):** Held
   until investigation concludes. Confirmed non-ring members are released and paid.
   Confirmed ring members are rejected and reported.

---

### 13.4 Ring-Level Escalation Protocol

When a coordinated ring is detected — a graph cluster of ≥ 10 accounts showing synchronized
suspicious behavior — the following protocol activates automatically:

1. **Batch hold:** All claims from the cluster are suspended simultaneously, not processed
   individually. This prevents the ring from partially draining the pool before detection
   completes.

2. **Silent flag:** The cluster is not notified, preventing the ring from pivoting tactics or
   destroying evidence before the investigation.

3. **Retroactive 4-week audit:** The fraud engine reruns the last 4 weeks of payouts for all
   cluster accounts, flagging amounts eligible for clawback. The liquidity team is alerted
   with a full evidence brief.

4. **Platform partner alert:** The delivery platform (Blinkit / Zepto / Swiggy) whose rider
   IDs are implicated is notified via API webhook for account-level action. Cross-platform
   corroboration closes the loop on whether the riders were genuinely active at all.

5. **Per-zone payout velocity cap:** If total payouts from a single zone in a single hour
   exceed **3× the actuarial expectation** for the observed trigger severity, all further
   payouts queue for human review until the anomaly is resolved. The liquidity pool is
   protected *before* the ring can drain it. This cap is the last-resort backstop that makes
   the entire fraud architecture self-protecting even under novel attack vectors.

---

### 13.5 Policy Safeguards & Architecture Summary

**Policy safeguards that protect honest riders:**
- Claims are **never** rejected on a single GPS signal alone — auto-reject (score 86–100)
  requires convergent evidence across at least two independent signals.
- Every flagged claim receives a specific reason code in plain language — no vague rejections.
- Every rejected claim has a manual appeal path with a 4-hour human review SLA.
- Fraud score thresholds are calibrated **conservatively**; any threshold producing > 2%
  false-positive rate in retrospective analysis triggers an automatic model review.
- Fraud findings are fed back into model retraining continuously — the system improves with
  every event.

**Architecture summary:**
Zylo's anti-spoofing defense is a five-layer system: (1) a device-signal layer using
the OS Mock Location API as a heavy-weight corroborating input (never standalone) alongside IMU
fingerprinting, device clustering, and battery anomaly detection; (2) a multi-modal signal
fusion layer across GPS quality, cell towers, platform logs, earnings trajectory, and app
behavior requiring convergent evidence across independent physical channels; (3) a four-layer
ring detection stack combining device fingerprints, behavioral anomaly detection, Neo4j graph
analysis, and zone-level coherence checks; (4) a four-tier numeric scoring system with
time-bounded SLAs, pre-disruption telemetry buffers, live video geo-stamps, and trust score
adjustments ensuring honest workers are never punished for signals that bad weather itself
creates; and (5) a ring-level escalation protocol with batch holds, silent flags, retroactive
audits, platform partner alerts, and per-zone payout velocity caps that protects liquidity
before a ring can drain it. No GPS spoofing app defeats all five layers simultaneously.

---

## Regulatory Compliance & Insurance Sense

### Social Security Code, 2020 — Engagement Rule

Zylo enforces a configurable **minimum engagement threshold** before a rider can purchase
parametric income protection:

- **90-day rule** (single-platform riders) / **120-day rule** (multi-apping riders) per SS Code, 2020.
- Configuration: `MIN_ENGAGEMENT_DAYS` environment variable (default: `0` for demo, set to `90`
  for production compliance).
- Enforcement point: Policy creation (`POST /api/policies`) calculates `tenure_days` from the
  rider's `created_at` timestamp and rejects purchases below the threshold with an
  `ENGAGEMENT_RULE` error code.
- Admin visibility: The pool health endpoint exposes the count of active riders vs. total
  registered riders, enabling the "how many workers fall below the SS Code threshold" metric.

### DPDP Act, 2023 — Data Consent Framework

All personal data processing follows India's Digital Personal Data Protection Act, 2023:

| Data Category | Purpose | Consent Mechanism |
|---|---|---|
| **GPS location** | Zone presence verification for claim adjudication | Explicit checkbox during registration |
| **UPI / Bank account** | Automatic payout disbursement | Explicit checkbox during registration |
| **Platform activity** | Earnings baseline and disruption corroboration | Explicit checkbox during registration |

- Consent is **mandatory** — the registration flow blocks until all three consents are granted.
- Consent state is recorded at the point of registration and can be audited.
- Platform data is currently simulated; real-world deployment requires B2B data-sharing agreements
  with Zepto/Blinkit/Swiggy under the DPDP Act's Data Fiduciary framework.

### IRDAI Guidelines Alignment

| Requirement | Implementation |
|---|---|
| **Dynamic pricing** | LightGBM ML model + zone risk scores + monsoon detection + slot-level granularity |
| **Accuracy** | Per-zone lat/lon weather polling, Three-Factor Validation Gate (trigger + online + earnings drop) |
| **Fraud prevention** | 6-signal fraud scoring: GPS, peer comparison, baseline validity, anomaly ML, collusion, EXIF |
| **Financial sustainability (BCR)** | `GET /api/admin/analytics/pool-health` — real-time BCR calculation with IRDAI target ≤0.65 |
| **Stress test** | `GET /api/admin/analytics/stress-test` — simulated 14-day monsoon proving pool survival |
| **Zero-touch claims** | Fully automated auto-claim pipeline: trigger → fraud → UPI payout, zero human intervention |
| **Trusted data sources** | OpenWeatherMap (live), CPCB AQI proxy, Google Traffic API (simulated in dev) |

### Adverse Selection Prevention (48-Hour Lockout)

Zylo uses a **weekly policy cycle** as a natural adverse selection prevention mechanism:

- Policies are purchased **before the coverage week begins** (typically Sunday).
- Once a week starts, riders cannot retroactively purchase coverage after a weather event is
  reported — the `DUPLICATE_POLICY` check prevents same-week re-enrollment.
- This is functionally equivalent to a "48-hour lockout before red alert" while being simpler
  for riders to understand.

### Operational Cost Efficiency

- Auto-claims: **zero-touch** — trigger fires → fraud check → instant UPI payout. No human.
- Manual claims: **AI-adjudicated** — Nebius/Kimi LLM evaluates evidence → recommends approve/reject
  → admin reviews only edge cases.
- Premiums: **₹20–₹169/week** — micro enough that admin costs don't eat into collection.

---

## Limitations & Future Work

- Phase 1–2 ML models run on **synthetic data**; real-world calibration requires platform
  partnerships and regulatory approval.
- Advanced models (Offline RL, PI-GNN, Causal AI) are **roadmap items**, not hackathon
  deliverables — we are transparent about this distinction.
- Production deployment requires IRDAI sandbox/regulatory clearance for insurance products
  in India.
- Reinsurance arrangements for catastrophic zone events are a commercial layer not built
  in the prototype.
- **Manual claim photo storage** uses a local filesystem in the prototype; production requires
  a secure, signed-URL object store (AWS S3 / GCS) with image integrity verification.
- **EXIF GPS extraction** relies on camera-embedded metadata; photos shared via messaging apps
  often have EXIF stripped — in those cases the system falls back to the device GPS recorded by
  the rider app at upload time.
- Manual claims are rate-limited to **1 per policy week per rider** in the prototype; the
  production cap should be informed by real claim data and the portfolio loss ratio.

---

*Built with ❤️ for India's 10M+ gig workers — the invisible backbone of quick commerce.
DEVTrails 2026 Hackathon Submission.*