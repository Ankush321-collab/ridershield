export type ClaimStatus = "pending" | "approved" | "rejected" | "paid" | "under_review";

export type TriggerType =
  | "heavy_rain"
  | "extreme_heat"
  | "traffic_congestion"
  | "store_closure"
  | "platform_outage"
  | "regulatory_curfew"
  | "gps_shadowban"
  | "dark_store_queue"
  | "algorithmic_shock"
  | "community_signal";

export interface AutoClaim {
  id: string;
  rider_id: string;
  rider_name?: string | null;
  type: "auto" | "manual";
  disruption_type?: string | null;
  income_loss: number;
  payout_amount: number;
  fraud_score: number;
  status: ClaimStatus;
  created_at: string;
}

export interface ManualClaimReview {
  id: string;
  claim_id: string | null;
  rider_id: string;
  rider_name?: string | null;
  zone_name?: string | null;
  disruption_type: string;
  description?: string | null;
  photo_path?: string | null;
  photo_url?: string | null;
  spam_score: number;
  geo_valid?: boolean | null;
  gps_distance_m?: number | null;
  weather_match?: boolean | null;
  traffic_match?: boolean | null;
  review_status: string;
  reviewer_notes?: string | null;
  created_at: string;
  reviewed_at?: string | null;
}

export interface ActiveTrigger {
  trigger_id: string;
  type: string;
  zone: string;
  zone_id: string;
  threshold: string;
  active_since: string;
  affected_riders: number;
  severity: string;
}

export interface CommunitySignal {
  zone: string;
  zone_id: string;
  affected_pct: number;
  threshold_pct: number;
  affected_riders: number;
  total_riders: number;
  detected_at: string;
}

export interface TriggerStatusResponse {
  active_triggers: ActiveTrigger[];
  community_signals: CommunitySignal[];
  last_evaluation: string;
}

export interface DisruptionEvent {
  event_id: string;
  trigger_type: string;
  zone: string;
  zone_id: string;
  slot: string;
  severity: string;
  affected_riders: number;
  data?: Record<string, unknown> | null;
  created_at: string;
}

export interface Zone {
  id: string;
  name: string;
  city: string;
  risk_score: number;
  lat?: number | null;
  lon?: number | null;
}

export interface DashboardStats {
  total_claims: number;
  pending_review: number;
  active_triggers: number;
  loss_ratio: number;
  total_payouts: number;
  total_income_loss: number;
  bcr: number;
  pool_status: string;
}

export interface PoolHealth {
  bcr: number;
  target_bcr: number;
  status: "sustainable" | "caution" | "critical";
  assessment: string;
  pool_balance: number;
  total_premiums_collected: number;
  total_payouts_disbursed: number;
  coverage_utilization: number;
  active_policies: number;
  active_riders: number;
}

export interface FraudAlertItem {
  claim_id: string;
  rider_id: string;
  rider_name?: string | null;
  disruption_type?: string | null;
  fraud_score: number;
  status: string;
  payout_amount: number;
  created_at: string;
}

export interface PredictiveZoneForecast {
  zone_id: string;
  zone: string;
  city: string;
  risk_score: number;
  recent_event_count: number;
  max_predicted_risk: number;
  forecast: Array<{
    date: string;
    day_of_week: number;
    predicted_disruption_probability: number;
    risk_band: string;
    expected_earnings_multiplier: number;
  }>;
}

export interface OverviewData {
  autoClaims: AutoClaim[];
  manualClaims: ManualClaimReview[];
  triggerStatus: TriggerStatusResponse;
  stats: DashboardStats;
  poolHealth: PoolHealth | null;
}

export const TRIGGER_LABELS: Record<string, string> = {
  heavy_rain: "Heavy Rain",
  extreme_heat: "Extreme Heat",
  traffic_congestion: "Traffic Congestion",
  store_closure: "Store Closure",
  platform_outage: "Platform Outage",
  regulatory_curfew: "Regulatory Curfew",
  gps_shadowban: "GPS Shadowban",
  dark_store_queue: "Dark Store Queue",
  algorithmic_shock: "Algorithmic Shock",
  community_signal: "Community Signal",
};

export const TRIGGER_EMOJI: Record<string, string> = {
  heavy_rain: "\u{1F327}\uFE0F",
  extreme_heat: "\u{1F321}\uFE0F",
  traffic_congestion: "\u{1F697}",
  store_closure: "\u{1F3EA}",
  platform_outage: "\u{1F4F1}",
  regulatory_curfew: "\u{1F6AB}",
  gps_shadowban: "\u{1F4CD}",
  dark_store_queue: "\u{1F6D2}",
  algorithmic_shock: "\u26A1",
  community_signal: "\u{1F4E3}",
};

export const STATUS_STYLES: Record<string, string> = {
  pending:      "badge badge-amber",
  under_review: "badge badge-purple",
  approved:     "badge badge-cyan",
  paid:         "badge badge-emerald",
  rejected:     "badge badge-rose",
};
