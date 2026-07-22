import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pdfplumber
from pypdf import PdfReader


DATE_RE = r"\d{2}-\d{2}-\d{2}"

FULL_ROW_RE = re.compile(
    rf"^({DATE_RE})\s+(.+?)\s+(-|\S+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$"
)

PARTIAL_ROW_RE = re.compile(
    rf"^({DATE_RE})\s+(-|\S+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$"
)

ORPHAN_DESC_RE = re.compile(r"^(?!.*\d{2}-\d{2}-\d{2}).*/.*/.*$")


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

    @property
    def parsed_date(self) -> datetime:
        return datetime.strptime(self.date, "%d-%m-%y")


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def decrypt_if_needed(file_path: str, password: Optional[str] = None) -> None:
    reader = PdfReader(file_path)
    if reader.is_encrypted:
        if not password:
            raise ValueError("This PDF is password-protected. Please provide the password.")
        result = reader.decrypt(password)
        if result == 0:
            raise ValueError("Incorrect password for this PDF.")


def parse_sbi_statement(file_path: str, password: Optional[str] = None) -> list[RawTransaction]:
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

        if ORPHAN_DESC_RE.match(line) and "/" in line:
            pending_desc = line
        else:
            pending_desc = None

    return transactions


def reconcile(transactions: list[RawTransaction]) -> dict:
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
