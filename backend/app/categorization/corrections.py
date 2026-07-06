"""
User correction overrides.

This is the personalization mechanism: when the rule engine can't confidently
categorize a merchant (person-to-person transfers, local shops, vending
machines -- anything with no generic keyword match), the USER'S OWN
correction becomes the source of truth going forward for that merchant name.

Right now this is a simple in-memory/JSON-backed dict, standing in for what
will become a database table (user_corrections) once persistence is wired
up. The interface (get_override / add_override) is designed to stay the
same when we swap the storage backend later -- only load_overrides() and
save_overrides() will change to hit a database instead of a file.
"""

import json
from pathlib import Path

from app.categorization.rules import Category

CORRECTIONS_FILE = Path(__file__).parent / "user_corrections.json"


def load_overrides() -> dict[str, str]:
    """Loads merchant-name -> category-value overrides from disk."""
    if not CORRECTIONS_FILE.exists():
        return {}
    with open(CORRECTIONS_FILE, "r") as f:
        return json.load(f)


def save_overrides(overrides: dict[str, str]) -> None:
    with open(CORRECTIONS_FILE, "w") as f:
        json.dump(overrides, f, indent=2)


def add_correction(merchant_name: str, category: Category) -> None:
    """
    Records a user correction: from now on, this merchant name will always
    be categorized as this category, overriding the generic rule engine.
    Matching is case-insensitive on the clean merchant name.
    """
    overrides = load_overrides()
    overrides[merchant_name.strip().lower()] = category.value
    save_overrides(overrides)


def get_override(merchant_name: str) -> str | None:
    """
    Returns the corrected category value for this merchant, if one exists.
    Matching is substring-based (not exact), since the normalized merchant
    name may include extra words the user didn't type when correcting it
    (e.g. correcting "Drop" should still match the normalized name
    "Drop It" -- exact matching would silently miss this).
    """
    overrides = load_overrides()
    merchant_lower = merchant_name.strip().lower()
    for stored_name, category_value in overrides.items():
        if stored_name in merchant_lower or merchant_lower in stored_name:
            return category_value
    return None
