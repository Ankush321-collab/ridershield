"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  DollarSign,
  ShieldAlert,
  User,
  Activity,
} from "lucide-react";

import { adminApi } from "@/lib/api";
import { formatCurrency, formatTriggerWithEmoji, shortId } from "@/lib/format";
import BorderGlow from "@/components/ui/BorderGlow";
import type { AutoClaim } from "@/lib/types";
import { STATUS_STYLES } from "@/lib/types";
import { PageContainer } from "@/components/PageContainer";

const STATUS_FILTERS = ["all", "pending", "approved", "paid", "rejected"] as const;

const TRIGGER_FILTER_LABELS: Record<string, string> = {
  heavy_rain: "🌧 Rain",
  extreme_heat: "🌡️ Heat",
  traffic_congestion: "🚗 Traffic",
  store_closure: "🏪 Closure",
  platform_outage: "📱 Outage",
};

export default function ClaimsPage() {
  const [claims, setClaims] = useState<AutoClaim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]>("all");
  const [triggerFilter, setTriggerFilter] = useState("all");

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        await adminApi.autoLogin();
        const response = await adminApi.claims.listAll();
        if (!active) return;
        setClaims(response.claims);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load claims.");
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    const interval = window.setInterval(() => void load(), 30000);
    return () => { active = false; window.clearInterval(interval); };
  }, []);

  const triggerOptions = useMemo(
    () => ["all", ...Array.from(new Set(claims.map((c) => c.disruption_type).filter(Boolean) as string[]))],
    [claims],
  );

  const filteredClaims = useMemo(
    () =>
      claims.filter((c) => {
        const matchStatus = statusFilter === "all" || c.status === statusFilter;
        const matchTrigger = triggerFilter === "all" || c.disruption_type === triggerFilter;
        return matchStatus && matchTrigger;
      }),
    [claims, statusFilter, triggerFilter],
  );

  const summary = useMemo(() => {
    const totalPayouts = filteredClaims.reduce((s, c) => s + c.payout_amount, 0);
    const avgFraud = filteredClaims.length
      ? filteredClaims.reduce((s, c) => s + c.fraud_score, 0) / filteredClaims.length
      : 0;
    return { totalClaims: filteredClaims.length, totalPayouts, avgFraud };
  }, [filteredClaims]);

  const statCards = [
    {
      label: "Pipeline Count",
      value: summary.totalClaims.toString(),
      icon: FileText,
      color: "#7c3aed",
      bg: "rgba(124,58,237,0.08)",
    },
    {
      label: "Aggregate Payout",
      value: formatCurrency(summary.totalPayouts),
      icon: DollarSign,
      color: "#10b981",
      bg: "rgba(16,185,129,0.07)",
    },
    {
      label: "Trust Index (Avg)",
      value: `${Math.round(summary.avgFraud)}%`,
      icon: ShieldAlert,
      color: "#f59e0b",
      bg: "rgba(245,158,11,0.07)",
    },
  ];

  return (
    <PageContainer>
      <div className="space-y-8">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="text-[9px] font-black uppercase tracking-[0.25em] mb-2.5" style={{ color: "var(--text-muted)" }}>
            Claims Management
          </div>
          <h1 className="text-3xl font-black tracking-tight mb-1" style={{ color: "var(--text-primary)" }}>
            Automated Payouts
          </h1>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Verified claims triggered by real-time network anomalies
          </p>
        </motion.div>

        {error && (
          <div
            className="rounded-2xl p-4 text-sm font-medium"
            style={{ background: "rgba(244,63,94,0.07)", color: "#fca5a5" }}
          >
            {error}
          </div>
        )}

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          {statCards.map((s, idx) => {
            const Icon = s.icon;
            return (
              <motion.div
                key={s.label}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.08 }}
              >
                <BorderGlow animated={false} backgroundColor="#000000" colors={[s.color, "#000000", s.color]} className="flex-1 w-full">
                  <div className="card p-5 h-full bg-transparent border-none">
                    <div className="flex items-center gap-3 mb-4">
                      <div
                        className="flex items-center justify-center rounded-xl"
                        style={{ width: 34, height: 34, background: s.bg, border: `1px solid ${s.color}20` }}
                      >
                        <Icon className="w-4 h-4" style={{ color: s.color }} />
                      </div>
                      <span className="text-[9px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                        {s.label}
                      </span>
                    </div>
                    <div className="text-2xl font-black" style={{ color: s.color }}>
                      {s.value}
                    </div>
                  </div>
                </BorderGlow>
              </motion.div>
            );
          })}
        </div>

        {/* Filters (Compact) */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl p-5"
          style={{ background: "var(--bg-surface)" }}
        >
          <div className="flex flex-col md:flex-row items-center gap-5">
            <div className="flex items-center gap-2 min-w-fit">
              <div className="text-[9px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                Filters:
              </div>
            </div>
            
            <div className="flex flex-1 flex-col md:flex-row gap-4 w-full">
              <div className="flex items-center gap-3 w-full md:w-auto">
                <span className="text-[9px] font-bold uppercase tracking-widest flex-shrink-0" style={{ color: "var(--text-muted)" }}>State</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as "all" | "pending" | "approved" | "paid" | "rejected")}
                  className="flex-1 md:w-40 rounded-xl px-4 py-2.5 text-xs font-bold outline-none appearance-none transition-all cursor-pointer"
                  style={{
                    background: "var(--bg-elevated)", border: "none", color: "var(--text-primary)",
                  }}
                >
                  {STATUS_FILTERS.map((f) => (
                    <option key={f} value={f} style={{ background: "#111", color: "#fff" }}>{f.toUpperCase()}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-3 w-full md:w-auto">
                <span className="text-[9px] font-bold uppercase tracking-widest flex-shrink-0" style={{ color: "var(--text-muted)" }}>Source</span>
                <select
                  value={triggerFilter}
                  onChange={(e) => setTriggerFilter(e.target.value)}
                  className="flex-1 md:w-48 rounded-xl px-4 py-2.5 text-xs font-bold outline-none appearance-none transition-all cursor-pointer"
                  style={{
                    background: "var(--bg-elevated)", border: "none", color: "var(--text-primary)",
                  }}
                >
                  {triggerOptions.map((f) => (
                    <option key={f} value={f} style={{ background: "#111", color: "#fff" }}>
                      {f === "all" ? "ALL TRIGGERS" : (TRIGGER_FILTER_LABELS[f]?.toUpperCase() || f.toUpperCase())}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Table */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="rounded-2xl overflow-hidden"
          style={{ background: "var(--bg-surface)" }}
        >
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr style={{ background: "var(--bg-elevated)", borderBottom: "1px solid var(--border-subtle)" }}>
                  {["Sequence", "Identity", "Anomaly", "Valuation", "Payout", "Trust", "State"].map((col) => (
                    <th
                      key={col}
                      className={`px-5 py-4 text-[9px] font-black uppercase tracking-widest ${
                        ["Valuation", "Payout"].includes(col) ? "text-right" :
                        ["Trust", "State"].includes(col) ? "text-center" : "text-left"
                      }`}
                      style={{ color: "var(--text-muted)" }}
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 7 }).map((__, c) => (
                        <td key={c} className="px-5 py-4">
                          <div className="skeleton h-3 rounded" style={{ opacity: 0.6 - i * 0.08 }} />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : filteredClaims.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="py-16 text-center text-xs font-bold uppercase tracking-widest"
                      style={{ color: "var(--text-muted)" }}
                    >
                      No matching claims found
                    </td>
                  </tr>
                ) : (
                  <AnimatePresence>
                    {filteredClaims.map((claim, idx) => (
                      <motion.tr
                        key={claim.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: idx * 0.015 }}
                        style={{ borderBottom: "1px solid var(--border-subtle)" }}
                        className="group transition-colors"
                      >
                        <td className="px-5 py-4 font-mono text-[10px]" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
                          {shortId(claim.id).toUpperCase()}
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-2">
                            <User className="w-3 h-3" style={{ color: "var(--text-muted)" }} />
                            <span className="font-bold text-sm" style={{ color: "var(--text-primary)" }}>
                              {claim.rider_name || shortId(claim.rider_id)}
                            </span>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-2">
                            <Activity className="w-3 h-3" style={{ color: "var(--text-muted)" }} />
                            <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                              {formatTriggerWithEmoji(claim.disruption_type)}
                            </span>
                          </div>
                        </td>
                        <td className="px-5 py-4 text-right font-bold text-xs" style={{ color: "#f43f5e" }}>
                          {formatCurrency(claim.income_loss)}
                        </td>
                        <td className="px-5 py-4 text-right font-bold text-xs" style={{ color: "#10b981" }}>
                          {formatCurrency(claim.payout_amount)}
                        </td>
                        <td className="px-5 py-4 text-center">
                          <span
                            className="inline-block text-[9px] font-black px-2.5 py-1 rounded-lg"
                            style={{
                              background:
                                claim.fraud_score < 30
                                  ? "rgba(16,185,129,0.12)"
                                  : claim.fraud_score < 70
                                  ? "rgba(245,158,11,0.12)"
                                  : "rgba(244,63,94,0.12)",
                              color:
                                claim.fraud_score < 30 ? "#6ee7b7" :
                                claim.fraud_score < 70 ? "#fcd34d" : "#fca5a5",
                            }}
                          >
                            {claim.fraud_score}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-center">
                          <span className={STATUS_STYLES[claim.status] || STATUS_STYLES.pending}>
                            {claim.status.replace(/_/g, " ")}
                          </span>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                )}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </PageContainer>
  );
}
