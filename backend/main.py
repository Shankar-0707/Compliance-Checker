"""
main.py
───────
FastAPI application — entry point.

Exposes:
    POST /api/analyze   — multipart: image + description → compliance + health JSON
    GET  /healthz       — simple liveness probe

Orchestration flow for POST /api/analyze
─────────────────────────────────────────
  1. Upload image to Cloudinary → image_url (internal, not returned to frontend)
  2. preprocess_image(bytes) → image_array
  3. extract_text(image_array) → raw_ocr_text
  4. parse_label_text(raw_ocr_text) → ocr_fields
  5. parse_description_text(description) → desc_fields
  6. merge_fields(ocr_fields, desc_fields) → (merged, contradictions)
  7. check_compliance(merged) → compliance_results
  8. get_health_grade(merged) → health | None
  9. Persist AuditResult to PostgreSQL
 10. Return { compliance: { results: [...] }, health: {...} | null }
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db.database import create_all_tables
from db.models import AuditResult
from db.database import get_session
from extraction.merge import merge_fields
from extraction.ocr import extract_text
from extraction.parse_description import parse_description_text
from extraction.parse_label import parse_label_text
from extraction.preprocess import preprocess_image
from ml_client import get_health_grade
from rules.engine import check_compliance
from storage.cloudinary_client import upload_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Application lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """
    Create DB tables on startup (idempotent — safe to run every time).
    In production, use ``alembic upgrade head`` before starting the app.
    """
    logger.info("Starting up — ensuring database tables exist...")
    try:
        await create_all_tables()
        logger.info("Database ready.")
    except Exception as exc:
        logger.warning(
            "Could not connect to PostgreSQL database (%s). "
            "Backend will continue in local mode without audit persistence until DATABASE_URL is reachable.",
            exc,
        )
    yield
    logger.info("Shutting down.")


# ── App instance ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Compliance & Health Rating Copilot — Backend API",
    description=(
        "OCR-powered compliance checker for FSSAI and Legal Metrology regulations, "
        "with AI health grading via an external ML service."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend (any origin in dev; tighten for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict to frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/healthz", tags=["Infra"])
async def health_check():
    """Liveness probe — returns 200 OK when the service is up."""
    return {"status": "ok"}


@app.post("/api/analyze", tags=["Analysis"])
async def analyze(
    image: UploadFile = File(..., description="Label image file (JPEG/PNG/WEBP)"),
    description: str = Form(..., description="Product description text"),
):
    """
    Analyse a product label image and description for compliance and health grade.

    **Request**: multipart/form-data with fields ``image`` and ``description``.

    **Response**:
    ```json
    {
        "compliance": {
            "results": [
                {"field": "fssai_license_number", "passed": false, "citation": "..."},
                ...
            ]
        },
        "health": {
            "grade": "D",
            "flagged_ingredients": ["contains_palm_oil"],
            "advice": "..."
        }
    }
    ```
    ``health`` is ``null`` when the ML service is unreachable.
    """

    # ── 1. Read image bytes ───────────────────────────────────────────────────
    try:
        image_bytes = await image.read()
    except Exception as exc:
        logger.error("Failed to read uploaded image: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read uploaded image file.",
        ) from exc

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty.",
        )

    filename = image.filename or "label_image"

    # ── 2. Upload to Cloudinary ───────────────────────────────────────────────
    image_url: str | None = None
    try:
        image_url = await upload_image(image_bytes, filename)
        logger.info("Image uploaded to Cloudinary: %s", image_url)
    except Exception as exc:
        # Non-fatal — log and continue without storage
        logger.warning("Cloudinary upload failed (%s) — proceeding without image URL.", exc)

    # ── 3. Preprocess + OCR ───────────────────────────────────────────────────
    try:
        image_array = preprocess_image(image_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Image preprocessing failed: {exc}",
        ) from exc

    raw_ocr_text = extract_text(image_array)
    logger.info("OCR extracted %d characters.", len(raw_ocr_text))

    # ── 4. Parse both text sources ────────────────────────────────────────────
    ocr_fields = parse_label_text(raw_ocr_text)
    desc_fields = parse_description_text(description)

    # ── 5. Merge fields ───────────────────────────────────────────────────────
    merged_fields, contradictions = merge_fields(ocr_fields, desc_fields)

    if contradictions:
        logger.info(
            "Field contradictions detected between OCR and description: %s",
            [c["field"] for c in contradictions],
        )

    # ── 6. Compliance check ───────────────────────────────────────────────────
    compliance_results = check_compliance(merged_fields)
    passed_count = sum(1 for r in compliance_results if r["passed"])
    logger.info(
        "Compliance: %d/%d rules passed.", passed_count, len(compliance_results)
    )

    # ── 7. ML health grade (graceful degradation) ─────────────────────────────
    health_result: dict | None = await get_health_grade(merged_fields)

    # ── 8. Persist to database ────────────────────────────────────────────────
    try:
        audit = AuditResult(
            description_text=description,
            image_url=image_url,
            compliance_results=compliance_results,
            health_grade=health_result["grade"] if health_result else None,
            health_flags=health_result["flagged_ingredients"] if health_result else None,
            health_advice=health_result["advice"] if health_result else None,
            contradictions=contradictions or None,
        )
        async with get_session() as session:
            session.add(audit)
        logger.info("AuditResult saved to database (id will be assigned by DB).")
    except Exception as exc:
        # Non-fatal — log and continue; don't fail the request over a DB write error
        logger.error("Failed to persist AuditResult: %s", exc)

    # ── 9. Build and return response ──────────────────────────────────────────
    response_body = {
        "compliance": {
            "results": compliance_results,
        },
        "health": health_result,  # None if ML service was down
    }

    return JSONResponse(content=response_body, status_code=status.HTTP_200_OK)
