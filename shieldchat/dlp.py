"""
dlp.py - Layer 1 Data Loss Prevention (DLP) engine.

Runs LOCALLY on the server, before anything else, on every message.
Think of it as the airport X-ray scanner for chat messages: it looks for
shapes of sensitive data (card numbers, Aadhaar, PAN, IFSC, bank accounts)
and then double-checks them with maths (Luhn / Verhoeff checksums) so that
random numbers are not flagged by mistake.

If this layer finds anything, the message is blocked and the raw text is
NEVER sent to the Gemini AI (sensitive data must not leave our server).

Main entry points:
    scan(text)              -> list of findings
    mask_text(text, found)  -> the message with sensitive values masked
    public_findings(found)  -> findings without internal position data (for the UI)
"""

import re

# --------------------------------------------------------------------------
# Checksums
# --------------------------------------------------------------------------


def luhn_valid(number: str) -> bool:
    """Return True if a digit string passes the Luhn (mod 10) check used by all payment cards."""
    # Luhn is like a spelling check for numbers: the last digit is calculated
    # from the others, so one wrong or swapped digit makes the check fail.
    # Steps: from the right, double every second digit; if that gives > 9,
    # subtract 9; add everything up; a valid number's total ends in 0.
    digits = [int(d) for d in number if d.isdigit()]
    if not digits:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# Verhoeff algorithm tables (fixed constants from the published algorithm).
# Verhoeff is stronger than Luhn: it catches every single-digit mistake and
# every swap of two neighbouring digits. UIDAI uses it for Aadhaar's last digit.
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]  # multiplication table
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]  # permutation table
_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]  # inverse table


def verhoeff_valid(number: str) -> bool:
    """Return True if a digit string (including its last check digit) passes Verhoeff."""
    digits = [int(d) for d in number if d.isdigit()]
    c = 0
    for i, d in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][d]]
    return bool(digits) and c == 0


def verhoeff_check_digit(number: str) -> str:
    """Calculate the Verhoeff check digit to append to a digit string (used to make FAKE test values)."""
    digits = [int(d) for d in number if d.isdigit()]
    c = 0
    for i, d in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[(i + 1) % 8][d]]
    return str(_VERHOEFF_INV[c])


# --------------------------------------------------------------------------
# Masking helpers: keep only the last 4 characters visible
# --------------------------------------------------------------------------


def _mask_digits(digits: str, group: bool = True) -> str:
    """Replace all but the last 4 digits with X, e.g. XXXX XXXX XXXX 7352."""
    masked = "X" * (len(digits) - 4) + digits[-4:]
    if not group:
        return masked
    # Group in fours from the left, like a printed card number.
    return " ".join(masked[i:i + 4] for i in range(0, len(masked), 4))


def mask_pan(pan: str) -> str:
    """Mask a PAN so only its 4 digits remain, e.g. ABCDE1234F -> XXXXX1234X."""
    return "XXXXX" + pan[5:9] + "X"


# --------------------------------------------------------------------------
# Patterns
# --------------------------------------------------------------------------

# Card: 13-19 digits, each digit optionally followed by ONE space or dash.
# (?<!\d) and (?!\d) make sure we do not start/end in the middle of a longer number.
CARD_RE = re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")

# Expiry date written near a card: MM/YY, M/YY, MM/YYYY or M/YYYY.
EXPIRY_RE = re.compile(r"(?<!\d)(0?[1-9]|1[0-2])\s*/\s*(\d{4}|\d{2})(?!\d)")
EXPIRY_WINDOW = 40  # characters after the card number in which we look for an expiry

# Aadhaar: 12 digits, first digit 2-9 (UIDAI never issues 0 or 1 first),
# optionally written as 4-4-4 with spaces or dashes.
AADHAAR_RE = re.compile(r"(?<!\d)[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?!\d)")

# PAN: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F). Case-insensitive so
# "abcde1234f" is caught too; we normalise to upper case.
PAN_RE = re.compile(r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b")

# IFSC (bank branch code): 4 letters, the digit 0, then 6 letters/digits.
IFSC_RE = re.compile(r"\b[A-Za-z]{4}0[A-Za-z0-9]{6}\b")

# Bank account: 9 to 18 digits in a row.
BANK_RE = re.compile(r"(?<!\d)\d{9,18}(?!\d)")
# Words that tell us a long number really is a bank account.
BANK_CONTEXT_RE = re.compile(r"account|a/c|\bacc\b|\bacct\b|bank|ifsc", re.IGNORECASE)
BANK_CONTEXT_WINDOW = 40  # characters before/after the number to look for those words


def card_network(digits: str) -> str:
    """Guess the card network from its first digits (the 'prefix' or IIN)."""
    two = int(digits[:2])
    four = int(digits[:4])
    if digits[0] == "4":
        return "Visa"
    if 51 <= two <= 55 or 2221 <= four <= 2720:
        return "Mastercard"
    if two in (34, 37):
        return "Amex"
    if two in (60, 65, 81, 82):
        return "RuPay"
    return "Unknown network"


def _overlaps(start, end, taken):
    """True if the span start..end overlaps any span already claimed by another finding."""
    return any(start < t_end and end > t_start for t_start, t_end in taken)


# --------------------------------------------------------------------------
# Main scanner
# --------------------------------------------------------------------------


def scan(text: str) -> list:
    """Scan a message and return a list of findings: {type, label, masked_value, reason, ...}."""
    findings = []
    taken = []  # character spans already reported, so one number is not reported twice

    # ---- 1. Payment cards (pattern + Luhn checksum) ----
    for m in CARD_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        # The Luhn check removes most false alarms: a random 16-digit number
        # (order ID, tracking number) passes Luhn only 1 time in 10.
        if not luhn_valid(digits):
            continue
        network = card_network(digits)
        masked = _mask_digits(digits)
        redactions = [(m.start(), m.end(), masked)]
        reason = f"Matches a {len(digits)}-digit {network} card number and passes the Luhn checksum"

        # Expiry date shortly after the card = part of the same finding.
        window = text[m.end():m.end() + EXPIRY_WINDOW]
        exp = EXPIRY_RE.search(window)
        if exp:
            s, e = m.end() + exp.start(), m.end() + exp.end()
            redactions.append((s, e, "XX/XX"))
            masked += " (expiry XX/XX)"
            reason += ", with an expiry date next to it"

        findings.append({
            "type": "CARD",
            "label": f"Credit/Debit Card Number ({network})",
            "masked_value": masked,
            "reason": reason,
            "redactions": redactions,
        })
        taken.extend((s, e) for s, e, _ in redactions)

    # ---- 2. Aadhaar (pattern + Verhoeff checksum) ----
    for m in AADHAAR_RE.finditer(text):
        if _overlaps(m.start(), m.end(), taken):
            continue
        digits = re.sub(r"\D", "", m.group())
        if not verhoeff_valid(digits):
            continue
        masked = _mask_digits(digits)
        findings.append({
            "type": "AADHAAR",
            "label": "Aadhaar Number",
            "masked_value": masked,
            "reason": "12-digit number starting 2-9 that passes the Verhoeff checksum used by Aadhaar",
            "redactions": [(m.start(), m.end(), masked)],
        })
        taken.append((m.start(), m.end()))

    # ---- 3. PAN ----
    for m in PAN_RE.finditer(text):
        pan = m.group().upper()
        if pan.startswith("XXXXX") and pan.endswith("X"):
            continue  # already masked by us (XXXXX1234X); not a real PAN
        masked = mask_pan(pan)
        findings.append({
            "type": "PAN",
            "label": "PAN (Permanent Account Number)",
            "masked_value": masked,
            "reason": "Matches the PAN format: 5 letters, 4 digits, 1 letter",
            "redactions": [(m.start(), m.end(), masked)],
        })
        taken.append((m.start(), m.end()))

    # ---- 4. IFSC ----
    ifsc_matches = list(IFSC_RE.finditer(text))
    for m in ifsc_matches:
        code = m.group().upper()
        masked = "X" * 7 + code[-4:]
        findings.append({
            "type": "IFSC",
            "label": "Bank IFSC Code",
            "masked_value": masked,
            "reason": "Matches the IFSC format: 4 letters, 0, then 6 letters/digits",
            "redactions": [(m.start(), m.end(), masked)],
        })
        taken.append((m.start(), m.end()))

    # ---- 5. Bank account numbers (ONLY with context) ----
    # A 9-18 digit number on its own could be a phone number (10 digits),
    # an order ID, an invoice number or a tracking number. Flagging all of
    # them would block normal work and users would start ignoring the tool.
    # So we only treat it as a bank account when the message also mentions
    # banking words ("account", "a/c", "bank", "ifsc"...) close to the number,
    # or contains an IFSC code. This trades a little recall for far fewer
    # false positives, which is how real DLP tools use "proximity keywords".
    for m in BANK_RE.finditer(text):
        if _overlaps(m.start(), m.end(), taken):
            continue
        nearby = text[max(0, m.start() - BANK_CONTEXT_WINDOW):m.end() + BANK_CONTEXT_WINDOW]
        if not (BANK_CONTEXT_RE.search(nearby) or ifsc_matches):
            continue
        masked = _mask_digits(m.group(), group=False)
        findings.append({
            "type": "BANK_ACCOUNT",
            "label": "Bank Account Number",
            "masked_value": masked,
            "reason": "9-18 digit number appearing next to banking words or an IFSC code",
            "redactions": [(m.start(), m.end(), masked)],
        })
        taken.append((m.start(), m.end()))

    return findings


def mask_text(text: str, findings: list) -> str:
    """Return the message with every sensitive value replaced by its masked form."""
    redactions = sorted((r for f in findings for r in f["redactions"]), key=lambda r: r[0], reverse=True)
    # Replace from the end of the text backwards so earlier positions stay valid.
    for start, end, replacement in redactions:
        text = text[:start] + replacement + text[end:]
    return text


def public_findings(findings: list) -> list:
    """Strip internal position data; this is what the browser and the incident log get."""
    return [
        {"type": f["type"], "label": f["label"], "masked_value": f["masked_value"], "reason": f["reason"]}
        for f in findings
    ]


if __name__ == "__main__":
    # Quick manual check: python dlp.py
    sample = "Hi Bob, here is the client card: Visa: 4485 3647 3952 7352 Expires: 2/2009"
    found = scan(sample)
    for f in public_findings(found):
        print(f)
    print(mask_text(sample, found))
