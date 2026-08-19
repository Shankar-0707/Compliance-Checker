"""
ml_client.py
────────────
HTTP client that calls the teammate's ML service ``/predict`` endpoint.

Responsibilities
----------------
- Builds the request payload from merged nutrient values and ingredient flags.
- Derives ``ingredient_flags`` via a local keyword lookup (separate from the
  ML team's Open Food Facts training data).
- Handles all network/HTTP failures gracefully — returns ``None`` instead of
  raising, so the main endpoint can still return compliance results.
- ML service base URL is read from the ``ML_SERVICE_URL`` environment variable.

Usage:
    health = await get_health_grade(merged_fields)
    # Returns dict | None
"""

import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_ML_BASE_URL: str = os.environ.get("ML_SERVICE_URL", "http://localhost:8001")
_PREDICT_ENDPOINT = f"{_ML_BASE_URL}/predict"
_TIMEOUT_SECONDS = 10.0


# ── Ingredient flag keyword lookup ────────────────────────────────────────────
# Each entry: (flag_name, list_of_substrings_to_match_case_insensitively)
_FLAG_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "contains_palm_oil",
        ["palm oil", "palm kernel oil", "palm olein", "palm stearin"],
    ),
    (
        "contains_trans_fat",
        ["hydrogenated", "partially hydrogenated", "vanaspati", "dalda"],
    ),
    (
        "contains_added_sugar",
        [
            "sugar",
            "glucose syrup",
            "hfcs",
            "high fructose corn syrup",
            "fructose",
            "sucrose",
            "dextrose",
            "corn syrup",
            "invert syrup",
            "malt syrup",
            "molasses",
        ],
    ),
    (
        "contains_artificial_sweetener",
        ["aspartame", "sucralose", "saccharin", "acesulfame", "neotame", "steviol"],
    ),
    (
        "contains_artificial_color",
        [
            "tartrazine",
            "sunset yellow",
            "carmoisine",
            "brilliant blue",
            "erythrosine",
            "allura red",
            "quinoline yellow",
            "e102",
            "e110",
            "e122",
            "e129",
            "e133",
        ],
    ),
    (
        "contains_preservative",
        [
            "sodium benzoate",
            "potassium sorbate",
            "bha",
            "bht",
            "e211",
            "e202",
            "e220",
            "sulphur dioxide",
            "sodium nitrite",
            "sodium nitrate",
        ],
    ),
]


def _derive_ingredient_flags(ingredients_text: str | None) -> dict[str, bool]:
    """
    Scan the ingredients string for known harmful ingredient keywords and
    return a dict of flag_name → bool.

    Only flags that are True are included in the result (the ML service
    defaults absent flags to False).
    """
    if not ingredients_text:
        return {}

    lowered = ingredients_text.lower()
    flags: dict[str, bool] = {}
    for flag_name, keywords in _FLAG_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            flags[flag_name] = True

    return flags


def _build_nutrients_payload(merged_fields: dict) -> dict[str, float | None]:
    """
    Extract nutrient values from the merged field dict.
    Sends ``null`` for any nutrient not found (never omits them).
    """
    return {
        "energy_kcal": merged_fields.get("energy_kcal"),
        "sugars_g": merged_fields.get("sugars_g"),
        "saturated_fat_g": merged_fields.get("saturated_fat_g"),
        "sodium_mg": merged_fields.get("sodium_mg"),
        "fiber_g": merged_fields.get("fiber_g"),
        "protein_g": merged_fields.get("protein_g"),
    }


async def get_health_grade(merged_fields: dict) -> dict | None:
    """
    Call the ML service ``/predict`` endpoint and return the health result.

    Parameters
    ----------
    merged_fields : dict
        The merged extracted fields dict from ``merge.merge_fields()``.

    Returns
    -------
    dict | None
        ``{"grade": ..., "flagged_ingredients": [...], "advice": "..."}``
        on success, or ``None`` if the ML service is unreachable or returns
        an error.
    """
    nutrients = _build_nutrients_payload(merged_fields)
    ingredient_flags = _derive_ingredient_flags(merged_fields.get("ingredients_list"))

    payload = {
        "nutrients_per_100g": nutrients,
        "ingredient_flags": ingredient_flags,
    }

    logger.debug("Calling ML service at %s with payload: %s", _PREDICT_ENDPOINT, payload)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(_PREDICT_ENDPOINT, json=payload)
            response.raise_for_status()
            data: dict = response.json()

        # Validate expected keys are present
        required_keys = {"grade", "flagged_ingredients", "advice"}
        if not required_keys.issubset(data.keys()):
            logger.error(
                "ML service response missing expected keys. Got: %s", list(data.keys())
            )
            return None

        logger.info("ML service returned grade: %s", data.get("grade"))
        return data

    except httpx.TimeoutException:
        logger.warning(
            "ML service timed out after %.1f seconds — returning health: null.",
            _TIMEOUT_SECONDS,
        )
    except httpx.ConnectError:
        logger.warning(
            "Could not connect to ML service at %s — is it running? Returning health: null.",
            _PREDICT_ENDPOINT,
        )
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "ML service returned HTTP %d — returning health: null. Body: %s",
            exc.response.status_code,
            exc.response.text[:300],
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Unexpected error calling ML service: %s", exc)

    return None
