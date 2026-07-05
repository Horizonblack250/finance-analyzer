"""
Parser for SBI (State Bank of India) 'Relationship Summary' statement PDFs.

Real-world quirks this parser handles (discovered from an actual statement):
1. Some transaction rows wrap: a long description overflows onto the PREVIOUS
   line, leaving the date/ref/credit/debit/balance on their own line with no
   description. We merge these using a one-line lookback buffer.
2. The "Opening Balance" line is frequently garbled by pdfplumber (overlapping
   text gets interleaved into gibberish) since it's rendered as an overlay in
   the source PDF. We don't rely on parsing it — opening balance is instead
   derived by reconciliation from the first transaction's own balance delta.
3. Passwords: some SBI PDFs have a real "open" password (needs pypdf.decrypt),
   others only have an owner/permissions password (pdfplumber can read them
   directly). We try both.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pdfplumber
from pypdf import PdfReader


DATE_RE = r"\d{2}-\d{2}-\d{2}"

# A complete transaction row: date, description, ref (usually "-"), credit, debit, balance
FULL_ROW_RE = re.compile(
    rf"^({DATE_RE})\s+(.+?)\s+(-|\S+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$"
)

# A row missing its description (it wrapped onto the previous line):
# just date, ref, credit, debit, balance
PARTIAL_ROW_RE = re.compile(
    rf"^({DATE_RE})\s+(-|\S+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$"
)

# An orphan description line: no date prefix, but looks like a UPI/transaction reference
ORPHAN_DESC_RE = re.compile(r"^(?!.*\d{2}-\d{2}-\d{2}).*/.*/.*$")


@dataclass
class RawTransaction:
    date: str          # DD-MM-YY as string (matches statement format)
    description: str
    credit: float
    debit: float
    balance: float

    @property
    def amount(self) -> float:
        """Positive = money in, negative = money out."""
        return self.credit - self.debit

    @property
    def parsed_date(self) -> datetime:
        return datetime.strptime(self.date, "%d-%m-%y")


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def decrypt_if_needed(file_path: str, password: Optional[str] = None) -> None:
    """
    Checks if a PDF needs a password to open. Raises ValueError if a password
    is required but not provided or incorrect. No-op if the PDF opens freely
    (some bank PDFs only have owner/print restrictions, not a real open password).
    """
    reader = PdfReader(file_path)
    if reader.is_encrypted:
        if not password:
            raise ValueError("This PDF is password-protected. Please provide the password.")
        result = reader.decrypt(password)
        if result == 0:
            raise ValueError("Incorrect password for this PDF.")


def parse_sbi_statement(file_path: str, password: Optional[str] = None) -> list[RawTransaction]:
    """
    Parses an SBI relationship-summary statement PDF into a list of RawTransaction.
    Handles multi-line-wrapped descriptions automatically.
    """
    decrypt_if_needed(file_path, password)

    all_lines: list[str] = []
    with pdfplumber.open(file_path, password=password) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_lines.extend(text.split("\n"))

    transactions: list[RawTransaction] = []
    pending_desc: Optional[str] = None

    for line in all_lines:
        line = line.strip()
        if not line:
            continue

        full_match = FULL_ROW_RE.match(line)
        if full_match:
            date, desc, _ref, credit, debit, balance = full_match.groups()
            transactions.append(RawTransaction(
                date=date,
                description=desc.strip(),
                credit=_to_float(credit),
                debit=_to_float(debit),
                balance=_to_float(balance),
            ))
            pending_desc = None
            continue

        partial_match = PARTIAL_ROW_RE.match(line)
        if partial_match:
            date, _ref, credit, debit, balance = partial_match.groups()
            # Description must have come from the previous (orphan) line
            desc = pending_desc or "UNKNOWN"
            transactions.append(RawTransaction(
                date=date,
                description=desc.strip(),
                credit=_to_float(credit),
                debit=_to_float(debit),
                balance=_to_float(balance),
            ))
            pending_desc = None
            continue

        # Not a transaction row at all — check if it looks like an orphan
        # description that belongs to the NEXT line.
        if ORPHAN_DESC_RE.match(line) and "/" in line:
            pending_desc = line
        else:
            pending_desc = None  # reset; this was some unrelated line (header, footer, etc.)

    return transactions


def reconcile(transactions: list[RawTransaction]) -> dict:
    """
    Sanity-checks the parsed transactions: for each row, balance should equal
    previous balance + credit - debit. Returns a summary including any
    mismatches found, so we can trust (or flag) the parse quality.
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

    # Derive opening balance from the first transaction (since the printed
    # "Opening Balance" line is unreliable in the source PDF)
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
