"use client";

import { useCallback, useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Zap, 
  Map as MapIcon, 
  AlertTriangle, 
  Users, 
  Target,
} from "lucide-react";
import { adminApi } from "@/lib/api";
import { 
  Map, 
  MapMarker, 
  MarkerContent, 
  MarkerPopup, 
  MapControls 
} from "@/components/ui/map";
import { cn } from "@/lib/utils";
import type { TriggerStatusResponse, Zone, ActiveTrigger } from "@/lib/types";
import { getTriggerEmoji, formatTriggerLabel } from "@/lib/format";
import { PageContainer } from "@/components/PageContainer";

const TRIGGER_COLORS: Record<string, { border: string; bg: string; text: string; glow: string }> = {
  heavy_rain: { bg: "rgba(59,130,246,0.1)", border: "rgba(59,130,246,0.5)", text: "#93c5fd", glow: "#3b82f6" },
  traffic_congestion: { bg: "rgba(245,158,11,0.1)", border: "rgba(245,158,11,0.5)", text: "#fcd34d", glow: "#f59e0b" },
  store_closure: { bg: "rgba(244,63,94,0.1)", border: "rgba(244,63,94,0.5)", text: "#fca5a5", glow: "#f43f5e" },
  platform_outage: { bg: "rgba(124,58,237,0.1)", border: "rgba(124,58,237,0.5)", text: "#a78bfa", glow: "#7c3aed" },
  extreme_heat: { bg: "rgba(249,115,22,0.1)", border: "rgba(249,115,22,0.5)", text: "#fdba74", glow: "#f97316" },
  regulatory_curfew: { bg: "rgba(239,68,68,0.1)", border: "rgba(239,68,68,0.5)", text: "#fca5a5", glow: "#ef4444" },
  gps_shadowban: { bg: "rgba(6,182,212,0.1)", border: "rgba(6,182,212,0.5)", text: "#67e8f9", glow: "#0891b2" },
  dark_store_queue: { bg: "rgba(132,204,22,0.1)", border: "rgba(132,204,22,0.5)", text: "#bef264", glow: "#84cc16" },
  algorithmic_shock: { bg: "rgba(234,179,8,0.1)", border: "rgba(234,179,8,0.5)", text: "#fde047", glow: "#eab308" },
  community_signal: { bg: "rgba(99,102,241,0.1)", border: "rgba(99,102,241,0.5)", text: "#a5b4fc", glow: "#6366f1" },
  default: { bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.2)", text: "#9ca3af", glow: "#ffffff" },
};

const DEFAULT_CITY_VIEWPORTS: Record<string, { lat: number; lon: number; zoom: number }> = {
  bengaluru: { lat: 12.9716, lon: 77.5946, zoom: 11 },
  hyderabad: { lat: 17.3850, lon: 78.4867, zoom: 11 },
  mumbai: { lat: 19.0760, lon: 72.8777, zoom: 10 },
  delhi: { lat: 28.6139, lon: 77.2090, zoom: 10 },
};

const DEFAULT_CITY = "bengaluru";

function normalizeCity(city: string) {
  return city.trim().toLowerCase();
}

function formatCityLabel(city: string) {
  return city.replace(/_/g, " ");
}

export default function MapPage() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [triggerStatus, setTriggerStatus] = useState<TriggerStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCity, setSelectedCity] = useState(DEFAULT_CITY);
  const [viewport, setViewport] = useState({
    center: [DEFAULT_CITY_VIEWPORTS[DEFAULT_CITY].lon, DEFAULT_CITY_VIEWPORTS[DEFAULT_CITY].lat] as [number, number],
    zoom: DEFAULT_CITY_VIEWPORTS[DEFAULT_CITY].zoom
  });

  const loadData = async () => {
    try {
      const [zonesRes, triggersRes] = await Promise.all([
        adminApi.zones.list(),
        adminApi.triggers.getStatus(),
      ]);
      setZones(zonesRes.zones);
      setTriggerStatus(triggersRes);
    } catch (err) {
      console.error("Failed to load map data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = window.setInterval(loadData, 30000);
    return () => window.clearInterval(interval);
  }, []);

  const activeTriggersByZoneId = useMemo(() => {
    const map: Record<string, ActiveTrigger[]> = {};
    if (!triggerStatus) return map;
    for (const t of triggerStatus.active_triggers) {
      if (!map[t.zone_id]) map[t.zone_id] = [];
      map[t.zone_id].push(t);
    }
    return map;
  }, [triggerStatus]);

  const cityOptions = useMemo(() => {
    const fromZones = [...new Set(zones.map((zone) => normalizeCity(zone.city)).filter(Boolean))];
    if (fromZones.length > 0) return fromZones.sort();
    return Object.keys(DEFAULT_CITY_VIEWPORTS);
  }, [zones]);

  const getCityViewport = useCallback((city: string) => {
    const normalizedCity = normalizeCity(city);
    const cityZones = zones.filter((zone) => normalizeCity(zone.city) === normalizedCity);
    const zonesWithCoords = cityZones.filter((zone) => zone.lon != null && zone.lat != null);

    if (zonesWithCoords.length > 0) {
      const lon = zonesWithCoords.reduce((sum, zone) => sum + Number(zone.lon), 0) / zonesWithCoords.length;
      const lat = zonesWithCoords.reduce((sum, zone) => sum + Number(zone.lat), 0) / zonesWithCoords.length;
      return {
        center: [lon, lat] as [number, number],
        zoom: DEFAULT_CITY_VIEWPORTS[normalizedCity]?.zoom ?? 11,
      };
    }

    const fallback = DEFAULT_CITY_VIEWPORTS[normalizedCity] ?? DEFAULT_CITY_VIEWPORTS[DEFAULT_CITY];
    return {
      center: [fallback.lon, fallback.lat] as [number, number],
      zoom: fallback.zoom,
    };
  }, [zones]);

  const filteredZones = useMemo(() => {
    return zones.filter(z => 
      normalizeCity(z.city) === normalizeCity(selectedCity)
    );
  }, [zones, selectedCity]);

  const focusCity = useCallback((city: string) => {
    const normalizedCity = normalizeCity(city);
    setSelectedCity(normalizedCity);
    setViewport(getCityViewport(normalizedCity));
  }, [getCityViewport]);

  const focusZone = useCallback((zone: Zone, zoom = 13) => {
    const city = normalizeCity(zone.city);
    setSelectedCity(city);
    setViewport({
      center: [zone.lon ?? getCityViewport(city).center[0], zone.lat ?? getCityViewport(city).center[1]],
      zoom,
    });
  }, [getCityViewport]);

  return (
    <PageContainer fullBleed>
      <div className="flex flex-col h-full bg-black relative overflow-hidden">
        {/* Header Bar */}
        <div className="absolute top-6 left-6 right-6 z-20 flex items-center justify-between pointer-events-none">
          <div className="flex flex-col pointer-events-auto">
            <div className="flex items-center gap-3 mb-1">
              <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 shadow-[0_0_20px_rgba(168,85,247,0.15)]">
                <MapIcon className="w-5 h-5 text-purple-400" />
              </div>
              <h1 className="text-2xl font-black text-white tracking-tight">Anomalies Map</h1>
            </div>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500 ml-1">
              Real-time Regional Network Health
            </p>
          </div>

          <div className="flex gap-2 p-1.5 rounded-2xl bg-black/40 backdrop-blur-xl border border-white/5 pointer-events-auto">
            {cityOptions.map((city) => (
              <button
                key={city}
                onClick={() => focusCity(city)}
                className={cn(
                  "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all duration-300",
                  normalizeCity(selectedCity) === normalizeCity(city)
                    ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                    : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
                )}
              >
                {formatCityLabel(city)}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 w-full bg-[#050505]">
          <Map
            viewport={viewport}
            onViewportChange={(v) => setViewport({ center: v.center, zoom: v.zoom })}
            className="w-full h-full"
          >
            {filteredZones.map((zone) => {
              const activeTriggers = activeTriggersByZoneId[zone.id] || [];
              const isTriggered = activeTriggers.length > 0;
              const primaryTrigger = activeTriggers[0];
              const color = primaryTrigger 
                ? (TRIGGER_COLORS[primaryTrigger.type] || TRIGGER_COLORS.default) 
                : TRIGGER_COLORS.default;

              return (
                <MapMarker
                  key={zone.id}
                  longitude={zone.lon ?? 0}
                  latitude={zone.lat ?? 0}
                >
                  <MarkerContent>
                    <div className="relative group">
                      {isTriggered && (
                        <div 
                          className="absolute -inset-8 rounded-full animate-pulse blur-xl opacity-40 mix-blend-screen"
                          style={{ background: color.glow }}
                        />
                      )}
                      
                      <div 
                        className={cn(
                          "relative w-6 h-6 rounded-full border-2 transition-all duration-300 flex items-center justify-center shadow-2xl scale-100 group-hover:scale-125",
                          isTriggered ? "border-white/50" : "border-white/10"
                        )}
                        style={{ 
                          background: isTriggered ? color.glow : "rgba(255,255,255,0.05)",
                          boxShadow: isTriggered ? `0 0 20px ${color.glow}` : "none"
                        }}
                      >
                        {isTriggered ? (
                          <span className="text-[12px]">{getTriggerEmoji(primaryTrigger.type)}</span>
                        ) : (
                          <div className="w-1.5 h-1.5 rounded-full bg-white/30" />
                        )}
                      </div>

                      <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 px-3 py-1.5 rounded-lg bg-black/80 backdrop-blur-md border border-white/10 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                        <div className="text-[10px] font-black uppercase tracking-tight text-white">{zone.name}</div>
                        {isTriggered && (
                          <div className="text-[9px] font-bold text-purple-400 mt-0.5">
                            {activeTriggers.length} Active Anomaly
                          </div>
                        )}
                      </div>
                    </div>
                  </MarkerContent>

                  <MarkerPopup className="p-0 border-none bg-transparent">
                    <div 
                      className="w-64 rounded-2xl p-5 backdrop-blur-2xl border border-white/10 shadow-2xl"
                      style={{ background: "rgba(0,0,0,0.8)" }}
                    >
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h3 className="text-sm font-black text-white uppercase tracking-tight">{zone.name}</h3>
                          <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">{zone.city}</p>
                        </div>
                        <div 
                          className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/5 border border-white/10"
                          style={{ color: color.text }}
                        >
                          <Zap className="w-5 h-5" />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 mb-4">
                        <div className="bg-white/5 rounded-xl p-2.5">
                          <div className="text-[9px] font-bold text-gray-500 uppercase mb-1">Risk Score</div>
                          <div className="text-xs font-black text-white">{zone.risk_score || "—"}</div>
                        </div>
                        <div className="bg-white/5 rounded-xl p-2.5">
                          <div className="text-[9px] font-bold text-gray-500 uppercase mb-1">Anomalies</div>
                          <div className="text-xs font-black text-purple-400">{activeTriggers.length}</div>
                        </div>
                      </div>

                      {isTriggered ? (
                        <div className="space-y-2">
                          {activeTriggers.map(t => (
                            <div key={t.trigger_id} className="p-3 rounded-xl border border-white/5 bg-white/5">
                              <div className="flex items-center gap-2 mb-1.5">
                                <span className="text-base">{getTriggerEmoji(t.type)}</span>
                                <span className="text-[11px] font-black text-white uppercase tracking-tight">
                                  {formatTriggerLabel(t.type)}
                                </span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-[9px] font-bold text-gray-500">AFFECTED RIDERS</span>
                                <span className="text-[10px] font-black text-purple-400">{t.affected_riders}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center py-6 border border-dashed border-white/10 rounded-xl">
                          <Target className="w-8 h-8 text-gray-700 mb-2 opacity-20" />
                          <span className="text-[9px] font-bold text-gray-600 uppercase tracking-widest">Zone Healthy</span>
                        </div>
                      )}
                    </div>
                  </MarkerPopup>
                </MapMarker>
              );
            })}
            <MapControls position="bottom-right" className="mb-2 mr-2" />
          </Map>
        </div>

        <div className="absolute top-24 bottom-24 right-6 w-80 z-20 pointer-events-none flex flex-col gap-4">
          <AnimatePresence>
            {triggerStatus?.active_triggers.map((trigger, idx) => (
              <motion.div
                key={trigger.trigger_id}
                initial={{ x: 100, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: 100, opacity: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="pointer-events-auto"
              >
                <div 
                  className="rounded-2xl border border-white/10 overflow-hidden shadow-2xl flex backdrop-blur-md bg-black/60"
                >
                  <div 
                    className="w-1.5 shrink-0" 
                    style={{ background: TRIGGER_COLORS[trigger.type]?.glow || TRIGGER_COLORS.default.glow }} 
                  />
                  <div className="flex-1 p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{getTriggerEmoji(trigger.type)}</span>
                        <div>
                          <div className="text-[11px] font-black text-white uppercase tracking-tight">
                            {formatTriggerLabel(trigger.type)}
                          </div>
                          <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">
                            {trigger.zone}
                          </div>
                        </div>
                      </div>
                      <button 
                        onClick={() => {
                          const z = zones.find(z => z.id === trigger.zone_id);
                          if (z) {
                            focusZone(z);
                          }
                        }}
                        type="button"
                        aria-label={`Focus ${trigger.zone} on the map`}
                        title={`Focus ${trigger.zone}`}
                        className="p-1.5 rounded-lg hover:bg-white/5 transition-colors"
                      >
                        <Target className="w-3.5 h-3.5 text-gray-400" />
                      </button>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex flex-col">
                        <span className="text-[8px] font-black text-gray-600 uppercase">Impact</span>
                        <span className="text-[11px] font-black text-purple-400">{trigger.affected_riders} Riders</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[8px] font-black text-gray-600 uppercase">Severity</span>
                        <span className="text-[11px] font-black text-amber-500">{trigger.severity}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )).slice(0, 4)}
          </AnimatePresence>
        </div>

        <div className="absolute bottom-6 left-6 z-20 pointer-events-auto">
          <div className="bg-black/40 backdrop-blur-2xl border border-white/5 rounded-2xl p-4 flex items-center gap-8 shadow-2xl">
             <div className="flex flex-col">
               <div className="flex items-center gap-2 mb-1">
                 <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                 <span className="text-[10px] font-black text-gray-400 uppercase tracking-[0.1em]">Network Anomalies</span>
               </div>
               <div className="text-xl font-black text-white leading-none">
                 {triggerStatus?.active_triggers.length || 0}
               </div>
             </div>
             <div className="w-px h-10 bg-white/5" />
             <div className="flex flex-col">
               <div className="flex items-center gap-2 mb-1">
                 <Users className="w-3.5 h-3.5 text-purple-400" />
                 <span className="text-[10px] font-black text-gray-400 uppercase tracking-[0.1em]">Impacted Riders</span>
               </div>
               <div className="text-xl font-black text-white leading-none">
                 {triggerStatus?.active_triggers.reduce((sum, t) => sum + t.affected_riders, 0) || 0}
               </div>
             </div>
          </div>
        </div>
        {loading && (
          <div className="absolute inset-x-0 bottom-6 z-20 flex justify-center pointer-events-none">
            <div className="rounded-xl border border-white/10 bg-black/70 px-4 py-2 text-[10px] font-bold uppercase tracking-widest text-gray-400">
              Loading map data
            </div>
          </div>
        )}
      </div>
    </PageContainer>
  );
}
