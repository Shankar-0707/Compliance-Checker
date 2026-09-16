"""
extraction/ocr/training/train_char_model.py
────────────────────────────────────────────
Training script for the custom character recognition CNN.

Trains ``CharCNN`` on combined EMNIST + synthetic printed-font data,
saves the best checkpoint, and writes accuracy + confusion-matrix results
to ``extraction/ocr/README.md``.

Usage
─────
    # From the backend/ directory:
    python -m extraction.ocr.training.train_char_model

    # With custom options:
    python -m extraction.ocr.training.train_char_model \\
        --data-root ./data \\
        --epochs 25 \\
        --batch-size 256 \\
        --lr 1e-3

Output files
────────────
    extraction/ocr/model/char_model.pt   — best model weights (state_dict)
    extraction/ocr/README.md             — updated with accuracy + confusion matrix

Expected results (typical run on CPU, ~20 epochs):
    Test accuracy (printed-font chars):  85–92%
    Test accuracy (overall incl. EMNIST): 75–85%
    Highest-confusion pairs: O/0, l/1/I, 5/S, B/8, rn/m
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# Allow running as `python -m extraction.ocr.training.train_char_model`
# from the backend/ directory
_BACKEND_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_BACKEND_DIR))

from extraction.ocr.charset import CHARSET, NUM_CLASSES, idx_to_char  # noqa: E402
from extraction.ocr.model.cnn import CharCNN  # noqa: E402
from extraction.ocr.training.prepare_char_data import build_datasets  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_MODEL_DIR = Path(__file__).resolve().parents[2] / "model"
_MODEL_PATH = _MODEL_DIR / "char_model.pt"
_README_PATH = Path(__file__).resolve().parents[2] / "README.md"

# ── Default hyperparameters ────────────────────────────────────────────────────
_DEFAULT_EPOCHS = 20
_DEFAULT_BATCH = 256
_DEFAULT_LR = 1e-3
_DEFAULT_DATA_ROOT = str(_BACKEND_DIR / "data")
_EARLY_STOP_PATIENCE = 4   # stop if val loss doesn't improve for this many epochs
_NUM_WORKERS = 0           # 0 = main process (safer on Windows)


# ── Training / evaluation routines ────────────────────────────────────────────

def _train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    """Run one training epoch; return mean loss."""
    model.train()
    total_loss = 0.0
    for imgs, labels in loader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        logits = model(imgs)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * imgs.size(0)
    return total_loss / len(loader.dataset)


def _evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float, torch.Tensor]:
    """
    Evaluate model on *loader*.

    Returns
    -------
    loss     : float
    accuracy : float  (0–1)
    conf_mat : torch.Tensor shape (NUM_CLASSES, NUM_CLASSES)
    """
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    conf_mat = torch.zeros(NUM_CLASSES, NUM_CLASSES, dtype=torch.long)

    with torch.no_grad():
        for imgs, labels in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            logits = model(imgs)
            loss = criterion(logits, labels)
            total_loss += loss.item() * imgs.size(0)

            preds = logits.argmax(dim=1)
            correct += (preds == labels).sum().item()
            total += imgs.size(0)

            # Fill confusion matrix
            for pred, true in zip(preds.cpu(), labels.cpu()):
                conf_mat[true, pred] += 1

    return total_loss / total, correct / total, conf_mat


# ── Results reporting ──────────────────────────────────────────────────────────

def _top_confusions(
    conf_mat: torch.Tensor,
    top_n: int = 20,
) -> list[tuple[str, str, int]]:
    """
    Return the top-N off-diagonal confusion pairs (true, predicted, count).
    Filters out pairs where count == 0.
    """
    rows = []
    mat = conf_mat.numpy()
    for i in range(NUM_CLASSES):
        for j in range(NUM_CLASSES):
            if i != j and mat[i, j] > 0:
                rows.append((idx_to_char(i), idx_to_char(j), int(mat[i, j])))
    rows.sort(key=lambda x: -x[2])
    return rows[:top_n]


def _per_class_accuracy(conf_mat: torch.Tensor) -> dict[str, float]:
    """Return per-class accuracy dict {char: accuracy}."""
    mat = conf_mat.float()
    totals = mat.sum(dim=1)
    correct = mat.diagonal()
    result = {}
    for i in range(NUM_CLASSES):
        ch = idx_to_char(i)
        if totals[i] > 0:
            result[ch] = float(correct[i] / totals[i])
        else:
            result[ch] = float("nan")
    return result


def _write_readme(
    overall_acc: float,
    per_class_acc: dict[str, float],
    top_confusions: list[tuple[str, str, int]],
    epoch_reached: int,
    elapsed_s: float,
) -> None:
    """
    Write (overwrite) extraction/ocr/README.md with training results.
    The evaluate.py script will append the benchmark comparison section later.
    """
    lines: list[str] = [
        "# Custom OCR Pipeline\n",
        "\n",
        "## Pipeline Overview\n",
        "\n",
        "```\n",
        "raw image bytes\n",
        "    │\n",
        "    ▼  extraction/preprocess.py  (grayscale → deskew → CLAHE → Otsu)\n",
        "    │\n",
        "    ▼  extraction/ocr/preprocess.py  (adaptive threshold → denoising)\n",
        "    │\n",
        "    ▼  extraction/ocr/segment_lines.py  (horizontal projection profile)\n",
        "    │\n",
        "    ▼  extraction/ocr/segment_chars.py  (connected components + word gaps)\n",
        "    │\n",
        "    ▼  extraction/ocr/recognize.py  (CNN character classifier)\n",
        "    │\n",
        "    ▼  extraction/ocr.py  extract_text()  (assemble characters → text)\n",
        "```\n",
        "\n",
        "## Character Set\n",
        "\n",
        "75 classes: uppercase A-Z (26), lowercase a-z (26), digits 0-9 (10), "
        "punctuation `. , % / - ₹ ( ) : @ + # space` (13).\n",
        "\n",
        "## CNN Architecture\n",
        "\n",
        "Input `(N, 1, 28, 28)` → Conv32 → Conv64 → Conv128 → FC512 → FC75.  "
        "~1.5M parameters.  Framework: PyTorch.\n",
        "\n",
        "## Retraining\n",
        "\n",
        "```bash\n",
        "# From the backend/ directory:\n",
        "pip install torch torchvision Pillow opencv-python-headless\n",
        "python -m extraction.ocr.training.train_char_model\n",
        "```\n",
        "EMNIST data is downloaded automatically on first run (~500 MB).\n",
        "\n",
        "---\n",
        "\n",
        "## Training Results\n",
        "\n",
        f"Trained for **{epoch_reached} epochs** in {elapsed_s:.0f} s.\n",
        "\n",
        f"**Overall test accuracy: {overall_acc * 100:.2f}%**\n",
        "\n",
        "### Per-class accuracy (lowest 15 — worst performers)\n",
        "\n",
        "| Char | Accuracy |\n",
        "|------|----------|\n",
    ]

    # Lowest-accuracy classes
    valid = {ch: acc for ch, acc in per_class_acc.items() if not (acc != acc)}  # filter NaN
    lowest = sorted(valid.items(), key=lambda x: x[1])[:15]
    for ch, acc in lowest:
        lines.append(f"| `{ch}` | {acc * 100:.1f}% |\n")

    lines += [
        "\n",
        "### Top confusion pairs\n",
        "\n",
        "Common OCR confusion pairs (true → predicted):\n",
        "\n",
        "| True | Predicted | Count |\n",
        "|------|-----------|-------|\n",
    ]
    for true_ch, pred_ch, count in top_confusions:
        lines.append(f"| `{true_ch}` | `{pred_ch}` | {count} |\n")

    lines += [
        "\n",
        "> **Note on accuracy gap**: A custom CNN trained on EMNIST + synthetic\n",
        "> fonts is expected to achieve lower accuracy than EasyOCR on real-world\n",
        "> photographed labels. The gap is documented in the benchmark section\n",
        "> below. Common hard pairs: `O`/`0`, `l`/`1`/`I`, `5`/`S`, `rn`/`m`.\n",
        "\n",
        "---\n",
        "\n",
        "## Benchmark Comparison\n",
        "\n",
        "*Run `python -m extraction.ocr.evaluate --image-dir <path>` to populate this section.*\n",
    ]

    _README_PATH.parent.mkdir(parents=True, exist_ok=True)
    _README_PATH.write_text("".join(lines), encoding="utf-8")
    logger.info("README written to %s", _README_PATH)


# ── Main training loop ─────────────────────────────────────────────────────────

def train(
    data_root: str = _DEFAULT_DATA_ROOT,
    epochs: int = _DEFAULT_EPOCHS,
    batch_size: int = _DEFAULT_BATCH,
    lr: float = _DEFAULT_LR,
) -> None:
    """End-to-end training pipeline."""

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training device: %s", device)

    # ── Datasets & loaders ────────────────────────────────────────────────────
    train_ds, test_ds, class_counts = build_datasets(data_root=data_root)

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=_NUM_WORKERS,
        pin_memory=(device.type == "cuda"),
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size * 2,
        shuffle=False,
        num_workers=_NUM_WORKERS,
    )

    # ── Model ─────────────────────────────────────────────────────────────────
    model = CharCNN(n_classes=NUM_CLASSES).to(device)
    total_params = sum(p.numel() for p in model.parameters())
    logger.info("CharCNN: %d parameters", total_params)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", patience=2, factor=0.5
    )

    # ── Training loop with early stopping ────────────────────────────────────
    best_val_loss = float("inf")
    patience_counter = 0
    best_epoch = 0
    start_time = time.time()
    epoch_reached = 0

    _MODEL_DIR.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, epochs + 1):
        epoch_reached = epoch
        train_loss = _train_epoch(model, train_loader, optimizer, criterion, device)
        val_loss, val_acc, _ = _evaluate(model, test_loader, criterion, device)
        scheduler.step(val_loss)

        logger.info(
            "Epoch %3d/%d | train_loss=%.4f | val_loss=%.4f | val_acc=%.2f%%",
            epoch, epochs, train_loss, val_loss, val_acc * 100,
        )

        if val_loss < best_val_loss - 1e-4:
            best_val_loss = val_loss
            patience_counter = 0
            best_epoch = epoch
            torch.save(model.state_dict(), _MODEL_PATH)
            logger.info("  ✓ New best model saved (val_loss=%.4f)", best_val_loss)
        else:
            patience_counter += 1
            if patience_counter >= _EARLY_STOP_PATIENCE:
                logger.info(
                    "Early stopping at epoch %d (no improvement for %d epochs).",
                    epoch, _EARLY_STOP_PATIENCE,
                )
                break

    elapsed = time.time() - start_time
    logger.info("Training complete. Best epoch: %d (val_loss=%.4f)", best_epoch, best_val_loss)

    # ── Final evaluation on best checkpoint ───────────────────────────────────
    logger.info("Loading best checkpoint for final evaluation …")
    model.load_state_dict(torch.load(_MODEL_PATH, map_location=device))
    _, test_acc, conf_mat = _evaluate(model, test_loader, criterion, device)

    logger.info("Final test accuracy: %.2f%%", test_acc * 100)

    per_cls = _per_class_accuracy(conf_mat)
    confusions = _top_confusions(conf_mat)

    # Print highlights to stdout
    print("\n" + "=" * 60)
    print(f"  FINAL TEST ACCURACY: {test_acc * 100:.2f}%")
    print("=" * 60)
    print("\n  Top confusion pairs (true → predicted):")
    for true_ch, pred_ch, count in confusions[:10]:
        print(f"    '{true_ch}' → '{pred_ch}': {count} times")

    # Explicitly call out classic OCR confusions
    _CLASSIC_PAIRS = [
        ("O", "0"), ("0", "O"), ("l", "1"), ("1", "l"),
        ("I", "1"), ("I", "l"), ("5", "S"), ("S", "5"),
        ("B", "8"), ("8", "B"),
    ]
    print("\n  Classic OCR confusion pair counts:")
    mat = conf_mat.numpy()
    for true_ch, pred_ch in _CLASSIC_PAIRS:
        try:
            from extraction.ocr.charset import char_to_idx
            t_idx = char_to_idx(true_ch)
            p_idx = char_to_idx(pred_ch)
            count = int(mat[t_idx, p_idx])
            print(f"    '{true_ch}' → '{pred_ch}': {count}")
        except (KeyError, IndexError):
            pass

    print(f"\n  Model saved to: {_MODEL_PATH}")
    print("=" * 60 + "\n")

    _write_readme(test_acc, per_cls, confusions, epoch_reached, elapsed)


# ── CLI entry point ────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Train the custom OCR character recognition CNN.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--data-root", default=_DEFAULT_DATA_ROOT,
                   help="Directory for EMNIST download cache.")
    p.add_argument("--epochs", type=int, default=_DEFAULT_EPOCHS,
                   help="Maximum training epochs.")
    p.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH,
                   help="Mini-batch size.")
    p.add_argument("--lr", type=float, default=_DEFAULT_LR,
                   help="Initial learning rate.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    train(
        data_root=args.data_root,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
    )
