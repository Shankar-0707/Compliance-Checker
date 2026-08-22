"""
Feature definitions and data transformation pipelines for Health Rating ML Model.
This module is the SINGLE SOURCE OF TRUTH for feature order and extraction logic,
shared across both offline training and online inference.
"""

from typing import Dict, List, Optional, Any
import numpy as np

# Exact numeric nutrient features contract (per 100g)
FEATURE_ORDER: List[str] = [
    "energy_kcal",
    "sugars_g",
    "saturated_fat_g",
    "sodium_mg",
    "fiber_g",
    "protein_g",
]

# Exact boolean ingredient / additive flag features contract
FLAG_ORDER: List[str] = [
    "contains_palm_oil",
    "contains_trans_fat",
    "contains_added_sugar",
    "contains_artificial_sweetener",
    "contains_artificial_color",
    "contains_preservative",
]

# Combined feature list used by model estimators
ALL_FEATURES: List[str] = FEATURE_ORDER + FLAG_ORDER


def build_feature_vector(
    nutrients_per_100g: Optional[Dict[str, Optional[float]]],
    ingredient_flags: Optional[Dict[str, Optional[bool]]],
    medians: Dict[str, float],
) -> np.ndarray:
    """
    Constructs a 1D numpy feature vector in exact ALL_FEATURES order.
    
    Missing value handling:
    - If a nutrient value is None / absent, substitute training median.
    - If an ingredient flag is None / absent, default to False (0.0).
    """
    nutrients = nutrients_per_100g or {}
    flags = ingredient_flags or {}

    vector: List[float] = []

    # 1. Numeric features with median imputation
    for feat in FEATURE_ORDER:
        val = nutrients.get(feat)
        if val is None or not isinstance(val, (int, float)) or np.isnan(val):
            # Impute median
            imputed_val = medians.get(feat, 0.0)
            vector.append(float(imputed_val))
        else:
            # Clip non-negative
            vector.append(float(max(0.0, float(val))))

    # 2. Boolean flag features (default False / 0.0)
    for flag in FLAG_ORDER:
        val = flags.get(flag)
        if val is True:
            vector.append(1.0)
        else:
            vector.append(0.0)

    import pandas as pd
    return pd.DataFrame([vector], columns=ALL_FEATURES)
