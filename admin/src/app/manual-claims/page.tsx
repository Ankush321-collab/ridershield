"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  Calendar,
  CheckCircle,
  ClipboardList,
  Clock,
  Eye,
  MapPin,
  ShieldAlert,
  XCircle,
  Camera,
} from "lucide-react";

import { adminApi, API_BASE } from "@/lib/api";
import { getTriggerEmoji, formatTriggerLabel, shortId, formatApiDate } from "@/lib/format";
import type { ManualClaimReview } from "@/lib/types";
import { STATUS_STYLES } from "@/lib/types";
import BorderGlow from "@/components/ui/BorderGlow";
import { PageContainer } from "@/components/PageContainer";

export default function ManualClaimsPage() {
  const [claims, setClaims] = useState<ManualClaimReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedClaim, setSelectedClaim] = useState<ManualClaimReview | null>(null);
  const [reviewing, setReviewing] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectInput, setShowRejectInput] = useState(false);

  const loadClaims = async () => {
    try {
      const response = await adminApi.claims.listManual("spam_score", "asc", "all");
      setClaims(response.claims);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load manual claims.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadClaims();
    const interval = window.setInterval(() => void loadClaims(), 30000);
    return () => window.clearInterval(interval);
  }, []);

  const hasFinalDecision = (c: ManualClaimReview) => ["approved", "rejected"].includes(c.review_status);
  const needsHumanOverride = (c: ManualClaimReview) => !hasFinalDecision(c);
  const getActionCopy = (c: ManualClaimReview) =>
    hasFinalDecision(c)
      ? { approve: "Override Approve", reject: "Override Reject" }
      : { approve: "Approve", reject: "Reject" };

  const handleReview = async (claimId: string, status: "approved" | "rejected") => {
    if (status === "rejected" && !rejectReason.trim()) {
      alert("Provide a justification for rejection.");
      return;
    }
    if (!selectedClaim?.claim_id) {
      alert("Invalid claim. Sector ID missing.");
      return;
    }
    setReviewing(claimId);
    try {
      if (status === "approved") {
        await adminApi.claims.approve(selectedClaim.claim_id);
      } else {
        await adminApi.claims.reject(selectedClaim.claim_id, rejectReason);
      }
      await loadClaims();
      setSelectedClaim(null);
      setRejectReason("");
      setShowRejectInput(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to submit review.");
    } finally {
      setReviewing(null);
    }
  };

  const reviewableClaims = claims.filter(needsHumanOverride);
  const automatedClaims = claims.filter(hasFinalDecision);

  return (
    <PageContainer>
      <div className="space-y-8">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="text-[9px] font-black uppercase tracking-[0.25em] mb-2.5" style={{ color: "var(--text-muted)" }}>
            Automated Adjudication
          </div>
          <h1 className="text-3xl font-black tracking-tight mb-1" style={{ color: "var(--text-primary)" }}>
            Manual Claims
          </h1>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Auto-decided claims from the rider app, with admin override for exceptions and audits.
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

        <div className="grid gap-7 xl:grid-cols-[1fr_400px]">
          {/* Left: Signal List */}
          <section className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className="flex items-center justify-center rounded-xl"
                  style={{
                    width: 34, height: 34,
                    background: "rgba(124,58,237,0.1)",
                  }}
                >
                  <Clock className="w-4 h-4" style={{ color: "#a855f7" }} />
                </div>
                <h2 className="text-lg font-black" style={{ color: "var(--text-primary)" }}>Needs Override</h2>
              </div>
              <span
                className="text-[9px] font-black uppercase tracking-wider px-3 py-1.5 rounded-full"
                style={{
                  background: "rgba(124,58,237,0.1)",
                  color: "#a855f7",
                }}
              >
                {reviewableClaims.length} open
              </span>
            </div>

            <div className="space-y-3">
              <AnimatePresence mode="popLayout">
                {loading && claims.length === 0 ? (
                  Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="skeleton h-20 rounded-2xl" />
                  ))
                ) : reviewableClaims.length === 0 ? (
                  <motion.div
                    key="empty-queue"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="rounded-2xl py-16 text-center"
                    style={{ background: "var(--bg-elevated)", border: "1px dashed var(--border-subtle)" }}
                  >
                    <CheckCircle className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--text-muted)", opacity: 0.4 }} />
                    <div className="text-xs font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                      No Overrides Needed
                    </div>
                    <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
                      Manual claims are being auto-adjudicated successfully.
                    </p>
                  </motion.div>
                ) : (
                  reviewableClaims.map((claim, idx) => (
                    <motion.div
                      key={claim.id}
                      layout
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      onClick={() => { setSelectedClaim(claim); setShowRejectInput(false); }}
                      className="cursor-pointer rounded-2xl p-5 transition-all duration-200"
                      style={{
                        background: selectedClaim?.id === claim.id ? "rgba(124,58,237,0.07)" : "var(--bg-surface)",
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <span className="text-3xl">{getTriggerEmoji(claim.disruption_type)}</span>
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span
                                className="text-[8px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full"
                                style={{ background: "rgba(124,58,237,0.1)", color: "#a855f7" }}
                              >
                                Node {shortId(claim.rider_id).toUpperCase()}
                              </span>
                            </div>
                            <div className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
                              {claim.rider_name || "Anonymous"}
                            </div>
                            <div className="text-[10px] font-black uppercase tracking-widest mt-0.5" style={{ color: "#f59e0b" }}>
                              {formatTriggerLabel(claim.disruption_type)}
                            </div>
                            <div className="text-[9px] mt-1" style={{ color: "var(--text-muted)" }}>
                              Awaiting manual override
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-[10px] font-medium mb-2" style={{ color: "var(--text-muted)" }}>
                            {formatApiDate(claim.created_at)}
                          </div>
                          <div
                            className="flex items-center gap-1 text-[10px] font-black uppercase tracking-widest"
                            style={{ color: "#a855f7" }}
                          >
                            Review <ArrowRight className="w-3 h-3" />
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))
                )}
              </AnimatePresence>
            </div>

            {automatedClaims.length > 0 && (
              <div className="pt-4">
                <div className="flex items-center gap-2 mb-4 opacity-50">
                  <ClipboardList className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
                  <h2 className="text-sm font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                    Automated Decisions
                  </h2>
                </div>
                <div className="space-y-2">
                  {automatedClaims.slice(0, 10).map((claim) => (
                    <div
                      key={claim.id}
                      onClick={() => { setSelectedClaim(claim); setShowRejectInput(false); }}
                      className="flex items-center justify-between px-4 py-3 rounded-xl transition-colors"
                      style={{ background: "var(--bg-elevated)", cursor: "pointer" }}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xl opacity-50">{getTriggerEmoji(claim.disruption_type)}</span>
                        <div>
                          <div className="text-xs font-bold" style={{ color: "var(--text-secondary)" }}>
                            {claim.rider_name || shortId(claim.rider_id)}
                          </div>
                          <div className="text-[9px] uppercase tracking-widest font-black" style={{ color: "var(--text-muted)" }}>
                            {formatTriggerLabel(claim.disruption_type)}
                          </div>
                        </div>
                      </div>
                      <span className={STATUS_STYLES[claim.review_status] || STATUS_STYLES.pending}>
                        {claim.review_status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* Right: Analysis Panel */}
          <aside className="sticky top-8 h-fit">
            <AnimatePresence mode="wait">
              {!selectedClaim ? (
                <motion.div
                  key="empty-side"
                  initial={{ opacity: 0, scale: 0.97 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.97 }}
                >
                  <BorderGlow animated={false} backgroundColor="#000000">
                    <div
                      className="rounded-2xl p-10 text-center bg-transparent border-none"
                      style={{
                        background: "var(--bg-surface)",
                        minHeight: 360,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <div
                        className="flex items-center justify-center rounded-2xl mb-5"
                        style={{
                          width: 56, height: 56,
                          background: "rgba(124,58,237,0.07)",
                        }}
                      >
                        <Eye className="w-6 h-6" style={{ color: "var(--text-muted)" }} />
                      </div>
                      <h3 className="text-base font-black mb-2" style={{ color: "var(--text-secondary)" }}>
                        Claim Decision
                      </h3>
                      <p className="text-xs leading-relaxed max-w-[200px]" style={{ color: "var(--text-muted)" }}>
                        Select a manual claim to inspect its evidence and apply an admin override if needed.
                      </p>
                    </div>
                  </BorderGlow>
                </motion.div>
              ) : (
                <motion.div
                  key={selectedClaim.id}
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 16 }}
                >
                  <BorderGlow animated={false} backgroundColor="#000000">
                    <div className="rounded-2xl overflow-hidden bg-transparent border-none">
                      <div
                        className="p-5 flex items-center justify-between"
                        style={{ borderBottom: "1px solid var(--border-subtle)" }}
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{getTriggerEmoji(selectedClaim.disruption_type)}</span>
                          <div>
                            <div className="text-sm font-black" style={{ color: "var(--text-primary)" }}>
                              {selectedClaim.rider_name || "Unknown"}
                            </div>
                            <div className="text-[9px] font-black uppercase tracking-widest" style={{ color: "#f59e0b" }}>
                              {formatTriggerLabel(selectedClaim.disruption_type)}
                            </div>
                          </div>
                        </div>
                        <span
                          className="text-[8px] font-black uppercase tracking-widest px-2.5 py-1 rounded-full"
                          style={{ background: "rgba(124,58,237,0.1)", color: "#a855f7" }}
                        >
                          {selectedClaim.review_status}
                        </span>
                      </div>

                      <div className="p-5 space-y-4">
                        <div
                          className="rounded-xl p-4 space-y-2"
                          style={{ background: "rgba(124,58,237,0.06)" }}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <div className="text-[9px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                                Decision Status
                              </div>
                              <div className="text-sm font-black mt-1" style={{ color: "var(--text-primary)" }}>
                                {selectedClaim.review_status === "approved" ? "Auto-approved" : selectedClaim.review_status === "rejected" ? "Auto-rejected" : "Pending manual action"}
                              </div>
                            </div>
                            <span className={STATUS_STYLES[selectedClaim.review_status] || STATUS_STYLES.pending}>
                              {selectedClaim.review_status}
                            </span>
                          </div>
                          {selectedClaim.reviewer_notes && (
                            <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                              {selectedClaim.reviewer_notes}
                            </p>
                          )}
                        </div>

                        <div
                          className="rounded-xl p-4 space-y-3"
                          style={{ background: "var(--bg-elevated)" }}
                        >
                          <div className="text-[9px] font-black uppercase tracking-widest mb-3" style={{ color: "var(--text-muted)" }}>
                            Telemetry
                          </div>
                          <div className="flex items-center gap-3">
                            <MapPin className="w-3.5 h-3.5 flex-shrink-0" style={{ color: "var(--text-muted)" }} />
                            <div>
                              <div className="text-[9px] uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Zone</div>
                              <div className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>
                                {selectedClaim.zone_name || "GPS Mismatch"}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <Calendar className="w-3.5 h-3.5 flex-shrink-0" style={{ color: "var(--text-muted)" }} />
                            <div>
                              <div className="text-[9px] uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Timestamp</div>
                              <div className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>
                                {formatApiDate(selectedClaim.created_at)}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0" style={{ color: "var(--text-muted)" }} />
                            <div className="flex-1">
                              <div className="text-[9px] uppercase tracking-widest mb-1" style={{ color: "var(--text-muted)" }}>
                                Spam Score
                              </div>
                              <div className="flex items-center gap-2">
                                <div
                                  className="flex-1 h-1.5 rounded-full overflow-hidden"
                                  style={{ background: "var(--bg-overlay)" }}
                                >
                                  <div
                                    className="h-full rounded-full"
                                    style={{
                                      width: `${selectedClaim.spam_score}%`,
                                      background:
                                        selectedClaim.spam_score < 40 ? "#10b981" :
                                        selectedClaim.spam_score < 70 ? "#f59e0b" : "#f43f5e",
                                    }}
                                  />
                                </div>
                                <span className="text-xs font-black">{selectedClaim.spam_score}%</span>
                              </div>
                            </div>
                          </div>
                        </div>

                        <div
                          className="rounded-xl p-4"
                          style={{ background: "var(--bg-elevated)" }}
                        >
                          <div className="flex items-center gap-2 mb-3">
                            <Camera className="w-3.5 h-3.5" style={{ color: "var(--text-muted)" }} />
                            <div className="text-[9px] font-black uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                              Evidence
                            </div>
                          </div>
                          <p className="text-xs italic leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                            &ldquo;{selectedClaim.description || "No description provided."}&rdquo;
                          </p>
                          {selectedClaim.photo_url && (
                            <div className="mt-3 rounded-xl overflow-hidden">
                              <Image
                                src={selectedClaim.photo_url.startsWith("http") ? selectedClaim.photo_url : `${API_BASE}${selectedClaim.photo_url}`}
                                alt="Signal Evidence"
                                width={512}
                                height={112}
                                unoptimized
                                className="w-full h-28 object-cover opacity-80 hover:opacity-100 transition-opacity"
                              />
                            </div>
                          )}
                        </div>

                        {!showRejectInput ? (
                          <div className="flex gap-2">
                            <button
                              disabled={reviewing !== null}
                              onClick={() => handleReview(selectedClaim.id, "approved")}
                              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-xs font-black uppercase tracking-wider transition-all disabled:opacity-40"
                              style={{
                                background: "linear-gradient(135deg, #7c3aed, #9333ea)",
                                color: "#fff",
                              }}
                            >
                              {reviewing === selectedClaim.id ? (
                                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                              ) : (
                                <><CheckCircle className="w-3.5 h-3.5" /> {getActionCopy(selectedClaim).approve}</>
                              )}
                            </button>
                            <button
                              disabled={reviewing !== null}
                              onClick={() => setShowRejectInput(true)}
                              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-xs font-black uppercase tracking-wider transition-all disabled:opacity-40"
                              style={{
                                background: "rgba(244,63,94,0.08)",
                                color: "#f43f5e",
                              }}
                            >
                              <XCircle className="w-3.5 h-3.5" /> {getActionCopy(selectedClaim).reject}
                            </button>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            <div
                              className="rounded-xl p-4"
                              style={{ background: "rgba(244,63,94,0.05)" }}
                            >
                              <div className="text-[9px] font-black uppercase tracking-widest mb-2" style={{ color: "#f43f5e" }}>
                                Override Reason
                              </div>
                              <textarea
                                value={rejectReason}
                                onChange={(e) => setRejectReason(e.target.value)}
                                placeholder="Explain why this auto-decision should be overridden..."
                                className="w-full text-xs leading-relaxed resize-none outline-none min-h-[80px] bg-transparent"
                                style={{ color: "var(--text-primary)" }}
                              />
                            </div>
                            <div className="flex gap-2">
                              <button
                                disabled={reviewing !== null}
                                onClick={() => handleReview(selectedClaim.id, "rejected")}
                                className="flex-1 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider"
                                style={{ background: "#f43f5e", color: "#fff" }}
                              >
                                Confirm Override
                              </button>
                              <button
                                onClick={() => { setShowRejectInput(false); setRejectReason(""); }}
                                className="px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider"
                                style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </BorderGlow>
                </motion.div>
              )}
            </AnimatePresence>
          </aside>
        </div>
      </div>
    </PageContainer>
  );
}
