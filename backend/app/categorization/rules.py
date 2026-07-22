from dataclasses import dataclass
from enum import Enum

from app.categorization.merchant_normalizer import normalize_merchant


class Category(str, Enum):
    FOOD_DELIVERY = "Food Delivery"
    FOOD_DINING = "Food & Dining"
    GROCERIES = "Groceries"
    SUBSCRIPTIONS = "Subscriptions"
    UTILITIES = "Utilities & Recharge"
    TRANSPORT = "Transport"
    SHOPPING = "Shopping"
    HEALTH = "Health & Medical"
    ENTERTAINMENT = "Entertainment"
    SNACKS_VENDING = "Snacks & Vending"
    RENT_HOUSING = "Rent & Housing"
    TRANSFER_PERSON = "Person-to-Person Transfer"
    INCOME = "Income / Credit"
    UNCATEGORIZED = "Uncategorized"


CATEGORY_RULES: dict[Category, set[str]] = {
    Category.FOOD_DELIVERY: {"zomato", "swiggy", "blinkit"},
    Category.GROCERIES: {"bigbasket", "grofers", "dmart"},
    Category.SUBSCRIPTIONS: {"spotify", "netflix", "prime", "hotstar", "youtube premium"},
    Category.UTILITIES: {"airtel", "jio", "vodafone", "vi ", "electricity", "recharge"},
    Category.TRANSPORT: {"uber", "ola", "pune metro", "metro", "rapido"},
    Category.SHOPPING: {"amazon", "flipkart", "myntra", "ajio"},
    Category.HEALTH: {"pharmeasy", "1mg", "apollo", "practo", "max heal"},
    Category.ENTERTAINMENT: {"bookmyshow", "pvr", "inox", "fancode"},
    Category.INCOME: {"itdtax", "cemtex", "interest credit"},
}


@dataclass
class CategorizedTransaction:
    clean_merchant: str
    category: Category
    confidence: float
    needs_review: bool


def _match_category_by_keyword(clean_name_lower: str) -> Category | None:
    for category, keywords in CATEGORY_RULES.items():
        if any(kw in clean_name_lower for kw in keywords):
            return category
    return None


def categorize(raw_description: str, credit: float, debit: float) -> CategorizedTransaction:
    merchant_info = normalize_merchant(raw_description)
    clean_name = merchant_info["clean_name"]
    clean_name_lower = clean_name.lower()

    from app.categorization.corrections import get_override
    override_value = get_override(clean_name)
    if override_value is not None:
        return CategorizedTransaction(
            clean_merchant=clean_name,
            category=Category(override_value),
            confidence=1.0,
            needs_review=False,
        )

    matched_category = _match_category_by_keyword(clean_name_lower)
    if matched_category is not None:
        return CategorizedTransaction(
            clean_merchant=clean_name,
            category=matched_category,
            confidence=1.0,
            needs_review=False,
        )

    if credit > 0:
        return CategorizedTransaction(
            clean_merchant=clean_name,
            category=Category.INCOME,
            confidence=0.6,
            needs_review=True,
        )

    if merchant_info["is_known_merchant"]:
        return CategorizedTransaction(
            clean_merchant=clean_name,
            category=Category.UNCATEGORIZED,
            confidence=0.3,
            needs_review=True,
        )

    return CategorizedTransaction(
        clean_merchant=clean_name,
        category=Category.TRANSFER_PERSON,
        confidence=0.4,
        needs_review=True,
    )
