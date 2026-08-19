"""
extraction/preprocess.py
────────────────────────
OpenCV image preprocessing pipeline applied before OCR.

Steps (in order):
  1. Grayscale conversion     — reduces noise
  2. Deskew                   — corrects slight label rotation via Hough lines
  3. CLAHE contrast boost     — improves faint / low-contrast text
  4. Otsu binarisation        — B&W output optimal for PaddleOCR

Usage:
    image_array = preprocess_image(raw_image_bytes)
"""

import cv2
import numpy as np


def _to_numpy(image_bytes: bytes) -> np.ndarray:
    """Decode raw bytes into an OpenCV BGR image array."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes — unsupported format or corrupted file.")
    return img


def _to_grayscale(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _deskew(gray: np.ndarray) -> np.ndarray:
    """
    Detect dominant line angle via Hough transform and rotate to correct it.
    Only corrects angles in the range ±15°; larger rotations are left as-is
    to avoid mangling portrait vs. landscape label orientations.
    """
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

    if lines is None:
        return gray  # No lines detected — skip deskew

    angles = []
    for line in lines[:20]:  # Use up to 20 strongest lines
        rho, theta = line[0]
        angle = np.degrees(theta) - 90
        if -15 <= angle <= 15:
            angles.append(angle)

    if not angles:
        return gray

    median_angle = float(np.median(angles))
    h, w = gray.shape
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, scale=1.0)
    deskewed = cv2.warpAffine(
        gray,
        rotation_matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return deskewed


def _enhance_contrast(gray: np.ndarray) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalisation)."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _binarise(gray: np.ndarray) -> np.ndarray:
    """Otsu's global thresholding — produces a clean B&W image."""
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """
    Run the full preprocessing pipeline on raw image bytes.

    Parameters
    ----------
    image_bytes : bytes
        Raw bytes from the uploaded label image file.

    Returns
    -------
    np.ndarray
        Preprocessed single-channel (grayscale/binary) image array,
        ready to be passed to PaddleOCR.
    """
    img = _to_numpy(image_bytes)
    gray = _to_grayscale(img)
    deskewed = _deskew(gray)
    enhanced = _enhance_contrast(deskewed)
    binary = _binarise(enhanced)
    return binary
