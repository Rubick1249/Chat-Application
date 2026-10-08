"""
Tests for the Layer 1 DLP engine (dlp.py).  Run with:  python -m pytest -v

All values here are FAKE test values. Card numbers are well-known test
numbers; the Aadhaar number is generated below with the Verhoeff algorithm
from made-up digits; it does not belong to any real person.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dlp import luhn_valid, mask_text, scan, verhoeff_check_digit, verhoeff_valid  # noqa: E402


def types_found(text):
    """Helper: the list of finding types for a message."""
    return [f["type"] for f in scan(text)]


# A FAKE Aadhaar: 11 made-up digits + the correct Verhoeff check digit.
FAKE_AADHAAR_BASE = "23456789012"
FAKE_AADHAAR = FAKE_AADHAAR_BASE + verhoeff_check_digit(FAKE_AADHAAR_BASE)


# ---------------- Luhn / cards ----------------

def test_luhn_valid_numbers():
    assert luhn_valid("4485364739527352")      # Visa sample from the brief
    assert luhn_valid("4111111111111111")      # standard Visa test card
    assert luhn_valid("5555555555554444")      # standard Mastercard test card


def test_luhn_invalid_number():
    assert not luhn_valid("4485364739527353")  # last digit changed


def test_visa_sample_detected_with_expiry():
    text = "Visa: 4485 3647 3952 7352 Expires: 2/2009"
    found = scan(text)
    assert len(found) == 1
    card = found[0]
    assert card["type"] == "CARD"
    assert "Visa" in card["label"]
    assert card["masked_value"].startswith("XXXX XXXX XXXX 7352")
    assert "expiry" in card["reason"]
    masked = mask_text(text, found)
    assert "4485" not in masked and "2/2009" not in masked
    assert "7352" in masked


def test_card_with_dashes_and_networks():
    assert "Mastercard" in scan("card 5555-5555-5555-4444")[0]["label"]
    assert "Amex" in scan("amex 378282246310005")[0]["label"]


def test_card_failing_luhn_not_flagged():
    assert "CARD" not in types_found("Order ref 4485 3647 3952 7353")


# ---------------- Aadhaar / Verhoeff ----------------

def test_verhoeff_published_examples():
    # Worked examples from the Verhoeff algorithm's standard description.
    assert verhoeff_check_digit("236") == "3"
    assert verhoeff_check_digit("12345") == "1"
    assert verhoeff_valid("2363") and not verhoeff_valid("2364")


def test_generated_fake_aadhaar_is_valid():
    assert verhoeff_valid(FAKE_AADHAAR)


def test_aadhaar_detected_plain_and_spaced():
    spaced = f"{FAKE_AADHAAR[:4]} {FAKE_AADHAAR[4:8]} {FAKE_AADHAAR[8:]}"
    assert types_found(f"My Aadhaar is {FAKE_AADHAAR}") == ["AADHAAR"]
    found = scan(f"Aadhaar: {spaced}")
    assert found[0]["type"] == "AADHAAR"
    assert found[0]["masked_value"] == "XXXX XXXX " + FAKE_AADHAAR[-4:]


def test_aadhaar_wrong_check_digit_not_flagged():
    wrong = FAKE_AADHAAR[:-1] + str((int(FAKE_AADHAAR[-1]) + 1) % 10)
    assert "AADHAAR" not in types_found(f"id {wrong}")


def test_aadhaar_cannot_start_with_0_or_1():
    base = "13456789012"
    assert "AADHAAR" not in types_found(base + verhoeff_check_digit(base))


# ---------------- PAN / IFSC ----------------

def test_pan_detected_and_masked():
    found = scan("PAN is abcde1234f")
    assert found[0]["type"] == "PAN"
    assert found[0]["masked_value"] == "XXXXX1234X"


def test_masked_message_is_clean():
    # "Send masked version" must not be blocked a second time.
    text = f"PAN ABCDE1234F, card 4485 3647 3952 7352, Aadhaar {FAKE_AADHAAR}, IFSC ABCD0123456"
    assert scan(mask_text(text, scan(text))) == []


def test_ifsc_detected():
    assert "IFSC" in types_found("IFSC ABCD0123456")


def test_ordinary_words_not_pan_or_ifsc():
    assert types_found("Please review the quarterly roadmap document") == []


# ---------------- Bank account (context rule) ----------------

def test_bank_account_with_keyword():
    found = scan("Transfer to account no 123456789012 today")
    assert [f["type"] for f in found] == ["BANK_ACCOUNT"]
    assert found[0]["masked_value"] == "XXXXXXXX9012"


def test_bank_account_with_ifsc_in_message():
    assert sorted(types_found("Pay 123456789012 at ABCD0123456")) == ["BANK_ACCOUNT", "IFSC"]


def test_long_number_without_context_not_flagged():
    assert types_found("Your order 123456789012 has shipped") == []


def test_phone_number_not_flagged():
    assert types_found("Call me on 9876543210 after lunch") == []
    assert types_found("My number is +91 98765 43210") == []


def test_clean_message():
    assert scan("Hi Bob, can we meet at 3 pm about the Q3 report?") == []
