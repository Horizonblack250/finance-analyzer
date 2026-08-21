"""
HDFC statement parser -- STUB. The actual column-extraction logic (date
format, description/reference columns, debit/credit layout, header/footer
noise) has NOT been implemented yet, because it needs to be built against a
real HDFC statement, the same way both SBI parsers were built and
reconciliation-tested against real statements before being trusted.

This file exists so the rest of the app (dispatch logic, upload endpoint,
frontend dropdown) is fully wired and ready -- selecting HDFC and uploading
right now will fail with a clear, friendly error instead of a confusing
500 or, worse, a parser that silently mis-reads columns and produces wrong
numbers. Once a real sample HDFC statement is available, only
parse_hdfc_statement() below needs real logic -- everything else in the
app already knows how to route to it.
"""

from dataclasses import dataclass
from typing import Optional

from pypdf import PdfReader


@dataclass
class RawTransaction:
    date: str
    description: str
    credit: float
    debit: float
    balance: float

    @property
    def amount(self) -> float:
        return self.credit - self.debit


def decrypt_if_needed(file_path: str, password: Optional[str] = None) -> None:
    reader = PdfReader(file_path)
    if reader.is_encrypted:
        if not password:
            raise ValueError("This PDF is password-protected. Please provide the password.")
        if reader.decrypt(password) == 0:
            raise ValueError("Incorrect password for this PDF.")


def parse_hdfc_statement(file_path: str, password: Optional[str] = None) -> list[RawTransaction]:
    """
    NOT YET IMPLEMENTED. Column layout, date format, and description
    parsing need to be built against a real HDFC statement before this can
    be trusted -- see module docstring above for why.
    """
    decrypt_if_needed(file_path, password)
    raise ValueError(
        "HDFC statement support is coming soon but isn't ready yet -- the "
        "parsing logic hasn't been built and tested against a real HDFC "
        "statement. Please use SBI for now."
    )


def reconcile(transactions: list[RawTransaction]) -> dict:
    """
    Bank-agnostic -- kept identical to the SBI parsers' reconcile() by
    design, since balance-chain reconciliation logic doesn't depend on
    bank-specific formatting, only on debit/credit/balance being correctly
    populated per transaction.
    """
    issues = []
    for i in range(1, len(transactions)):
        prev = transactions[i - 1]
        curr = transactions[i]
        expected = round(prev.balance + curr.credit - curr.debit, 2)
        if abs(expected - curr.balance) > 0.01:
            issues.append({
                "index": i,
                "expected_balance": expected,
                "actual_balance": curr.balance,
                "description": curr.description,
            })

    opening_balance = None
    if transactions:
        first = transactions[0]
        opening_balance = round(first.balance - first.credit + first.debit, 2)

    return {
        "total_transactions": len(transactions),
        "opening_balance": opening_balance,
        "closing_balance": transactions[-1].balance if transactions else None,
        "mismatches": issues,
    }