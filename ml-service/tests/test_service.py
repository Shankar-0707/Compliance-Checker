"""
Unit and integration tests for Health Rating ML Service.
Verifies API contract adherence, median imputation for missing values,
defaulting of omitted boolean flags, and qualitative advice generation.
"""

import pytest
from fastapi.testclient import TestClient
from service.main import app
from service.advice import generate_advice
from service.inference import predict

client = TestClient(app)


def test_health_check():
    """Verify /health endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "health-rating-ml-service"}


def test_predict_full_payload():
    """Verify Section 3.6 exact request contract."""
    payload = {
        "nutrients_per_100g": {
            "energy_kcal": 520,
            "sugars_g": 28,
            "saturated_fat_g": 12,
            "sodium_mg": 450,
            "fiber_g": 2,
            "protein_g": 6,
        },
        "ingredient_flags": {
            "contains_palm_oil": True,
            "contains_trans_fat": False,
            "contains_added_sugar": True,
            "contains_artificial_sweetener": False,
            "contains_artificial_color": False,
            "contains_preservative": True,
        },
    }

    response = client.post("/predict", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "grade" in data
    assert data["grade"] in ["A", "B", "C", "D", "E"]
    assert "flagged_ingredients" in data
    assert isinstance(data["flagged_ingredients"], list)
    assert "contains_palm_oil" in data["flagged_ingredients"]
    assert "contains_added_sugar" in data["flagged_ingredients"]
    assert "contains_preservative" in data["flagged_ingredients"]
    assert "advice" in data
    assert isinstance(data["advice"], str)
    assert len(data["advice"]) > 10


def test_predict_missing_nutrients_imputation():
    """Verify null nutrient values are imputed with medians rather than crashing."""
    payload = {
        "nutrients_per_100g": {
            "energy_kcal": None,
            "sugars_g": None,
            "saturated_fat_g": 1.5,
            "sodium_mg": None,
            "fiber_g": 8.0,
            "protein_g": 12.0,
        },
        "ingredient_flags": {
            "contains_palm_oil": False,
        },
    }

    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["grade"] in ["A", "B", "C", "D", "E"]


def test_predict_omitted_flags_default_false():
    """Verify omitted ingredient flags default to false."""
    payload = {
        "nutrients_per_100g": {
            "energy_kcal": 350,
            "sugars_g": 2.0,
            "saturated_fat_g": 0.5,
            "sodium_mg": 10,
            "fiber_g": 10.0,
            "protein_g": 14.0,
        },
        "ingredient_flags": {},
    }

    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["flagged_ingredients"] == []


def test_advice_qualitative_rules():
    """Verify qualitative advice framing without numeric frequencies."""
    # Test Grade A healthy choice
    advice_a = generate_advice("A", [])
    assert "healthy choice for regular consumption" in advice_a
    assert "times a month" not in advice_a

    # Test Grade D occasional item
    advice_d = generate_advice("D", ["contains_palm_oil", "contains_added_sugar"])
    assert "occasional item than a daily staple" in advice_d
    assert "palm oil" in advice_d or "sugars" in advice_d
    assert "times a week" not in advice_d
