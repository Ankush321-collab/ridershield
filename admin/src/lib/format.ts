import { TRIGGER_EMOJI, TRIGGER_LABELS } from "@/lib/types";

export function parseApiDate(input?: string | null) {
  if (!input) return null;

  const normalized =
    /(?:Z|[+\-]\d{2}:\d{2})$/.test(input) ? input : `${input}Z`;

  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatCurrency(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount || 0);
}

export function formatPercent(value: number) {
  return `${Math.round((value || 0) * 100)}%`;
}

export function formatRelativeTime(input: string) {
  const date = parseApiDate(input);
  if (!date) return "Unknown time";

  const diffMs = date.getTime() - Date.now();
  const diffMinutes = Math.round(diffMs / 60000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  if (Math.abs(diffMinutes) < 60) return formatter.format(diffMinutes, "minute");

  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) return formatter.format(diffHours, "hour");

  return formatter.format(Math.round(diffHours / 24), "day");
}

export function formatDateTime(input: string) {
  const date = parseApiDate(input);
  if (!date) return "Unknown";

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export const formatApiDate = formatDateTime;

export function getTriggerEmoji(type?: string | null) {
  if (!type) return "⚠️";
  return TRIGGER_EMOJI[type] || "⚠️";
}

export function formatTriggerLabel(type?: string | null) {
  if (!type) return "Unknown Signal";
  return TRIGGER_LABELS[type] || type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatTriggerWithEmoji(type?: string | null) {
  return `${getTriggerEmoji(type)} ${formatTriggerLabel(type)}`;
}

export function shortId(value?: string | null) {
  if (!value) return "Unknown";
  return value.slice(0, 8);
}

export function formatDurationSince(input: string) {
  const date = parseApiDate(input);
  if (!date) return "Unknown";

  const diffMs = Date.now() - date.getTime();
  const totalMinutes = Math.max(0, Math.floor(diffMs / 60000));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours === 0) return `${minutes}m`;
  return `${hours}h ${minutes}m`;
}
