import re
from dataclasses import dataclass
from typing import Optional

import pdfplumber
from pypdf import PdfReader

DATE_RE = r"\d{2}/\d{2}/\d{4}"

TRANSACTION_LINE_RE = re.compile(
    rf"^({DATE_RE})\s+({DATE_RE})\s+(?:(.+?)\s+)?(-|\S+)\s+(-|[\d,]+\.\d{{2}})\s+(-|[\d,]+\.\d{{2}})\s+([\d,]+\.\d{{2}})$"
)

TYPE_LINE_RE = re.compile(r"^(DEP TFR|WDL TFR)$")
DATE_START_RE = re.compile(rf"^{DATE_RE}\s+{DATE_RE}")
PAGE_FOOTER_RE = re.compile(r"^Page no\.")


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


def _to_float(s: str) -> float:
    if s == "-":
        return 0.0
    return float(s.replace(",", ""))


def decrypt_if_needed(file_path: str, password: Optional[str] = None) -> None:
    reader = PdfReader(file_path)
    if reader.is_encrypted:
        if not password:
            raise ValueError("This PDF is password-protected. Please provide the password.")
        if reader.decrypt(password) == 0:
            raise ValueError("Incorrect password for this PDF.")


def parse_sbi_statement_of_account(file_path: str, password: Optional[str] = None) -> list[RawTransaction]:
    decrypt_if_needed(file_path, password)

    all_lines: list[str] = []
    with pdfplumber.open(file_path, password=password) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_lines.extend(text.split("\n"))

    transactions: list[RawTransaction] = []
    i = 0
    n = len(all_lines)

    while i < n:
        line = all_lines[i].strip()
        match = TRANSACTION_LINE_RE.match(line)

        if not match:
            i += 1
            continue

        date1, _date2, desc_partial, _ref, debit, credit, balance = match.groups()

        if not desc_partial and i > 0:
            prev_line = all_lines[i - 1].strip()
            if prev_line and not TYPE_LINE_RE.match(prev_line) and not DATE_START_RE.match(prev_line):
                desc_partial = prev_line

        desc_parts = [(desc_partial or "UNKNOWN").strip()]
        j = i + 1
        while j < n:
            next_line = all_lines[j].strip()
            if (not next_line
                    or TYPE_LINE_RE.match(next_line)
                    or DATE_START_RE.match(next_line)
                    or PAGE_FOOTER_RE.match(next_line)):
                break
            desc_parts.append(next_line)
            j += 1
            if len(desc_parts) >= 4:
                break

        full_description = "/".join(desc_parts)

        transactions.append(RawTransaction(
            date=date1,
            description=full_description,
            credit=_to_float(credit),
            debit=_to_float(debit),
            balance=_to_float(balance),
        ))

        i = j if j > i + 1 else i + 1

    return transactions


def reconcile(transactions: list[RawTransaction]) -> dict:
    issues = []
    for k in range(1, len(transactions)):
        prev = transactions[k - 1]
        curr = transactions[k]
        expected = round(prev.balance + curr.credit - curr.debit, 2)
        if abs(expected - curr.balance) > 0.01:
            issues.append({
                "index": k,
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
