# app/services/arabic_normalizer.py
"""
Arabic text normalization & detection helpers (no font hacks).

- has_arabic(text): quick check for Arabic script.
- normalize_text(text): remove diacritics/tatweel, normalize punctuation & digits, collapse whitespace, NFC.
"""

import re
import unicodedata

# Arabic diacritics (Harakat) U+064B..U+0652 + extras
_ARABIC_DIACRITICS = re.compile(r"[\u064B-\u0652\u0653\u0654\u0655\u0670]")
_TATWEEL = "\u0640"

# Arabic-Indic and Eastern Arabic-Indic digits → Western
_DIGITS_MAP = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789"
)

# Common Arabic punctuation to ASCII
_PUNCT_MAP = str.maketrans({
    "،": ",",
    "؛": ";",
    "۔": ".",  # Urdu/Farsi period
    "؟": "?",  # keep if you prefer Arabic '?'
    "ـ": "",   # tatweel
})

_ARABIC_BLOCK = (0x0600, 0x06FF)

def has_arabic(text: str) -> bool:
    """
    True if any char is in Arabic core/supplement/extended or presentation forms.
    Covers codepoints used by many Arabic PDFs.
    """
    ranges = (
        (0x0600, 0x06FF),  # Arabic
        (0x0750, 0x077F),  # Arabic Supplement
        (0x08A0, 0x08FF),  # Arabic Extended-A
        (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
        (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
    )
    for ch in text:
        cp = ord(ch)
        for lo, hi in ranges:
            if lo <= cp <= hi:
                return True
    return False

def strip_diacritics(text: str) -> str:
    return _ARABIC_DIACRITICS.sub("", text)

def normalize_digits(text: str) -> str:
    return text.translate(_DIGITS_MAP)

def normalize_punct(text: str) -> str:
    return text.translate(_PUNCT_MAP)

def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def normalize_text(text: str) -> str:
    if not text:
        return text
    # NFC normalize first
    text = unicodedata.normalize("NFC", text)
    # remove tatweel explicitly (also covered by punct map)
    text = text.replace(_TATWEEL, "")
    # diacritics
    text = strip_diacritics(text)
    # punctuation & digits
    text = normalize_punct(text)
    text = normalize_digits(text)
    # collapse whitespace
    text = collapse_ws(text)
    return text
