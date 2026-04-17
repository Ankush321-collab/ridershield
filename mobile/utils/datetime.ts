export function parseApiDate(input?: string | null) {
  if (!input) return null;

  const normalized =
    /(?:Z|[+\-]\d{2}:\d{2})$/.test(input) ? input : `${input}Z`;

  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatApiDateTime(input?: string | null) {
  const date = parseApiDate(input);
  if (!date) return "Unknown";
  return date.toLocaleString();
}
