"""
extraction/ocr/training/prepare_char_data.py
─────────────────────────────────────────────
Builds the combined character image dataset used to train the OCR classifier.

Two data sources are merged:

1. EMNIST ("byclass" split)
   ─────────────────────────
   Downloaded via ``torchvision.datasets.EMNIST``.  Covers handwritten uppercase
   A-Z, lowercase a-z, and digits 0-9 (~800k samples total across classes).
   EMNIST images are already 28×28 grayscale; the "byclass" split uses integer
   labels 0-61 (0-9 digits, 10-35 uppercase, 36-61 lowercase).  We remap these
   to our charset indices.

2. Synthetic printed-font data
   ────────────────────────────
   Rendered using PIL.ImageDraw + PIL.ImageFont at multiple font sizes with
   light augmentation (rotation, Gaussian noise, blur).  Covers:
     • The full charset (including punctuation not present in EMNIST)
     • Machine-printed appearance (vs. EMNIST's handwriting)
   This source is critical for real-world label accuracy.

Combined dataset → 80/20 stratified train/test split.

Usage (standalone)
──────────────────
    python -m extraction.ocr.training.prepare_char_data
This prints dataset statistics but does not save anything — the dataset is
consumed in-process by ``train_char_model.py``.

Public API
──────────
    from extraction.ocr.training.prepare_char_data import build_datasets
    train_ds, test_ds, class_counts = build_datasets(data_root="./data")
"""

from __future__ import annotations

import io
import logging
import math
import random
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from torch.utils.data import ConcatDataset, Dataset, Subset

logger = logging.getLogger(__name__)

# ── Import charset ────────────────────────────────────────────────────────────
# Allow running as a script from the backend/ directory
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from extraction.ocr.charset import CHARSET, NUM_CLASSES, char_to_idx  # noqa: E402

# ── EMNIST label → our charset index mapping ──────────────────────────────────
# EMNIST "byclass": labels 0-9 → digits '0'-'9'; 10-35 → 'A'-'Z'; 36-61 → 'a'-'z'
_EMNIST_LABEL_TO_CHAR: dict[int, str] = {}
for _i in range(10):
    _EMNIST_LABEL_TO_CHAR[_i] = str(_i)
for _i in range(26):
    _EMNIST_LABEL_TO_CHAR[10 + _i] = chr(ord("A") + _i)
    _EMNIST_LABEL_TO_CHAR[36 + _i] = chr(ord("a") + _i)

# Only keep EMNIST classes that exist in our charset
_EMNIST_VALID_LABELS: set[int] = {
    lbl for lbl, ch in _EMNIST_LABEL_TO_CHAR.items() if ch in CHARSET
}

# ── Synthetic data config ─────────────────────────────────────────────────────
_FONT_SIZES: list[int] = [18, 22, 26]
_AUGMENTATIONS_PER_SAMPLE: int = 4   # number of augmented variants per (char, font, size)

# Characters to render synthetically — the full charset
_SYNTH_CHARS: list[str] = CHARSET

# Font paths to try (in order of preference)
_FONT_CANDIDATES: list[str] = [
    # DejaVu (usually available on Linux; may be in Windows font dirs too)
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    # Liberation (Red Hat / Google fonts bundle)
    "LiberationSans-Regular.ttf",
    "LiberationMono-Regular.ttf",
    # Windows
    "arial.ttf",
    "Arial.ttf",
    "cour.ttf",    # Courier New
    "times.ttf",
    "verdana.ttf",
]


def _try_load_fonts() -> list[ImageFont.FreeTypeFont]:
    """Load all available fonts from _FONT_CANDIDATES, skip missing ones."""
    loaded: list[ImageFont.FreeTypeFont] = []
    for size in _FONT_SIZES:
        found_any = False
        for name in _FONT_CANDIDATES:
            try:
                font = ImageFont.truetype(name, size=size)
                loaded.append(font)
                found_any = True
            except (OSError, IOError):
                pass

        if not found_any:
            # Fallback: PIL's built-in bitmap font (no path needed)
            try:
                loaded.append(ImageFont.load_default())
            except Exception:
                pass

    if not loaded:
        logger.warning(
            "prepare_char_data: no TrueType fonts found — synthetic data will use "
            "PIL default font only, which may degrade model quality."
        )
        loaded.append(ImageFont.load_default())

    unique = list({id(f): f for f in loaded}.values())
    logger.info("prepare_char_data: loaded %d font variants.", len(unique))
    return unique


def _render_char(ch: str, font: ImageFont.FreeTypeFont) -> np.ndarray:
    """
    Render a single character *ch* using *font* onto a 28×28 grayscale canvas.
    Returns uint8 array with text=0, background=255.
    """
    canvas_size = 64  # render large, then downscale for quality
    img = Image.new("L", (canvas_size, canvas_size), color=255)
    draw = ImageDraw.Draw(img)

    # Measure character size and centre it
    try:
        bbox = font.getbbox(ch)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except AttributeError:
        # Older PIL versions
        tw, th = draw.textsize(ch, font=font)
        bbox = (0, 0, tw, th)

    x = (canvas_size - tw) // 2 - bbox[0]
    y = (canvas_size - th) // 2 - bbox[1]
    draw.text((x, y), ch, fill=0, font=font)

    # Downscale to 28×28
    img = img.resize((28, 28), Image.LANCZOS)
    return np.array(img, dtype=np.uint8)


def _augment(arr: np.ndarray) -> np.ndarray:
    """
    Apply random light augmentation to a 28×28 uint8 char image.
    Augmentations: rotation ±8°, Gaussian noise, blur.
    """
    img = Image.fromarray(arr)

    # Random rotation ±8°
    angle = random.uniform(-8.0, 8.0)
    img = img.rotate(angle, fillcolor=255, resample=Image.BICUBIC)

    # Random Gaussian blur (radius 0 – 0.6)
    if random.random() < 0.5:
        radius = random.uniform(0.0, 0.6)
        img = img.filter(ImageFilter.GaussianBlur(radius=radius))

    out = np.array(img, dtype=np.float32)

    # Gaussian noise (σ ≤ 12 on 0-255 scale)
    if random.random() < 0.6:
        noise = np.random.normal(0, random.uniform(2, 12), out.shape)
        out = out + noise

    out = np.clip(out, 0, 255).astype(np.uint8)
    return out


# ── Dataset classes ────────────────────────────────────────────────────────────

class SyntheticCharDataset(Dataset):
    """
    Generates synthetic printed-font character images on-the-fly.

    Renders each character in CHARSET across all loaded fonts with
    _AUGMENTATIONS_PER_SAMPLE augmented variants each.
    """

    def __init__(self, transform=None) -> None:
        self.transform = transform
        self.fonts = _try_load_fonts()
        self.samples: list[tuple[str, ImageFont.FreeTypeFont]] = [
            (ch, font)
            for ch in _SYNTH_CHARS
            for font in self.fonts
            if ch.strip()  # skip pure whitespace (space char renders blank)
        ]
        logger.info(
            "SyntheticCharDataset: %d base samples × %d augmentations = %d total",
            len(self.samples),
            _AUGMENTATIONS_PER_SAMPLE,
            len(self.samples) * _AUGMENTATIONS_PER_SAMPLE,
        )

    def __len__(self) -> int:
        return len(self.samples) * _AUGMENTATIONS_PER_SAMPLE

    def __getitem__(self, idx: int):
        sample_idx = idx // _AUGMENTATIONS_PER_SAMPLE
        ch, font = self.samples[sample_idx]

        arr = _render_char(ch, font)
        arr = _augment(arr)

        # Normalise to [0, 1] float tensor, shape (1, 28, 28)
        tensor = torch.tensor(arr, dtype=torch.float32).unsqueeze(0) / 255.0

        label = char_to_idx(ch)
        return tensor, label


class EMNISTCharDataset(Dataset):
    """
    Wraps torchvision.datasets.EMNIST, remapping labels to our charset indices
    and filtering out classes not in our charset.
    """

    def __init__(self, root: str, train: bool = True, transform=None) -> None:
        try:
            import torchvision.datasets as tvd
            import torchvision.transforms as tvt
        except ImportError as exc:
            raise ImportError(
                "torchvision is required for EMNIST data. "
                "Install it with: pip install torchvision"
            ) from exc

        _transform = tvt.Compose([
            tvt.ToTensor(),          # PIL→Tensor, scales to [0,1]
        ])

        logger.info(
            "EMNISTCharDataset: downloading/loading EMNIST byclass (%s split) …",
            "train" if train else "test",
        )
        raw = tvd.EMNIST(
            root=root,
            split="byclass",
            train=train,
            download=True,
            transform=_transform,
        )

        # Filter to valid labels only and remap
        self._data: list[tuple[torch.Tensor, int]] = []
        for img, emnist_label in raw:
            emnist_label = int(emnist_label)
            if emnist_label not in _EMNIST_VALID_LABELS:
                continue
            ch = _EMNIST_LABEL_TO_CHAR[emnist_label]
            our_label = char_to_idx(ch)
            self._data.append((img, our_label))

        logger.info(
            "EMNISTCharDataset: retained %d/%d samples after charset filtering.",
            len(self._data), len(raw),
        )

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, idx: int):
        img, label = self._data[idx]
        # EMNIST images need to be transposed (they are stored rotated)
        img = torch.rot90(img, k=3, dims=[1, 2])   # undo EMNIST 90° rotation
        img = torch.flip(img, dims=[2])             # mirror left-right
        return img, label


# ── Public API ─────────────────────────────────────────────────────────────────

def build_datasets(
    data_root: str = "./data",
    emnist_fraction: float = 1.0,
    test_split: float = 0.2,
    seed: int = 42,
) -> tuple[Dataset, Dataset, dict[int, int]]:
    """
    Build combined train and test datasets.

    Parameters
    ----------
    data_root : str
        Directory where EMNIST data is downloaded/cached.
    emnist_fraction : float
        Fraction of EMNIST samples to include (0–1).  Set < 1 to speed up
        experimentation; set to 1.0 for the full training run.
    test_split : float
        Fraction of the combined dataset to hold out for testing.
    seed : int
        Random seed for reproducible splits.

    Returns
    -------
    train_ds : Dataset
    test_ds  : Dataset
    class_counts : dict[int, int]
        Number of training samples per class index.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    # ── Load sources ──────────────────────────────────────────────────────────
    synth_ds = SyntheticCharDataset()

    try:
        emnist_train = EMNISTCharDataset(root=data_root, train=True)
        emnist_test = EMNISTCharDataset(root=data_root, train=False)
        emnist_full = ConcatDataset([emnist_train, emnist_test])

        if emnist_fraction < 1.0:
            n_keep = int(len(emnist_full) * emnist_fraction)
            indices = random.sample(range(len(emnist_full)), n_keep)
            emnist_full = Subset(emnist_full, indices)

        combined = ConcatDataset([synth_ds, emnist_full])
        logger.info(
            "Combined dataset: %d synthetic + %d EMNIST = %d total",
            len(synth_ds), len(emnist_full), len(combined),
        )
    except Exception as exc:
        logger.warning(
            "EMNIST loading failed (%s) — training on synthetic data only.", exc
        )
        combined = synth_ds

    # ── Stratified train/test split ───────────────────────────────────────────
    total = len(combined)
    indices_by_class: dict[int, list[int]] = {i: [] for i in range(NUM_CLASSES)}

    # Collect all labels (this iterates the dataset once — acceptable for offline use)
    logger.info("Collecting labels for stratified split …")
    for idx in range(total):
        try:
            _, label = combined[idx]
        except Exception:
            continue
        indices_by_class[int(label)].append(idx)

    train_indices: list[int] = []
    test_indices: list[int] = []
    class_counts: dict[int, int] = {}

    for cls_idx, idxs in indices_by_class.items():
        if not idxs:
            class_counts[cls_idx] = 0
            continue
        random.shuffle(idxs)
        n_test = max(1, int(len(idxs) * test_split))
        test_indices.extend(idxs[:n_test])
        train_indices.extend(idxs[n_test:])
        class_counts[cls_idx] = len(idxs) - n_test

    train_ds = Subset(combined, train_indices)
    test_ds = Subset(combined, test_indices)

    logger.info(
        "Split: %d train, %d test (%.0f%% / %.0f%%)",
        len(train_ds), len(test_ds),
        100 * len(train_ds) / total,
        100 * len(test_ds) / total,
    )
    return train_ds, test_ds, class_counts


# ── Standalone entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    train_ds, test_ds, counts = build_datasets()
    print(f"\nTrain samples: {len(train_ds)}")
    print(f"Test  samples: {len(test_ds)}")
    print(f"\nSamples per class (top 10):")
    for idx, count in sorted(counts.items(), key=lambda x: -x[1])[:10]:
        from extraction.ocr.charset import idx_to_char
        print(f"  [{idx:2d}] '{idx_to_char(idx)}': {count}")
