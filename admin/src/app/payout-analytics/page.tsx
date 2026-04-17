"use client";

import { useEffect, useMemo, useState } from "react";

import { adminApi } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { PageContainer } from "@/components/PageContainer";

type PayoutAnalytics = {
  window_days: number;
  total_payout_amount: number;
  payout_count: number;
  by_trigger: Array<{ trigger_type: string; amount: number }>;
  by_zone: Array<{ zone: string; amount: number }>;
  daily_trend: Array<{ date: string; amount: number }>;
};

export default function PayoutAnalyticsPage() {
  const [data, setData] = useState<PayoutAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        await adminApi.autoLogin();
        const response = await adminApi.analytics.payouts(14);
        setData(response);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load payout analytics.");
      }
    };
    void load();
  }, []);

  const topTrigger = useMemo(() => data?.by_trigger[0], [data]);
  const topZone = useMemo(() => data?.by_zone[0], [data]);

  return (
    <PageContainer>
      <div className="space-y-8">
        <div>
          <div className="text-[9px] font-black uppercase tracking-[0.25em] mb-2.5" style={{ color: "var(--text-muted)" }}>
            Payout Analytics
          </div>
          <h1 className="text-3xl font-black tracking-tight mb-1" style={{ color: "var(--text-primary)" }}>
            Trigger/Zone/Time Breakdown
          </h1>
        </div>

        {error && (
          <div className="rounded-2xl p-4 text-sm font-medium" style={{ background: "rgba(244,63,94,0.08)", color: "#fca5a5" }}>
            {error}
          </div>
        )}

        {data && (
          <div className="grid gap-4 md:grid-cols-3">
            <div className="card p-6" style={{ background: "var(--bg-surface)" }}>
              <div className="text-[10px] font-black uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>Total payouts</div>
              <div className="text-3xl font-black" style={{ color: "#10b981" }}>{formatCurrency(data.total_payout_amount)}</div>
            </div>
            <div className="card p-6" style={{ background: "var(--bg-surface)" }}>
              <div className="text-[10px] font-black uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>Top trigger</div>
              <div className="text-lg font-black" style={{ color: "var(--text-primary)" }}>{topTrigger?.trigger_type || "—"}</div>
              <div className="text-sm" style={{ color: "#a78bfa" }}>{topTrigger ? formatCurrency(topTrigger.amount) : "—"}</div>
            </div>
            <div className="card p-6" style={{ background: "var(--bg-surface)" }}>
              <div className="text-[10px] font-black uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>Top zone</div>
              <div className="text-lg font-black" style={{ color: "var(--text-primary)" }}>{topZone?.zone || "—"}</div>
              <div className="text-sm" style={{ color: "#38bdf8" }}>{topZone ? formatCurrency(topZone.amount) : "—"}</div>
            </div>
          </div>
        )}

        <div className="grid gap-6 xl:grid-cols-2">
          <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-surface)" }}>
            <table className="min-w-full text-sm">
              <thead><tr style={{ background: "var(--bg-elevated)" }}><th className="px-5 py-4 text-left text-[9px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Trigger</th><th className="px-5 py-4 text-left text-[9px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Amount</th></tr></thead>
              <tbody>
                {data?.by_trigger.map((row) => (
                  <tr key={row.trigger_type} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    <td className="px-5 py-4">{row.trigger_type}</td>
                    <td className="px-5 py-4">{formatCurrency(row.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-surface)" }}>
            <table className="min-w-full text-sm">
              <thead><tr style={{ background: "var(--bg-elevated)" }}><th className="px-5 py-4 text-left text-[9px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Date</th><th className="px-5 py-4 text-left text-[9px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Amount</th></tr></thead>
              <tbody>
                {data?.daily_trend.map((row) => (
                  <tr key={row.date} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    <td className="px-5 py-4">{row.date}</td>
                    <td className="px-5 py-4">{formatCurrency(row.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
