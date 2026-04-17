# Zylo — Product Requirements Document (PRD)

## Parametric Income Protection for Delivery Riders

**Project Type:** Hackathon Prototype  
**Version:** 1.0  
**Date:** March 2026  
**Status:** For Development Team  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals & Objectives](#3-goals--objectives)
4. [Target Users / Personas](#4-target-users--personas)
5. [User Stories](#5-user-stories)
6. [End-to-End User Journey](#6-end-to-end-user-journey)
7. [Feature Requirements](#7-feature-requirements)
8. [Functional Requirements](#8-functional-requirements)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Success Metrics](#10-success-metrics)
11. [Assumptions \& Constraints](#11-assumptions--constraints)
12. [Risks \& Mitigations](#12-risks--mitigations)
13. [Out of Scope](#13-out-of-scope)
14. [Demo Script Flow](#14-demo-script-flow-judge-facing-narrative)

---

## 1. Executive Summary

### 1.1 What is Zylo?

Zylo is a **parametric income protection system** designed for quick-commerce delivery riders (Zepto, Blinkit, Swiggy Instamart). It provides automatic payouts when external disruptions—rain, traffic congestion, store closures, or platform outages—cause income loss.

### 1.2 Core Value Proposition

| Feature | Benefit |
|---------|--------|
| **Parametric Triggers** | No manual claims—disruption detected → payout credited automatically |
| **Weekly Premiums** | Aligned with rider weekly cash flow (₹20–₹150/week) |
| **Micro-Slot Pricing** | Premiums personalized by zone risk, time slot, and rider history |
| **Manual Claim Fallback** | Geo-tagged photo submission for undetected disruptions |
| **Admin Review** | Fraud-prevented manual claim queue with approve/reject |
| **Zero-Touch Payouts** | Instant UPI credit (simulated) within minutes of disruption |

### 1.3 Product Scope (Hackathon)

- **Mobile-First PWA** for rider-facing app
- **Admin Dashboard** for claim review
- **5 Automated Triggers** (rain, traffic, store, platform, regulatory)
- **Simulated Data** for platform APIs (no real Zepto/Blinkit integration)
- **Mock Payments** via UPI simulator

### 1.4 Target Audience

- **Primary:** Delivery riders in Bengaluru, Hyderabad, Mumbai, Delhi
- **Secondary:** Insurers, platform partners (future phase)
- **Hackathon Judges:** Demo-focused, end-to-end flow visibility

---

## 2. Problem Statement

### 2.1 The Reality of Delivery Work

India's q-commerce sector (~$11.5B) runs on an invisible workforce of delivery partners:

| Reality | Impact |
|---------|--------|
| **Variable Income** | ₹15,000–₹25,000/month, entirely per-delivery |
| **External Vulnerabilities** | 20–30% monthly income lost to disruptions beyond rider control |
| **Weekly Cash Flow** | Riders are paid weekly; debt serviced on phones/bikes weekly |
| **Hyper-Local Zones** | 2–5 km radius around dark stores = acute sensitivity to micro-disruptions |

### 2.2 Why Traditional Insurance Fails

| Problem | Why It Fails |
|---------|-------------|
| **No Fixed Salary** | Cannot underwrite variable daily income |
| **Manual Claims** | 30-day claims process unusable—riders need money this week |
| **Asset Focus** | Covers vehicle damage, not lost earnings |
| **Proof Burden** | "It rained and I lost orders" is not provable to claims adjuster |

### 2.3 The Solution: Parametric Insurance

**Instead of proving a loss**, Zylo uses measurable, objective data signals (rainfall mm, congestion index, store status) as automatic triggers. **If the data says it happened, the rider gets paid.**

> **Coverage Scope (Strict):** Income loss from external disruptions only. Health, life, vehicle damage, and accidents are explicitly excluded.

---

## 3. Goals & Objectives

### 3.1 Hackathon Goals

| Goal | Success Criteria |
|------|-----------------|
| **G1: Working Prototype** | End-to-end flow runs without crash for demo |
| **G2: Complete User Journey** | Registration → Policy → Premium → Trigger → Claim → Payout works |
| **G3: Zero-Touch Automation** | Simulated disruption triggers automatic payout |
| **G4: Manual Fallback** | Geo-tagged claim submission + admin review works |
| **G5: Demo-Ready** | 2-minute video showcases full flow to judges |

### 3.2 Technical Objectives

| ID | Objective | Priority |
|----|-----------|----------|
| **O1** | Rider registration with OTP (mock) | P0 |
| **O2** | Policy selection (3 tiers: Essential, Balanced, Max Protect) | P0 |
| **O3** | Dynamic premium calculation (zone risk + ML model) | P0 |
| **O4** | 5 automated triggers operational | P0 |
| **O5** | Auto claim + payout flow | P0 |
| **O6** | Manual claim with geo-tagged photo | P1 |
| **O7** | Admin dashboard for claim review | P1 |
| **O8** | Fraud detection (spam score) | P1 |

### 3.3 Demo Objectives

| ID | Objective | Priority |
|----|-----------|----------|
| **D1** | Registration flow visible | P0 |
| **D2** | Premium difference by zone visible | P0 |
| **D3** | Auto-disruption + auto-payout visible | P0 |
| **D4** | Manual claim submission visible | P0 |
| **D5** | Admin approve visible | P0 |

---

## 4. Target Users / Personas

### 4.1 Primary Persona

| Attribute | Details |
|-----------|---------|
| **Name** | Arjun |
| **Age** | 24 |
| **Location** | Bengaluru (Indiranagar/Koramangala) |
| **Employer** | Zepto |
| **Income** | ~₹18,000/month |
| **Pattern** | Evening peaks (6–11 PM), weekend mornings (8–11 AM) |
| **Zone** | 3-km radius |
| **Pain Points** | Monsoon flooding, GPS drift in high-rises, store queues, road blockades |

### 4.2 Secondary Personas

| Persona | Scenario | Relevance |
|---------|----------|----------|
| **Rohit** | Heavy rain + flooding, Hyderabad | Weather trigger demo |
| **Ankush** | GPS multipath shadowban, Gurugram | Platform trigger demo |
| **Priya** | Dark store outage, Delhi | Store trigger demo |
| **Ravi** | Undetected local disruption, Pune | Manual claim fallback |

### 4.3 Admin Persona

| Attribute | Details |
|-----------|---------|
| **Name** | Insurance Admin |
| **Role** | Claims reviewer |
| **Tasks** | Approve/reject manual claims, monitor fraud queue |
| **Success Metric** | Process claims within 4 hours |

---

## 5. User Stories

### 5.1 Registration & Onboarding

| ID | User Story | Acceptance Criteria |
|----|-----------|-----------------|
| **US-01** | As a new rider, I want to register with my phone number so I can create an account | OTP sent, mock "123456" verifies successfully, JWT token returned |
| **US-02** | As a rider, I want to link my delivery platform (Zepto/Blinkit/Swiggy) so I'm identified as a rider | Platform selection saved to profile |
| **US-03** | As a rider, I want to select my working zone and time slots so the system knows my risk profile | Zone + slot preferences saved, risk profile generated |
| **US-04** | As a rider, I want to see my risk profile with explanation so I understand my premium | Zone risk score + volatility + explanation displayed |

### 5.2 Policy Management

| ID | User Story | Acceptance Criteria |
|----|-----------|-----------------|
| **US-05** | As a rider, I want to view 3 policy tiers so I can choose coverage | Essential/Balanced/Max Protect displayed with prices |
| **US-06** | As a rider, I want to purchase a weekly policy so I'm protected | Policy created, premium paid via mock UPI, policy active |
| **US-07** | As a rider, I want to view my active policy so I know what's covered | Active policy with slots_covered, hours_remaining shown |
| **US-08** | As a rider, I want to renew my policy for next week so coverage continues | Policy renewed, premium recalculated |

### 5.3 Premium Calculation

| ID | User Story | Acceptance Criteria |
|----|-----------|-----------------|
| **US-09** | As a rider, I want to see my dynamic premium so I know what I'm paying | Zone-specific premium with breakdown (risk score, tenure discount, plan multiplier) |
| **US-10** | As a rider, I want premiums to differ by zone so pricing is fair | High-risk zone = higher premium, low-risk = lower premium |

### 5.4 Triggers & Automation

| ID | User Story | Acceptance Criteria |
|----|-----------|-----------------|
| **US-11** | As a rider, I want the system to automatically detect disruptions so I don't need to file claims | 5 trigger types evaluate every 5 min |
| **US-12** | As a rider, I want to receive payouts automatically when disruptions occur so I get paid instantly | Payout credited to mock UPI without rider action |

### 5.5 Claims System

| ID | User Story | Acceptance Criteria |
|----|-----------|-----------------|
| **US-13** | As a rider, I want to submit a manual claim with a photo when disruption isn't detected | Geo-tagged photo uploaded, disruption type selected, description added |
| **US-14** | As a rider, I want to track my manual claim status so I know if it's approved | Claim status (submitted → under review → approved/rejected) visible |
| **US-15** | As an admin, I want to review manual claims so I can approve or reject them | Claims queue sorted by spam score, approve/reject buttons functional |

### 5.6 Dashboard

| ID | User Story | Acceptance Criteria |
|----|-----------|-----------------|
| **US-16** | As a rider, I want a dashboard showing my coverage and claim history so I can track everything | Active coverage, disruption alerts, claim history displayed |

---

## 6. End-to-End User Journey

### 6.1 Complete Rider Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     RIDER JOURNEY MAP                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [1. DOWNLOAD/PWA]  →  [2. SIGN UP]  →  [3. OTP VERIFY]               │
│         ↓                      ↓                   ↓                    │
│   Open browser           Enter phone          Enter 123456               │
│   Install to home       Get OTP                                    │
│                        screen                                                        │
│         ↓                      ↓                   ↓                    │
│  [4. PLATFORM LINK]  →  [5. ZONE SELECT]  →  [6. SLOT PICK]           │
│         ↓                      ↓                   ↓                    │
│   Select Zepto/         Select zone         Pick working slots        │
│   Blinkit/             from map           (view risk colors)        │
│   Swiggy                                                           │
│                        ↓                   ↓                    │
│  [7. RISK PROFILE]  →  [8. POLICY SELECT]  →  [9. PREMIUM PAY]       │
│         ↓                      ↓                   ↓                    │
│   View zone risk        Pick tier          Pay via UPI mock         │
│   + explanation       (Essential/        (policy activates)        │
│                       Balanced/                                                     │
│                       Max Protect)                                                │
│                        ↓                   ↓                    │
│  [10. ACTIVE POLICY] →  [11. WORK NORMALLY]  →  [12. DISRUPTION]      │
│         ↓                      ↓                   ↓                    │
│   View coverage       App monitors       Auto-trigger fires         │
│   status            in background      (rain/traffic/store/      │
│                                            platform/regulatory)                         │
│                        ↓                   ↓                    │
│  [13. AUTO PAYOUT]  →  [14. NOTIFICATION]  →  [15. DASHBOARD]        │
│         ↓                      ↓                   ↓                    │
│   Payout credited    Push notification    View payout history     │
│   to UPI          + breakdown                             │
│                        ↓                                              │
│                  [BRANCH: IF NO AUTO TRIGGER]                                     │
│                         ↓                                              │
│  [16. MANUAL CLAIM]  →  [17. PHOTO UPLOAD]  →  [18. SUBMIT]          │
│         ↓                      ↓                   ↓                    │
│   Tap "Request        Take geo-tagged     Select disruption       │
│   Manual Claim"     photo              type + submit             │
│                        ↓                   ↓                    │
│  [19. UNDER REVIEW]  →  [20. ADMIN DECISION]  →  [21. PAYOUT]     │
│         ↓                      ↓                   ↓                    │
│   Status shows       Admin reviews       If approved: payout      │
│   "under review"    spam score        If rejected: reason     │
│                        (spam ≥ 70: reject)                                        │
│                                            ↓                                  │
│                                    [22. DASHBOARD UPDATE]                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Step-by-Step Details

| Step | User Action | System Response | Expected Output |
|------|------------|--------------|----------------|
| **1** | Open PWA URL | Serve onboarding UI | PWA loads |
| **2** | Enter phone | Send OTP to Redis | OTP stored: "123456" |
| **3** | Enter OTP | Verify against Redis | JWT token returned |
| **4** | Select platform | Save to rider profile | Platform linked |
| **5** | Select zone | Save zone + fetch risk data | Zone saved |
| **6** | Pick slots | Save time preferences | Slots saved |
| **7** | View risk profile | Calculate risk score | Risk score + explanation |
| **8** | Select plan tier | Return tier-specific pricing | 3 plans shown with prices |
| **9** | Pay premium | Process mock UPI | Payment confirmed |
| **10** | View policy | Return active policy | Coverage status shown |
| **11** | Work (background) | Monitor triggers every 5 min | N/A |
| **12** | Disruption occurs | Trigger evaluates zone+slot+rider | Disruption event created |
| **13** | Income loss detected | Calculate payout | Payout computed |
| **14** | Fraud check passes | Approve claim | Claim approved |
| **15** | Payout credited | Create payout record + notify | Money credited |
| **16** | (Fallback) Tap manual claim | Open claim form | Form displayed |
| **17** | Take photo | Extract EXIF GPS + timestamp | Photo + metadata saved |
| **18** | Submit claim | Store claim + geo-validate | Claim submitted |
| **19** | (Admin) View queue | Return claims sorted by spam | Queue displayed |
| **20** | (Admin) Review | Check spam score + evidence | Decision options shown |
| **21** | (Admin) Approve | Trigger payout | Money credited |

---

## 7. Feature Requirements

### 7.1 Registration & Onboarding

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| **F1.1** | Phone Registration | Enter phone number to start | P0 |
| **F1.2** | OTP Verification | Mock OTP "123456" verification | P0 |
| **F1.3** | Platform Linking | Select Zepto/Blinkit/Swiggy Instamart | P0 |
| **F1.4** | Zone Selection | Interactive zone picker on map | P0 |
| **F1.5** | Slot Selection | Select working time slots | P0 |
| **F1.6** | Risk Profile Display | Show zone risk score + explanation | P0 |
| **F1.7** | JWT Authentication | Secure session after registration | P0 |

### 7.2 Policy Management

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| **F2.1** | Tier Display | Show 3 policy tiers with pricing | P0 |
| **F2.2** | Plan Selection | Select Essential/Balanced/Max Protect | P0 |
| **F2.3** | Premium Payment | Mock UPI payment flow | P0 |
| **F2.4** | Policy Activation | Policy becomes active after payment | P0 |
| **F2.5** | Active Policy View | Dashboard shows coverage details | P0 |
| **F2.6** | Policy Renewal | Renew for next week | P1 |
| **F2.7** | Policy Cancellation | Cancel active policy | P1 |

### 7.3 Dynamic Premium

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| **F3.1** | Risk Score Calculation | Zone-based risk scoring (0–100) | P0 |
| **F3.2** | ML Premium Model | LightGBM model for disruption probability | P0 |
| **F3.3** | Tier Pricing | Calculate price for Essential/Balanced/Max | P0 |
| **F3.4** | Premium Breakdown | Show risk explanation per slot | P0 |
| **F3.5** | Zone Differentiation | High-risk = higher premium | P0 |

### 7.4 Automated Triggers

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| **F4.1** | Weather Trigger | Rainfall > 40mm/hr triggers | P0 |
| **F4.2** | Traffic Trigger | Congestion > 80/100 for 60+ min | P0 |
| **F4.3** | Store Closure Trigger | Dark store status = CLOSED | P0 |
| **F4.4** | Platform Outage Trigger | Platform status = DOWN | P0 |
| **F4.5** | Regulatory Trigger | Curfew/ban active | P0 |
| **F4.6** | Community Signal | >70% riders in zone affected | P1 |
| **F4.7** | Trigger Evaluation | Run every 5 min per zone/slot | P0 |

### 7.5 Claims System — Auto

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| **F5.1** | Disruption Event | Create event when trigger fires | P0 |
| **F5.2** | Rider Identification | Find insured riders in zone | P0 |
| **F5.3** | Income Gap Calc | Expected - Actual = Loss | P0 |
| **F5.4** | Payout Calculation | min(Income Loss, Coverage Limit) | P0 |
| **F5.5** | Basic Fraud Check | GPS + peer comparison | P0 |
| **F5.6** | Auto Payout | Credit to mock UPI | P0 |
| **F5.7** | Push Notification | Alert rider of payout | P0 |

### 7.6 Claims System — Manual

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| **F6.1** | Manual Claim Form | Disruption type + description input | P0 |
| **F6.2** | Photo Capture | Geo-tagged photo with EXIF | P0 |
| **F6.3** | Geo-Validation | Compare photo GPS vs telemetry | P0 |
| **F6.4** | Weather Corroboration | Verify weather at photo time/location | P1 |
| **F6.5** | Traffic Corroboration | Verify traffic at photo time/location | P1 |
| **F6.6** | Spam Score | Composite spam score (0–100) | P1 |
| **F6.7** | Auto-Reject | Reject if spam score ≥ 70 | P1 |
| **F6.8** | Admin Queue | Display claims sorted by spam | P1 |
| **F6.9** | Admin Approve/Reject | One-click decision | P1 |

### 7.7 Admin Dashboard

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| **F7.1** | Claims Queue | List pending manual claims | P1 |
| **F7.2** | Spam Sorting | Sort by ascending spam score | P1 |
| **F7.3** | Evidence Preview | Show photo + validation result | P1 |
| **F7.4** | Approve Action | Approve → trigger payout | P1 |
| **F7.5** | Reject Action | Reject → notify rider with reason | P1 |
| **F7.6** | Loss Ratio Display | Payouts / Premiums collected | P1 |

---

## 8. Functional Requirements

### 8.1 Authentication

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-01** | POST /api/riders/send-otp | Store mock OTP "123456" in Redis |
| **FR-02** | POST /api/riders/verify-otp | Return JWT on valid OTP |
| **FR-03** | GET /api/riders/me | Return authenticated rider profile |
| **FR-04** | All rider endpoints require JWT | Auth middleware enforced |

### 8.2 Rider Profile

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-05** | POST /api/riders/register | Create rider with platform, zone, slots |
| **FR-06** | PUT /api/riders/onboard | Save baseline earnings, return risk profile |
| **FR-07** | GET /api/riders/me/risk-profile | Return zone risk + volatility + explanation |

### 8.3 Policy Management

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-08** | GET /api/policies/quote | Return 3-tier pricing with breakdown |
| **FR-09** | POST /api/policies | Create policy for current calendar week |
| **FR-10** | GET /api/policies/active | Return active policy with coverage |
| **FR-11** | PUT /api/policies/{id}/renew | Renew for next week with recalculated premium |
| **FR-12** | DELETE /api/policies/{id} | Cancel policy |

### 8.4 Premium Engine

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-13** | GET /api/risk/premium | Return risk score + 3-tier pricing |
| **FR-14** | LightGBM model serving | Return disruption probability per slot |
| **FR-15** | Zone-based differentiation | High-risk zones priced higher |

### 8.5 Triggers

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-16** | GET /api/disruptions | List disruption events |
| **FR-17** | Trigger evaluation | Run every 5 min, evaluate zone × slot × rider |
| **FR-18** | 3-condition gate | trigger TRUE + rider online + earnings below baseline |

### 8.6 Claims — Auto

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-19** | GET /api/claims | List rider's claims |
| **FR-20** | GET /api/claims/{id} | Claim detail with breakdown |
| **FR-21** | Auto-create on disruption | Claims created for all affected riders |
| **FR-22** | Payout calculation | min(income loss, coverage limit) |
| **FR-23** | Basic fraud check | GPS + peer comparison |

### 8.7 Claims — Manual

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-24** | POST /api/claims/manual | Submit claim with photo |
| **FR-25** | GET /api/claims/manual/{id} | Check manual claim status |
| **FR-26** | Rate limiting | 1 manual claim per policy week |
| **FR-27** | EXIF extraction | Extract GPS + timestamp from photo |
| **FR-28** | Geo-validation | Haversine distance > 500m flagged |
| **FR-29** | Spam score | Composite from multiple signals |
| **FR-30** | Auto-reject threshold | Spam ≥ 70 auto-rejected |

### 8.8 Admin

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-31** | GET /api/admin/claims/manual | List pending claims sorted by spam |
| **FR-32** | POST /api/admin/claims/{id}/approve | Approve → trigger payout |
| **FR-33** | POST /api/admin/claims/{id}/reject | Reject → notify rider |

### 8.9 Payouts

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-34** | POST /api/payouts | Create payout record |
| **FR-35** | Mock UPI credit | Simulated instant credit |
| **FR-36** | Push notification | FCM or mock notification |

---

## 9. Non-Functional Requirements

### 9.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-01** | API response time | < 500ms for 95th percentile |
| **NFR-02** | Trigger evaluation | < 2 seconds per zone |
| **NFR-03** | Page load (PWA) | < 3 seconds on 3G |
| **NFR-04** | Photo upload | < 5 seconds for 5MB file |

### 9.2 Scalability

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-05** | Concurrent riders | Support 100+ (hackathon scale) |
| **NFR-06** | Database connections | Pool of 20 connections |
| **NFR-07** | Horizontal scaling | Ready for 2+ backend instances |

### 9.3 Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-08** | Uptime | 99% during demo window |
| **NFR-09** | Error handling | Graceful degradation on API failures |
| **NFR-10** | Retry logic | 3 retries with exponential backoff |

### 9.4 Security

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-11** | JWT encryption | HS256, secret in .env |
| **NFR-12** | Password handling | No plain text storage |
| **NFR-13** | Input validation | Pydantic models on all endpoints |
| **NFR-14** | Rate limiting | Applied to sensitive endpoints |

### 9.5 Data

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-15** | Synthetic seed data | 20 riders across 4 cities |
| **NFR-16** | Platform simulation | Realistic q-commerce patterns |
| **NFR-17** | Weather API | OpenWeatherMap polling every 5 min |

---

## 10. Success Metrics

### 10.1 Hackathon Demo Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **SM-1** | Registration completes | Rider can sign up and log in |
| **SM-2** | Policy purchases work | All 3 tiers purchasable |
| **SM-3** | Premium varies by zone | At least 2 different risk levels shown |
| **SM-4** | Disruption triggers fire | At least 1 demo scenario works |
| **SM-5** | Auto-payout occurs | Demo shows money credited |
| **SM-6** | Manual claim submits | Photo upload works |
| **SM-7** | Admin review works | Approve/reject functional |
| **SM-8** | Video length | ≤ 2 minutes |
| **SM-9** | No critical bugs | Flow runs end-to-end |

### 10.2 Functional Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **FM-1** | API tests pass | > 80% test coverage |
| **FM-2** | Response times met | NFR targets achieved |
| **FM-3** | All 5 triggers | Each trigger testable |
| **FM-4** | Spam detection | Score calculation verified |

### 10.3 Real-World Metrics (Future)

| Metric | Target | Timeline |
|--------|--------|----------|
| **RW-1** | Adoption rate | 10% of target riders in pilot zone |
| **RW-2** | Loss ratio | Payouts / Premiums < 60% |
| **RW-3** | Claim satisfaction | < 4 hour average resolution |
| **RW-4** | Fraud rate | < 5% of claims flagged |

---

## 11. Assumptions & Constraints

### 11.1 Hackathon Assumptions

| ID | Assumption | Impact |
|----|-----------|--------|
| **A1** | Team of 5 developers | Scope manageable for 2-week sprint |
| **A2** | Mock platforms only | No real Zepto/Blinkit/Swiggy API access |
| **A3** | Synthetic data | Realistic but simulated rider/zones |
| **A4** | Mock payment | No real UPI integration |
| **A5** | 5 triggers | Simplified from full roadmap |
| **A6** | Single city focus | Bengaluru for demo |

### 11.2 Technical Constraints

| ID | Constraint | Resolution |
|----|------------|------------|
| **C1** | No production ML | LightGBM on synthetic data |
| **C2** | Limited historical data | Use zone-level baselines |
| **C3** | No background app | PWA with polling |
| **C4** | Simulated platform data | PlatformSimulator module |

### 11.3 API Constraints

| ID | Constraint | Resolution |
|----|------------|------------|
| **C5** | No real weather API (production) | OpenWeatherMap free tier + mocks |
| **C6** | No real traffic API | Mocked congestion data |
| **C7** | No real platform API | Simulated order/dispatch data |

---

## 12. Risks & Mitigations

### 12.1 Technical Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| **R1** | ML model accuracy low | Medium | High | Use rule-based fallback, simplified features |
| **R2** | Trigger false positives | Medium | Medium | Multi-condition gate, fraud check |
| **R3** | Photo EXIF extraction fails | Low | High | Fallback to manual GPS entry |
| **R4** | Database connection issues | Low | High | Connection pooling, health checks |
| **R5** | Docker issues on judge machines | Medium | High | Clear README, docker-compose.yml |

### 12.2 Demo Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| **R6** | Video exceeds 2 minutes | Low | High | Pre-recorded, edited video |
| **R7** | Live demo fails | Medium | High | Backup video recording |
| **R8** | Network issues | Medium | High | Local-first, no external deps for demo |

### 12.3 Process Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| **R9** | Scope creep | High | Medium | Frozen scope after sprint 1 |
| **R10** | Integration issues | Medium | High | Daily integration builds |
| **R11** | Missing documentation | Medium | Medium | PRD + README + code comments |

---

## 13. Out of Scope

### 13.1 Explicitly Excluded

| Item | Reason |
|------|--------|
| **OS-1** | Health insurance | Out of product scope |
| **OS-2** | Life insurance | Out of product scope |
| **OS-3** | Vehicle damage coverage | Out of product scope |
| **OS-4** | Accident coverage | Out of product scope |
| **OS-5** | Real payments | Mock only for hackathon |
| **OS-6** | Production ML models | LightGBM on synthetic data |
| **OS-7** | Background push notifications | Polling-based instead |
| **OS-8** | iOS/Android native apps | PWA only |
| **OS-9** | Multi-city expansion | Single city for demo |
| **OS-10** | B2B platform integration | Simulated APIs only |

### 13.2 Future Phases

| Item | Status |
|------|--------|
| **F-1** | Advanced fraud detection (Neo4j graph) | Phase 3 |
| **F-2** | Causal AI models | Future |
| **F-3** | Real platform partnerships | Future |
| **F-4** | Guidewire integration | Future |
| **F-5** | Offline Deep RL pricing | Future |

---

## 14. Demo Script Flow (Judge-Facing Narrative)

### 14.1 Demo Overview

| Item | Details |
|------|--------|
| **Duration** | ≤ 2 minutes |
| **Format** | Pre-recorded video OR live demo with backup |
| **Platform** | Screen recording with voiceover |
| **Audience** | Hackathon judges |

### 14.2 Demo Storyboard

#### [0:00–0:15] OPENING — THE PROBLEM

> **Visual:** Split screen — Rider in rain vs. empty wallet
> 
> **Voiceover:** *"India's q-commerce riders earn ₹15,000–₹25,000/month. But 20–30% of that income disappears to rain, traffic, and store closures—with no protection. Traditional insurance doesn't work for them."*

---

#### [0:15–0:30] REGISTRATION FLOW

> **Visual:** PWA — Rider signs up
> 
> **Action 1:** Open PWA → Enter phone number
> 
> **Action 2:** Receive OTP (mock "123456") → Enter OTP → Logged in
> 
> **Action 3:** Link platform (select Zepto) → Select zone (Koramangala) → Select slots (6–11 PM)
> 
> **Voiceover:** *"Zylo starts with a simple mobile-first registration. Just your phone, platform, zone, and work hours—and you're in."*

---

#### [0:30–0:45] POLICY SELECTION + PREMIUM

> **Visual:** Policy tier selection screen
> 
> **Action 4:** View 3 tiers — Essential (₹20), Balanced (₹50), Max Protect (₹80)
> **Note:** Show high-risk zone premium higher than low-risk (demonstrate differentiation)
> 
> **Action 5:** Select "Balanced" → Pay via UPI mock → Policy activated
> 
> **Voiceover:** *"One weekly premium—aligned with how riders get paid. And it's personalized: high-risk zones pay more than low-risk zones."*

---

#### [0:45–1:00] ACTIVE POLICY + DASHBOARD

> **Visual:** Rider dashboard
> 
> **Action 6:** View active policy — Coverage: 5 slots, 20 hours remaining
> **Action 7:** View risk forecast — "Thursday high rain risk"
> 
> **Voiceover:** *"The rider sees their coverage and risk forecast for the week. Now the system monitors in the background."*

---

#### [1:00–1:15] AUTO DISRUPTION + TRIGGER

> **Visual:** Admin trigger dashboard (or log output)
> 
> **Action 8:** Inject HEAVY_RAIN disruption scenario
> **System:** Trigger fires — Rain > 40mm detected in Koramangala
> 
> **Voiceover:** *"When heavy rain hits—this system detects it automatically. No human involvement. Just data signals."*

---

#### [1:15–1:30] AUTO PAYOUT

> **Visual:** Rider phone notification + dashboard update
> 
> **Action 9:** Push notification — "💰 ₹540 credited — Rain disruption"
> **Action 10:** View payout breakdown — Expected ₹720, Actual ₹180, Loss ₹540, Limit ₹540
> **Action 11:** Dashboard shows payout history
> 
> **Voiceover:** *"Within minutes, the payout is automatic. Expected earnings minus actual—covered. That's parametric insurance."*

---

#### [1:30–1:45] MANUAL CLAIM FALLBACK

> **Visual:** Manual claim submission flow
> 
> **Action 12:** No auto-trigger fired → Rider taps "Request Manual Claim"
> **Action 13:** Select disruption type "Traffic" → Write description → Take photo
> **Action 14:** Submit → Status: "Under Review"
> 
> **Voiceover:** *"But what if the disruption is too local to trigger? The rider can submit a manual claim with a geo-tagged photo."*

---

#### [1:45–1:55] ADMIN REVIEW

> **Visual:** Admin dashboard
> 
> **Action 15:** Admin views queue — Claim appears with spam score "25/100" (low risk)
> **Action 16:** View evidence — Photo + geo-validation (✅ matches) + weather corroboration (✅)
> **Action 17:** Click "Approve" → Payout triggered
> 
> **Voiceover:** *"The admin seesCorroborated claims first, sorted by spam score. Low-risk claims are fast-tracked."*

---

#### [1:55–2:00] CLOSING

> **Visual:** Cycle repeats — Rider working, system protecting
> 
> **Voiceover:** *"Zylo: protection that actually works for gig workers. Registration, policy, auto-trigger, zero-touch payout. That's the hackathon demo."*

---

### 14.3 Demo Checklist

| Item | Status | Notes |
|------|--------|-------|
| [ ] Registration flow visible | Required | OTP → Zones → Slots |
| [ ] Premium differentiation shown | Required | High vs low risk |
| [ ] Auto trigger fires | Required | At least 1 trigger |
| [ ] Auto payout credited | Required | Mock UPI |
| [ ] Manual claim submits | Required | Photo upload |
| [ ] Admin approves | Required | Queue → Approve |
| [ ] Total time ≤ 2 min | Required | Record edited |

### 14.4 Backup Plan

| Scenario | Backup |
|----------|--------|
| Live demo fails | Pre-recorded video plays |
| Network down | Local demo runs |
| Device issue | Backup laptop ready |

---

## Appendix A: Technical Reference

### A.1 Tech Stack

| Layer | Technology |
|-------|------------|
| Mobile App | React Native / Next.js PWA |
| Admin UI | Next.js + TypeScript + Tailwind |
| API Layer | FastAPI (Python) |
| ML/AI | Python, LightGBM |
| Database | PostgreSQL 15 + TimescaleDB |
| Cache | Redis 7 |
| Event Streaming | Apache Kafka |
| Weather | OpenWeatherMap + Mock |
| Traffic | Google Maps / Mock |
| Payments | Mock UPI |
| Storage | Local FS (dev) |
| Deployment | Docker + Docker Compose |

### A.2 Database Schema Summary

| Table | Key Fields |
|-------|-----------|
| riders | id, phone, name, platform, zone_id, trust_score |
| policies | id, rider_id, tier, premium, week_start, week_end, status |
| micro_slots | id, rider_id, slot_start, slot_end, expected_earnings |
| claims | id, rider_id, policy_id, disruption_id, income_loss, payout |
| manual_claims | id, rider_id, disruption_type, photo_url, spam_score, status |
| payouts | id, claim_id, amount, upi_ref, status |
| disruption_events | id, zone_id, trigger_type, severity, started_at |

### A.3 API Endpoints Summary

```
POST   /api/riders/send-otp
POST   /api/riders/verify-otp
POST   /api/riders/register
GET    /api/riders/me
GET    /api/riders/me/risk-profile
GET    /api/policies/quote
POST   /api/policies
GET    /api/policies/active
GET    /api/risk/premium
GET    /api/disruptions
GET    /api/claims
GET    /api/claims/{id}
POST   /api/claims/manual
GET    /api/claims/manual/{id}
GET    /api/admin/claims/manual
POST   /api/admin/claims/{id}/approve
POST   /api/admin/claims/{id}/reject
```

---

## Appendix B: Risk Scores Reference

### B.1 Zone Risk Tiers

| Risk Level | Score Range | Example Areas | Weekly Premium |
|------------|------------|---------------|----------------|
| **Low** | 0–25 | Dry-season Pune suburb | ₹20–₹35 |
| **Medium** | 26–50 | Normal Hyderabad zone | ₹50–₹80 |
| **High** | 51–75 | Mumbai pre-monsoon | ₹80–₹120 |
| **Very High** | 76–100 | Coastal cyclone season | ₹120–₹150 |

### B.2 Trigger Thresholds

| Trigger | Threshold | Data Source |
|----------|-----------|-------------|
| Heavy Rain | > 40mm/hr | OpenWeatherMap |
| Traffic Congestion | > 80/100 for 60+ min | Google Maps/Mock |
| Store Closure | store_status = CLOSED | PlatformSimulator |
| Platform Outage | platform_status = DOWN | PlatformSimulator |
| Regulatory | curfew_active = TRUE | Mock data |

---

*Document Version: 1.0*  
*Created: March 2026*  
*For: Zylo Hackathon Team*