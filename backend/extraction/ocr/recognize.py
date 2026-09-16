"""
extraction/ocr/recognize.py
────────────────────────────
Character recognition inference module.

Loads the trained CharCNN once at module import time (singleton pattern,
mirroring how EasyOCR was initialised in the previous implementation).

Public API
──────────
    from extraction.ocr.recognize import recognize_chars
    predictions: list[str] = recognize_chars(char_blobs)

Where ``char_blobs`` is the list of CharBlob namedtuples returned by
``extraction.ocr.segment_chars.segment_chars()``.

Fallback behaviour
──────────────────
If the model file is not found (i.e., training has not been run yet), the
module logs a warning and ``recognize_chars`` returns ``"?"`` for every blob.
This ensures the rest of the pipeline does not crash — the API endpoint
returns an empty/garbage string rather than an HTTP 500.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import torch

from extraction.ocr.charset import NUM_CLASSES, safe_idx_to_char
from extraction.ocr.model.cnn import CharCNN
from extraction.ocr.segment_chars import CharBlob

logger = logging.getLogger(__name__)

# ── Model path ────────────────────────────────────────────────────────────────
_MODEL_PATH = Path(__file__).resolve().parent / "model" / "char_model.pt"

# ── Inference batch size (number of char crops processed at once) ──────────────
_INFERENCE_BATCH_SIZE = 128

# ── Singleton model ───────────────────────────────────────────────────────────
_model: CharCNN | None = None
_device: torch.device = torch.device("cpu")
_model_ready: bool = False


def _load_model() -> None:
    """Load the trained model weights (called once at import time)."""
    global _model, _device, _model_ready

    if not _MODEL_PATH.exists():
        logger.warning(
            "OCR model not found at %s. "
            "Run `python -m extraction.ocr.training.train_char_model` to train it. "
            "Recognition will return '?' for all characters until the model is trained.",
            _MODEL_PATH,
        )
        return

    try:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _model = CharCNN(n_classes=NUM_CLASSES)
        state = torch.load(_MODEL_PATH, map_location=_device, weights_only=True)
        _model.load_state_dict(state)
        _model.to(_device)
        _model.eval()
        _model_ready = True
        logger.info(
            "CharCNN loaded from %s (device=%s).", _MODEL_PATH, _device
        )
    except Exception as exc:
        logger.error(
            "Failed to load OCR model from %s: %s — recognition disabled.",
            _MODEL_PATH, exc,
        )
        _model = None
        _model_ready = False


# Load on import
_load_model()


# ── Public API ─────────────────────────────────────────────────────────────────

def recognize_chars(char_blobs: list[CharBlob]) -> list[str]:
    """
    Classify a list of character image crops using the trained CNN.

    Parameters
    ----------
    char_blobs : list[CharBlob]
        Output of ``segment_chars.segment_chars()`` — each blob has a
        normalised 28×28 uint8 image (text=0, bg=255).

    Returns
    -------
    list[str]
        Predicted character string for each blob, in the same order.
        Returns ``["?"] * len(char_blobs)`` if the model is not loaded.
    """
    if not char_blobs:
        return []

    if not _model_ready or _model is None:
        return ["?"] * len(char_blobs)

    # ── Build input tensor ────────────────────────────────────────────────────
    # Each blob.image is uint8 shape (28, 28), text=0 bg=255
    # CNN expects float32 in [0, 1], shape (N, 1, 28, 28)
    arrays = [blob.image.astype(np.float32) / 255.0 for blob in char_blobs]
    batch = torch.tensor(np.stack(arrays), dtype=torch.float32).unsqueeze(1)
    # Note: no inversion here — the CNN was trained with text=0 bg=255 convention
    # (same as what segment_chars produces).

    # ── Batched inference ─────────────────────────────────────────────────────
    all_preds: list[int] = []
    with torch.no_grad():
        for start in range(0, len(batch), _INFERENCE_BATCH_SIZE):
            chunk = batch[start : start + _INFERENCE_BATCH_SIZE].to(_device)
            logits = _model(chunk)
            preds = logits.argmax(dim=1).cpu().tolist()
            all_preds.extend(preds)

    return [safe_idx_to_char(idx) for idx in all_preds]
