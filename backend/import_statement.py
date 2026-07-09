"""
CLI wrapper around app/services/statement_import.py -- kept for local
testing convenience. The actual logic lives in the service module, shared
with the FastAPI /upload endpoint, so the two can never silently drift
apart from each other.

Usage:
    python import_statement.py path/to/statement.pdf --format relationship_summary
    python import_statement.py path/to/statement.pdf --format statement_of_account
"""

import argparse

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.services.statement_import import import_and_save_statement


def run(file_path: str, statement_format: str, password: str | None) -> None:
    session = SessionLocal()
    try:
        summary = import_and_save_statement(session, DEFAULT_USER_ID, file_path, statement_format, password)
    finally:
        session.close()

    print(f"Parsed {summary['total_parsed']} transactions from {file_path}")
    print(f"Inserted {summary['inserted']} new transactions.")
    print(f"Skipped {summary['skipped_duplicates']} already-imported duplicates.")
    print(f"{summary['needs_review']} of the inserted transactions need your review (low-confidence categorization).")


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
