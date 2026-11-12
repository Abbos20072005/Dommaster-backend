"""Masks personal data in the customer's message before it is saved or sent to Gemini (BLD-409, rules of 11.11).

Each match is replaced with a label, nothing of the value is kept:
- [EMAIL]   an e-mail address;
- [KARTA]   a card: 16 digits (spaces / dashes between them allowed) that pass the Luhn check;
- [HUJJAT]  a JShShIR (PINFL): 14 digits in a row; a passport / ID card: 2 Latin letters + 7 digits ("AA1234567");
- [TELEFON] a phone: +998 / 998 and 9 digits, or 9 digits starting with an Uzbek operator / city code
            ("90 123 45 67", "(90) 123-45-67", "901234567");
- [KOD]     an SMS code: 4-6 digits right after (or right before) "kod / код / sms / смс / parol / пароль / code";
            not after "artikul / mahsulot / tovar / shtrix / 1C ..." ("mahsulot kodi 12345" is a product code).

Product queries are full of numbers ("600×300×200", "3х2.5", "М400", EAN-13 barcodes, prices), so a bare 9-digit
number counts as a phone only when it starts with an operator / city code, and a 16-digit one as a card only when
it passes the Luhn check.
"""
import re

SEP = r"[ \-]?"
EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])")
CARD = re.compile(r"(?<![\d+])\d(?:" + SEP + r"\d){15}(?!\d)")
PINFL = re.compile(r"(?<![\d+])\d{14}(?!\d)")
PASSPORT = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{2} ?\d{7}(?![\d])")
CODES = r"(?:20|33|50|55|61|62|65|66|67|69|7[0-9]|88|9[0-9])"
PHONE = re.compile(
    r"(?<![\d+])(?:\+?998" + SEP + r"\(?\d{2}\)?|\(?" + CODES + r"\)?)" + SEP
    + r"\d{3}" + SEP + r"\d{2}" + SEP + r"\d{2}(?!\d)"
)
CODE_WORDS = r"(?:kod\w*|код\w*|sms|смс|parol\w*|парол\w*|code)"
CODE_AFTER = re.compile(r"(?i)(\b" + CODE_WORDS + r"\W{0,3}(?:\w+\W{1,3})?)(\d{4,6})(?!\d)")
CODE_BEFORE = re.compile(r"(?i)(?<![\d+])(\d{4,6})(\W{1,3}" + CODE_WORDS + r"\b)")
# "mahsulot kodi 12345", "артикул код 1234" are product codes, not SMS codes
PRODUCT_WORDS = re.compile(r"(?i)(?:artikul|артикул|mahsulot|tovar|товар|shtrix|штрих|1c|1с)\W*\w*\W*$")

LABEL_EMAIL, LABEL_CARD, LABEL_DOCUMENT, LABEL_PHONE, LABEL_CODE = "[EMAIL]", "[KARTA]", "[HUJJAT]", "[TELEFON]", "[KOD]"


def luhn(digits):
    total = 0
    for index, digit in enumerate(int(d) for d in reversed(digits)):
        if index % 2:
            digit = digit * 2 - 9 if digit > 4 else digit * 2
        total += digit
    return total % 10 == 0


def _card(match):
    return LABEL_CARD if luhn(re.sub(r"\D", "", match.group())) else match.group()


def _sms_code(match):
    if PRODUCT_WORDS.search(match.string[max(0, match.start() - 30):match.start()]):
        return match.group()
    return match.group(1) + LABEL_CODE


def mask(text):
    """(text with the personal data replaced by labels, whether anything was masked)."""
    masked = EMAIL.sub(LABEL_EMAIL, text)
    masked = CARD.sub(_card, masked)
    masked = PINFL.sub(LABEL_DOCUMENT, masked)
    masked = PASSPORT.sub(LABEL_DOCUMENT, masked)
    masked = PHONE.sub(LABEL_PHONE, masked)
    masked = CODE_AFTER.sub(_sms_code, masked)
    masked = CODE_BEFORE.sub(lambda m: LABEL_CODE + m.group(2), masked)
    return masked, masked != text
