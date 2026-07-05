"""
Parser for SBI 'Statement of Account' PDFs — a DIFFERENT layout than the
'Relationship Summary' format handled by sbi_parser.py.

Real-world discovery: the same bank (SBI) produces at least two structurally
different statement templates depending on account type/branch. Columns here
are: Value Date | Post Date | Details | Ref No/Cheque No | Debit | Credit | Balance
(vs. Date | Transaction Reference | Ref.No./Chq.No. | Credit | Debit | Balance
in the other format — note Credit/Debit are even in a different column order).

Layout quirk this parser handles: each transaction's date + amounts are on
ONE line, but the merchant name is truncated on that line and continues on
the line(s) below (e.g. ".../ONE" then "PUNE/HDFC/punencmctv/paym" on the
next line). We stitch these back together so merchant normalization has the
full name instead of a truncated fragment.
"""

import re
from dataclasses import dataclass
from typing import Optional

import pdfplumber
from pypdf import PdfReader

DATE_RE = r"\d{2}/\d{2}/\d{4}"

# The core transaction line: two dates, a (possibly truncated) description,
# then ref, debit, credit, balance -- ALL FOUR trailing columns captured
# explicitly (an earlier version only captured 3, which let the Ref column's
# "-" leak into the description text, e.g. "Adwait -/S/SBIN/..." instead of
# "Adwait/S/SBIN/..."). Ref is virtually always "-" in UPI statements but we
# capture and discard it explicitly rather than relying on it merging safely
# into the lazy description match.
# Description is OPTIONAL: some rows (e.g. a "CEMTEX DEP ITDTAX REFUND" tax
# refund credit) have no inline description at all between the two dates and
# the ref/debit/credit/balance columns -- their description text instead
# sits entirely on the line BEFORE this one. Without this being optional,
# such rows silently fail to match and get dropped, which understated the
# reconciled credit total by exactly that row's amount.
TRANSACTION_LINE_RE = re.compile(
    rf"^({DATE_RE})\s+({DATE_RE})\s+(?:(.+?)\s+)?(-|\S+)\s+(-|[\d,]+\.\d{{2}})\s+(-|[\d,]+\.\d{{2}})\s+([\d,]+\.\d{{2}})$"
)

# Lines that mark a NEW transaction is starting (so we know to stop
# stitching continuation lines onto the previous one)
TYPE_LINE_RE = re.compile(r"^(DEP TFR|WDL TFR)$")
DATE_START_RE = re.compile(rf"^{DATE_RE}\s+{DATE_RE}")
PAGE_FOOTER_RE = re.compile(r"^Page no\.")


@dataclass
class RawTransaction:
    date: str          # DD/MM/YYYY
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
    """
    Parses an SBI 'Statement of Account' PDF (distinct layout from the
    Relationship Summary format) into a list of RawTransaction.
    """
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

        # Some rows have no inline description (see regex comment above) --
        # in that case, the description text sits on the PRECEDING raw line
        # instead. Fall back to it, best-effort (it may also have been
        # appended to the previous transaction's description already, which
        # is a harmless cosmetic duplication rather than a data error).
        if not desc_partial and i > 0:
            prev_line = all_lines[i - 1].strip()
            if prev_line and not TYPE_LINE_RE.match(prev_line) and not DATE_START_RE.match(prev_line):
                desc_partial = prev_line

        # Stitch continuation lines onto the description (up to 3 lines,
        # stopping at the next transaction/type line or page footer)
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
            if len(desc_parts) >= 4:  # safety cap
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
    """Same reconciliation approach as the other parser: validate running
    balance consistency and derive opening balance from the first row."""
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
