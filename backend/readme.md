# Compliance & Health Rating Copilot — Backend

FastAPI backend that:
- Extracts label fields from a product image via **PaddleOCR + OpenCV**
- Parses a user-typed product description for the same fields
- Checks both sources against **FSSAI + Legal Metrology** compliance rules
- Calls an external ML service for a **health grade (A–E)**
- Persists every audit result to **Neon PostgreSQL**
- Stores uploaded label images in **Cloudinary**

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| pip | latest |
| Neon PostgreSQL | Cloud account (free tier works) |
| Cloudinary | Free account |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL connection string — format: `postgresql+asyncpg://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require` |
| `ML_SERVICE_URL` | Base URL of the teammate's ML FastAPI service (default: `http://localhost:8001`) |
| `CLOUDINARY_CLOUD_NAME` | Your Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Your Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Your Cloudinary API secret |

---

## Local Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env with your actual credentials

# 4. Run database migration (creates the audit_results table in Neon)
alembic upgrade head

# 5. Start the development server
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## Running Without the ML Service

If your teammate's ML service isn't running yet, the backend handles this gracefully. Simply start the backend — if the ML service at `ML_SERVICE_URL` is unreachable, the `/api/analyze` endpoint will still return compliance results with `"health": null` and log a warning. No code changes needed.

---

## API Reference

### `POST /api/analyze`

Analyse a product label image and description text.

**Request** — `multipart/form-data`:

| Field | Type | Description |
|---|---|---|
| `image` | file | Label photo (JPEG / PNG / WEBP) |
| `description` | string | Product description text |

**Example with `curl`:**

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "image=@/path/to/label.jpg" \
  -F "description=Britannia NutriChoice Digestive Biscuits 250g. Mfg: Britannia Industries Ltd, Bangalore. FSSAI: 10013022002253. MRP Rs. 45. Best Before: 6 months from manufacture."
```

**Response (200 OK):**

```json
{
  "compliance": {
    "results": [
      {
        "field": "fssai_license_number",
        "passed": true,
        "citation": "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(7)"
      },
      {
        "field": "net_quantity",
        "passed": true,
        "citation": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(c)"
      },
      {
        "field": "manufacturer_address",
        "passed": true,
        "citation": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(a)"
      },
      {
        "field": "manufacture_date",
        "passed": false,
        "citation": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(d)"
      },
      {
        "field": "mrp",
        "passed": true,
        "citation": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(e)"
      },
      {
        "field": "consumer_care",
        "passed": false,
        "citation": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(f)"
      },
      {
        "field": "product_name",
        "passed": false,
        "citation": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(b)"
      },
      {
        "field": "ingredients_list",
        "passed": false,
        "citation": "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(2)"
      },
      {
        "field": "best_before_date",
        "passed": true,
        "citation": "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(5)"
      },
      {
        "field": "veg_nonveg_symbol",
        "passed": false,
        "citation": "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(8)"
      }
    ]
  },
  "health": {
    "grade": "C",
    "flagged_ingredients": ["contains_added_sugar"],
    "advice": "Moderate sugar content — suitable in limited quantities."
  }
}
```

When the ML service is unavailable:
```json
{
  "compliance": { "results": [ ... ] },
  "health": null
}
```

### `GET /healthz`

Liveness probe — returns `{"status": "ok"}` with 200 OK.

---

## Project Structure

```
backend/
├── extraction/
│   ├── _patterns.py          # Shared regex patterns (single source of truth)
│   ├── ocr.py                # PaddleOCR singleton wrapper
│   ├── preprocess.py         # OpenCV image preprocessing pipeline
│   ├── parse_label.py        # OCR text → structured fields
│   ├── parse_description.py  # User description → structured fields
│   └── merge.py              # Merge + contradiction detection
├── rules/
│   ├── engine.py             # Compliance rule engine
│   └── rules.json            # 10 FSSAI + Legal Metrology rules
├── storage/
│   └── cloudinary_client.py  # Cloudinary upload helper
├── db/
│   ├── database.py           # Async SQLAlchemy engine + session
│   └── models.py             # AuditResult ORM model
├── alembic/
│   ├── env.py                # Alembic async env (reads DATABASE_URL)
│   └── versions/
│       └── 0001_create_audit_results.py
├── ml_client.py              # ML service HTTP client + ingredient flags
├── main.py                   # FastAPI app + /api/analyze endpoint
├── alembic.ini               # Alembic config
├── requirements.txt
├── .env.example
└── README.md
```

---

## Database Schema

Table: `audit_results`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `created_at` | TIMESTAMP | UTC, server default |
| `description_text` | TEXT | User-typed description |
| `image_url` | VARCHAR(2048) | Cloudinary CDN URL (internal) |
| `compliance_results` | JSON | Full list of rule check results |
| `health_grade` | VARCHAR(2) | A–E or null |
| `health_flags` | JSON | List of flagged ingredient strings |
| `health_advice` | TEXT | ML service qualitative advice |
| `contradictions` | JSON | Fields where OCR ≠ description |

---

## Compliance Rules Reference

Rules are encoded in `rules/rules.json` from:
- **Legal Metrology (Packaged Commodities) Rules, 2011** — Rule 6
- **FSS (Labelling and Display) Regulations, 2020**

| Field | Citation |
|---|---|
| `manufacturer_address` | Legal Metrology Rules, 2011 — Rule 6(1)(a) |
| `product_name` | Legal Metrology Rules, 2011 — Rule 6(1)(b) |
| `net_quantity` | Legal Metrology Rules, 2011 — Rule 6(1)(c) |
| `manufacture_date` | Legal Metrology Rules, 2011 — Rule 6(1)(d) |
| `mrp` | Legal Metrology Rules, 2011 — Rule 6(1)(e) |
| `consumer_care` | Legal Metrology Rules, 2011 — Rule 6(1)(f) |
| `fssai_license_number` | FSS Labelling Regulations, 2020 — Reg. 2.2(7) |
| `ingredients_list` | FSS Labelling Regulations, 2020 — Reg. 2.2(2) |
| `best_before_date` | FSS Labelling Regulations, 2020 — Reg. 2.2(5) |
| `veg_nonveg_symbol` | FSS Labelling Regulations, 2020 — Reg. 2.2(8) |

---

## Sharing with the ML Service Teammate

Give your teammate:
- The `/predict` request shape (section 6.1 of the build spec)
- Confirm the port — currently assuming `8001` via `ML_SERVICE_URL`
- Tell them: missing nutrient values will arrive as `null` (not omitted, not `0`)
