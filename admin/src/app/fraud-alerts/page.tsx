"use client";

import { useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";

import { adminApi } from "@/lib/api";
import { formatCurrency, formatRelativeTime, formatTriggerWithEmoji } from "@/lib/format";
import type { FraudAlertItem } from "@/lib/types";
import { STATUS_STYLES } from "@/lib/types";
import { PageContainer } from "@/components/PageContainer";

export default function FraudAlertsPage() {
  const [alerts, setAlerts] = useState<FraudAlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        await adminApi.autoLogin();
        const response = await adminApi.claims.fraudAlerts(70);
        if (!active) return;
        setAlerts(response.alerts);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load fraud alerts.");
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    const interval = window.setInterval(() => void load(), 30000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  return (
    <PageContainer>
      <div className="space-y-6">
        <div>
          <div className="text-[9px] font-black uppercase tracking-[0.25em] mb-2.5" style={{ color: "var(--text-muted)" }}>
            Fraud Intelligence
          </div>
          <h1 className="text-3xl font-black tracking-tight mb-1" style={{ color: "var(--text-primary)" }}>
            Dedicated Fraud Alert Queue
          </h1>
        </div>

        {error && (
          <div className="rounded-2xl p-4 text-sm font-medium" style={{ background: "rgba(244,63,94,0.08)", color: "#fca5a5" }}>
            {error}
          </div>
        )}

        <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-surface)" }}>
          <table className="min-w-full text-sm">
            <thead>
              <tr style={{ background: "var(--bg-elevated)", borderBottom: "1px solid var(--border-subtle)" }}>
                {["Claim", "Rider", "Trigger", "Fraud Score", "Payout", "Status", "Time"].map((col) => (
                  <th key={col} className="px-5 py-4 text-left text-[9px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td className="px-5 py-10 text-xs" colSpan={7}>Loading...</td></tr>
              ) : alerts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-16 text-center">
                    <ShieldAlert className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--text-muted)" }} />
                    <div className="text-xs font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                      No high-risk alerts
                    </div>
                  </td>
                </tr>
              ) : (
                alerts.map((alert) => (
                  <tr key={alert.claim_id} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    <td className="px-5 py-4 font-mono">{alert.claim_id.slice(0, 8)}</td>
                    <td className="px-5 py-4">{alert.rider_name || alert.rider_id.slice(0, 8)}</td>
                    <td className="px-5 py-4">{formatTriggerWithEmoji(alert.disruption_type)}</td>
                    <td className="px-5 py-4 font-bold" style={{ color: alert.fraud_score >= 85 ? "#fb7185" : "#f59e0b" }}>
                      {alert.fraud_score}
                    </td>
                    <td className="px-5 py-4">{formatCurrency(alert.payout_amount)}</td>
                    <td className="px-5 py-4">
                      <span className={STATUS_STYLES[alert.status] || STATUS_STYLES.pending}>{alert.status}</span>
                    </td>
                    <td className="px-5 py-4">{formatRelativeTime(alert.created_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </PageContainer>
  );
}
