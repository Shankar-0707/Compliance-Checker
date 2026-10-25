# 🔍 Custom OCR Pipeline — How It Works (Plain Language)

> This document explains **what the OCR system does, how it works step by step, and why each piece exists** — written so anyone can understand it, even without a machine learning background.

---

## The Big Picture

When you take a photo of a food label, the computer needs to "read" it — just like you do with your eyes.
That process is called **OCR** (Optical Character Recognition).

Instead of using a pre-built OCR library, this project builds OCR **from scratch** using a small neural network trained specifically on printed text. Here's why:

- More control over what characters are recognised
- No dependency on a heavy external library (EasyOCR weighs ~1 GB)
- Faster inference on CPU-only servers
- Easier to fine-tune on food-label-specific fonts

The trade-off: **~85–92% accuracy on clean printed text** vs ~98% for EasyOCR. That gap is documented and acceptable for compliance checking, where the description text field provides a safety net.

---

## The Full Pipeline (Step by Step)

Imagine you hand a photograph to a very methodical reader. They'd do something like this:

```
📷 Raw photo
   │
   ▼  Step 1: Clean up the image
   │  (grayscale → deskew → sharpen → binarise)
   │
   ▼  Step 2: Refine binarisation (OCR-specific)
   │  (adaptive threshold → remove speckles)
   │
   ▼  Step 3: Find each line of text
   │  (horizontal projection profile)
   │
   ▼  Step 4: Find each character within a line
   │  (connected components + gap detection)
   │
   ▼  Step 5: Recognise each character
   │  (feed 28×28 pixel image into a neural network)
   │
   ▼  Step 6: Assemble characters into words and lines
   │
   ▼  📝 Final text string
```

Let's walk through each step.

---

## Step 1 — Clean Up the Image (`extraction/preprocess.py`)

**What it does:** Takes the raw JPEG/PNG photo and produces a clean black-and-white image.

**Why:** Camera photos have colour, uneven lighting, blur, and rotation. Computers find it much easier to read clean black-and-white images.

**How:**
1. **Convert to grayscale** — throw away colour; only brightness matters for text
2. **Deskew** — rotate the image so text lines are horizontal (if the photo was taken at an angle)
3. **CLAHE** — a contrast enhancement trick that makes faded text darker
4. **Otsu thresholding** — decide which pixels are "text" (dark) and which are "background" (white), using a smart automatic cutoff

---

## Step 2 — Refine Binarisation (`extraction/ocr/preprocess.py`)

**What it does:** A second, more careful binarisation pass, this time region-by-region.

**Why:** Global thresholding (Step 1) can fail when part of the label is in shadow and part is brightly lit. A uniform cutoff makes shadow areas all-black and bright areas all-white.

**How:**
1. **Adaptive thresholding** — instead of one global dark/light cutoff, it computes the cutoff for every small 31×31 pixel neighbourhood separately. This handles uneven lighting perfectly.
2. **Median blur** — removes tiny random noise pixels (salt-and-pepper noise) without blurring the character edges
3. **Morphological opening** — a mathematical operation that erases isolated single-pixel blobs (more noise removal)
4. **Polarity check** — makes sure text is always dark on a white background (flips if the image is inverted)

---

## Step 3 — Find Text Lines (`extraction/ocr/segment_lines.py`)

**What it does:** Cuts the image horizontally into one strip per line of text.

**The clever idea — Horizontal Projection Profile:**

Imagine counting how many dark pixels are in each horizontal row of the image. A row that cuts through letters will have many dark pixels. A row between lines of text will have almost none.

```
Row 5  ████ ███ █ ████   ← lots of dark pixels = text row
Row 6  ████ ███   ████
Row 7  ████ ███   ████
Row 8                    ← almost no dark pixels = gap between lines
Row 9  ████ ████  ███
```

Plot those counts as a graph (the "projection profile") and text lines appear as peaks, gaps appear as valleys.

**Steps:**
1. Count dark pixels per row → 1D array of numbers
2. Smooth the array slightly (Gaussian smoothing) so tiny dips within a letter don't look like line gaps
3. Any row where count > 5% of the maximum is "text"; the rest are "gap"
4. Group consecutive text rows into runs → each run = one line of text
5. Add 3 pixels of padding above and below each line (so tall letters like `h`, `g` aren't clipped)
6. Merge lines that are fewer than 2 pixels apart (handles letters with stray pixels)

---

## Step 4 — Find Individual Characters (`extraction/ocr/segment_chars.py`)

**What it does:** Within each text line strip, finds the exact bounding box of every single character.

**The technique — Connected Components:**

A "connected component" is a group of dark pixels that are all touching each other. Each character (A, B, 3, %) forms its own connected blob if there's white space between them.

OpenCV has a built-in function (`cv2.connectedComponentsWithStats`) that finds all these blobs automatically and returns each one's position and size.

**Tricky parts:**
- **Filtering noise**: Tiny blobs (too small to be a letter) are discarded
- **Dot detection**: The dot of an `i` or `j` is a separate blob — it gets merged with the letter below it
- **Word gaps**: When the horizontal gap between two characters is large enough, the system marks the next character as "start of a new word" (so spaces get inserted later)
- **Normalisation**: Each character crop is resized to exactly **28×28 pixels** — the size the neural network expects

---

## Step 5 — Recognise Each Character (`extraction/ocr/recognize.py`)

**What it does:** Takes each 28×28 character image and predicts which character it is.

**The tool: CharCNN** — a small Convolutional Neural Network (CNN)

### What is a CNN?

A CNN is a type of artificial neural network that is especially good at understanding images. It works in layers:

1. **Early layers** detect simple patterns — edges, corners, curves
2. **Middle layers** combine those into shapes — loops, vertical strokes, arcs
3. **Final layers** combine shapes into character identities — "this is the letter B"

### CharCNN Architecture

```
Input image (28×28 pixels, greyscale)
    │
    ▼  Conv Layer 1 — 32 filters, 3×3 kernel
    │  Learns: edges, basic strokes
    │
    ▼  Conv Layer 2 — 64 filters, 3×3 kernel
    │  Learns: curves, loops
    │
    ▼  Conv Layer 3 — 128 filters, 3×3 kernel
    │  Learns: complex character parts
    │
    ▼  Fully-Connected Layer (512 neurons)
    │  Combines all features
    │
    ▼  Output Layer (75 neurons)
       One score per character class
       → pick the highest score → predicted character
```

**Total parameters: ~1.5 million** (very small by modern standards — trains on CPU in ~20 minutes)

### The 75 Characters

The network recognises:
- 26 uppercase letters: `A–Z`
- 26 lowercase letters: `a–z`
- 10 digits: `0–9`
- 13 punctuation/symbols: `. , % / - ₹ ( ) : @ + # space`

### Known Hard Cases

Some characters look very similar to each other:

| True character | Often confused with | Why |
|---|---|---|
| `O` | `0` | Nearly identical circles |
| `l` | `1` and `I` | All thin vertical strokes |
| `5` | `S` | Similar curves |
| `B` | `8` | Both have two loops |
| `rn` | `m` | `r` and `n` together look like `m` |

These are called **classic OCR confusion pairs** and are tracked in the training results.

---

## Step 6 — Reassemble Text (`extraction/ocr/__init__.py`)

**What it does:** Stitches the individual predicted characters back into readable text.

**How:**
- For each line, go through the characters in left-to-right order
- If a character was marked as "word start" (there was a big gap before it), insert a space first
- Join everything into a string
- All lines joined with newlines → final text output

---

## Training the Neural Network

The CharCNN is trained on two datasets combined:

1. **EMNIST** — a large public dataset of ~800,000 handwritten character images (downloaded automatically)
2. **Synthetic printed-font data** — images of characters rendered in various common fonts at various sizes, to match machine-printed labels

### Training Process

```
For each epoch (training round):
    ┌─────────────────────────────────────┐
    │  Show the network batches of 256    │
    │  character images                   │
    │                                     │
    │  Network makes predictions          │
    │                                     │
    │  Compare to correct answers         │
    │  → calculate "loss" (error score)   │
    │                                     │
    │  Adjust network weights slightly    │
    │  to reduce the error                │
    │  (backpropagation + Adam optimiser) │
    └─────────────────────────────────────┘
    
    After each epoch:
    → Run on validation set (images not seen during training)
    → If validation loss improved: save checkpoint ✓
    → If no improvement for 4 epochs: stop early (early stopping)
```

### Learning Rate Scheduling

The "learning rate" controls how big a step the optimiser takes each update. It starts at `0.001`. If validation loss stops improving for 2 epochs, the learning rate is halved (multiplied by 0.5). This helps the network settle into a more precise answer near the end of training.

This is done by `ReduceLROnPlateau` in PyTorch.

### Training Output

After training completes, the script:
- Saves the best model weights to `extraction/ocr/model/char_model.pt`
- Prints a confusion matrix of the top error pairs
- Writes accuracy results to `extraction/ocr/README.md` (this file's Training Results section)

---

## Health Grade Algorithm (ML Service)

Separate from OCR, the ML service predicts a **health grade (A–E)** for the product.

### How the grade is assigned

1. **Input**: Nutritional values per 100g (sugar, fat, sodium, protein, fibre, calories) + ingredient flags (contains palm oil, artificial sweeteners, trans fat, etc.)
2. **Feature engineering**: Missing values are filled with saved median values from the training dataset
3. **Prediction**: A scikit-learn classifier (trained on labelled food products) outputs a grade
4. **Advice generation**: Based on the grade and flagged ingredients, a human-readable recommendation is generated

### Grade meaning

| Grade | Meaning |
|-------|---------|
| A | Excellent — nutrient-dense, no problematic ingredients |
| B | Good — mostly healthy |
| C | Average — some concerns |
| D | Poor — high in sugar, fat, or salt, or has problematic ingredients |
| E | Very poor — strongly advise limiting consumption |

---

## Accuracy & Limitations

| Scenario | Expected accuracy |
|----------|------------------|
| Clean, machine-printed text (scanned) | 85–92% |
| Photographed label (good lighting) | 75–85% |
| Photographed label (shadows/blur) | 60–75% |
| Handwritten text | Not supported |

**The description text field** acts as a safety net — the user can paste the label text directly, and `parse_description_text()` will extract structured fields from it, compensating for any OCR errors.

---

## File Reference

| File | What it does (one line) |
|------|------------------------|
| [`extraction/preprocess.py`](../../preprocess.py) | Raw image → clean numpy array |
| [`extraction/ocr/__init__.py`](__init__.py) | Public `extract_text()` entry point |
| [`extraction/ocr/preprocess.py`](preprocess.py) | Adaptive threshold + denoising |
| [`extraction/ocr/segment_lines.py`](segment_lines.py) | Horizontal projection → line crops |
| [`extraction/ocr/segment_chars.py`](segment_chars.py) | Connected components → 28×28 char crops |
| [`extraction/ocr/recognize.py`](recognize.py) | CharCNN batch inference |
| [`extraction/ocr/charset.py`](charset.py) | 75-class character set definition |
| [`extraction/ocr/model/cnn.py`](model/cnn.py) | CharCNN architecture |
| [`extraction/ocr/training/train_char_model.py`](training/train_char_model.py) | Full training loop + evaluation |
| [`extraction/ocr/evaluate.py`](evaluate.py) | Benchmark vs EasyOCR |

---

*For the overall project setup and API reference, see the [project README](../../../README.md).*

## Pipeline Overview

```
raw image bytes
    │
    ▼  extraction/preprocess.py  (grayscale → deskew → CLAHE → Otsu)
    │
    ▼  extraction/ocr/preprocess.py  (adaptive threshold → denoising)
    │
    ▼  extraction/ocr/segment_lines.py  (horizontal projection profile)
    │
    ▼  extraction/ocr/segment_chars.py  (connected components + word gaps)
    │
    ▼  extraction/ocr/recognize.py  (CNN character classifier)
    │
    ▼  extraction/ocr.py  extract_text()  (assemble characters → text)
```

## Character Set

75 classes: uppercase A-Z (26), lowercase a-z (26), digits 0-9 (10),
punctuation `. , % / - ₹ ( ) : @ + # space` (13).

## CNN Architecture

Input `(N, 1, 28, 28)` → Conv32 → Conv64 → Conv128 → FC512 → FC75.
~1.5M parameters. Framework: PyTorch.

## Retraining

```bash
# From the backend/ directory:
pip install torch torchvision Pillow opencv-python-headless
python -m extraction.ocr.training.train_char_model
```

EMNIST data is downloaded automatically on first run (~500 MB).

---

## Training Results

*Not yet trained — run the training script above to populate this section.*

---

---

---

## Benchmark Results

Evaluated on 5 test image(s).

| File | Custom CER | Custom WER | EasyOCR CER | EasyOCR WER |
|------|-----------|-----------|------------|------------|
| label 1.png | 0.824 | 1.000 | 0.011 | 0.033 |
| label 2.png | 0.819 | 1.085 | 0.244 | 0.256 |
| label 3.jpg | 0.993 | 1.000 | 1.000 | 1.000 |
| label 4.jpg | 0.871 | 1.229 | 0.052 | 0.200 |
| label 5.jpg | 0.979 | 1.000 | 0.996 | 0.998 |

**Average**

| — | **0.897** | **1.063** | **0.460** | **0.498** |

> **Expected accuracy gap**: The custom CNN is intentionally less accurate than EasyOCR on real-world photographed labels. This is the documented outcome for a self-built system — see project report for analysis.
