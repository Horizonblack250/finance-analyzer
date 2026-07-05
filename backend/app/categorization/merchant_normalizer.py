"""
Merchant normalization: turns messy raw transaction descriptions into a
clean merchant name we can reliably categorize.

Why this exists (see research notes in project docs): categorization
accuracy is bottlenecked by description quality, not the classifier. A raw
SBI UPI description looks like:

    UPI/DR/612483787644/ZOMATO L/UTIB/zomatoorde/UPI

...which contains: transaction type, a 12-digit txn ID, a TRUNCATED merchant
name fragment, a bank code, and a VPA-style handle. None of that noise
should reach the categorizer — only "ZOMATO" should.
"""

import re

# Bank/PSP codes that show up as a segment in UPI descriptions — never the
# merchant name, so we can safely ignore these when picking which segment
# is "the merchant".
BANK_CODES = {
    "UTIB", "HDFC", "YESB", "SBIN", "ICIC", "KKBK", "JSBP", "BKID", "AIRP",
    "FDRL", "COSB", "PUNB", "UBIN", "MAHB", "CNRB", "IOBA", "IDIB", "AXIS",
    "INDB", "PYTM", "APBL",
}

# Known merchant name fragments -> canonical clean name.
# The SBI statement truncates names to ~8 chars, so we match on prefixes.
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
}


def _looks_like_person_name(segment: str) -> bool:
    """
    Heuristic: SBI truncates person-to-person transfer names to 8 chars,
    often ending mid-word (e.g. 'KABRA DE', 'Mr HANEE', 'SANJAYKU').
    We treat any segment we don't recognize as a known merchant as a
    likely P2P transfer, rather than guessing at a brand name.
    """
    return True  # fallback path; see categorize_merchant for the real logic


def normalize_merchant(raw_description: str) -> dict:
    """
    Parses a raw SBI UPI transaction description and extracts a clean
    merchant name + transaction subtype.

    Returns:
        {
            "clean_name": str,       # best-guess clean merchant/payee name
            "is_known_merchant": bool,
            "transaction_subtype": str,  # "UPI_DR", "UPI_CR", "OTHER"
            "raw": str,
        }
    """
    raw = raw_description.strip()
    segments = raw.split("/")

    subtype = "OTHER"
    if "UPI/DR" in raw:
        subtype = "UPI_DR"  # debit
    elif "UPI/CR" in raw:
        subtype = "UPI_CR"  # credit

    # Candidate segments: strip known non-merchant tokens (UPI, DR, CR, txn ID,
    # bank codes, and anything that's purely numeric or matches a VPA handle)
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
        # VPA-style handles (contain a dot or look like 'zomatoorde', 'q729249948')
        # are usually the last segment before /UPI — skip as merchant candidate
        # only if we already have a better candidate; otherwise keep as fallback.
        candidates.append(seg_clean)

    # Try known merchant match first (most reliable)
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

    # No known merchant matched — this is likely a person-to-person transfer.
    # Take the first non-VPA-looking candidate segment as the payee name.
    payee = None
    for cand in candidates:
        # Skip segments that look like VPA handles: lowercase with digits/dots,
        # e.g. 'zomatoorde', 'q729249948', 'gpay-11239'
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
