"""
FastAPI Microservice for Health Rating Prediction.
Exposes POST /predict matching the Section 3.6 contract.
"""

from typing import Dict, List, Optional
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from service.inference import predict

app = FastAPI(
    title="Health Rating ML Service",
    description="Open Food Facts–trained ML service predicting product health grades and qualitative advice.",
    version="1.0.0",
)

# CORS Middleware: While the architecture specifies backend-to-ML server-to-server calls,
# CORS is enabled for manual testing and local developer convenience.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NutrientsPer100g(BaseModel):
    energy_kcal: Optional[float] = Field(default=None, description="Energy in kcal per 100g")
    sugars_g: Optional[float] = Field(default=None, description="Sugars in grams per 100g")
    saturated_fat_g: Optional[float] = Field(default=None, description="Saturated fat in grams per 100g")
    sodium_mg: Optional[float] = Field(default=None, description="Sodium in milligrams per 100g")
    fiber_g: Optional[float] = Field(default=None, description="Dietary fiber in grams per 100g")
    protein_g: Optional[float] = Field(default=None, description="Protein in grams per 100g")


class IngredientFlags(BaseModel):
    contains_palm_oil: Optional[bool] = Field(default=False, description="Detected palm oil flag")
    contains_trans_fat: Optional[bool] = Field(default=False, description="Detected trans fat flag")
    contains_added_sugar: Optional[bool] = Field(default=False, description="Detected added sugar flag")
    contains_artificial_sweetener: Optional[bool] = Field(default=False, description="Detected artificial sweetener flag")
    contains_artificial_color: Optional[bool] = Field(default=False, description="Detected artificial color flag")
    contains_preservative: Optional[bool] = Field(default=False, description="Detected preservative flag")


class PredictRequest(BaseModel):
    nutrients_per_100g: Optional[NutrientsPer100g] = Field(
        default_factory=NutrientsPer100g,
        description="Nutritional values per 100g. Any field may be null/omitted.",
    )
    ingredient_flags: Optional[IngredientFlags] = Field(
        default_factory=IngredientFlags,
        description="Boolean ingredient taxonomy flags. Any flag may be omitted (defaults to false).",
    )


class PredictResponse(BaseModel):
    grade: str = Field(..., description="Nutri-Score style letter grade (A, B, C, D, E)")
    flagged_ingredients: List[str] = Field(
        ..., description="List of detected ingredient concerns"
    )
    advice: str = Field(
        ..., description="Explainable, qualitative consumption guidance"
    )


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Service liveness and health endpoint."""
    return {"status": "ok", "service": "health-rating-ml-service"}


@app.post("/predict", response_model=PredictResponse, status_code=status.HTTP_200_OK)
def predict_health_rating(payload: PredictRequest):
    """
    Predicts product health grade (A-E) and qualitative advice from nutrient profile and ingredient flags.
    """
    nutrients_dict = payload.nutrients_per_100g.model_dump() if payload.nutrients_per_100g else {}
    flags_dict = payload.ingredient_flags.model_dump() if payload.ingredient_flags else {}

    result = predict(
        nutrients_per_100g=nutrients_dict,
        ingredient_flags=flags_dict,
    )

    return PredictResponse(**result)
