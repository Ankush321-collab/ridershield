"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LayoutDashboard, FileText, Camera, Zap, Activity, Menu, X, Map as MapIcon, ShieldAlert, LineChart, Wallet } from "lucide-react";
import { adminApi } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/map", label: "Map", icon: MapIcon },
  { href: "/claims", label: "Auto Claims", icon: FileText },
  { href: "/manual-claims", label: "Manual Claims", icon: Camera },
  { href: "/fraud-alerts", label: "Fraud Alerts", icon: ShieldAlert },
  { href: "/predictive", label: "Risk Forecast", icon: LineChart },
  { href: "/payout-analytics", label: "Payout Analytics", icon: Wallet },
  { href: "/triggers", label: "Triggers", icon: Zap },
];

export function Sidebar() {
  const pathname = usePathname();
  const [isOpenMobile, setIsOpenMobile] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [systemHealthy, setSystemHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    const loadHealth = async () => {
      try {
        const health = await adminApi.health();
        if (active) setSystemHealthy(health.status === "healthy");
      } catch {
        if (active) setSystemHealthy(false);
      }
    };
    void loadHealth();
    const interval = window.setInterval(() => void loadHealth(), 30000);
    return () => { active = false; window.clearInterval(interval); };
  }, []);

  return (
    <>
      {/* Mobile Toggle */}
      <button
        type="button"
        onClick={() => setIsOpenMobile((o) => !o)}
        className="fixed left-4 top-4 z-50 md:hidden rounded-xl px-3 py-2 text-xs font-bold flex items-center justify-center"
        style={{
          background: "var(--bg-elevated)",
          color: "var(--text-secondary)",
        }}
      >
        {isOpenMobile ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Overlay */}
      {isOpenMobile && (
        <div
          className="fixed inset-0 z-30 md:hidden"
          style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}
          onClick={() => setIsOpenMobile(false)}
        />
      )}

      {/* Desktop Toggle (only shows when sidebar is not collapsed, or shows inside it)
          Actually, let's put it at the very top of the sidebar. */}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex flex-col md:sticky md:top-0 md:h-screen md:translate-x-0 transition-all duration-300 ${isOpenMobile ? "translate-x-0" : "-translate-x-full"
          }`}
        style={{
          width: isCollapsed ? "72px" : "236px",
          background: "var(--bg-surface)",
          borderRight: "1px solid var(--border-subtle)",
        }}
      >
        <div className={`flex flex-col h-full py-7 ${isCollapsed ? "px-2.5" : "px-4"}`}>

          {/* Header Row: Logo & Hamburger */}
          <div className={`flex items-center ${isCollapsed ? "flex-col items-center gap-4 px-0" : "justify-between px-2"} mb-8`}>
            {/* Logo */}
            <div className={isCollapsed ? "flex items-center justify-center" : "flex items-center gap-3"}>
              <Image
                src="/Zylo.png"
                alt="Zylo Logo"
                width={48}
                height={48}
                className="w-12 h-12 object-contain drop-shadow-[0_0_12px_rgba(168,85,247,0.35)]"
              />
              {!isCollapsed && (
                <div>
                  <div
                    className="text-[2rem] font-black tracking-tight"
                    style={{
                      background: "linear-gradient(135deg, #a855f7, #7c3aed)",
                      WebkitBackgroundClip: "text",
                      backgroundClip: "text",
                      color: "transparent",
                    }}
                  >
                    Zylo
                  </div>
                </div>
              )}
            </div>

            {/* Desktop Hamburger */}
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="hidden md:flex items-center justify-center w-8 h-8 rounded-lg transition-colors hover:bg-white/5 text-gray-500 hover:text-gray-300 shrink-0"
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>

          {/* System Health */}
          {!isCollapsed && (
            <div
              className="mb-6 mx-1 rounded-2xl p-3.5 flex items-center justify-between border"
              style={{
                background: "var(--bg-elevated)",
                borderColor: "var(--border-subtle)",
              }}
            >
              <div>
                <div className="text-[9px] font-bold uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>
                  System Status
                </div>
                <div className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>
                  {systemHealthy === null ? "Checking..." : systemHealthy ? "Operational" : "Degraded"}
                </div>
              </div>
              <div className="relative flex items-center justify-center">
                {systemHealthy === true && (
                  <span className="absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping" style={{ background: "#10b981" }} />
                )}
                <span
                  className="relative h-2.5 w-2.5 rounded-full"
                  style={{
                    background:
                      systemHealthy === null ? "#4a4a6a" :
                        systemHealthy ? "#10b981" : "#f43f5e",
                    boxShadow:
                      systemHealthy === true ? "0 0 8px rgba(16,185,129,0.6)" :
                        systemHealthy === false ? "0 0 8px rgba(244,63,94,0.6)" : "none",
                  }}
                />
              </div>
            </div>
          )}

          {/* Nav Label */}
          {!isCollapsed && (
            <div className="px-3 mb-2">
              <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                Navigation
              </span>
            </div>
          )}

          {/* Navigation */}
          <nav className="flex-1 flex flex-col gap-1.5">
            {NAV_ITEMS.map((item) => {
              const active = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={isCollapsed ? item.label : undefined}
                  onClick={() => setIsOpenMobile(false)}
                  className={`relative flex items-center ${isCollapsed ? "justify-center px-0 py-3" : "gap-3 px-3 py-3"} rounded-2xl text-sm font-semibold transition-all duration-200`}
                  style={{
                    background: active ? "rgba(124,58,237,0.16)" : "transparent",
                    color: active ? "#a855f7" : "var(--text-secondary)",
                    border: active ? "1px solid rgba(168,85,247,0.08)" : "1px solid transparent",
                  }}
                  onMouseEnter={(e) => {
                    if (!active) {
                      (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.03)";
                      (e.currentTarget as HTMLElement).style.color = "var(--text-primary)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!active) {
                      (e.currentTarget as HTMLElement).style.background = "transparent";
                      (e.currentTarget as HTMLElement).style.color = "var(--text-secondary)";
                    }
                  }}
                >
                  {active && !isCollapsed && <div className="nav-active-indicator" />}
                  <Icon className="w-5 h-5 shrink-0" style={{ marginLeft: active && !isCollapsed ? "8px" : 0 }} />
                  {!isCollapsed && item.label}
                  {active && !isCollapsed && (
                    <span
                      className="ml-auto text-[9px] font-black uppercase tracking-wider rounded-full px-2 py-0.5"
                      style={{ background: "rgba(124,58,237,0.22)", color: "#c084fc" }}
                    >
                      live
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Live Traffic Footer */}
          {!isCollapsed && (
            <div
              className="mt-6 rounded-2xl p-4 border"
              style={{
                background: "rgba(76,29,149,0.14)",
                borderColor: "rgba(168,85,247,0.1)",
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-3.5 h-3.5" style={{ color: "#a855f7" }} />
                <span className="text-[9px] font-black uppercase tracking-widest" style={{ color: "#a855f7" }}>
                  Live Monitor
                </span>
                <span
                  className="ml-auto h-1.5 w-1.5 rounded-full animate-pulse"
                  style={{ background: "#a855f7", boxShadow: "0 0 6px rgba(168,85,247,0.6)" }}
                />
              </div>
              <div className="text-[10px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Real-time claim streams &amp; zone anomaly detection active.
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
