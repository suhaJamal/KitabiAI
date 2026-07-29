# app/core/slugify.py
import re
import unicodedata

_AR = {
    'ا': 'a', 'أ': 'a', 'إ': 'i', 'آ': 'a', 'ب': 'b', 'ت': 't', 'ث': 'th',
    'ج': 'j', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'th', 'ر': 'r', 'ز': 'z',
    'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'd', 'ط': 't', 'ظ': 'z', 'ع': 'a',
    'غ': 'gh', 'ف': 'f', 'ق': 'q', 'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n',
    'ه': 'h', 'و': 'w', 'ي': 'y', 'ى': 'a', 'ة': 'a', 'ئ': 'y', 'ؤ': 'w',
    'ء': '',
}


def slugify(title: str, max_len: int = 60) -> str:
    """Convert a book title (Arabic or English) to a URL-safe ASCII slug."""
    result = ''.join(_AR.get(ch, ch) for ch in title)
    result = unicodedata.normalize('NFKD', result).encode('ascii', 'ignore').decode('ascii')
    result = result.lower()
    result = re.sub(r'[^a-z0-9]+', '-', result)
    result = result.strip('-')
    return result[:max_len].rstrip('-')


def book_path(book_id: int, title: str) -> str:
    """Return the URL path segment for a book: '{id}-{slug}' or '{id}'."""
    slug = slugify(title)
    return f"{book_id}-{slug}" if slug else str(book_id)
