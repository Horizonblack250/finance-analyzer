"""
Rule-based transaction categorization.

Design decisions (informed by research — see project notes):
- Categorizes the NORMALIZED merchant name, not the raw description, since
  merchant-name noise is the main source of categorization error.
- Returns a confidence score, not just a category. Low-confidence results
  should be surfaced to the user for confirmation rather than silently
  guessed — this is the "guided feedback loop" pattern used in production
  categorization systems, and it's also our personalization hook: every
  user correction becomes training signal for later.
- Rules are intentionally simple keyword matches. This is meant to be the
  fast, deterministic first pass; a learned classifier can sit on top of
  this later for the residual "Uncategorized" cases without changing this
  module's interface.
"""

from dataclasses import dataclass
from enum import Enum

from app.categorization.merchant_normalizer import normalize_merchant


class Category(str, Enum):
    FOOD_DELIVERY = "Food Delivery"
    GROCERIES = "Groceries"
    SUBSCRIPTIONS = "Subscriptions"
    UTILITIES = "Utilities & Recharge"
    TRANSPORT = "Transport"
    SHOPPING = "Shopping"
    HEALTH = "Health & Medical"
    ENTERTAINMENT = "Entertainment"
    TRANSFER_PERSON = "Person-to-Person Transfer"
    INCOME = "Income / Credit"
    UNCATEGORIZED = "Uncategorized"


# Category -> set of clean-merchant-name keywords that map to it.
# Matched case-insensitively against the NORMALIZED merchant name.
CATEGORY_RULES: dict[Category, set[str]] = {
    Category.FOOD_DELIVERY: {"zomato", "swiggy", "blinkit"},
    Category.GROCERIES: {"bigbasket", "grofers", "dmart"},
    Category.SUBSCRIPTIONS: {"spotify", "netflix", "prime", "hotstar", "youtube premium"},
    Category.UTILITIES: {"airtel", "jio", "vodafone", "vi ", "electricity", "recharge"},
    Category.TRANSPORT: {"uber", "ola", "pune metro", "metro", "rapido"},
    Category.SHOPPING: {"amazon", "flipkart", "myntra", "ajio"},
    Category.HEALTH: {"pharmeasy", "1mg", "apollo", "practo", "max heal"},
    Category.ENTERTAINMENT: {"bookmyshow", "pvr", "inox"},
}


@dataclass
class CategorizedTransaction:
    clean_merchant: str
    category: Category
    confidence: float  # 0.0 - 1.0
    needs_review: bool  # True if confidence is too low to trust automatically


def _match_category_by_keyword(clean_name_lower: str) -> Category | None:
    """Checks the clean merchant name against every category's keyword set."""
    for category, keywords in CATEGORY_RULES.items():
        if any(kw in clean_name_lower for kw in keywords):
            return category
    return None


def categorize(raw_description: str, credit: float, debit: float) -> CategorizedTransaction:
    """
    Categorizes a single transaction using the rule engine.

    Order of checks (a keyword match always wins, regardless of whether the
    merchant normalizer separately flagged it as "known" -- those two systems
    used to disagree, e.g. 'Max Heal' matching the Health keyword rule but
    not being in the normalizer's known-merchant list, silently falling
    through to the P2P-transfer guess. Checking keywords first fixes that.):

      1. Keyword rule match on the clean merchant name -> high confidence (1.0)
      2. Credit with no keyword match -> treated as income (0.6, needs review)
      3. No keyword match, is a recognized brand pattern but no rule written
         for it yet -> Uncategorized (0.3, needs review)
      4. No keyword match, not a recognized brand -> likely a person-to-person
         transfer (0.4, needs review)

    Anything below 0.7 confidence should be flagged needs_review=True so the
    app can ask the user to confirm/correct it, rather than silently guessing.
    """
    merchant_info = normalize_merchant(raw_description)
    clean_name = merchant_info["clean_name"]
    clean_name_lower = clean_name.lower()

    matched_category = _match_category_by_keyword(clean_name_lower)
    if matched_category is not None:
        return CategorizedTransaction(
            clean_merchant=clean_name,
            category=matched_category,
            confidence=1.0,
            needs_review=False,
        )

    # Credits (money coming in) that aren't a known merchant refund pattern
    # are treated as income/credit by default.
    if credit > 0:
        return CategorizedTransaction(
            clean_merchant=clean_name,
            category=Category.INCOME,
            confidence=0.6,
            needs_review=True,
        )

    if merchant_info["is_known_merchant"]:
        # Known brand but no category rule written for it yet
        return CategorizedTransaction(
            clean_merchant=clean_name,
            category=Category.UNCATEGORIZED,
            confidence=0.3,
            needs_review=True,
        )

    # Not a known merchant -> likely a person-to-person transfer
    return CategorizedTransaction(
        clean_merchant=clean_name,
        category=Category.TRANSFER_PERSON,
        confidence=0.4,
        needs_review=True,
    )
