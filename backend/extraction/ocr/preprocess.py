"""
extraction/ocr/preprocess.py
────────────────────────────
OCR-specific preprocessing applied to the already-binarised image produced by
``extraction/preprocess.py`` before segmentation begins.

Why a second preprocessing pass?
---------------------------------
The upstream ``preprocess_image()`` in ``extraction/preprocess.py`` uses Otsu
global thresholding, which works well for clean images but can leave uneven
binarisation on photographed labels with non-uniform lighting or shadows.
This module applies adaptive thresholding (which works locally per region) and
a denoising step to produce a cleaner binary image for segmentation.

Pipeline:
    1. Normalise   — ensure uint8, single channel, values 0/255
    2. Adaptive threshold — handles local lighting variations
    3. Median blur  — removes speckle noise without blurring text edges
    4. Morphological opening — erases isolated noise pixels
    5. Invert if necessary — ensure text is DARK on LIGHT background
"""

import cv2
import numpy as np


# ── Private helpers ────────────────────────────────────────────────────────────

def _ensure_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert BGR or BGRA to grayscale; leave single-channel unchanged."""
    if img.ndim == 3:
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def _ensure_dark_on_light(binary: np.ndarray) -> np.ndarray:
    """
    Guarantee that text pixels are dark (0) and background is light (255).

    Heuristic: if more than half the pixels are dark, the image is inverted
    (white text on dark background) — flip it.
    """
    dark_ratio = np.sum(binary == 0) / binary.size
    if dark_ratio > 0.5:
        binary = cv2.bitwise_not(binary)
    return binary


# ── Public API ─────────────────────────────────────────────────────────────────

def refine_binary(img: np.ndarray) -> np.ndarray:
    """
    Refine an image for character segmentation.

    Accepts the output of ``extraction.preprocess.preprocess_image()`` —
    either a grayscale or already-binarised single-channel uint8 array.
    Returns a clean binary image (uint8, single channel, text=0, bg=255).

    Parameters
    ----------
    img : np.ndarray
        Input image array — may be grayscale or already binary.

    Returns
    -------
    np.ndarray
        Single-channel binary uint8 array, text pixels = 0, background = 255.
    """
    gray = _ensure_grayscale(img)

    # ── Step 1: Adaptive thresholding ────────────────────────────────────────
    # Block size 31 covers ~10% of a typical label line height.
    # C=10 biases toward calling ambiguous pixels background.
    binary = cv2.adaptiveThreshold(
        gray,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )

    # ── Step 2: Median blur — removes salt-and-pepper noise ─────────────────
    # ksize=3 is the smallest effective kernel; keeps character edges sharp.
    denoised = cv2.medianBlur(binary, ksize=3)

    # ── Step 3: Morphological opening — removes isolated single-pixel noise ─
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    opened = cv2.morphologyEx(denoised, cv2.MORPH_OPEN, kernel, iterations=1)

    # ── Step 4: Polarity correction ──────────────────────────────────────────
    result = _ensure_dark_on_light(opened)

    return result
