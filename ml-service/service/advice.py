"""
Qualitative health advice generator based on predicted grade and ingredient flags.
Mirrors front-of-pack labeling systems (e.g. Nutri-Score & India's proposed labeling guidelines)
by providing qualitative risk bands and explainable ingredient attributions.
"""

from typing import List, Dict, Optional

# Human-readable phrasing for flags in qualitative advice
FLAG_EXPLANATIONS: Dict[str, str] = {
    "contains_palm_oil": "high in saturated palm oil",
    "contains_trans_fat": "contains industrial trans fats",
    "contains_added_sugar": "high in added sugars / syrups",
    "contains_artificial_sweetener": "contains non-nutritive artificial sweeteners",
    "contains_artificial_color": "contains synthetic artificial food dyes",
    "contains_preservative": "contains synthetic chemical preservatives",
}


def generate_advice(
    grade: str,
    flagged_ingredients: List[str],
    nutrients_per_100g: Optional[Dict[str, Optional[float]]] = None,
) -> str:
    """
    Constructs explainable, qualitative consumption advice matching Section 3.7 rules.
    Never prescribes numeric frequencies (e.g. 'eat 2 times a month').
    """
    grade = grade.upper().strip()
    nutrients = nutrients_per_100g or {}

    # Extract driving concerns
    concerns: List[str] = []

    for flag in flagged_ingredients:
        if flag in FLAG_EXPLANATIONS:
            concerns.append(FLAG_EXPLANATIONS[flag])

    # Check high nutrient thresholds if provided
    sat_fat = nutrients.get("saturated_fat_g")
    if sat_fat is not None and sat_fat >= 5.0 and "contains_palm_oil" not in flagged_ingredients:
        concerns.append("elevated saturated fat content")

    sugars = nutrients.get("sugars_g")
    if sugars is not None and sugars >= 15.0 and "contains_added_sugar" not in flagged_ingredients:
        concerns.append("high sugar content")

    sodium = nutrients.get("sodium_mg")
    if sodium is not None and sodium >= 600.0:
        concerns.append("high sodium levels")

    # Tone mapping based on Grade
    if grade in {"A", "B"}:
        if not concerns:
            return "A reasonably healthy choice for regular consumption."
        else:
            concerns_str = ", ".join(concerns)
            return f"A reasonably healthy choice for regular consumption, though noted for {concerns_str}."

    elif grade == "C":
        if not concerns:
            return "A moderate choice — fine in your regular rotation, not a primary staple."
        else:
            concerns_str = ", ".join(concerns)
            return f"A moderate choice — fine in your regular rotation, not a primary staple (noted for {concerns_str})."

    else:  # D or E
        if concerns:
            # Capitalize first letter of combined concerns
            concerns_str = ", ".join(concerns)
            concerns_str = concerns_str[0].upper() + concerns_str[1:]
            return f"{concerns_str} — better suited as an occasional item than a daily staple."
        else:
            return "Higher in energy density or refined nutrients — better suited as an occasional item than a daily staple."
