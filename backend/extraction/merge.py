"""
extraction/merge.py
───────────────────
Merges OCR-extracted fields and description-parsed fields into a single
authoritative ``extracted_fields`` dict for the compliance rule engine.

Merge strategy
--------------
- OCR value takes priority (it comes from the actual label image).
- If OCR value is None/empty, the description value is used as a fallback.
- If both sources provide a non-None value AND they differ → recorded as a
  contradiction (a helpful warning, not a compliance failure).

Usage:
    merged, contradictions = merge_fields(ocr_fields, desc_fields)
"""

from typing import Any


def _values_differ(a: Any, b: Any) -> bool:
    """
    Return True if two field values are meaningfully different.
    Normalises strings to lowercase + stripped for comparison.
    """
    if a is None or b is None:
        return False

    def norm(v: Any) -> str:
        return str(v).strip().lower()

    return norm(a) != norm(b)


def merge_fields(
    ocr_fields: dict,
    desc_fields: dict,
) -> tuple[dict, list[dict]]:
    """
    Merge OCR and description field dicts.

    Parameters
    ----------
    ocr_fields : dict
        Output of ``parse_label_text()``.
    desc_fields : dict
        Output of ``parse_description_text()``.

    Returns
    -------
    tuple[dict, list[dict]]
        - ``merged`` : Unified field dict (OCR priority, desc as fallback).
        - ``contradictions`` : List of dicts, each with keys:
              ``field``, ``ocr_value``, ``description_value``.
          Empty list when there are no disagreements.
    """
    all_keys = set(ocr_fields) | set(desc_fields)
    merged: dict = {}
    contradictions: list[dict] = []

    for key in all_keys:
        ocr_val = ocr_fields.get(key)
        desc_val = desc_fields.get(key)

        # OCR takes priority; fall back to description if OCR is empty/None
        if ocr_val is not None and str(ocr_val).strip():
            merged[key] = ocr_val
        elif desc_val is not None and str(desc_val).strip():
            merged[key] = desc_val
        else:
            merged[key] = None

        # Record contradiction if both sources non-None and differ
        if _values_differ(ocr_val, desc_val):
            contradictions.append(
                {
                    "field": key,
                    "ocr_value": ocr_val,
                    "description_value": desc_val,
                }
            )

    return merged, contradictions
