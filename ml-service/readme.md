# Health Rating ML Service

Standalone FastAPI microservice that computes Nutri-Score-style health grades (A–E) and qualitative consumption advice for packaged food products. The underlying model is trained on authentic data from **Open Food Facts**.

---

## 1. Architecture & Service Role

```
[ Frontend (Next.js) ]
        │
        │  POST /api/analyze  (multipart: image + description)
        ▼
[ Backend (FastAPI - Teammate) ]
   - OCR & text parsing
   - Legal Metrology & FSSAI rule engine
        │
        │  POST /predict  (JSON: nutrients + ingredient flags)
        ▼
[ ML Service (FastAPI - Port 8001) ]
   - Health Rating Classifier (Random Forest with class balancing)
   - Median Imputation Engine
   - Qualitative Advice Engine
```

The ML module is an **independently runnable FastAPI service** communicating exclusively via HTTP (`POST /predict`), ensuring zero cross-codebase coupling.

---

## 2. Dataset & Feature Engineering

### 2.1 Authentic Open Food Facts Ingestion
- **Source**: Official Open Food Facts S3 dataset export (`en.openfoodfacts.org.products.csv.gz`).
- **Composition**: Blended dataset prioritizing India-tagged products (`countries_tags` containing `india` / `en:india`) supplemented by global products across all 5 Nutri-Score grades (A, B, C, D, E).
- **Quality Filtering**: Discarded records missing >50% core nutrient fields or lacking verified Nutri-Score labels. Total authentic dataset size: **8,000 products**.

### 2.2 Feature Contract (`training/features.py`)

#### Numeric Features (`nutrients_per_100g`):
```python
FEATURE_ORDER = [
    "energy_kcal",
    "sugars_g",
    "saturated_fat_g",
    "sodium_mg",
    "fiber_g",
    "protein_g",
]
```

#### Boolean Features (`ingredient_flags`):
Derived from Open Food Facts taxonomy tags (`ingredients_analysis_tags`, `additives_tags`, `ingredients_tags`):
```python
FLAG_ORDER = [
    "contains_palm_oil",
    "contains_trans_fat",
    "contains_added_sugar",
    "contains_artificial_sweetener",
    "contains_artificial_color",
    "contains_preservative",
]
```

### 2.3 Missing Value Imputation Strategy
- **Nutrients**: If a nutrient field is missing (`null` or omitted due to OCR incompleteness), the system imputes the **training-set median** saved in `model/medians.json`.
- **Ingredient Flags**: Omitted flags default to `False` (not detected).

---

## 3. Model Architecture & Evaluation Metrics

- **Algorithm**: `RandomForestClassifier(n_estimators=200, max_depth=12, class_weight='balanced', random_state=42)`
- **Class Imbalance Mitigation**: Weighted sample penalties counteract typical e-commerce skew toward middle grades (C/D) and ensure robust sensitivity on minority grades (A, E).
- **Train/Test Split**: 80% Train (6,400 samples) / 20% Test (1,600 samples) stratified on grade.

### 3.1 Performance Summary (Cited for Project Report & Viva)

| Metric | Score |
|---|---|
| **Overall Accuracy** | **80.25%** |
| **Macro F1-Score** | **79.42%** |
| **Weighted F1-Score** | **80.43%** |

### 3.2 Per-Class Breakdown

| Nutri-Score Grade | Precision | Recall | F1-Score | Test Support |
|---|---|---|---|---|
| **Grade A** | 84.1% | 83.4% | **83.7%** | 253 |
| **Grade B** | 61.3% | 74.2% | **67.1%** | 198 |
| **Grade C** | 82.5% | 75.1% | **78.6%** | 397 |
| **Grade D** | 79.8% | 82.2% | **81.0%** | 381 |
| **Grade E** | 88.5% | 84.9% | **86.7%** | 371 |

### 3.3 Confusion Matrix (5x5)

```
                     PREDICTED GRADE
                A      B      C      D      E
  True A      [211]    31      7      3      1
  True B        19   [147]    24      6      2
  True C        10     58   [298]    27      4
  True D         7      2     25   [313]    34
  True E         4      2      7     43   [315]
```

---

## 4. API Specification

### Endpoint: `POST /predict`

#### Request Payload:
```json
{
  "nutrients_per_100g": {
    "energy_kcal": 520,
    "sugars_g": 28,
    "saturated_fat_g": 12,
    "sodium_mg": 450,
    "fiber_g": 2,
    "protein_g": 6
  },
  "ingredient_flags": {
    "contains_palm_oil": true,
    "contains_trans_fat": false,
    "contains_added_sugar": true,
    "contains_artificial_sweetener": false,
    "contains_artificial_color": false,
    "contains_preservative": true
  }
}
```

#### Response Payload:
```json
{
  "grade": "D",
  "flagged_ingredients": [
    "contains_palm_oil",
    "contains_added_sugar",
    "contains_preservative"
  ],
  "advice": "High in saturated palm oil, high in added sugars / syrups, contains synthetic chemical preservatives — better suited as an occasional item than a daily staple."
}
```

---

## 5. Local Setup & Execution Guide

### 5.1 Environment Setup
```bash
cd ml-service

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5.2 Reproduce Data Processing & Training
```bash
# 1. Stream & process authentic Open Food Facts dataset
python -m training.prepare_data

# 2. Train model & generate evaluation report
python -m training.train
```

### 5.3 Run Automated Tests
```bash
pytest tests/ -v
```

### 5.4 Launch FastAPI Inference Service
```bash
uvicorn service.main:app --host 0.0.0.0 --port 8001 --reload
```

Interactive Swagger API docs available at: `http://localhost:8001/docs`
