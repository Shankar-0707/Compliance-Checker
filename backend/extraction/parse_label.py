"""
extraction/parse_label.py
─────────────────────────
Parses OCR-extracted raw text (from a label image) into structured fields.

This module is a thin wrapper around the shared ``extract_all_fields()``
helper in ``_patterns.py`` — it exists as a separate file so its
counterpart (parse_description.py) is symmetric and the code is self-documenting.

Usage:
    ocr_fields = parse_label_text(raw_ocr_text)
"""

from extraction._patterns import extract_all_fields


def parse_label_text(raw_text: str) -> dict:
    """
    Parse OCR raw text into a structured field dictionary.

    Parameters
    ----------
    raw_text : str
        Concatenated text output from ``ocr.extract_text()``.

    Returns
    -------
    dict
        Keys: fssai_license_number, net_quantity, mrp, manufacture_date,
              best_before_date, consumer_care, product_name, ingredients_list,
              veg_nonveg_symbol, manufacturer_address,
              energy_kcal, sugars_g, saturated_fat_g, sodium_mg, fiber_g,
              protein_g.
        All values are ``str | None`` for text fields and ``float | None``
        for nutrient fields.
    """
    return extract_all_fields(raw_text)
