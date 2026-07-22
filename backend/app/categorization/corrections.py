import json
from pathlib import Path

CORRECTIONS_FILE = Path(__file__).parent / "user_corrections.json"


def load_overrides() -> dict[str, str]:
    if not CORRECTIONS_FILE.exists():
        return {}
    with open(CORRECTIONS_FILE, "r") as f:
        return json.load(f)


def save_overrides(overrides: dict[str, str]) -> None:
    with open(CORRECTIONS_FILE, "w") as f:
        json.dump(overrides, f, indent=2)


def add_correction(merchant_name: str, category) -> None:
    overrides = load_overrides()
    overrides[merchant_name.strip().lower()] = category.value if hasattr(category, "value") else category
    save_overrides(overrides)


def get_override(merchant_name: str) -> str | None:
    overrides = load_overrides()
    merchant_lower = merchant_name.strip().lower()
    for stored_name, category_value in overrides.items():
        if stored_name in merchant_lower or merchant_lower in stored_name:
            return category_value
    return None
