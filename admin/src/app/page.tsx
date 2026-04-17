"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp,
  Clock,
  Zap,
  BarChart3,
  Shield,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

import BorderGlow from "@/components/ui/BorderGlow";
import { adminApi } from "@/lib/api";
import {
  formatCurrency,
  formatDurationSince,
  formatPercent,
  parseApiDate,
  formatRelativeTime,
  formatTriggerWithEmoji,
} from "@/lib/format";
import type { OverviewData } from "@/lib/types";
import { STATUS_STYLES } from "@/lib/types";
import { PageContainer } from "@/components/PageContainer";

type ActivityItem = {
  id: string;
  rider: string;
  trigger: string;
  amountLabel: string;
  created_at: string;
  status: string;
};

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0 },
};

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

function StatSkeleton() {
  return (
    <div className="card p-7 animate-pulse">
      <div className="skeleton h-3 w-20 mb-5 rounded" />
      <div className="skeleton h-10 w-24 mb-3 rounded" />
      <div className="skeleton h-2.5 w-16 rounded" />
    </div>
  );
}

export default function AdminOverview() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    let active = true;
    const load = async (showLoading = true) => {
      if (showLoading) setLoading(true);
      else setIsRefreshing(true);
      try {
        const overview = await adminApi.stats.overview();
        if (!active) return;
        setData(overview);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Connection lost.");
      } finally {
        if (active) {
          setLoading(false);
          setIsRefreshing(false);
        }
      }
    };
    void load();
    const interval = window.setInterval(() => void load(false), 30000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const recentActivity = useMemo<ActivityItem[]>(() => {
    if (!data) return [];
    const autoItems = data.autoClaims.map((c) => ({
      id: c.id,
      rider: c.rider_name || c.rider_id.slice(0, 8),
      trigger: formatTriggerWithEmoji(c.disruption_type),
      amountLabel: formatCurrency(c.payout_amount),
      created_at: c.created_at,
      status: c.status,
    }));
    const manualItems = data.manualClaims.map((c) => ({
      id: c.id,
      rider: c.rider_name || c.rider_id.slice(0, 8),
      trigger: formatTriggerWithEmoji(c.disruption_type),
      amountLabel: "Awaiting review",
      created_at: c.created_at,
      status: c.review_status,
    }));
    return [...autoItems, ...manualItems]
      .sort((a, b) => (parseApiDate(b.created_at)?.getTime() || 0) - (parseApiDate(a.created_at)?.getTime() || 0))
      .slice(0, 6);
  }, [data]);

  const statsCards = data
    ? [
        {
          label: "Total Claims",
          value: data.stats.total_claims.toString(),
          sub: "all time processed",
          icon: TrendingUp,
          color: "#7c3aed",
          bg: "rgba(124,58,237,0.08)",
          hsl: "268 100 76",
        },
        {
          label: "Pending Review",
          value: data.stats.pending_review.toString(),
          sub: "awaiting action",
          icon: Clock,
          color: "#f59e0b",
          bg: "rgba(245,158,11,0.08)",
          hsl: "38 92 50",
        },
        {
          label: "Active Triggers",
          value: data.stats.active_triggers.toString(),
          sub: "live disruptions",
          icon: Zap,
          color: "#f43f5e",
          bg: "rgba(244,63,94,0.08)",
          hsl: "349 89 60",
        },
        {
          label: "Pool BCR",
          value: data.stats.bcr > 0 ? data.stats.bcr.toFixed(2) : formatPercent(data.stats.loss_ratio),
          sub: data.stats.bcr > 0
            ? `Target: ≤0.65 • ${data.stats.pool_status === "sustainable" ? "✓ Healthy" : data.stats.pool_status === "caution" ? "⚠ Caution" : "✗ Critical"}`
            : "payout efficiency",
          icon: data.stats.bcr > 0 ? Shield : BarChart3,
          color: data.stats.pool_status === "sustainable" ? "#10b981" : data.stats.pool_status === "caution" ? "#f59e0b" : "#f43f5e",
          bg: data.stats.pool_status === "sustainable" ? "rgba(16,185,129,0.08)" : data.stats.pool_status === "caution" ? "rgba(245,158,11,0.08)" : "rgba(244,63,94,0.08)",
          hsl: data.stats.pool_status === "sustainable" ? "160 84 39" : data.stats.pool_status === "caution" ? "38 92 50" : "349 89 60",
        },
      ]
    : [];

  return (
    <PageContainer className="max-w-[1380px] px-6 md:px-10">
      <div className="space-y-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}>
            <div className="text-[10px] font-black uppercase tracking-[0.28em] mb-3" style={{ color: "var(--text-muted)" }}>
              Admin Dashboard
            </div>
            <h1 className="text-4xl md:text-[3rem] font-black tracking-tight mb-2" style={{ color: "var(--text-primary)" }}>
              Command Center
            </h1>
            <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
              Real-time surveillance • automated claim flows • disruption monitoring
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4 }}
            className="flex items-center gap-2.5 rounded-full px-4 py-2.5 border"
            style={{ background: "rgba(76,29,149,0.24)", borderColor: "rgba(168,85,247,0.12)" }}
          >
            <RefreshCw
              className="w-3.5 h-3.5"
              style={{ color: "#a855f7", animation: isRefreshing ? "spin 1s linear infinite" : "none" }}
            />
            <span className="text-[10px] font-black uppercase tracking-widest" style={{ color: "#a855f7" }}>
              Live Sync
            </span>
            <span
              className="h-1.5 w-1.5 rounded-full animate-pulse"
              style={{ background: "#a855f7", boxShadow: "0 0 6px rgba(168,85,247,0.7)" }}
            />
          </motion.div>
        </div>

        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-2xl p-4 flex items-center gap-3 border"
            style={{
              background: "rgba(244,63,94,0.07)",
              borderColor: "rgba(244,63,94,0.14)",
            }}
          >
            <AlertCircle className="w-5 h-5 flex-shrink-0" style={{ color: "#f43f5e" }} />
            <span className="text-sm font-medium" style={{ color: "#fca5a5" }}>{error}</span>
            <button
              type="button"
              className="ml-auto text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 rounded-lg"
              style={{ background: "rgba(244,63,94,0.15)", color: "#f43f5e" }}
              onClick={() => window.location.reload()}
            >
              Retry
            </button>
          </motion.div>
        )}

        {loading && !data ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <StatSkeleton key={i} />)}
          </div>
        ) : (
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"
          >
            {statsCards.map((stat) => {
              const Icon = stat.icon;
              return (
                <motion.div key={stat.label} variants={fadeUp} className="flex">
                  <BorderGlow
                    className="flex-1 w-full"
                    glowColor={stat.hsl}
                    colors={[stat.color, "#000000", stat.color]}
                    backgroundColor="rgba(14,14,20,0.98)"
                    animated={false}
                    borderRadius={24}
                    glowRadius={34}
                    fillOpacity={0.28}
                  >
                    <div className="card p-6 relative overflow-hidden group h-full bg-transparent">
                      <div className="relative flex justify-between items-start">
                        <div>
                          <div className="text-[10px] font-black uppercase tracking-[0.24em] mb-3" style={{ color: "var(--text-muted)" }}>
                            {stat.label}
                          </div>
                          <div className="text-4xl font-black tracking-tight mb-2" style={{ color: stat.color }}>
                            {stat.value}
                          </div>
                          <div className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
                            {stat.sub}
                          </div>
                        </div>
                        <div
                          className="flex flex-shrink-0 items-center justify-center rounded-2xl"
                          style={{
                            width: 48,
                            height: 48,
                            background: stat.bg,
                            border: `1px solid ${stat.color}22`,
                          }}
                        >
                          <Icon className="w-5 h-5" style={{ color: stat.color }} />
                        </div>
                      </div>
                    </div>
                  </BorderGlow>
                </motion.div>
              );
            })}
          </motion.div>
        )}

        <div className="grid gap-6 xl:grid-cols-[1.42fr_0.58fr]">
          <section
            className="rounded-[28px] p-7 border"
            style={{ background: "var(--bg-surface)", borderColor: "var(--border-subtle)" }}
          >
            <div className="flex items-center justify-between mb-7">
              <div>
                <div className="text-[9px] font-black uppercase tracking-widest mb-1.5" style={{ color: "var(--text-muted)" }}>
                  Audit Stream
                </div>
                <h2 className="text-[2rem] leading-none font-black" style={{ color: "var(--text-primary)" }}>Recent Activity</h2>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full animate-pulse" style={{ background: "#a855f7" }} />
                <span className="text-[9px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                  Live
                </span>
              </div>
            </div>

            <div className="space-y-3 h-[300px] overflow-y-auto pr-2" style={{ scrollbarWidth: "thin" }}>
              <AnimatePresence mode="popLayout">
                {recentActivity.length === 0 ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="rounded-xl py-14 text-center text-xs font-bold uppercase tracking-widest"
                    style={{
                      background: "var(--bg-elevated)",
                      border: "1px dashed var(--border-subtle)",
                      color: "var(--text-muted)",
                    }}
                  >
                    No recent activity
                  </motion.div>
                ) : (
                  recentActivity.map((act, idx) => (
                    <motion.div
                      key={act.id}
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.04 }}
                      className="group flex items-center justify-between gap-4 rounded-xl px-4 py-3.5 transition-all duration-200"
                      style={{
                        background: "var(--bg-elevated)",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className="flex-shrink-0 flex items-center justify-center rounded-full text-[9px] font-black"
                          style={{
                            width: 34,
                            height: 34,
                            background: "rgba(124,58,237,0.12)",
                            color: "#a855f7",
                          }}
                        >
                          {act.rider.slice(0, 2).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm font-bold truncate" style={{ color: "var(--text-primary)" }}>
                            {act.rider}
                          </div>
                          <div className="text-[10px] font-medium mt-0.5" style={{ color: "var(--text-muted)" }}>
                            {act.trigger}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 flex-shrink-0">
                        <div className="text-right">
                          <div className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
                            {act.amountLabel}
                          </div>
                          <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                            {formatRelativeTime(act.created_at)}
                          </div>
                        </div>
                        <span className={STATUS_STYLES[act.status] || STATUS_STYLES.pending}>
                          {act.status.replace(/_/g, " ")}
                        </span>
                      </div>
                    </motion.div>
                  ))
                )}
              </AnimatePresence>
            </div>

            <button
              className="mt-5 flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest transition-all group"
              style={{ color: "#a855f7" }}
            >
              View Full Archive
              <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
            </button>
          </section>

          <BorderGlow
            backgroundColor="rgba(12,12,18,0.98)"
            animated={false}
            borderRadius={28}
            glowRadius={34}
            fillOpacity={0.2}
          >
            <section className="rounded-[28px] p-7 bg-transparent border" style={{ borderColor: "var(--border-subtle)" }}>
              <div className="flex items-center justify-between mb-7">
                <div>
                  <div className="text-[9px] font-black uppercase tracking-widest mb-1.5" style={{ color: "var(--text-muted)" }}>
                    Network
                  </div>
                  <h2 className="text-[2rem] leading-none font-black" style={{ color: "var(--text-primary)" }}>Live Disruptions</h2>
                </div>
                <div
                  className="flex items-center justify-center rounded-xl"
                  style={{
                    width: 36,
                    height: 36,
                    background: "rgba(244,63,94,0.08)",
                  }}
                >
                  <Zap className="w-4 h-4" style={{ color: "#f43f5e" }} />
                </div>
              </div>

              <div className="space-y-3 h-[300px] overflow-y-auto pr-2" style={{ scrollbarWidth: "thin" }}>
                {!data || data.triggerStatus.active_triggers.length === 0 ? (
                  <div
                    className="rounded-xl py-14 text-center"
                    style={{
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border-subtle)",
                    }}
                  >
                    <CheckCircle2 className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--text-muted)" }} />
                    <div className="text-xs font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                      All Clear
                    </div>
                    <div className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>
                      No active disruptions
                    </div>
                  </div>
                ) : (
                  data.triggerStatus.active_triggers.map((trigger, idx) => (
                    <motion.div
                      key={trigger.trigger_id}
                      initial={{ opacity: 0, scale: 0.97 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: idx * 0.08 }}
                      className="rounded-xl p-5 relative overflow-hidden"
                      style={{
                        background: "rgba(244,63,94,0.05)",
                        border: "1px solid rgba(244,63,94,0.08)",
                      }}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="text-base font-bold" style={{ color: "var(--text-primary)" }}>
                          {formatTriggerWithEmoji(trigger.type)}
                        </div>
                        <span
                          className="text-[9px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full"
                          style={{ background: "rgba(244,63,94,0.12)", color: "#fca5a5" }}
                        >
                          {trigger.severity}
                        </span>
                      </div>
                      <div className="text-[10px] font-medium mb-3" style={{ color: "var(--text-muted)" }}>
                        {trigger.zone}
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <TrendingUp className="w-3 h-3" style={{ color: "var(--text-muted)" }} />
                          <span className="text-[10px] font-bold" style={{ color: "var(--text-secondary)" }}>
                            {trigger.affected_riders} riders
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3 h-3" style={{ color: "#a855f7" }} />
                          <span className="text-[10px] font-bold" style={{ color: "#a855f7" }}>
                            {formatDurationSince(trigger.active_since)}
                          </span>
                        </div>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </section>
          </BorderGlow>
        </div>
      </div>
    </PageContainer>
  );
}
