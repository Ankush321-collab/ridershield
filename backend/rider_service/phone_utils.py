import re


INDIA_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def normalize_indian_mobile(phone: str) -> str:
    value = (phone or "").strip()
    if not value:
        raise ValueError("Phone number is required.")

    if re.search(r"[A-Za-z]", value):
        raise ValueError("Phone number must contain digits only.")

    cleaned = re.sub(r"[\s\-()]", "", value)
    if cleaned.startswith("+"):
        cleaned = f"+{cleaned[1:].replace('+', '')}"

    if cleaned.startswith("+91"):
        national = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        national = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        national = cleaned[1:]
    else:
        national = cleaned

    if not national.isdigit():
        raise ValueError("Phone number must contain digits only.")

    if not INDIA_MOBILE_RE.fullmatch(national):
        raise ValueError("Enter a valid 10-digit Indian mobile number.")

    return f"+91{national}"

