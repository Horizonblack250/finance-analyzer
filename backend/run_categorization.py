"""
Standalone script: parses a bank statement PDF, categorizes every
transaction, and prints a summary report.

USAGE (run from the backend/ folder):

    python run_categorization.py path/to/statement.pdf --format relationship_summary
    python run_categorization.py path/to/statement.pdf --format statement_of_account

Use --format relationship_summary for statements like Adwait's (columns:
Date | Transaction Reference | Ref.No./Chq.No. | Credit | Debit | Balance).

Use --format statement_of_account for statements like Amogh's (columns:
Value Date | Post Date | Details | Ref No/Cheque No | Debit | Credit | Balance).

If the PDF is password-protected, pass --password YOUR_PASSWORD too.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from app.categorization.rules import categorize
from app.parsers.sbi_parser import parse_sbi_statement
from app.parsers.sbi_statement_of_account_parser import parse_sbi_statement_of_account


def run(file_path: str, statement_format: str, password: str | None) -> None:
    if statement_format == "relationship_summary":
        raw_transactions = parse_sbi_statement(file_path, password=password)
    elif statement_format == "statement_of_account":
        raw_transactions = parse_sbi_statement_of_account(file_path, password=password)
    else:
        raise ValueError(f"Unknown format: {statement_format}")

    print(f"Parsed {len(raw_transactions)} transactions from {file_path}\n")

    category_totals: dict[str, float] = defaultdict(float)
    category_counts: dict[str, int] = defaultdict(int)
    needs_review: list = []

    for txn in raw_transactions:
        result = categorize(txn.description, txn.credit, txn.debit)
        category_totals[result.category.value] += txn.debit  # spend, not income
        category_counts[result.category.value] += 1
        if result.needs_review:
            needs_review.append((txn.date, result.clean_merchant, txn.debit, txn.credit, result.category.value))

    print("=" * 70)
    print("SPENDING BY CATEGORY (debits only)")
    print("=" * 70)
    for category, total in sorted(category_totals.items(), key=lambda x: -x[1]):
        count = category_counts[category]
        print(f"  {category:30s} Rs.{total:>10,.2f}  ({count} transactions)")

    print()
    print("=" * 70)
    print(f"NEEDS YOUR REVIEW ({len(needs_review)} transactions, low-confidence categorization)")
    print("=" * 70)
    for date, merchant, debit, credit, category in needs_review:
        amount = f"-{debit:.2f}" if debit else f"+{credit:.2f}"
        print(f"  {date} | {merchant:20s} | {amount:>10s} | guessed: {category}")

    # Also write the full list to a CSV so it's easy to scroll/filter/sort
    # outside the terminal, and easy to paste specific rows back for review.
    csv_path = Path(file_path).with_name("needs_review.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "merchant", "debit", "credit", "guessed_category"])
        for date, merchant, debit, credit, category in needs_review:
            writer.writerow([date, merchant, debit, credit, category])
    print()
    print(f"Full list also saved to: {csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse and categorize a bank statement PDF")
    parser.add_argument("file_path", help="Path to the statement PDF")
    parser.add_argument(
        "--format",
        dest="statement_format",
        required=True,
        choices=["relationship_summary", "statement_of_account"],
        help="Which SBI statement layout this file uses",
    )
    parser.add_argument("--password", default=None, help="PDF password, if protected")
    args = parser.parse_args()

    run(args.file_path, args.statement_format, args.password)
