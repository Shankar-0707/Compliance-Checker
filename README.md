# 🏷️ Compliance & Health Rating Copilot

> **Scan any packaged-food label → get instant FSSAI / Legal Metrology compliance results + an AI-generated health grade.**

---

## What does it do?

Upload a photo of a product label and paste its description text. The system:

1. **Reads the label** using a custom-built OCR pipeline (no third-party OCR service)
2. **Checks every mandatory field** against Indian food-labelling regulations (FSSAI + Legal Metrology)
3. **Grades the product's nutritional quality** (A–E) using a trained ML classifier
4. **Flags problem ingredients** (palm oil, artificial sweeteners, trans fats, etc.) and gives human-readable advice
5. **Stores every audit** in a PostgreSQL database with the uploaded image on Cloudinary

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  Next.js Frontend                │
│           (User uploads image + description)     │
└────────────────────┬────────────────────────────┘
                     │  POST /api/analyze
                     ▼
┌─────────────────────────────────────────────────┐
│              FastAPI Backend  (Python)           │
│                                                 │
│  ① Cloudinary  → store image                    │
│  ② preprocess_image()  → clean numpy array      │
│  ③ extract_text()      → custom OCR pipeline    │
│  ④ parse_label_text()  → structured fields      │
│  ⑤ parse_description_text() → extra fields      │
│  ⑥ merge_fields()      → unified field dict     │
│  ⑦ check_compliance()  → rule engine results    │
│  ⑧ get_health_grade()  → calls ML service ─────►│
│  ⑨ AuditResult         → PostgreSQL             │
└─────────────────────────────────────────────────┘
                                                  │
                     ┌────────────────────────────┘
                     ▼
        ┌────────────────────────┐
        │    FastAPI ML Service   │
        │  (health_model.pkl      │
        │   + advice generator)   │
        └────────────────────────┘
```

### Three services, one repository

| Service | Stack | Port | Purpose |
|---------|-------|------|---------|
| `frontend/` | Next.js 14, TypeScript, Tailwind | 3000 | UI — image upload, results display |
| `backend/` | FastAPI, PyTorch, OpenCV, SQLAlchemy | 8000 | Orchestration, OCR, compliance engine |
| `ml-service/` | FastAPI, scikit-learn (joblib) | 8001 | Health grade prediction |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (or use any hosted instance — Supabase, Neon, etc.)
- Cloudinary account (optional — backend degrades gracefully without it)

---

### 1. Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

# Copy the example env file and fill in your values
copy .env.example .env

# Apply database migrations
alembic upgrade head

# Start the API server
uvicorn main:app --reload --port 8000
```

> **No trained OCR model yet?** The backend still starts. OCR returns `?` for characters until you train (see below).

---

### 2. ML Service

```bash
cd ml-service

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

uvicorn service.main:app --reload --port 8001
```

> If `model/health_model.pkl` is missing, the service returns grade `"C"` as a safe fallback.

---

### 3. Frontend

```bash
cd frontend

npm install
copy .env.example .env.local   # fill in NEXT_PUBLIC_API_URL

npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

### Training the OCR model

```bash
cd backend

# EMNIST dataset is downloaded automatically (~500 MB on first run)
python -m extraction.ocr.training.train_char_model

# With custom hyperparameters:
#   --epochs 25 --batch-size 256 --lr 1e-3 --data-root ./data
```

Trained weights are saved to `backend/extraction/ocr/model/char_model.pt`.  
See [`backend/extraction/ocr/README.md`](backend/extraction/ocr/README.md) for accuracy benchmarks.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL DSN | `postgresql+asyncpg://user:pass@localhost/compliance` |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | `my-cloud` |
| `CLOUDINARY_API_KEY` | Cloudinary API key | `123456789` |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | `abc...` |
| `ML_SERVICE_URL` | ML service base URL | `http://localhost:8001` |

### Frontend (`frontend/.env.local`)

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |

---

## API Reference

### `POST /api/analyze`

**Request** — `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `image` | file | Label photo (JPEG / PNG / WEBP) |
| `description` | string | Free-text product description |

**Response — `200 OK`**

```json
{
  "compliance": {
    "results": [
      {
        "field": "fssai_license_number",
        "passed": false,
        "citation": "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(7)"
      }
    ]
  },
  "health": {
    "grade": "D",
    "flagged_ingredients": ["contains_palm_oil"],
    "advice": "This product contains palm oil, which is high in saturated fat..."
  }
}
```

> `health` is `null` when the ML service is unreachable.

### `GET /healthz`

Liveness probe — returns `{"status": "ok"}`.

---

## Compliance Rules Checked

All rules are defined in `backend/rules/rules.json` and enforced by `backend/rules/engine.py`.

| Field | Regulation |
|-------|-----------|
| Manufacturer name + address | Legal Metrology Rules 2011 — Rule 6(1)(a) |
| Product name | Legal Metrology Rules 2011 — Rule 6(1)(b) |
| Net quantity (with unit) | Legal Metrology Rules 2011 — Rule 6(1)(c) |
| Manufacture date | Legal Metrology Rules 2011 — Rule 6(1)(d) |
| MRP | Legal Metrology Rules 2011 — Rule 6(1)(e) |
| Consumer care details | Legal Metrology Rules 2011 — Rule 6(1)(f) |
| FSSAI licence number (14-digit) | FSS Labelling Regulations 2020 — Reg. 2.2(7) |
| Ingredients list | FSS Labelling Regulations 2020 — Reg. 2.2(2) |
| Best-before / use-by date | FSS Labelling Regulations 2020 — Reg. 2.2(5) |
| Veg / non-veg colour symbol | FSS Labelling Regulations 2020 — Reg. 2.2(8) |

---

## Project Structure

```
Compliance-Checker/
├── README.md                      ← you are here
│
├── backend/
│   ├── main.py                    # FastAPI app + /api/analyze endpoint
│   ├── ml_client.py               # HTTP client for ML service
│   ├── requirements.txt
│   ├── alembic/                   # Database migrations
│   ├── db/                        # SQLAlchemy models + async session
│   ├── storage/                   # Cloudinary upload client
│   ├── rules/
│   │   ├── engine.py              # Compliance rule checker
│   │   └── rules.json             # Rule definitions (field, pattern, citation)
│   └── extraction/
│       ├── preprocess.py          # Raw image → cleaned numpy array
│       ├── parse_label.py         # Regex extractor for OCR text
│       ├── parse_description.py   # Regex extractor for user description
│       ├── merge.py               # Merges + deduplicates fields
│       └── ocr/                   # Custom OCR pipeline
│           ├── __init__.py        # Public extract_text() function
│           ├── preprocess.py      # Adaptive threshold + denoising
│           ├── segment_lines.py   # Horizontal projection → line crops
│           ├── segment_chars.py   # Connected components → char crops
│           ├── recognize.py       # CharCNN inference (singleton)
│           ├── charset.py         # 75-class character set
│           ├── evaluate.py        # Benchmark vs EasyOCR
│           ├── model/cnn.py       # CharCNN architecture (~1.5M params)
│           └── training/          # train_char_model.py + data prep
│
├── ml-service/
│   ├── service/
│   │   ├── main.py                # FastAPI app + /predict endpoint
│   │   ├── inference.py           # HealthRatingInferenceEngine
│   │   └── advice.py              # Human-readable advice generator
│   ├── training/                  # Model + feature engineering scripts
│   └── model/                     # health_model.pkl + medians.json
│
└── frontend/
    └── src/
        ├── app/                   # Next.js app router pages
        ├── components/            # React components
        ├── lib/                   # API client utilities
        └── types/                 # TypeScript type definitions
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend API | FastAPI, Uvicorn, Python 3.11 |
| OCR | Custom PyTorch CNN (CharCNN, ~1.5 M params) + OpenCV |
| Compliance engine | JSON rule definitions + Python regex |
| Health grading | scikit-learn classifier (joblib) |
| Database | PostgreSQL + SQLAlchemy (async) + Alembic |
| Image storage | Cloudinary |
| Inter-service HTTP | httpx |

---

## License

MIT
