"""
Add your own merchant corrections here, then run this script once.

HOW TO USE:
1. Look at the "NEEDS YOUR REVIEW" list from run_categorization.py
2. For any merchant you recognize (a local shop, a specific person, a
   vending machine, etc.), add a line below telling it the right category
3. Run: python add_my_corrections.py
4. Re-run run_categorization.py -- those merchants will now be
   auto-categorized instead of flagged for review

Available categories (copy the exact name):
    Category.FOOD_DELIVERY      "Food Delivery"        (Zomato, Swiggy, Blinkit)
    Category.FOOD_DINING        "Food & Dining"         (restaurants, sweet shops)
    Category.GROCERIES          "Groceries"
    Category.SUBSCRIPTIONS      "Subscriptions"
    Category.UTILITIES          "Utilities & Recharge"
    Category.TRANSPORT          "Transport"
    Category.SHOPPING           "Shopping"
    Category.HEALTH             "Health & Medical"
    Category.ENTERTAINMENT      "Entertainment"
    Category.SNACKS_VENDING     "Snacks & Vending"
    Category.RENT_HOUSING       "Rent & Housing"
    Category.TRANSFER_PERSON    "Person-to-Person Transfer"
    Category.INCOME             "Income / Credit"
"""

from app.categorization.corrections import add_correction
from app.categorization.rules import Category

# ------------------------------------------------------------------
# ADD YOUR CORRECTIONS BELOW THIS LINE (one add_correction() per merchant)
# ------------------------------------------------------------------

add_correction("Drop", Category.SNACKS_VENDING)
add_correction("Chitale", Category.FOOD_DINING)
add_correction("Ajinkya", Category.RENT_HOUSING)
add_correction("Mauli", Category.FOOD_DINING)

# Example of how to add more -- uncomment and edit:
# add_correction("Mauli", Category.FOOD_DINING)

# ------------------------------------------------------------------

print("Corrections saved. Re-run run_categorization.py to see the effect.")
