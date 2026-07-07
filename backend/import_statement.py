"""
Parses a bank statement, categorizes every transaction (checking your
saved DB corrections first, then falling back to the rule engine), and
saves everything to the database. Safe to re-run on the same file --
it skips transactions that already exist instead of creating duplicates.

Usage:
    python import_statement.py path/to/statement.pdf --format relationship_summary
    python import_statement.py path/to/statement.pdf --format statement_of_account
"""

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.models.transaction import Transaction
from app.categorization.rules import categorize
from app.categorization.db_corrections import get_override
from app.parsers.sbi_parser import parse_sbi_statement
from app.parsers.sbi_statement_of_account_parser import parse_sbi_statement_of_account


def transaction_already_exists(session: Session, user_id, date: str, raw_description: str, debit: float, credit: float) -> bool:
    """
    Dedup check: a transaction is considered "the same" if it has the same
    user, date, raw description, and amounts. This lets you safely re-run
    the import on a file you've already imported (e.g. after adding new
    corrections) without creating duplicate rows.
    """
    existing = session.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date == date,
            Transaction.raw_description == raw_description,
            Transaction.debit == debit,
            Transaction.credit == credit,
        )
    ).scalar_one_or_none()
    return existing is not None


def run(file_path: str, statement_format: str, password: str | None) -> None:
    if statement_format == "relationship_summary":
        raw_transactions = parse_sbi_statement(file_path, password=password)
    elif statement_format == "statement_of_account":
        raw_transactions = parse_sbi_statement_of_account(file_path, password=password)
    else:
        raise ValueError(f"Unknown format: {statement_format}")

    print(f"Parsed {len(raw_transactions)} transactions from {file_path}")

    session = SessionLocal()
    inserted = 0
    skipped_duplicates = 0

    try:
        for txn in raw_transactions:
            if transaction_already_exists(session, DEFAULT_USER_ID, txn.date, txn.description, float(txn.debit), float(txn.credit)):
                skipped_duplicates += 1
                continue

            # Check your saved corrections FIRST -- this is the
            # personalization loop, now backed by the database instead
            # of a local JSON file.
            from app.categorization.merchant_normalizer import normalize_merchant
            clean_name = normalize_merchant(txn.description)["clean_name"]
            override_category = get_override(session, DEFAULT_USER_ID, clean_name)

            if override_category is not None:
                category_value = override_category
                confidence = 1.0
                needs_review = False
                merchant_name = clean_name
            else:
                result = categorize(txn.description, txn.credit, txn.debit)
                category_value = result.category.value
                confidence = result.confidence
                needs_review = result.needs_review
                merchant_name = result.clean_merchant

            session.add(Transaction(
                user_id=DEFAULT_USER_ID,
                transaction_date=txn.date,
                raw_description=txn.description,
                clean_merchant=merchant_name,
                credit=txn.credit,
                debit=txn.debit,
                balance=txn.balance,
                category=category_value,
                confidence=confidence,
                needs_review=needs_review,
                source_filename=file_path,
                statement_format=statement_format,
            ))
            inserted += 1

        session.commit()
    finally:
        session.close()

    print(f"Inserted {inserted} new transactions.")
    print(f"Skipped {skipped_duplicates} already-imported duplicates.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse, categorize, and save a bank statement to the database")
    parser.add_argument("file_path", help="Path to the statement PDF")
    parser.add_argument(
        "--format",
        dest="statement_format",
        required=True,
        choices=["relationship_summary", "statement_of_account"],
    )
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    run(args.file_path, args.statement_format, args.password)
