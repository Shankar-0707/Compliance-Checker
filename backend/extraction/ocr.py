"""
extraction/ocr.py
─────────────────
EasyOCR wrapper (Python 3.13-compatible).

The OCR reader is initialised once at module import time (singleton pattern)
to avoid re-loading the model on every request.

Usage:
    raw_text = extract_text(preprocessed_image_array)
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

# ── Singleton initialisation ─────────────────────────────────────────────────
_reader = None
_easyocr_available = False

try:
    import easyocr

    # gpu=False is safe on CPU-only machines; EasyOCR will use GPU automatically
    # if CUDA is available and gpu=True.
    _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    _easyocr_available = True
    logger.info("EasyOCR initialised successfully.")
except ImportError:
    logger.warning(
        "EasyOCR not installed — OCR will return empty string. "
        "Run `pip install easyocr` to enable."
    )
except Exception as exc:
    logger.warning("EasyOCR failed to initialise: %s — OCR disabled.", exc)


def extract_text(image_array: np.ndarray) -> str:
    """
    Run EasyOCR on a preprocessed image array.

    Parameters
    ----------
    image_array : np.ndarray
        Output of ``preprocess_image()`` — single-channel or BGR array.

    Returns
    -------
    str
        All detected text lines joined by newlines, filtered by confidence >= 0.5.
        Returns an empty string if OCR fails or EasyOCR is not installed.
    """
    if not _easyocr_available or _reader is None:
        logger.error("EasyOCR is unavailable — returning empty text.")
        return ""

    try:
        # EasyOCR returns: list of (bbox, text, confidence)
        results = _reader.readtext(image_array)
    except Exception as exc:
        logger.error("EasyOCR.readtext() raised an exception: %s", exc)
        return ""

    if not results:
        return ""

    lines: list[str] = []
    for _bbox, text, score in results:
        if score >= 0.5 and text.strip():
            lines.append(text.strip())

    return "\n".join(lines)
