"""
extraction/ocr/charset.py
─────────────────────────
Defines the character set used by the custom OCR model — the fixed ordered
list of classes the CNN can predict, and the mapping helpers used by both
the training script and the inference module.

Scope: uppercase A-Z, lowercase a-z, digits 0-9, and common product-label
punctuation.  No support for arbitrary Unicode, non-Latin scripts, or
handwriting beyond what EMNIST provides.

Character count: 75 classes (26 + 26 + 10 + 13 punctuation chars).
"""

# ── Character set definition ──────────────────────────────────────────────────

# Ordered list — index = class label used by the CNN
CHARSET: list[str] = (
    # Uppercase A-Z  (indices 0-25)
    list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    +
    # Lowercase a-z  (indices 26-51)
    list("abcdefghijklmnopqrstuvwxyz")
    +
    # Digits 0-9     (indices 52-61)
    list("0123456789")
    +
    # Common product-label punctuation  (indices 62-74)
    [".", ",", "%", "/", "-", "₹", "(", ")", ":", "@", "+", "#", " "]
)

NUM_CLASSES: int = len(CHARSET)  # 75

# ── Lookup helpers ────────────────────────────────────────────────────────────

_CHAR_TO_IDX: dict[str, int] = {ch: i for i, ch in enumerate(CHARSET)}


def char_to_idx(ch: str) -> int:
    """
    Return the class index for character *ch*.

    Raises ``KeyError`` if *ch* is not in the charset.
    """
    return _CHAR_TO_IDX[ch]


def idx_to_char(idx: int) -> str:
    """
    Return the character for class index *idx*.

    Raises ``IndexError`` if *idx* is out of range.
    """
    return CHARSET[idx]


def safe_idx_to_char(idx: int, fallback: str = "?") -> str:
    """
    Return the character for class index *idx*, or *fallback* if out of range.
    Used during inference to avoid crashes on unexpected model outputs.
    """
    if 0 <= idx < NUM_CLASSES:
        return CHARSET[idx]
    return fallback
