"""
Inference engine for Health Rating Service.
Loads serialized model and imputation medians once at startup.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import joblib

from training.features import build_feature_vector, FLAG_ORDER
from service.advice import generate_advice

logger = logging.getLogger("inference")

SERVICE_DIR = Path(__file__).resolve().parent
ML_DIR = SERVICE_DIR.parent
MODEL_PATH = ML_DIR / "model" / "health_model.pkl"
MEDIANS_PATH = ML_DIR / "model" / "medians.json"


class HealthRatingInferenceEngine:
    """Singleton model loader and prediction coordinator."""

    def __init__(self):
        self.model = None
        self.medians: Dict[str, float] = {}
        self._load_artifacts()

    def _load_artifacts(self):
        # 1. Load Medians
        if MEDIANS_PATH.exists():
            with open(MEDIANS_PATH, "r", encoding="utf-8") as f:
                self.medians = json.load(f)
            logger.info(f"Loaded feature imputation medians from {MEDIANS_PATH}")
        else:
            logger.warning(f"Medians file not found at {MEDIANS_PATH}, using fallback zero medians.")
            self.medians = {}

        # 2. Load Model
        if MODEL_PATH.exists():
            self.model = joblib.load(MODEL_PATH)
            logger.info(f"Loaded trained health model from {MODEL_PATH}")
        else:
            logger.warning(f"Model file not found at {MODEL_PATH}.")
            self.model = None

    def predict(
        self,
        nutrients_per_100g: Optional[Dict[str, Optional[float]]] = None,
        ingredient_flags: Optional[Dict[str, Optional[bool]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes health rating inference on nutrient & ingredient flag payload.
        Imputes missing values with saved medians and generates qualitative advice.
        """
        nutrients = nutrients_per_100g or {}
        flags = ingredient_flags or {}

        # 1. Identify which ingredient flags were detected as True
        flagged_ingredients: List[str] = [
            flag for flag in FLAG_ORDER if flags.get(flag) is True
        ]

        # 2. Build feature vector with median imputation
        feature_vector = build_feature_vector(nutrients, flags, self.medians)

        # 3. Model Inference
        if self.model is not None:
            predicted_grade = str(self.model.predict(feature_vector)[0]).upper()
        else:
            # Fallback if model is not yet trained
            predicted_grade = "C"

        # 4. Generate Qualitative Advice
        advice_text = generate_advice(
            grade=predicted_grade,
            flagged_ingredients=flagged_ingredients,
            nutrients_per_100g=nutrients,
        )

        return {
            "grade": predicted_grade,
            "flagged_ingredients": flagged_ingredients,
            "advice": advice_text,
        }


# Instantiate singleton instance for fast reuse across requests
engine = HealthRatingInferenceEngine()


def predict(
    nutrients_per_100g: Optional[Dict[str, Optional[float]]] = None,
    ingredient_flags: Optional[Dict[str, Optional[bool]]] = None,
) -> Dict[str, Any]:
    """Convenience functional wrapper for engine prediction."""
    return engine.predict(nutrients_per_100g, ingredient_flags)
