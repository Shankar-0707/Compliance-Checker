# Compliance Checker — Backend

## Project Structure

```
backend/
│
├── extraction/                  # Image OCR + text parsing pipeline
│   ├── preprocess.py            # Grayscale → deskew → CLAHE → binarise
│   ├── ocr.py                   # extract_text() — custom OCR pipeline (see below)
│   ├── parse_label.py           # OCR text → structured field dict
│   ├── parse_description.py     # User description → structured field dict
│   ├── merge.py                 # Merge OCR + description fields, detect contradictions
│   ├── _patterns.py             # Shared regex patterns for field extraction
│   │
│   └── ocr/                     # Custom OCR sub-package
│       ├── charset.py           # 75-class character set definition
│       ├── preprocess.py        # Adaptive threshold + denoising refinement
│       ├── segment_lines.py     # Horizontal projection profile → line crops
│       ├── segment_chars.py     # Connected components → 28×28 char crops
│       ├── recognize.py         # CharCNN inference (loads model once at startup)
│       ├── evaluate.py          # Benchmark: custom vs EasyOCR (offline use only)
│       ├── README.md            # Training results + confusion matrix
│       ├── model/
│       │   ├── cnn.py           # CharCNN architecture (~1.5M params, PyTorch)
│       │   └── char_model.pt    # Trained weights (run training script to regenerate)
│       └── training/
│           ├── prepare_char_data.py  # EMNIST + synthetic font dataset builder
│           └── train_char_model.py   # Training script (offline, not imported at runtime)
│
├── rules/
│   ├── engine.py                # Compliance rule engine (check_compliance)
│   └── rules.json               # FSSAI / Legal Metrology rules
│
├── db/                          # SQLAlchemy async models + session
├── storage/                     # Cloudinary upload client
├── ml_client.py                 # HTTP client for ML health-rating service
├── main.py                      # FastAPI app + /api/analyze endpoint
└── requirements.txt
```

## OCR Approach

**Current approach: custom-built pipeline** (replaced EasyOCR in Sept 2026).

The OCR is fully self-implemented — no Tesseract, PaddleOCR, or EasyOCR in the
production path.  The pipeline runs:

1. **Preprocessing** — adaptive threshold + median blur denoising
2. **Line segmentation** — horizontal projection profile
3. **Character segmentation** — connected-component labelling + word-gap detection
4. **Recognition** — small CNN (2 conv blocks + dense head, ~1.5M params, PyTorch)
5. **Assembly** — characters + word boundaries → text

See [`extraction/ocr/README.md`](extraction/ocr/README.md) for the full architecture
description, training results, confusion matrix, and benchmark comparison vs. EasyOCR.

### Retraining the model

If you need to retrain `char_model.pt` (e.g. after adding new fonts or expanding
the charset), run from the `backend/` directory:

```bash
pip install torch torchvision Pillow opencv-python-headless
python -m extraction.ocr.training.train_char_model
```

EMNIST data (~500 MB) is downloaded automatically on the first run.
The script writes the new weights to `extraction/ocr/model/char_model.pt`
and updates `extraction/ocr/README.md` with the new accuracy metrics.

### Running the benchmark comparison

```bash
python -m extraction.ocr.evaluate \
    --image-dir ./test_images \
    --gt-dir ./ground_truth
```

This is the only place where EasyOCR is invoked — it is not used anywhere in
the production API path.

## Running Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

API available at `http://localhost:8000`.  Interactive docs at `/docs`.