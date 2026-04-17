# Main Branch Review — 2026-04-16

## Scope
Reviewed current `origin/main` state for:
- functionality checks
- merge/conflict status
- hardcoded values
- leftover items

## 1) Functionality Check Results

### Backend
- Command run: `cd backend && python -m pytest -q tests`
- Initial issue: test collection failed because `aiosqlite` was missing.
- After installing `aiosqlite`, result: **26 passed, 1 skipped**.
- Observation: backend test dependency gap exists (`aiosqlite` is required for tests but not in `backend/requirements.txt`).

### Admin
- Commands run: `cd admin && npm install && npm run lint && npm run build`
- Result: **lint passed, build passed**.
- Observation: npm reported **2 vulnerabilities** in dependency tree (1 moderate, 1 high).

### Mobile
- Command run: `cd mobile && npm install`
- Result: install passed.
- Observation: no lint/test/build script is defined in `mobile/package.json`, so no automated quality check was executed for mobile code.

## 2) Conflict Check

- No merge conflict markers found (`<<<<<<<`, `=======`, `>>>>>>>`).
- Current branch HEAD equals `origin/main` commit (`0a37cc3`), so no branch drift/conflict at review time.

## 3) Hardcoded Values Found

### Credentials / defaults
- `backend/shared/config.py`
  - hardcoded DB URLs with `zylo:password@localhost`
  - hardcoded `JWT_SECRET_KEY`
  - hardcoded `ADMIN_PASSWORD = "changeme"`
  - hardcoded OTP bypass defaults (`OTP_DEV_BYPASS_ENABLED=True`, code `123456`)
- `docker-compose.prod.yml`
  - hardcoded `POSTGRES_PASSWORD: ankush`
  - hardcoded DB connection strings embedding `postgres:ankush`

### Localhost/environment coupling
- `mobile/services/api.ts`
  - fallback API base candidates include hardcoded localhost values.
- `admin/src/lib/api.ts`
  - default API fallback uses `http://localhost:8000` in browser.

### Hardcoded fallback business data
- `mobile/app/(auth)/register.tsx`
  - hardcoded platform fallback list (Zepto/Blinkit/Swiggy) when config API fails.

## 4) Leftover / Cleanup Items

- `backend/ml/training/generate_synthetic_data.py`
  - contains stale TODO header (`TODO (Dev 2): Implement this script`) even though implementation exists.
- `backend/tmp_cleanup_zones.py`
  - one-off cleanup script with hardcoded local DB credentials appears to be temporary/operational residue.
- `mobile/app/(auth)/slot-select.tsx` and `mobile/app/policy/select.tsx`
  - contains development `console.log` debug statements.

## 5) Recommended Follow-ups

1. Add missing test dependency (`aiosqlite`) to backend dependency management.
2. Move all credentials/secrets to environment variables (especially prod compose + backend defaults).
3. Replace/remove dev OTP bypass defaults for non-dev runtime.
4. Remove or gate mobile debug logs.
5. Remove/archive `tmp_cleanup_zones.py` if no longer needed.
6. Clean stale TODO in synthetic data generator docstring.
7. Run `npm audit` remediation workflow for admin dependency vulnerabilities.
