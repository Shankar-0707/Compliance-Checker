"""
extraction/ocr/segment_chars.py
────────────────────────────────
Character (and word) segmentation within a single text line image.

Strategy
────────
Primary: connected-component labelling (cv2.connectedComponentsWithStats).
This works well for machine-printed labels where characters are visually
separated.  Returns bounding boxes for each character blob.

Word-boundary detection: after sorting character blobs left-to-right, the
x-gap between adjacent blobs is computed.  Gaps wider than
``WORD_GAP_RATIO × median_gap`` are classified as word boundaries.

Fallback / supplement: if a line yields zero or very few components (e.g.
heavily touching characters), a vertical projection profile is used to split
the line at low-density columns, and each resulting segment is treated as a
word, then re-split by connected components.

Each character crop is normalised to ``CHAR_SIZE × CHAR_SIZE`` (28 × 28 by
default) and returned alongside a flag marking the first character of each
word, so the caller can insert spaces during reassembly.

Returns
───────
list of CharBlob namedtuples:
    image        : np.ndarray  shape (CHAR_SIZE, CHAR_SIZE) uint8
    x            : int         left edge of the bounding box in the source line
    y            : int         top edge
    w            : int         width
    h            : int         height
    is_word_start: bool        True if this character starts a new word
"""

import logging
from typing import NamedTuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Tunables ──────────────────────────────────────────────────────────────────

# Output size fed to the classifier (must match training)
CHAR_SIZE: int = 28

# Ratio above which an x-gap is a word boundary (relative to the median gap)
WORD_GAP_RATIO: float = 1.8

# Minimum blob area (px²) — smaller blobs are discarded as noise
_MIN_BLOB_AREA: int = 20

# Minimum blob height (px) — strip thin horizontal noise
_MIN_BLOB_HEIGHT: int = 4

# Padding added around each character crop before resizing
_CROP_PAD: int = 2

# Vertical projection profile: fraction of line height below which column is gap
_VERT_GAP_THRESH_RATIO: float = 0.04

# Minimum column count to be considered a word segment (projection fallback)
_MIN_WORD_WIDTH: int = 5


class CharBlob(NamedTuple):
    """A single segmented character ready for classification."""
    image: np.ndarray    # shape (CHAR_SIZE, CHAR_SIZE) uint8, text=0 bg=255
    x: int               # left edge in source line image
    y: int               # top edge in source line image
    w: int               # bounding box width
    h: int               # bounding box height
    is_word_start: bool  # True if this char begins a new word


# ── Private helpers ────────────────────────────────────────────────────────────

def _normalise_char(crop: np.ndarray) -> np.ndarray:
    """
    Resize a character crop to CHAR_SIZE × CHAR_SIZE with padding to preserve
    aspect ratio, and ensure text = 0, background = 255.
    """
    h, w = crop.shape[:2]
    if h == 0 or w == 0:
        return np.full((CHAR_SIZE, CHAR_SIZE), 255, dtype=np.uint8)

    # Add padding
    padded = cv2.copyMakeBorder(
        crop, _CROP_PAD, _CROP_PAD, _CROP_PAD, _CROP_PAD,
        cv2.BORDER_CONSTANT, value=255,
    )
    ph, pw = padded.shape[:2]

    # Compute scale to fit within CHAR_SIZE × CHAR_SIZE
    scale = (CHAR_SIZE - 2) / max(ph, pw)
    new_h = max(1, int(round(ph * scale)))
    new_w = max(1, int(round(pw * scale)))

    resized = cv2.resize(padded, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Centre on a CHAR_SIZE × CHAR_SIZE white canvas
    canvas = np.full((CHAR_SIZE, CHAR_SIZE), 255, dtype=np.uint8)
    top = (CHAR_SIZE - new_h) // 2
    left = (CHAR_SIZE - new_w) // 2
    canvas[top : top + new_h, left : left + new_w] = resized

    return canvas


def _connected_component_blobs(
    line_img: np.ndarray,
) -> list[tuple[int, int, int, int]]:
    """
    Return list of (x, y, w, h) bounding boxes for character blobs in a line.
    Filters out blobs that are too small to be real characters.
    """
    # connectedComponentsWithStats needs binary: 0=bg, 255=fg
    # Our convention: text=0 bg=255, so we invert
    inverted = cv2.bitwise_not(line_img)
    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(inverted, connectivity=8)

    blobs: list[tuple[int, int, int, int]] = []
    for i in range(1, n_labels):  # skip background label 0
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area >= _MIN_BLOB_AREA and h >= _MIN_BLOB_HEIGHT:
            blobs.append((x, y, w, h))

    # Sort left-to-right
    blobs.sort(key=lambda b: b[0])
    return blobs


def _vertical_projection_word_segments(
    line_img: np.ndarray,
) -> list[tuple[int, int]]:
    """
    Vertical projection profile fallback: return list of (x_start, x_end)
    column spans corresponding to word-level segments.
    """
    h, w = line_img.shape
    # Count dark pixels per column
    dark_per_col = (line_img == 0).sum(axis=0).astype(float)
    threshold = dark_per_col.max() * _VERT_GAP_THRESH_RATIO

    segments: list[tuple[int, int]] = []
    in_seg = False
    start = 0
    for col, val in enumerate(dark_per_col):
        if val > threshold and not in_seg:
            in_seg = True
            start = col
        elif val <= threshold and in_seg:
            in_seg = False
            if col - start >= _MIN_WORD_WIDTH:
                segments.append((start, col - 1))
    if in_seg and w - start >= _MIN_WORD_WIDTH:
        segments.append((start, w - 1))
    return segments


def _word_boundary_mask(
    blobs: list[tuple[int, int, int, int]],
) -> list[bool]:
    """
    Return a list of bool flags (one per blob) indicating whether each blob
    is the first character of a new word.  The first blob is always True.
    """
    if not blobs:
        return []

    # Compute x-gaps between consecutive blobs
    gaps = []
    for i in range(1, len(blobs)):
        prev_right = blobs[i - 1][0] + blobs[i - 1][2]
        curr_left = blobs[i][0]
        gaps.append(max(0, curr_left - prev_right))

    if not gaps:
        return [True]

    median_gap = float(np.median(gaps)) if gaps else 0.0
    word_gap_threshold = max(1.0, median_gap * WORD_GAP_RATIO)

    flags = [True]  # first character always starts a word
    for gap in gaps:
        flags.append(gap >= word_gap_threshold)

    return flags


# ── Public API ─────────────────────────────────────────────────────────────────

def segment_chars(line_img: np.ndarray) -> list[CharBlob]:
    """
    Segment a single text line image into individual character blobs.

    Parameters
    ----------
    line_img : np.ndarray
        Single-channel uint8 binary image of one text line (text=0, bg=255).
        Typically a crop from ``segment_lines.segment_lines()``.

    Returns
    -------
    list[CharBlob]
        Left-to-right ordered list of character blobs.  Each blob has a
        28×28 normalised image and a word-start flag.
        Returns empty list if no characters are detected.
    """
    if line_img.ndim != 2:
        raise ValueError(
            f"segment_chars expects a 2D single-channel image; got {line_img.shape}"
        )

    # ── Primary: connected-component approach ─────────────────────────────────
    blobs = _connected_component_blobs(line_img)

    # ── Fallback: vertical projection profile ─────────────────────────────────
    if len(blobs) < 2:
        word_segs = _vertical_projection_word_segments(line_img)
        if word_segs:
            logger.debug(
                "segment_chars: CC found < 2 blobs; using vertical projection fallback "
                "(%d word segments).", len(word_segs)
            )
            blobs = []
            for x0, x1 in word_segs:
                word_crop = line_img[:, x0 : x1 + 1]
                sub_blobs = _connected_component_blobs(word_crop)
                # Offset x coordinates back to line space
                blobs.extend((b[0] + x0, b[1], b[2], b[3]) for b in sub_blobs)
            blobs.sort(key=lambda b: b[0])

    if not blobs:
        logger.debug("segment_chars: no character blobs found in line.")
        return []

    # ── Determine word boundaries ─────────────────────────────────────────────
    word_flags = _word_boundary_mask(blobs)

    # ── Build CharBlob list ───────────────────────────────────────────────────
    h_img = line_img.shape[0]
    char_blobs: list[CharBlob] = []
    for (x, y, w, h), is_word_start in zip(blobs, word_flags):
        # Clamp bounding box to image dimensions
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(line_img.shape[1], x + w)
        y1 = min(h_img, y + h)
        if x1 <= x0 or y1 <= y0:
            continue
        crop = line_img[y0:y1, x0:x1]
        normalised = _normalise_char(crop)
        char_blobs.append(CharBlob(
            image=normalised,
            x=x0, y=y0,
            w=x1 - x0, h=y1 - y0,
            is_word_start=bool(is_word_start),
        ))

    logger.debug("segment_chars: %d character blob(s) extracted.", len(char_blobs))
    return char_blobs
