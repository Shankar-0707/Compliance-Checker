"""
extraction/ocr/segment_lines.py
────────────────────────────────
Line segmentation via horizontal projection profile.

Algorithm
─────────
1. Compute a horizontal projection profile: for every row, count the number
   of dark (text) pixels.
2. Smooth the profile with a 1D Gaussian kernel to reduce noise from
   individual descenders / ascenders that create false troughs.
3. Apply a density threshold to classify rows as "text" or "gap".
4. Find contiguous text-row runs → each run is one line.
5. Add vertical padding (``V_PAD`` pixels) to avoid clipping ascenders/descenders.
6. Merge lines that are suspiciously close together (inter-line gap < ``MIN_GAP``).

Returns
───────
list of LineSegment namedtuples: (crop, y_start, y_end)
  - crop    : np.ndarray — the line image sub-array (may be returned by view)
  - y_start : int — inclusive top row index in the source image
  - y_end   : int — inclusive bottom row index in the source image
"""

import logging
from typing import NamedTuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Tunables ──────────────────────────────────────────────────────────────────

# Gaussian smoothing kernel half-width for the projection profile (rows)
_SMOOTH_SIGMA: float = 2.0

# Fraction of the max projection value below which a row is considered a gap
_GAP_THRESHOLD_RATIO: float = 0.05

# Vertical padding added around each detected line (pixels)
_V_PAD: int = 3

# Minimum line height — strips narrower than this are discarded as noise
_MIN_LINE_HEIGHT: int = 6

# Minimum gap between two lines; lines closer than this get merged
_MIN_GAP: int = 2


class LineSegment(NamedTuple):
    """A single detected text line with its position in the source image."""
    crop: np.ndarray
    y_start: int
    y_end: int


# ── Private helpers ────────────────────────────────────────────────────────────

def _gaussian_smooth_1d(signal: np.ndarray, sigma: float) -> np.ndarray:
    """Apply 1D Gaussian smoothing to a 1D array using a symmetric kernel."""
    if sigma <= 0:
        return signal.astype(float)
    radius = int(3 * sigma)
    size = 2 * radius + 1
    kernel = np.exp(-0.5 * ((np.arange(size) - radius) / sigma) ** 2)
    kernel /= kernel.sum()
    return np.convolve(signal.astype(float), kernel, mode="same")


def _horizontal_projection(binary: np.ndarray) -> np.ndarray:
    """
    Count dark pixels per row.

    ``binary`` must be a single-channel uint8 image where text = 0, bg = 255.
    Returns a 1D array of length ``binary.shape[0]``.
    """
    # Dark pixels are 0; invert so text pixels count as 1
    inverted = (binary == 0).astype(np.uint32)
    return inverted.sum(axis=1)


def _find_text_runs(
    profile: np.ndarray,
    threshold: float,
) -> list[tuple[int, int]]:
    """
    Return list of (start_row, end_row) spans where profile > threshold.
    Both indices are inclusive.
    """
    runs: list[tuple[int, int]] = []
    in_run = False
    start = 0

    for i, val in enumerate(profile):
        if val > threshold and not in_run:
            in_run = True
            start = i
        elif val <= threshold and in_run:
            in_run = False
            runs.append((start, i - 1))

    if in_run:
        runs.append((start, len(profile) - 1))

    return runs


def _merge_close_runs(
    runs: list[tuple[int, int]],
    min_gap: int,
) -> list[tuple[int, int]]:
    """Merge consecutive runs whose gap is smaller than *min_gap*."""
    if not runs:
        return runs
    merged = [runs[0]]
    for start, end in runs[1:]:
        prev_end = merged[-1][1]
        if start - prev_end <= min_gap:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


# ── Public API ─────────────────────────────────────────────────────────────────

def segment_lines(binary: np.ndarray) -> list[LineSegment]:
    """
    Segment a binary label image into individual text lines.

    Parameters
    ----------
    binary : np.ndarray
        Single-channel uint8 image (text = 0, background = 255),
        typically from ``ocr.preprocess.refine_binary()``.

    Returns
    -------
    list[LineSegment]
        Ordered top-to-bottom list of detected text line segments.
        Empty list if no lines are found.
    """
    if binary.ndim != 2:
        raise ValueError(
            f"segment_lines expects a single-channel 2D image; got shape {binary.shape}"
        )

    h, w = binary.shape

    # ── Projection profile ────────────────────────────────────────────────────
    profile = _horizontal_projection(binary)
    smoothed = _gaussian_smooth_1d(profile, _SMOOTH_SIGMA)

    max_val = smoothed.max()
    if max_val == 0:
        logger.debug("segment_lines: image appears to be blank — no text found.")
        return []

    threshold = max_val * _GAP_THRESHOLD_RATIO

    # ── Find and merge runs ───────────────────────────────────────────────────
    runs = _find_text_runs(smoothed, threshold)
    runs = _merge_close_runs(runs, _MIN_GAP)

    # ── Build LineSegment list ────────────────────────────────────────────────
    segments: list[LineSegment] = []
    for y_start, y_end in runs:
        # Apply padding (clamp to image bounds)
        y0 = max(0, y_start - _V_PAD)
        y1 = min(h - 1, y_end + _V_PAD)

        height = y1 - y0 + 1
        if height < _MIN_LINE_HEIGHT:
            continue  # too thin — noise

        crop = binary[y0 : y1 + 1, :]
        segments.append(LineSegment(crop=crop, y_start=y0, y_end=y1))

    logger.debug("segment_lines: found %d line(s) in %dx%d image.", len(segments), w, h)
    return segments
