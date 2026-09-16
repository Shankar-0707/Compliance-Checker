"""
extraction/ocr/__init__.py
──────────────────────────
Custom OCR pipeline package — public interface.

This file provides the ``extract_text()`` function consumed by
``main.py`` via ``from extraction.ocr import extract_text``.

Because this directory (``extraction/ocr/``) takes precedence over
``extraction/ocr.py`` in Python's module resolution, the package
``__init__.py`` is the right place to expose the public API.

Pipeline stages (all in sub-modules):
    preprocess    → adaptive threshold + denoising refinement
    segment_lines → horizontal projection profile → line crops
    segment_chars → connected components → char crops (28×28)
    recognize     → CharCNN forward pass → character predictions
    assembly      → characters + word-boundary flags → text string
"""

import logging

import numpy as np

from extraction.ocr.preprocess import refine_binary
from extraction.ocr.segment_lines import segment_lines
from extraction.ocr.segment_chars import segment_chars
from extraction.ocr.recognize import recognize_chars

logger = logging.getLogger(__name__)


def extract_text(image_array: np.ndarray) -> str:
    """
    Run the custom OCR pipeline on a preprocessed image array.

    Parameters
    ----------
    image_array : np.ndarray
        Output of ``preprocess_image()`` — single-channel or BGR array.
        Typically already binarised (Otsu) by the upstream preprocessing step.

    Returns
    -------
    str
        All detected text lines joined by newlines.
        Returns an empty string if no text is detected or if an error occurs.

    Notes
    -----
    The function signature and return type are **identical** to the previous
    EasyOCR wrapper — nothing in ``main.py``, the rule engine, or any parsing
    module needs to change.

    Accuracy note: the custom CNN achieves ~85-92% per-character accuracy on
    clean machine-printed text and lower on photographed labels.  This is the
    expected, documented trade-off for a self-implemented system.
    See ``extraction/ocr/README.md`` for the full benchmark comparison.
    """
    if image_array is None or image_array.size == 0:
        logger.warning("extract_text: received empty image array.")
        return ""

    try:
        # ── Stage 1: Refine binarisation ─────────────────────────────────────
        binary = refine_binary(image_array)

        # ── Stage 2: Line segmentation ────────────────────────────────────────
        line_segments = segment_lines(binary)
        if not line_segments:
            logger.debug("extract_text: no text lines detected in image.")
            return ""

        # ── Stages 3-5: Per-line char segmentation + recognition + assembly ──
        text_lines: list[str] = []

        for seg in line_segments:
            # Stage 3: Character segmentation
            char_blobs = segment_chars(seg.crop)
            if not char_blobs:
                continue

            # Stage 4: Character recognition
            predicted_chars = recognize_chars(char_blobs)

            # Stage 5: Reassemble characters into words then the line string.
            # Insert a space before each word-start character (not the first).
            line_chars: list[str] = []
            for blob, ch in zip(char_blobs, predicted_chars):
                if blob.is_word_start and line_chars:
                    line_chars.append(" ")
                line_chars.append(ch)

            line_text = "".join(line_chars).strip()
            if line_text:
                text_lines.append(line_text)

        result = "\n".join(text_lines)
        logger.info(
            "extract_text: %d line(s) detected, %d character(s) total.",
            len(text_lines),
            sum(len(line) for line in text_lines),
        )
        return result

    except Exception as exc:
        logger.error("extract_text: pipeline failed: %s", exc, exc_info=True)
        return ""
