import re

BANK_CODES = {
    "UTIB", "HDFC", "YESB", "SBIN", "ICIC", "KKBK", "JSBP", "BKID", "AIRP",
    "FDRL", "COSB", "PUNB", "UBIN", "MAHB", "CNRB", "IOBA", "IDIB", "AXIS",
    "INDB", "PYTM", "APBL",
}

KNOWN_MERCHANT_PREFIXES = {
    "ZOMATO": "Zomato",
    "SWIGGY": "Swiggy",
    "BLINKIT": "Blinkit",
    "SPOTIFY": "Spotify",
    "AIRTEL": "Airtel",
    "NETFLIX": "Netflix",
    "AMAZON": "Amazon",
    "FLIPKART": "Flipkart",
    "PUNE MET": "Pune Metro",
    "PUNEMET": "Pune Metro",
    "ONE PUNE": "Pune Metro Recharge",
    "UBER": "Uber",
    "OLA": "Ola",
    "MYNTRA": "Myntra",
    "BIGBASKET": "BigBasket",
    "FANCODE": "FanCode",
}


def normalize_merchant(raw_description: str) -> dict:
    raw = raw_description.strip()
    segments = raw.split("/")

    subtype = "OTHER"
    if "UPI/DR" in raw:
        subtype = "UPI_DR"
    elif "UPI/CR" in raw:
        subtype = "UPI_CR"

    candidates = []
    for seg in segments:
        seg_clean = seg.strip()
        if not seg_clean:
            continue
        if seg_clean.upper() in {"UPI", "DR", "CR"}:
            continue
        if seg_clean.upper() in BANK_CODES:
            continue
        if seg_clean.isdigit():
            continue
        candidates.append(seg_clean)

    for cand in candidates:
        cand_upper = cand.upper()
        for prefix, clean_name in KNOWN_MERCHANT_PREFIXES.items():
            if cand_upper.startswith(prefix[:8]) or prefix.startswith(cand_upper[:6]):
                return {
                    "clean_name": clean_name,
                    "is_known_merchant": True,
                    "transaction_subtype": subtype,
                    "raw": raw,
                }

    payee = None
    for cand in candidates:
        if re.match(r"^[a-z][a-z0-9._-]*\d", cand) or re.match(r"^q\d+$", cand.lower()):
            continue
        payee = cand
        break

    return {
        "clean_name": (payee or "Unknown").title(),
        "is_known_merchant": False,
        "transaction_subtype": subtype,
        "raw": raw,
    }
