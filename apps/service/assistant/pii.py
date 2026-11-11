"""Masks phone and card numbers in the customer's message before it is saved or sent to Gemini.

Product queries are full of numbers ("600×300×200", "3х2.5", "М400", barcodes of 13 digits), so only these
are masked:
- a card: 16-19 digits, spaces / dashes between them allowed -> "8600 **** **** 1234";
- a phone: +998 / 998 and 9 digits, or 9 digits starting with an Uzbek operator / city code grouped like a phone
  ("90 123 45 67", "(90) 123-45-67", "901234567") -> "+998 90 *** ** 67".
"""
import re

SEP = r"[ \-]?"
CARD = re.compile(r"(?<![\d+])\d(?:" + SEP + r"\d){15,18}(?!\d)")
CODES = r"(?:20|33|50|55|61|62|65|66|67|69|7[0-9]|77|88|9[0-9])"
PHONE = re.compile(
    r"(?<![\d+])(?:\+?998" + SEP + r")?\(?" + CODES + r"\)?" + SEP
    + r"\d{3}" + SEP + r"\d{2}" + SEP + r"\d{2}(?!\d)"
)


def _card(match):
    digits = re.sub(r"\D", "", match.group())
    return f"{digits[:4]} **** **** {digits[-4:]}"


def _phone(match):
    digits = re.sub(r"\D", "", match.group())[-9:]
    return f"+998 {digits[:2]} *** ** {digits[-2:]}"


def mask(text):
    """(text with the numbers masked, whether anything was masked)."""
    masked = CARD.sub(_card, text)
    masked = PHONE.sub(_phone, masked)
    return masked, masked != text
