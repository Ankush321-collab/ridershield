# Zylo — Parametric Insurance for Quick-Commerce Riders

## What This Is

Zylo is an AI-powered parametric insurance platform that protects quick-commerce delivery riders (Blinkit, Zepto, Instamart) from income loss caused by external disruptions — heavy rain, flooding, traffic congestion, dark store shutdowns, AQI spikes, or government curfews. The system automatically detects disruptions via external APIs and rider activity signals, then triggers compensation payouts without any manual claims process. Built as a hackathon/prototype using simulated (Stripe test mode) payouts.

## Core Value

Riders get paid automatically when external disruptions kill their income — zero claims, zero paperwork, zero delay.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Rider can register, onboard, and buy a weekly insurance policy
- [ ] System monitors parametric triggers (weather, traffic, AQI, dark store status, rider activity)
- [ ] Disruption detection agent fires when triggers are breached
- [ ] Claim automation creates payouts for affected riders without human intervention
- [ ] Fraud detection validates claims before payout (Isolation Forest)
- [ ] Simulated payout sent to rider wallet via Stripe test mode
- [ ] Rider receives in-app push notification when disruption detected and when payout is sent
- [ ] Admin dashboard shows disruption heatmap, claims, payout analytics, and fraud flags
- [ ] Community Signal Agent detects disruptions from rider order-drop patterns (>70% drop)
- [ ] Risk prediction model calculates dynamic premium based on zone risk score

### Out of Scope

- IRDAI licensing / real insurance compliance — prototype only
- Real money movement (using Stripe test mode, not production)
- Native iOS/Android build — React Native or Expo for cross-platform
- SMS / IVR channels — push notification only for v1
- International zones — India-specific (Hyderabad default zone)
- B2B API for platforms to embed — not in v1

## Context

- **Target persona:** Rohit — Blinkit rider, Hyderabad/Gachibowli zone, ~100 orders/day, ₹15/order = ₹1500/day income
- **Disruption example:** Heavy rain → orders drop 100→30, income drops ₹1500→₹450 (loss ₹1050), payout = min(₹1050, ₹800) = ₹800
- **Parametric triggers (key):** rainfall_mm > 40, traffic_index > 80, AQI > 300, dark_store_status = closed, curfew_active = TRUE, order_drop > 70%
- **Community Signal:** Redundant detection — if 70%+ of riders in a zone show order drops, disruption is confirmed even without external API data
- **Prototype context:** Hackathon build — focus on demo-ability, working flows end-to-end, no real compliance overhead
- **Simulated payments:** Stripe test mode (not Razorpay, per user correction) — payout reflects in rider wallet balance in DB

## Constraints

- **Tech Stack:** FastAPI (Python) backend, Next.js (TypeScript, Tailwind) for admin dashboard, React Native / Expo for rider mobile app, PostgreSQL + Redis, Kafka for event streaming, LangGraph + LangChain for agents, Scikit-learn + PyTorch for ML, Stripe (test mode) for payments
- **External APIs:** OpenWeatherMap, Google Maps Traffic API
- **Scope:** Prototype/hackathon — no production-grade compliance, no real money

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Stripe test mode over Razorpay | User correction — use Stripe test not Razorpay | — Pending |
| Both rider app + admin dashboard in v1 | User wants both shipped together | — Pending |
| React Native / Expo for mobile | Cross-platform, JS ecosystem, faster hackathon delivery | — Pending |
| LangGraph for agents | Stateful multi-step agent workflows with LangChain | — Pending |
| Isolation Forest for fraud detection | Lightweight anomaly detection, fits rider GPS + claim pattern features | — Pending |
| Kafka for event streaming | Decouple data ingestion from agent processing, real-time disruption pipeline | — Pending |

---
*Last updated: 2026-03-17 after initialization*
