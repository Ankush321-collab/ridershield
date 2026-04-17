export function normalizeIndianMobile(input: string) {
  const raw = (input || "").trim();
  if (!raw) {
    return { normalized: "", valid: false, error: "Phone number is required." };
  }

  if (/[A-Za-z]/.test(raw)) {
    return { normalized: "", valid: false, error: "Phone number must contain digits only." };
  }

  let cleaned = raw.replace(/[\s\-()]/g, "");
  if (cleaned.startsWith("+")) {
    cleaned = `+${cleaned.slice(1).replace(/\+/g, "")}`;
  }

  let national = cleaned;
  if (cleaned.startsWith("+91")) {
    national = cleaned.slice(3);
  } else if (cleaned.startsWith("91") && cleaned.length === 12) {
    national = cleaned.slice(2);
  } else if (cleaned.startsWith("0") && cleaned.length === 11) {
    national = cleaned.slice(1);
  }

  if (!/^\d+$/.test(national)) {
    return { normalized: "", valid: false, error: "Phone number must contain digits only." };
  }

  if (!/^[6-9]\d{9}$/.test(national)) {
    return { normalized: "", valid: false, error: "Enter a valid 10-digit Indian mobile number." };
  }

  return { normalized: `+91${national}`, valid: true, error: "" };
}

