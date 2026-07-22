import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.categorization.rules import categorize
from app.categorization.db_corrections import get_override
from app.categorization.merchant_normalizer import normalize_merchant
from app.parsers.sbi_parser import parse_sbi_statement
from app.parsers.sbi_statement_of_account_parser import parse_sbi_statement_of_account


def _transaction_already_exists(session: Session, user_id: uuid.UUID, date: str, raw_description: str, debit: float, credit: float) -> bool:
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


def import_and_save_statement(
    session: Session,
    user_id: uuid.UUID,
    file_path: str,
    statement_format: str,
    password: str | None = None,
) -> dict:
    if statement_format == "relationship_summary":
        raw_transactions = parse_sbi_statement(file_path, password=password)
    elif statement_format == "statement_of_account":
        raw_transactions = parse_sbi_statement_of_account(file_path, password=password)
    else:
        raise ValueError(f"Unknown format: {statement_format}")

    inserted = 0
    skipped_duplicates = 0
    needs_review_count = 0

    for txn in raw_transactions:
        if _transaction_already_exists(session, user_id, txn.date, txn.description, float(txn.debit), float(txn.credit)):
            skipped_duplicates += 1
            continue

        clean_name = normalize_merchant(txn.description)["clean_name"]
        override_category = get_override(session, user_id, clean_name)

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

        if needs_review:
            needs_review_count += 1

        session.add(Transaction(
            user_id=user_id,
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

    return {
        "total_parsed": len(raw_transactions),
        "inserted": inserted,
        "skipped_duplicates": skipped_duplicates,
        "needs_review": needs_review_count,
    }
