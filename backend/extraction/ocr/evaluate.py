"""
extraction/ocr/evaluate.py
──────────────────────────
Benchmark comparison script: custom OCR pipeline vs. EasyOCR.

**EasyOCR is imported HERE ONLY — it is not part of the production path.**
This script exists solely to generate the accuracy comparison table for the
project report.

Usage
─────
    # From the backend/ directory:
    python -m extraction.ocr.evaluate --image-dir /path/to/test/images

    # With optional ground-truth directory (plain .txt files, same stem as images):
    python -m extraction.ocr.evaluate \\
        --image-dir ./test_images \\
        --gt-dir ./ground_truth

Input
─────
``--image-dir``  : directory containing test label images (JPEG/PNG)
``--gt-dir``     : directory with matching .txt files containing ground-truth text
                   (one file per image, same filename stem).
                   If omitted, only raw OCR output is printed — no accuracy metrics.

Output
──────
Prints a side-by-side comparison table to stdout and appends a markdown
summary to ``extraction/ocr/README.md``.

Metrics
───────
- CER (Character Error Rate) = edit_distance(pred, gt) / len(gt)
- WER (Word Error Rate) = edit_distance(pred.split(), gt.split()) / len(gt.split())
Lower is better for both.
"""

from __future__ import annotations

import argparse
import logging
import sys
import textwrap
from pathlib import Path

import cv2
import numpy as np

# Allow running as `python -m extraction.ocr.evaluate` from backend/
_BACKEND_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_BACKEND_DIR))

from extraction.preprocess import preprocess_image  # noqa: E402
from extraction.ocr.preprocess import refine_binary  # noqa: E402
from extraction.ocr.segment_lines import segment_lines  # noqa: E402
from extraction.ocr.segment_chars import segment_chars  # noqa: E402
from extraction.ocr.recognize import recognize_chars  # noqa: E402

logger = logging.getLogger(__name__)

_README_PATH = Path(__file__).resolve().parent / "README.md"

# ── Metrics ────────────────────────────────────────────────────────────────────

def _edit_distance(a: str, b: str) -> int:
    """Standard dynamic-programming Levenshtein distance."""
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def _cer(pred: str, gt: str) -> float:
    """Character Error Rate."""
    if not gt:
        return 0.0 if not pred else 1.0
    return _edit_distance(pred, gt) / len(gt)


def _wer(pred: str, gt: str) -> float:
    """Word Error Rate."""
    gt_words = gt.split()
    pred_words = pred.split()
    if not gt_words:
        return 0.0 if not pred_words else 1.0
    return _edit_distance(pred_words, gt_words) / len(gt_words)


# ── Custom pipeline runner ─────────────────────────────────────────────────────

def run_custom_ocr(image_bytes: bytes) -> str:
    """Run the full custom OCR pipeline and return extracted text."""
    try:
        binary = preprocess_image(image_bytes)
        refined = refine_binary(binary)
        line_segs = segment_lines(refined)

        text_lines: list[str] = []
        for seg in line_segs:
            char_blobs = segment_chars(seg.crop)
            if not char_blobs:
                continue
            chars = recognize_chars(char_blobs)
            # Reassemble: insert space before each word-start (except the first)
            line_chars: list[str] = []
            for blob, ch in zip(char_blobs, chars):
                if blob.is_word_start and line_chars:
                    line_chars.append(" ")
                line_chars.append(ch)
            text_lines.append("".join(line_chars))

        return "\n".join(text_lines)
    except Exception as exc:
        logger.error("Custom OCR failed: %s", exc)
        return ""


# ── EasyOCR runner (benchmark only) ───────────────────────────────────────────

def run_easyocr(image_bytes: bytes) -> str:
    """
    Run EasyOCR on *image_bytes* and return extracted text.

    EasyOCR is imported here ONLY — not in the production path.
    Returns empty string if EasyOCR is not installed.
    """
    try:
        import easyocr  # type: ignore[import]
        import numpy as np

        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        results = reader.readtext(img)
        lines = [text for _, text, score in results if score >= 0.5 and text.strip()]
        return "\n".join(lines)
    except ImportError:
        logger.warning("EasyOCR not installed — skipping EasyOCR benchmark.")
        return ""
    except Exception as exc:
        logger.error("EasyOCR failed: %s", exc)
        return ""


# ── Main evaluation loop ───────────────────────────────────────────────────────

def _find_image_files(image_dir: Path) -> list[Path]:
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    return sorted(
        p for p in image_dir.iterdir()
        if p.suffix.lower() in extensions
    )


def _load_gt(gt_dir: Path | None, stem: str) -> str | None:
    if gt_dir is None:
        return None
    gt_path = gt_dir / f"{stem}.txt"
    if gt_path.exists():
        return gt_path.read_text(encoding="utf-8").strip()
    return None


def evaluate(
    image_dir: str,
    gt_dir: str | None = None,
    run_easyocr_flag: bool = True,
) -> None:
    """Run evaluation on all images in *image_dir*."""
    image_path = Path(image_dir)
    gt_path = Path(gt_dir) if gt_dir else None

    images = _find_image_files(image_path)
    if not images:
        print(f"No image files found in {image_path}")
        return

    print(f"\nEvaluating {len(images)} image(s) from {image_path}\n")
    print("─" * 80)

    results: list[dict] = []

    for img_path in images:
        image_bytes = img_path.read_bytes()
        gt_text = _load_gt(gt_path, img_path.stem)

        custom_text = run_custom_ocr(image_bytes)
        easy_text = run_easyocr(image_bytes) if run_easyocr_flag else None

        row: dict = {
            "file": img_path.name,
            "custom": custom_text,
            "easyocr": easy_text,
            "gt": gt_text,
        }

        if gt_text is not None:
            row["custom_cer"] = _cer(custom_text, gt_text)
            row["custom_wer"] = _wer(custom_text, gt_text)
            if easy_text is not None:
                row["easy_cer"] = _cer(easy_text, gt_text)
                row["easy_wer"] = _wer(easy_text, gt_text)

        results.append(row)

        print(f"File: {img_path.name}")
        print(f"  Custom OCR : {textwrap.shorten(custom_text.replace(chr(10), ' ↵ '), 70)}")
        if easy_text is not None:
            print(f"  EasyOCR    : {textwrap.shorten(easy_text.replace(chr(10), ' ↵ '), 70)}")
        if gt_text is not None:
            print(f"  Ground truth: {textwrap.shorten(gt_text.replace(chr(10), ' ↵ '), 70)}")
            print(f"  Custom  CER={row.get('custom_cer', 'n/a'):.3f}  WER={row.get('custom_wer', 'n/a'):.3f}")
            if easy_text is not None:
                print(f"  EasyOCR CER={row.get('easy_cer', 'n/a'):.3f}  WER={row.get('easy_wer', 'n/a'):.3f}")
        print()

    # ── Summary table ─────────────────────────────────────────────────────────
    rows_with_gt = [r for r in results if r.get("gt") is not None]
    if rows_with_gt:
        avg_custom_cer = np.mean([r["custom_cer"] for r in rows_with_gt])
        avg_custom_wer = np.mean([r["custom_wer"] for r in rows_with_gt])
        has_easy = all("easy_cer" in r for r in rows_with_gt)
        if has_easy:
            avg_easy_cer = np.mean([r["easy_cer"] for r in rows_with_gt])
            avg_easy_wer = np.mean([r["easy_wer"] for r in rows_with_gt])

        print("=" * 60)
        print("  SUMMARY (averaged over images with ground truth)")
        print("=" * 60)
        print(f"  Custom OCR  — CER: {avg_custom_cer:.3f}  WER: {avg_custom_wer:.3f}")
        if has_easy:
            print(f"  EasyOCR     — CER: {avg_easy_cer:.3f}  WER: {avg_easy_wer:.3f}")
        print()

        # ── Append markdown to README ─────────────────────────────────────────
        md_rows = []
        for r in results:
            if "custom_cer" not in r:
                continue
            easy_cer_str = f"{r['easy_cer']:.3f}" if "easy_cer" in r else "n/a"
            easy_wer_str = f"{r['easy_wer']:.3f}" if "easy_wer" in r else "n/a"
            md_rows.append(
                f"| {r['file']} | {r['custom_cer']:.3f} | {r['custom_wer']:.3f} "
                f"| {easy_cer_str} | {easy_wer_str} |"
            )

        md_section = (
            "\n\n---\n\n"
            "## Benchmark Results\n\n"
            "Evaluated on {} test image(s).\n\n".format(len(rows_with_gt)) +
            "| File | Custom CER | Custom WER | EasyOCR CER | EasyOCR WER |\n"
            "|------|-----------|-----------|------------|------------|\n" +
            "\n".join(md_rows) +
            "\n\n**Average**\n\n"
            f"| — | **{avg_custom_cer:.3f}** | **{avg_custom_wer:.3f}** "
        )
        if has_easy:
            md_section += f"| **{avg_easy_cer:.3f}** | **{avg_easy_wer:.3f}** |"
        else:
            md_section += "| n/a | n/a |"

        md_section += (
            "\n\n> **Expected accuracy gap**: The custom CNN is intentionally less "
            "accurate than EasyOCR on real-world photographed labels. This is the "
            "documented outcome for a self-built system — see project report for analysis.\n"
        )

        if _README_PATH.exists():
            existing = _README_PATH.read_text(encoding="utf-8")
            # Replace the benchmark section placeholder if present
            if "## Benchmark" in existing:
                idx = existing.index("## Benchmark")
                updated = existing[:idx] + md_section.lstrip("\n")
            else:
                updated = existing + md_section
            _README_PATH.write_text(updated, encoding="utf-8")
            logger.info("Appended benchmark results to %s", _README_PATH)
    else:
        print("No ground-truth files found — raw OCR output only.")


# ── CLI ────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Evaluate custom OCR vs EasyOCR on test label images.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--image-dir", required=True, help="Directory of test images.")
    p.add_argument("--gt-dir", default=None, help="Directory of ground-truth .txt files.")
    p.add_argument("--no-easyocr", action="store_true",
                   help="Skip EasyOCR comparison (custom pipeline only).")
    return p.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()
    evaluate(
        image_dir=args.image_dir,
        gt_dir=args.gt_dir,
        run_easyocr_flag=not args.no_easyocr,
    )
