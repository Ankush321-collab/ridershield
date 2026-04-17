# TASK-2: Policy Service + Premium Engine + ML Model
## Owner: Developer 2
## Branch: feature/task2-policy-service
## Status: In Progress

This branch contains the implementation of:
- Policy Service (REST API endpoints for policy management)
- Premium/Risk Calculation Engine (zone-based premium pricing)
- ML Model Integration (risk prediction using LightGBM)

### Key Components:
- `models.py` — SQLAlchemy models for Policy and MicroSlot tables
- `router.py` — FastAPI endpoints for policy operations
- `service.py` — Business logic for policy management
- `schemas.py` — Pydantic models for request/response validation
- `premium_service/` — Risk scoring and premium calculation
- `ml/` — ML model serving and prediction

### Database Tables:
- `policies` — Active rider policies with coverage tracking
- `micro_slots` — Zone + time slot risk data
- `zones` — Geographic zones with risk scores

### Development Status:
- ✅ Database models created
- ✅ ML model trained and integrated
- ⏳ API endpoints in development
- ⏳ Integration testing pending
