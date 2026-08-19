"""
extraction/_patterns.py
───────────────────────
Shared regex patterns and extraction helpers used by both
``parse_label.py`` (OCR text) and ``parse_description.py`` (user-typed text).

Keeping patterns in one place ensures OCR and description parsing use
identical rules — which is important for the contradiction-detection logic
in merge.py.
"""

import re
from typing import Optional

# ── Field patterns ────────────────────────────────────────────────────────────

# FSSAI 14-digit licence number
_FSSAI_RE = re.compile(r"\b(\d{14})\b")

# Net quantity  e.g. "200 g", "1.5 kg", "500ml", "2 L"
_NET_QTY_RE = re.compile(
    r"\b(\d+\.?\d*)\s?(g|kg|ml|l)\b",
    re.IGNORECASE,
)

# MRP  e.g. "MRP Rs. 45", "MRP: ₹120", "₹ 99.00"
_MRP_RE = re.compile(
    r"(?:MRP|M\.R\.P\.?)[:\s]*(?:Rs\.?|₹|INR)?\s*(\d+\.?\d*)",
    re.IGNORECASE,
)
# Also catch bare rupee symbol followed by amount
_MRP_RUPEE_RE = re.compile(r"(?:Rs\.?|₹)\s*(\d+\.?\d*)")

# Manufacture / packing date  e.g. "Mfg: 03/2024", "MFG Date: OCT 2024", "Manufactured: March 2024"
_MFG_DATE_RE = re.compile(
    r"(?:Mfg\.?\s*Date|Mfd\.?\s*Date|MFG\s+Date|Manufacture\s+Date"
    r"|Mfg\.?|Mfd\.?|Manufactured|Packed\s+On|Packing\s+Date)[:\s]*"
    r"(\d{2}[/-]\d{4}|\w{3,9}\.?\s*\d{4})",
    re.IGNORECASE,
)

# Best before / use by  e.g. "Best Before: 6 months", "Use By: 12/2025"
_BEST_BEFORE_RE = re.compile(
    r"(?:Best\s+Before|Use\s+By|Expiry|BB\.?|Exp\.?)[:\s]*"
    r"(.{3,40}?)(?:\n|$|,|\.|;)",
    re.IGNORECASE,
)

# Consumer / Customer care  e.g. phone numbers, email addresses
_CONSUMER_CARE_RE = re.compile(
    r"(?:(?:Consumer|Customer)\s+(?:Care|Helpline|Service|Care\s+Information)"
    r"|Toll\s+Free|Help\s*Line|Contact\s+Us|Consumer\s+Helpline)[:\s]*(.{5,80}?)(?:\n|$)",
    re.IGNORECASE,
)

# Product / generic name
# Tries many real-world label keyword variants first, then falls back to first line.
# Pattern covers: "Product Name:", "Item Name:", "Name:", "Brand Name:",
# "Commodity Name:", "Article Name:", "Description:", "Name of Commodity:"
_PRODUCT_NAME_RE = re.compile(
    r"(?:"
    r"Product\s+Name|Item\s+Name|Name\s+of\s+(?:the\s+)?Commodity|"
    r"Commodity\s+Name|Brand\s+Name|Article\s+Name|"
    r"Description\s+of\s+(?:Goods|Product|Commodity)|"
    r"Product|Item|Name"
    r")[:\s]+(.+?)(?:\n|\.|,|$)",
    re.IGNORECASE,
)
# Fallback: first meaningful line of text when no keyword prefix found
_FIRST_LINE_RE = re.compile(r"^\s*(.{3,80}?)(?:\.|,|\n|$)")

# Ingredients block — everything after "Ingredients:" until a blank line or
# another known label section keyword
_INGREDIENTS_RE = re.compile(
    r"(?:Ingredients?|INGREDIENTS?)[:\s]*(.+?)(?:\n\s*\n|Nutritio|Allergen|Net\s+Qty|$)",
    re.IGNORECASE | re.DOTALL,
)

# Veg / non-veg keyword marker
_VEG_RE = re.compile(r"\b(NON[-\s]?VEG(?:etarian)?|VEG(?:etarian)?)\b", re.IGNORECASE)

# Manufacturer / packer address — everything after known keyword until next section
_MANUFACTURER_RE = re.compile(
    r"(?:Manufactured\s+By|Packed\s+By|Marketed\s+By|Importer)[:\s]*(.+?)(?:\n\s*\n|FSSAI|Ingredients|Net\s+Qty|$)",
    re.IGNORECASE | re.DOTALL,
)

# ── Nutrient table patterns ───────────────────────────────────────────────────

_ENERGY_RE = re.compile(
    r"Energy[^:\n]*[:\s]+(\d+\.?\d*)\s*(?:kcal|kJ|Cal)",
    re.IGNORECASE,
)
_SUGARS_RE = re.compile(
    r"(?:Total\s+)?Sugars?[^:\n]*[:\s]+(\d+\.?\d*)\s*g",
    re.IGNORECASE,
)
_SAT_FAT_RE = re.compile(
    r"Saturated\s+Fatty?\s*Acids?[^:\n]*[:\s]+(\d+\.?\d*)\s*g",
    re.IGNORECASE,
)
_SODIUM_RE = re.compile(
    r"Sodium[^:\n]*[:\s]+(\d+\.?\d*)\s*mg",
    re.IGNORECASE,
)
_FIBER_RE = re.compile(
    r"(?:Dietary\s+)?Fibre?[^:\n]*[:\s]+(\d+\.?\d*)\s*g",
    re.IGNORECASE,
)
_PROTEIN_RE = re.compile(
    r"Protein[^:\n]*[:\s]+(\d+\.?\d*)\s*g",
    re.IGNORECASE,
)


# ── Public helpers ────────────────────────────────────────────────────────────

def _first_match(pattern: re.Pattern, text: str, group: int = 1) -> Optional[str]:
    """Return the first capture group of a pattern match, or None."""
    m = pattern.search(text)
    return m.group(group).strip() if m else None


def _float_or_none(value: Optional[str]) -> Optional[float]:
    """Parse a string to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def extract_all_fields(text: str) -> dict:
    """
    Extract all structured label fields from a text string.

    Works on both OCR-produced text and user-typed description text.
    Returns a dict with keys matching the rule engine's expected field names.
    Nutrient values are floats or None; all other values are strings or None.
    """
    return {
        # Compliance fields
        "fssai_license_number": _first_match(_FSSAI_RE, text),
        "net_quantity": _first_match(_NET_QTY_RE, text, group=0),
        "mrp": _first_match(_MRP_RE, text) or _first_match(_MRP_RUPEE_RE, text),
        "manufacture_date": _first_match(_MFG_DATE_RE, text),
        "best_before_date": _first_match(_BEST_BEFORE_RE, text),
        "consumer_care": _first_match(_CONSUMER_CARE_RE, text),
        "product_name": (
            _first_match(_PRODUCT_NAME_RE, text)
            or _first_match(_FIRST_LINE_RE, text)
        ),
        "ingredients_list": _first_match(_INGREDIENTS_RE, text),
        "veg_nonveg_symbol": _first_match(_VEG_RE, text, group=0),
        "manufacturer_address": _first_match(_MANUFACTURER_RE, text),
        # Nutrient fields (float or None)
        "energy_kcal": _float_or_none(_first_match(_ENERGY_RE, text)),
        "sugars_g": _float_or_none(_first_match(_SUGARS_RE, text)),
        "saturated_fat_g": _float_or_none(_first_match(_SAT_FAT_RE, text)),
        "sodium_mg": _float_or_none(_first_match(_SODIUM_RE, text)),
        "fiber_g": _float_or_none(_first_match(_FIBER_RE, text)),
        "protein_g": _float_or_none(_first_match(_PROTEIN_RE, text)),
    }
