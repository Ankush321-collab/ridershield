"use client";

import { useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Users,
  Clock,
  BarChart,
  AlertTriangle,
  PlayCircle,
  Activity,
  History,
  CheckCircle2,
} from "lucide-react";

import { adminApi } from "@/lib/api";
import { formatDurationSince, getTriggerEmoji, formatTriggerLabel, formatApiDate } from "@/lib/format";
import BorderGlow from "@/components/ui/BorderGlow";
import type { TriggerStatusResponse, ActiveTrigger, DisruptionEvent, Zone } from "@/lib/types";
import { PageContainer } from "@/components/PageContainer";

const TRIGGER_COLORS: Record<string, { border: string; bg: string; text: string; glow: string }> = {
  heavy_rain: { bg: "rgba(59,130,246,0.07)", border: "rgba(59,130,246,0.2)", text: "#93c5fd", glow: "rgba(59,130,246,0.15)" },
  traffic_congestion: { bg: "rgba(245,158,11,0.07)", border: "rgba(245,158,11,0.2)", text: "#fcd34d", glow: "rgba(245,158,11,0.12)" },
  store_closure: { bg: "rgba(244,63,94,0.07)", border: "rgba(244,63,94,0.2)", text: "#fca5a5", glow: "rgba(244,63,94,0.12)" },
  platform_outage: { bg: "rgba(124,58,237,0.07)", border: "rgba(124,58,237,0.2)", text: "#a78bfa", glow: "rgba(124,58,237,0.15)" },
  extreme_heat: { bg: "rgba(249,115,22,0.07)", border: "rgba(249,115,22,0.2)", text: "#fdba74", glow: "rgba(249,115,22,0.12)" },
  regulatory_curfew: { bg: "rgba(239,68,68,0.07)", border: "rgba(239,68,68,0.2)", text: "#fca5a5", glow: "rgba(239,68,68,0.12)" },
  gps_shadowban: { bg: "rgba(6,182,212,0.07)", border: "rgba(6,182,212,0.2)", text: "#67e8f9", glow: "rgba(6,182,212,0.12)" },
  dark_store_queue: { bg: "rgba(132,204,22,0.07)", border: "rgba(132,204,22,0.2)", text: "#bef264", glow: "rgba(132,204,22,0.1)" },
  algorithmic_shock: { bg: "rgba(234,179,8,0.07)", border: "rgba(234,179,8,0.2)", text: "#fde047", glow: "rgba(234,179,8,0.10)" },
  community_signal: { bg: "rgba(99,102,241,0.07)", border: "rgba(99,102,241,0.2)", text: "#a5b4fc", glow: "rgba(99,102,241,0.12)" },
  default: { bg: "rgba(255,255,255,0.03)", border: "rgba(255,255,255,0.08)", text: "#9ca3af", glow: "rgba(255,255,255,0.04)" },
};

export default function TriggersPage() {
  const [status, setStatus] = useState<TriggerStatusResponse | null>(null);
  const [events, setEvents] = useState<DisruptionEvent[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [triggerTypes, setTriggerTypes] = useState<{ type: string; label: string; icon: string; desc?: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState<string | null>(null);
  const [selectedZone, setSelectedZone] = useState("");

  const zonesByCity = useMemo(() => {
    const groups: Record<string, Zone[]> = {};
    for (const zone of zones) {
      const city = zone.city ?? "Other";
      if (!groups[city]) groups[city] = [];
      groups[city].push(zone);
    }
    return groups;
  }, [zones]);

  const loadData = async () => {
    try {
      const [statusRes, eventsRes] = await Promise.all([
        adminApi.triggers.getStatus(),
        adminApi.triggers.getDisruptionEvents(),
      ]);
      setStatus(statusRes);
      setEvents(eventsRes.events);
    } catch (err) {
      console.error("Failed to sync triggers:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    adminApi.zones.list()
      .then((res) => {
        setZones(res.zones);
        if (res.zones.length > 0) setSelectedZone(res.zones[0].name);
      })
      .catch(() => console.error("Failed to load zones"));
    adminApi.config.get()
      .then((cfg) => setTriggerTypes(cfg.trigger_types))
      .catch(() => console.error("Failed to load trigger types"));
  }, []);

  useEffect(() => {
    void loadData();
    const interval = window.setInterval(() => void loadData(), 30000);
    return () => window.clearInterval(interval);
  }, []);

  const simulateTrigger = async (type: string) => {
    setTriggering(type);
    try {
      await adminApi.triggers.inject({ trigger_type: type, zone: selectedZone });
      await loadData();
    } catch {
      alert("Simulation failed.");
    } finally {
      setTriggering(null);
    }
  };

  const getColor = (type: string) => TRIGGER_COLORS[type] || TRIGGER_COLORS.default;

  return (
    <PageContainer>
      <div className="space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between"
        >
          <div>
            <div className="text-[9px] font-black uppercase tracking-[0.25em] mb-2.5" style={{ color: "var(--text-muted)" }}>
              Network Intelligence
            </div>
            <h1 className="text-3xl font-black tracking-tight mb-1" style={{ color: "var(--text-primary)" }}>
              Network Surveillance
            </h1>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Parametric anomaly detection &amp; disruption monitoring
            </p>
          </div>
          <div
            className="flex items-center gap-2 px-4 py-2.5 rounded-2xl"
            style={{ background: "rgba(16,185,129,0.07)" }}
          >
            <Activity className="w-3.5 h-3.5 animate-pulse" style={{ color: "#10b981" }} />
            <span className="text-[9px] font-black uppercase tracking-widest" style={{ color: "#10b981" }}>
              Scanning Zones
            </span>
          </div>
        </motion.div>

        {/* Active Anomalies */}
        <section>
          <div className="flex items-center gap-2.5 mb-5">
            <Zap className="w-4 h-4" style={{ color: "#a855f7" }} />
            <h2 className="text-base font-black" style={{ color: "var(--text-primary)" }}>Active Anomalies</h2>
          </div>

          <AnimatePresence mode="popLayout">
            {!status || status.active_triggers.length === 0 ? (
              <motion.div
                key="no-triggers"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-2xl py-14 text-center"
                style={{ background: "var(--bg-surface)" }}
              >
                <CheckCircle2 className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--text-muted)", opacity: 0.4 }} />
                <div className="text-xs font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                  No active disruptions detected
                </div>
              </motion.div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 max-h-[300px] overflow-y-auto pr-2" style={{ scrollbarWidth: "thin" }}>
                {status.active_triggers.map((trigger: ActiveTrigger, idx: number) => {
                  const col = getColor(trigger.type);
                  return (
                    <BorderGlow key={trigger.trigger_id} animated={false} backgroundColor="#000000" colors={[col.text, "#000000", col.text]}>
                      <motion.div
                        layout
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: idx * 0.08 }}
                        className="rounded-2xl p-5 relative overflow-hidden bg-transparent border-none"
                      >
                        <div
                          className="absolute -right-4 -top-4 w-24 h-24 rounded-full blur-2xl opacity-40"
                          style={{ background: col.glow }}
                        />
                        <div className="relative">
                          <div className="flex items-start justify-between mb-4">
                            <span className="text-2xl">{getTriggerEmoji(trigger.type)}</span>
                            <span
                              className="text-[8px] font-black uppercase tracking-widest px-2.5 py-1 rounded-full"
                              style={{ background: col.border, color: col.text }}
                            >
                              {trigger.severity}
                            </span>
                          </div>
                          <div className="text-sm font-black mb-1" style={{ color: "var(--text-primary)" }}>
                            {formatTriggerLabel(trigger.type)}
                          </div>
                          <div className="text-[10px] font-medium mb-4" style={{ color: "var(--text-muted)" }}>
                            {trigger.zone}
                          </div>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5">
                              <Users className="w-3 h-3" style={{ color: "var(--text-muted)" }} />
                              <span className="text-[10px] font-bold" style={{ color: "var(--text-secondary)" }}>
                                {trigger.affected_riders} riders
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <Clock className="w-3 h-3" style={{ color: col.text }} />
                              <span className="text-[10px] font-bold" style={{ color: col.text }}>
                                {formatDurationSince(trigger.active_since)}
                              </span>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    </BorderGlow>
                  );
                })}
              </div>
            )}
          </AnimatePresence>
        </section>

        {/* Simulator Compact Panel */}
        <BorderGlow animated={false} backgroundColor="#000000">
          <section
            className="rounded-2xl p-6 relative overflow-hidden bg-transparent border-none"
          >
            <div className="flex items-center gap-2.5 mb-6">
              <PlayCircle className="w-4 h-4" style={{ color: "#10b981" }} />
              <h2 className="text-base font-black" style={{ color: "var(--text-primary)" }}>Simulator Command Deck</h2>
            </div>

            <div className="flex flex-col xl:flex-row gap-6 mb-6">
              <div className="xl:w-64 flex-shrink-0">
                <label
                  className="block text-[9px] font-black uppercase tracking-widest mb-2"
                  style={{ color: "var(--text-muted)" }}
                >
                  Target Zone
                </label>
                <select
                  value={selectedZone}
                  onChange={(e) => setSelectedZone(e.target.value)}
                  className="w-full rounded-xl px-4 py-2.5 text-xs font-bold outline-none appearance-none transition-all cursor-pointer"
                  style={{
                    background: "var(--bg-elevated)",
                    color: "var(--text-primary)",
                  }}
                >
                  {zones.length === 0 ? (
                    <option disabled>Loading zones...</option>
                  ) : (
                    Object.entries(zonesByCity).map(([city, cityZones]) => (
                      <optgroup key={city} label={city.charAt(0).toUpperCase() + city.slice(1)}>
                        {cityZones.map((z) => (
                          <option key={z.id} value={z.name} style={{ background: "#111", color: "#fff" }}>
                            {z.name.replace(/_/g, " ")}
                          </option>
                        ))}
                      </optgroup>
                    ))
                  )}
                </select>
              </div>

              <div
                className="flex-1 rounded-xl p-4 flex flex-col justify-center"
                style={{ background: "rgba(245,158,11,0.05)" }}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" style={{ color: "#f59e0b" }} />
                  <span className="text-[10px] font-black uppercase tracking-widest" style={{ color: "#f59e0b" }}>
                    Simulation Alert
                  </span>
                </div>
                <p className="text-xs leading-relaxed" style={{ color: "rgba(252,211,77,0.6)" }}>
                  Injecting triggers will generate <b>real automated payouts</b> for active network nodes in the target zone. Use caution.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {triggerTypes.map((opt) => (
                <button
                  key={opt.type}
                  disabled={triggering !== null}
                  onClick={() => simulateTrigger(opt.type)}
                  className="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group disabled:opacity-40"
                  style={{
                    background: "var(--bg-elevated)",
                  }}
                >
                  <span className="text-xl flex-shrink-0">{opt.icon}</span>
                  <div className="text-left min-w-0">
                    <div className="text-xs font-bold truncate" style={{ color: "var(--text-primary)" }}>
                      {opt.label}
                    </div>
                  </div>
                  {triggering === opt.type && (
                    <div className="ml-auto w-3 h-3 border-2 border-purple-500/30 border-t-purple-400 rounded-full animate-spin flex-shrink-0" />
                  )}
                </button>
              ))}
            </div>
          </section>
        </BorderGlow>

        {/* Disruption History */}
        <section
          className="rounded-2xl p-6 mt-8"
          style={{ background: "var(--bg-surface)" }}
        >
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2.5">
              <History className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
              <h2 className="text-base font-black" style={{ color: "var(--text-primary)" }}>Disruption History Log</h2>
            </div>
            <BarChart className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
          </div>

          <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2 flex flex-col" style={{ scrollbarWidth: "thin" }}>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="skeleton h-14 rounded-xl flex-shrink-0" style={{ opacity: 0.7 - i * 0.1 }} />
              ))
            ) : events.length === 0 ? (
              <div className="text-center py-10 text-xs font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                Archive Empty
              </div>
            ) : (
              events.map((event: DisruptionEvent, idx: number) => {
                return (
                  <motion.div
                    key={event.event_id}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.04 }}
                    className="flex items-center justify-between px-4 py-3.5 rounded-xl transition-all duration-200 group flex-shrink-0"
                    style={{ background: "var(--bg-elevated)" }}
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-2xl">{getTriggerEmoji(event.trigger_type)}</span>
                      <div>
                        <div className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
                          {formatTriggerLabel(event.trigger_type)}
                        </div>
                        <div className="text-[10px] font-black uppercase tracking-widest mt-0.5" style={{ color: "var(--text-muted)" }}>
                          {event.zone} · {event.severity}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[9px] uppercase tracking-widest font-black" style={{ color: "var(--text-muted)" }}>
                        Event Logged
                      </div>
                      <div className="text-[11px] font-mono font-bold mt-0.5" style={{ color: "var(--text-secondary)" }}>
                        {formatApiDate(event.created_at)}
                      </div>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
