"""
extraction/parse_description.py
────────────────────────────────
Parses the user-typed product description text into the same structured fields
produced by ``parse_label.py``.

Uses the exact same regex patterns so OCR and description fields can be
meaningfully compared for contradictions in ``merge.py``.

Usage:
    desc_fields = parse_description_text(user_description)
"""

from extraction._patterns import extract_all_fields


def parse_description_text(description: str) -> dict:
    """
    Parse a free-text product description into a structured field dictionary.

    Parameters
    ----------
    description : str
        The ``description`` string received from the frontend multipart form.

    Returns
    -------
    dict
        Same schema as ``parse_label_text()`` output.
    """
    return extract_all_fields(description)
