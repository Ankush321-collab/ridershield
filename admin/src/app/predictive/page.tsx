"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Gauge, LineChart, RadioTower } from "lucide-react";

import { adminApi } from "@/lib/api";
import { formatPercent } from "@/lib/format";
import type { PredictiveZoneForecast } from "@/lib/types";
import { PageContainer } from "@/components/PageContainer";

type ThresholdEntry = {
  zone_id: string;
  zone: string;
  thresholds: Record<string, number>;
};

const SERIES_COLORS = ["#a78bfa", "#38bdf8", "#f59e0b", "#10b981"];

function riskColor(value: number) {
  if (value >= 0.75) return "#f43f5e";
  if (value >= 0.55) return "#f59e0b";
  if (value >= 0.35) return "#38bdf8";
  return "#10b981";
}

function riskBand(value: number) {
  if (value >= 0.75) return "Critical";
  if (value >= 0.55) return "High";
  if (value >= 0.35) return "Medium";
  return "Low";
}

function topDayFor(zone: PredictiveZoneForecast) {
  return zone.forecast.reduce(
    (best, day) => (
      day.predicted_disruption_probability > best.predicted_disruption_probability ? day : best
    ),
    zone.forecast[0],
  );
}

function pathFrom(points: Array<{ x: number; y: number }>) {
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
}

function ForecastChart({
  zones,
  selectedZoneId,
}: {
  zones: PredictiveZoneForecast[];
  selectedZoneId: string | null;
}) {
  const width = 720;
  const height = 230;
  const padding = { top: 20, right: 24, bottom: 34, left: 42 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const selectedZone = zones.find((zone) => zone.zone_id === selectedZoneId);
  const series = [
    ...(selectedZone ? [selectedZone] : []),
    ...zones.filter((zone) => zone.zone_id !== selectedZoneId).slice(0, 3),
  ].slice(0, 4);
  const dates = series[0]?.forecast.map((day) => day.date.slice(5)) ?? [];

  return (
    <section className="rounded-lg border" style={{ background: "var(--bg-surface)", borderColor: "var(--border-subtle)" }}>
      <div className="flex items-start justify-between gap-4 p-5 pb-3">
        <div>
          <div className="text-[10px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
            Forecast curve
          </div>
          <h2 className="mt-1 text-lg font-black" style={{ color: "var(--text-primary)" }}>
            Seven-day disruption probability
          </h2>
        </div>
        <LineChart className="h-5 w-5" style={{ color: "#a78bfa" }} />
      </div>

      <div className="px-4 pb-3">
        <svg viewBox={`0 0 ${width} ${height}`} className="h-[260px] w-full" role="img" aria-label="Seven-day disruption probability chart">
          {[0.25, 0.5, 0.75, 1].map((tick) => {
            const y = padding.top + chartHeight - tick * chartHeight;
            return (
              <g key={tick}>
                <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} stroke="rgba(255,255,255,0.1)" strokeDasharray="4 8" />
                <text x={10} y={y + 4} fontSize="10" fill="rgba(255,255,255,0.45)" fontWeight="800">
                  {Math.round(tick * 100)}%
                </text>
              </g>
            );
          })}

          {dates.map((date, index) => {
            const x = padding.left + (dates.length === 1 ? 0 : (index / (dates.length - 1)) * chartWidth);
            return (
              <text key={date} x={x} y={height - 10} textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.45)" fontWeight="800">
                {date}
              </text>
            );
          })}

          {series.map((zone, zoneIndex) => {
            const points = zone.forecast.map((day, index) => {
              const x = padding.left + (zone.forecast.length === 1 ? 0 : (index / (zone.forecast.length - 1)) * chartWidth);
              const y = padding.top + chartHeight - day.predicted_disruption_probability * chartHeight;
              return { x, y };
            });
            const color = SERIES_COLORS[zoneIndex % SERIES_COLORS.length];
            return (
              <g key={zone.zone_id}>
                <path d={pathFrom(points)} fill="none" stroke={color} strokeWidth={zone.zone_id === selectedZoneId ? 4 : 2.5} strokeLinecap="round" strokeLinejoin="round" opacity={zone.zone_id === selectedZoneId ? 1 : 0.82} />
                {points.map((point, index) => (
                  <circle key={`${zone.zone_id}-${index}`} cx={point.x} cy={point.y} r={zone.zone_id === selectedZoneId ? 4.5 : 3.5} fill="#08080c" stroke={color} strokeWidth="2" />
                ))}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="grid gap-2 border-t p-4 sm:grid-cols-2 xl:grid-cols-4" style={{ borderColor: "var(--border-subtle)" }}>
        {series.map((zone, index) => (
          <div key={zone.zone_id} className="flex min-w-0 items-center gap-2 text-xs font-bold" style={{ color: "var(--text-secondary)" }}>
            <span className="h-2.5 w-2.5 flex-shrink-0 rounded-full" style={{ background: SERIES_COLORS[index % SERIES_COLORS.length] }} />
            <span className="truncate">{zone.zone}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ThresholdSummary({ entry }: { entry?: ThresholdEntry }) {
  const metrics = [
    { key: "rainfall_mm", label: "Rain", max: 70, unit: "mm", color: "#38bdf8" },
    { key: "heat_index", label: "Heat", max: 45, unit: "C", color: "#f59e0b" },
    { key: "aqi", label: "AQI", max: 450, unit: "", color: "#f43f5e" },
    { key: "congestion_index", label: "Traffic", max: 100, unit: "", color: "#a78bfa" },
  ];

  return (
    <section className="rounded-lg border p-5" style={{ background: "var(--bg-surface)", borderColor: "var(--border-subtle)" }}>
      <div className="text-[10px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
        Adaptive thresholds
      </div>
      <h2 className="mt-1 text-lg font-black" style={{ color: "var(--text-primary)" }}>
        {entry?.zone ?? "Select a zone"}
      </h2>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const value = entry?.thresholds[metric.key] ?? 0;
          const pct = Math.max(5, Math.min(100, (value / metric.max) * 100));
          return (
            <div key={metric.key}>
              <div className="mb-2 flex justify-between text-[10px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                <span>{metric.label}</span>
                <span>{Math.round(value)}{metric.unit}</span>
              </div>
              <div className="h-2 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                <div className="h-2 rounded-full" style={{ width: `${pct}%`, background: metric.color, boxShadow: `0 0 18px ${metric.color}55` }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default function PredictivePage() {
  const [zones, setZones] = useState<PredictiveZoneForecast[]>([]);
  const [thresholds, setThresholds] = useState<ThresholdEntry[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        await adminApi.autoLogin();
        const [predictive, thresholdData] = await Promise.all([
          adminApi.analytics.predictive(7),
          adminApi.analytics.thresholds(),
        ]);
        setZones(predictive.zones);
        setThresholds(thresholdData.zones);
        setSelectedZoneId((current) => current ?? predictive.zones[0]?.zone_id ?? null);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load risk forecast.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const selectedZone = useMemo(
    () => zones.find((zone) => zone.zone_id === selectedZoneId) ?? zones[0],
    [selectedZoneId, zones],
  );
  const selectedThresholds = useMemo(
    () => thresholds.find((entry) => entry.zone_id === selectedZone?.zone_id),
    [selectedZone?.zone_id, thresholds],
  );

  const metrics = useMemo(() => {
    const averageRisk = zones.length
      ? zones.reduce((sum, zone) => sum + zone.max_predicted_risk, 0) / zones.length
      : 0;
    const criticalZones = zones.filter((zone) => zone.max_predicted_risk >= 0.75).length;
    const highest = zones[0];
    return { averageRisk, criticalZones, highest };
  }, [zones]);

  const topDay = selectedZone ? topDayFor(selectedZone) : undefined;

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="text-[9px] font-black uppercase tracking-[0.25em] mb-2.5" style={{ color: "var(--text-muted)" }}>
              Predictive Intelligence
            </div>
            <h1 className="text-3xl font-black tracking-tight mb-2" style={{ color: "var(--text-primary)" }}>
              Next-Week Risk Forecast
            </h1>
            <p className="max-w-2xl text-sm leading-6" style={{ color: "var(--text-secondary)" }}>
              Seven-day heuristic disruption forecast and calibrated trigger thresholds by zone.
            </p>
          </div>

          <label className="flex flex-col gap-2">
            <span className="text-[10px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
              Select zone
            </span>
            <select
              value={selectedZone?.zone_id ?? ""}
              onChange={(event) => setSelectedZoneId(event.target.value)}
              className="min-w-72 rounded-lg border px-4 py-3 text-sm font-bold outline-none"
              style={{
                background: "var(--bg-surface)",
                borderColor: "var(--border-subtle)",
                color: "var(--text-primary)",
              }}
            >
              {zones.map((zone) => (
                <option key={zone.zone_id} value={zone.zone_id}>
                  {zone.zone} - {zone.city}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && (
          <div className="rounded-lg p-4 text-sm font-medium" style={{ background: "rgba(244,63,94,0.08)", color: "#fca5a5" }}>
            {error}
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border p-5" style={{ background: "var(--bg-surface)", borderColor: "var(--border-subtle)" }}>
            <div className="mb-3 flex items-center justify-between">
              <div className="text-[10px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Average max risk</div>
              <Gauge className="h-4 w-4" style={{ color: "#38bdf8" }} />
            </div>
            <div className="text-3xl font-black" style={{ color: riskColor(metrics.averageRisk) }}>{formatPercent(metrics.averageRisk)}</div>
            <div className="mt-1 text-xs font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>{riskBand(metrics.averageRisk)} exposure</div>
          </div>

          <div className="rounded-lg border p-5" style={{ background: "var(--bg-surface)", borderColor: "var(--border-subtle)" }}>
            <div className="mb-3 flex items-center justify-between">
              <div className="text-[10px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Critical zones</div>
              <AlertTriangle className="h-4 w-4" style={{ color: "#f43f5e" }} />
            </div>
            <div className="text-3xl font-black" style={{ color: "#f43f5e" }}>{metrics.criticalZones}</div>
            <div className="mt-1 text-xs font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>above 75%</div>
          </div>

          <div className="rounded-lg border p-5" style={{ background: "var(--bg-surface)", borderColor: "var(--border-subtle)" }}>
            <div className="mb-3 flex items-center justify-between">
              <div className="text-[10px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Highest watch</div>
              <RadioTower className="h-4 w-4" style={{ color: "#a78bfa" }} />
            </div>
            <div className="truncate text-xl font-black" style={{ color: "var(--text-primary)" }}>{metrics.highest?.zone ?? "Loading"}</div>
            <div className="mt-1 text-xs font-bold uppercase tracking-widest" style={{ color: "#a78bfa" }}>
              {metrics.highest ? formatPercent(metrics.highest.max_predicted_risk) : "calibrating"}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="rounded-lg border p-10 text-sm font-bold" style={{ background: "var(--bg-surface)", borderColor: "var(--border-subtle)", color: "var(--text-secondary)" }}>
            Calibrating forecast...
          </div>
        ) : (
          <>
            <div className="grid items-start gap-6 xl:grid-cols-[1.45fr_0.85fr]">
              <div className="space-y-6">
                <ForecastChart zones={zones} selectedZoneId={selectedZone?.zone_id ?? null} />
                <ThresholdSummary entry={selectedThresholds} />
              </div>

              <section className="rounded-lg border" style={{ background: "var(--bg-surface)", borderColor: "var(--border-subtle)" }}>
                <div className="border-b p-5" style={{ borderColor: "var(--border-subtle)" }}>
                  <div className="text-[10px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Zone outlook</div>
                  <div className="mt-1 text-xl font-black" style={{ color: "var(--text-primary)" }}>{selectedZone?.zone ?? "No forecast"}</div>
                  <div className="mt-1 text-sm font-bold" style={{ color: "#a78bfa" }}>
                    {selectedZone?.city} {topDay ? `- peak ${formatPercent(topDay.predicted_disruption_probability)} on ${topDay.date}` : ""}
                  </div>
                </div>

                <div className="grid gap-2 p-5 sm:grid-cols-2">
                  {selectedZone?.forecast.map((day) => (
                    <div key={day.date} className="rounded-lg border p-3" style={{ background: "var(--bg-elevated)", borderColor: "var(--border-subtle)" }}>
                      <div className="mb-2 flex items-center justify-between">
                        <div className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{day.date.slice(5)}</div>
                        <div className="text-sm font-black" style={{ color: riskColor(day.predicted_disruption_probability) }}>
                          {formatPercent(day.predicted_disruption_probability)}
                        </div>
                      </div>
                      <div className="h-2 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                        <div
                          className="h-2 rounded-full"
                          style={{
                            width: `${day.predicted_disruption_probability * 100}%`,
                            background: riskColor(day.predicted_disruption_probability),
                          }}
                        />
                      </div>
                      <div className="mt-2 text-[10px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                        {day.risk_band} - earnings x{day.expected_earnings_multiplier}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </>
        )}
      </div>
    </PageContainer>
  );
}
