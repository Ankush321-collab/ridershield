import Constants from 'expo-constants';
import { Platform } from 'react-native';

const currentHostname =
  typeof globalThis !== 'undefined' && 'location' in globalThis
    ? globalThis.location?.hostname || ''
    : '';
const currentProtocol =
  typeof globalThis !== 'undefined' && 'location' in globalThis
    ? globalThis.location?.protocol || 'http:'
    : 'http:';
const expoHost =
  Constants.expoConfig?.hostUri?.split(':')[0] ||
  Constants.manifest2?.extra?.expoClient?.hostUri?.split(':')[0] ||
  Constants.manifest?.debuggerHost?.split(':')[0] ||
  currentHostname;

const configuredApiBase = process.env.EXPO_PUBLIC_API_URL?.trim() || '';
const defaultCandidates = [
  configuredApiBase,
  currentHostname && currentHostname !== 'localhost' && currentHostname !== '127.0.0.1'
    ? `${currentProtocol === 'https:' ? 'https' : 'http'}://${currentHostname}:8000`
    : '',
  expoHost ? `http://${expoHost}:8000` : '',
  Platform.OS === 'android' ? 'http://10.0.2.2:8000' : '',
  'http://18.60.19.96:8000',
].filter(Boolean);

const API_CANDIDATES = [...new Set(defaultCandidates)];
const API_BASE = API_CANDIDATES[0] || 'http://18.60.19.96:8000';

let resolvedApiBase: string | null = configuredApiBase || null;
let resolvingApiBase: Promise<string> | null = null;

async function probeApiBase(baseUrl: string) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 1500);

  try {
    const response = await fetch(`${baseUrl}/health`, {
      method: 'GET',
      signal: controller.signal,
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

async function resolveApiBase() {
  if (resolvedApiBase) {
    return resolvedApiBase;
  }

  if (!resolvingApiBase) {
    resolvingApiBase = (async () => {
      for (const candidate of API_CANDIDATES) {
        if (await probeApiBase(candidate)) {
          resolvedApiBase = candidate;
          return candidate;
        }
      }

      throw new Error(
        `Unable to reach backend. Tried: ${API_CANDIDATES.join(', ')}. ` +
          `Set EXPO_PUBLIC_API_URL to your machine's reachable backend URL if needed.`
      );
    })().finally(() => {
      resolvingApiBase = null;
    });
  }

  return resolvingApiBase;
}

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

export interface RiderProfile {
  rider_id: string;
  name: string;
  phone: string;
  platform: string;
  city: string;
  zone_id: string;
  zone?: string | null;
  upi_id?: string | null;
  kyc_status: string;
  trust_score: number;
  jwt_token?: string | null;
}

export interface RiskProfile {
  zone_flood_risk: number;
  zone_traffic_risk: number;
  income_volatility: number;
  composite_risk_score: number;
  four_week_earnings?: Record<string, number> | null;
  avg_per_slot: Record<string, number>;
}

export interface RiderIntelligenceResponse {
  zone: string;
  next_week_forecast: Array<{
    date: string;
    day_of_week: number;
    predicted_disruption_probability: number;
    risk_band: string;
    expected_earnings_multiplier: number;
  }>;
  forward_alerts: Array<{
    type: string;
    severity: string;
    message: string;
    dates?: string[];
    triggers?: string[];
    coverage_used_ratio?: number;
  }>;
  recent_zone_events: Array<{
    trigger_type: string;
    severity: string;
    created_at: string | null;
    affected_riders: number;
  }>;
}

export interface Zone {
  id: string;
  name: string;
  city: string;
  risk_score?: number;
  flood_risk?: number;
  traffic_risk?: number;
  store_risk?: number;
  lat?: number;
  lon?: number;
}

export interface PolicyQuoteTier {
  tier: 'essential' | 'balanced' | 'max_protect';
  weekly_premium: number;
  coverage_pct: number;
  coverage_limit: number;
  slots_covered: number;
  risk_breakdown: {
    weather: number;
    traffic: number;
    store: number;
  };
}

export interface PolicySlotBreakdown {
  slot: string;
  expected_earnings: number;
  risk_score: number;
  premium?: number;
}

export interface PolicyQuoteResponse {
  quotes: PolicyQuoteTier[];
  zone_name: string;
  zone_risk_score: number;
  slot_breakdown: PolicySlotBreakdown[];
  valid_until: string;
  explanation?: string;
}

export interface PolicyResponse {
  policy_id: string;
  rider_id: string;
  plan_tier: string;
  coverage_week: string;
  premium: number;
  premium_paid: number;
  coverage_limit: number;
  coverage_pct: number;
  coverage_used?: number;
  status: string;
  slots_covered: string[];
  hours_remaining?: number;
  payment_method?: string;
  upi_id?: string | null;
  created_at?: string | null;
  expires_at?: string | null;
}

export interface TriggerStatus {
  active_triggers: Array<{
    trigger_id: string;
    type: string;
    zone: string;
    zone_id: string;
    threshold: string;
    active_since: string;
    affected_riders: number;
    severity: string;
  }>;
  community_signals: Array<{
    zone: string;
    zone_id: string;
    affected_pct: number;
    threshold_pct: number;
    affected_riders: number;
    total_riders: number;
    detected_at: string;
  }>;
  last_evaluation: string;
}

export interface ClaimListItem {
  claim_id: string;
  type: string;
  disruption_type: string;
  income_loss: number;
  payout_amount: number;
  fraud_score: number;
  status: string;
  created_at: string;
}

export interface PayoutListItem {
  payout_id: string;
  claim_id: string;
  amount: number;
  method: string;
  upi_id: string | null;
  status: string;
  reference_id: string;
  created_at: string;
}

export interface ManualClaimSubmitResponse {
  claim_id?: string;
  manual_claim_id?: string;
  status: string;
  spam_score: number;
  message: string;
  rejection_reasons: string[];
}

export interface OtpVerifyResponse {
  valid: boolean;
  temp_token?: string | null;
  jwt_token?: string | null;
  is_registered: boolean;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  clearToken() {
    this.token = null;
  }

  private async request<T>(
    method: HttpMethod,
    path: string,
    body?: unknown,
    isFormData = false,
    extraHeaders?: Record<string, string>
  ): Promise<T> {
    const apiBase = await resolveApiBase();
    const headers: Record<string, string> = { ...(extraHeaders || {}) };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }

    let res: Response;
    try {
      res = await fetch(`${apiBase}${path}`, {
        method,
        headers,
        body: isFormData ? (body as FormData) : body ? JSON.stringify(body) : undefined,
      });
    } catch {
      resolvedApiBase = null;
      throw new Error(
        `Unable to reach backend at ${apiBase}. ` +
          `Set EXPO_PUBLIC_API_URL if your backend is running on a different host.`
      );
    }

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      const detail = error?.detail;
      if (typeof detail === 'string') {
        throw new Error(detail);
      }
      throw new Error(detail?.message || detail?.error?.message || `API Error: ${res.status}`);
    }

    if (res.status === 204) return {} as T;
    return res.json() as Promise<T>;
  }

  riders = {
    sendOtp: (phone: string) =>
      this.request<{ message: string; expires_in: number; dev_otp?: string }>('POST', '/api/riders/send-otp', { phone }),

    verifyOtp: (phone: string, otp: string) =>
      this.request<OtpVerifyResponse>('POST', '/api/riders/verify-otp', { phone, otp }),

    register: (
      data: { name: string; platform: string; city: string; zone_id: string; slots: string[]; upi_id: string },
      tempToken?: string
    ) =>
      this.request<RiderProfile>(
        'POST',
        '/api/riders/register',
        data,
        false,
        tempToken ? { Authorization: `Bearer ${tempToken}` } : undefined
      ),

    onboard: (data: { typical_slots: string[]; plan_tier: string }) =>
      this.request<unknown>('POST', '/api/riders/onboard', data),

    getMe: () =>
      this.request<RiderProfile>('GET', '/api/riders/me'),

    getRiskProfile: () =>
      this.request<RiskProfile>('GET', '/api/riders/me/risk-profile'),

    getIntelligence: (days = 7) =>
      this.request<RiderIntelligenceResponse>('GET', `/api/riders/me/intelligence?days=${encodeURIComponent(String(days))}`),
  };

  zones = {
    list: async () => {
      try {
        return await this.request<{ zones: Zone[] }>('GET', '/api/zones');
      } catch (primaryError) {
        try {
          return await this.request<{ zones: Zone[] }>('GET', '/api/riders/zones');
        } catch {
          throw primaryError;
        }
      }
    },
  };

  config = {
    get: () =>
      this.request<{
        platforms: { id: string; name: string; icon: string }[];
        trigger_types: { type: string; label: string; icon: string }[];
      }>('GET', '/api/config'),
  };

  policies = {
    getQuote: (slots: string, city: string) =>
      this.request<PolicyQuoteResponse>('GET', `/api/policies/quote?slots=${encodeURIComponent(slots)}&city=${encodeURIComponent(city)}`),

    create: (data: { plan_tier: string; payment_method: string; upi_id: string; slots?: string[] }) =>
      this.request<PolicyResponse>('POST', '/api/policies', data),

    getActive: () =>
      this.request<PolicyResponse>('GET', '/api/policies/active'),

    getById: (policyId: string) =>
      this.request<PolicyResponse>('GET', `/api/policies/${policyId}`),

    renew: (policyId: string, plan_tier?: string) =>
      this.request<unknown>('PUT', `/api/policies/${policyId}/renew`, plan_tier ? { plan_tier } : {}),

    cancel: (policyId: string) =>
      this.request<void>('DELETE', `/api/policies/${policyId}`),
  };

  risk = {
    getPremium: (data: { zone?: string; slots: string[]; plan_tier: string; rider_tenure_days?: number }) =>
      this.request<{
        risk_score: number;
        zone_risk_score: number;
        disruption_probability: number;
        premium: Record<string, number>;
        explanation: string;
        tenure_discount: number;
        breakdown: Array<{ slot: string; risk: number; premium: number }>;
        slot_breakdown: PolicySlotBreakdown[];
        zone_name: string;
      }>('POST', '/api/risk/premium', data),
  };

  triggers = {
    getStatus: () =>
      this.request<TriggerStatus>('GET', '/api/triggers/status'),

    getDisruptionEvents: (zone?: string, from?: string) => {
      const params = new URLSearchParams();
      if (zone) params.set('zone', zone);
      if (from) params.set('from', from);
      const query = params.toString();
      return this.request<unknown>('GET', `/api/triggers/disruption-events${query ? `?${query}` : ''}`);
    },
  };

  claims = {
    list: () =>
      this.request<{ claims: ClaimListItem[] }>('GET', '/api/claims'),

    getById: (claimId: string) =>
      this.request<unknown>('GET', `/api/claims/${claimId}`),
  };

  payouts = {
    list: () =>
      this.request<{ payouts: PayoutListItem[] }>('GET', '/api/payouts'),
  };

  manualClaims = {
    submit: (formData: FormData) =>
      this.request<ManualClaimSubmitResponse>('POST', '/api/claims/manual', formData, true),

    getStatus: (claimId: string) =>
      this.request<unknown>('GET', `/api/claims/manual/${claimId}`),
  };

  health = () =>
    this.request<{ status: string }>('GET', '/health');
}

export const api = new ApiClient();
export { API_BASE };
