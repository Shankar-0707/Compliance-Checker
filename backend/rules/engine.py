"""
rules/engine.py
───────────────
Compliance rule engine.

Loads ``rules.json`` once at import time and exposes ``check_compliance()``,
which checks each rule against the merged extracted fields dict and returns
a list of pass/fail results with citations.

Usage:
    from rules.engine import check_compliance, RULES
    results = check_compliance(merged_fields)
"""

import json
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Load rules once ───────────────────────────────────────────────────────────
_RULES_PATH = Path(__file__).parent / "rules.json"

with _RULES_PATH.open(encoding="utf-8") as _f:
    RULES: list[dict] = json.load(_f)

logger.info("Loaded %d compliance rules from %s", len(RULES), _RULES_PATH)


def check_compliance(extracted_fields: dict, rules: list[dict] | None = None) -> list[dict]:
    """
    Check extracted label fields against each compliance rule.

    Parameters
    ----------
    extracted_fields : dict
        Merged output of OCR + description parsing (from ``merge.merge_fields()``).
    rules : list[dict] | None
        Rules list to use.  Defaults to the module-level ``RULES`` loaded from
        ``rules.json`` — override only in tests.

    Returns
    -------
    list[dict]
        One entry per rule, each with keys:
            ``field``    – rule field name
            ``passed``   – bool, True if the field is present and format-valid
            ``citation`` – regulation citation string

    Notes
    -----
    - ``pattern: null`` in a rule means a non-empty presence check only.
    - If a field is present in either OCR or description output (merged),
      it is counted as present.
    - The ``passed`` flag only reflects format/presence compliance — it does
      NOT carry semantic meaning about product safety.
    """
    if rules is None:
        rules = RULES

    results: list[dict] = []

    for rule in rules:
        field_name: str = rule["field"]
        pattern: str | None = rule.get("pattern")
        value = extracted_fields.get(field_name)

        # Determine pass/fail
        if value is None or str(value).strip() == "":
            passed = False
        elif pattern:
            try:
                passed = bool(re.search(pattern, str(value), re.IGNORECASE))
            except re.error as exc:
                logger.warning(
                    "Invalid regex pattern for field '%s': %s — treating as failed.",
                    field_name, exc,
                )
                passed = False
        else:
            # null pattern → presence check only
            passed = bool(str(value).strip())

        results.append(
            {
                "field": field_name,
                "passed": passed,
                "citation": rule.get("citation", ""),
            }
        )

    return results
