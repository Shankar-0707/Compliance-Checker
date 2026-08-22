"""
Model training and evaluation pipeline for Health Rating Prediction.

- Stratified 80/20 Train/Test split.
- Computes training-set nutrient medians for missing value imputation.
- Implements class imbalance mitigation via balanced class weights.
- Evaluates Accuracy, Macro F1, Per-Class Precision/Recall/F1, and Confusion Matrix.
- Serializes trained model to model/health_model.pkl and medians to model/medians.json.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    classification_report,
    confusion_matrix,
)

# Ensure parent directory is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
ML_DIR = SCRIPT_DIR.parent
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from training.features import FEATURE_ORDER, FLAG_ORDER, ALL_FEATURES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("train")

DATA_PATH = SCRIPT_DIR / "data" / "processed_off_data.csv"
MODEL_DIR = ML_DIR / "model"
MODEL_PATH = MODEL_DIR / "health_model.pkl"
MEDIANS_PATH = MODEL_DIR / "medians.json"
METRICS_PATH = MODEL_DIR / "metrics_report.json"


def load_and_preprocess_data(csv_path: Path) -> Tuple[pd.DataFrame, pd.Series]:
    """Loads CSV and extracts feature matrix X and label vector y."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Processed data file not found at {csv_path}. Please run `python -m training.prepare_data` first."
        )

    df = pd.read_csv(csv_path)
    logger.info(f"Loaded dataset with {len(df)} records from {csv_path}")

    # Ensure required columns exist
    missing_cols = [c for c in FEATURE_ORDER + FLAG_ORDER + ["nutriscore_grade"] if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in CSV: {missing_cols}")

    # Target variable
    y = df["nutriscore_grade"].str.upper().str.strip()

    # Features
    X = df[ALL_FEATURES].copy()

    return X, y


def train_and_evaluate():
    """Executes the complete training, imputation calculation, and evaluation pipeline."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    X, y = load_and_preprocess_data(DATA_PATH)

    # 1. Stratified 80/20 Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    logger.info(f"Train split size: {len(X_train)} samples, Test split size: {len(X_test)} samples")

    # 2. Compute Training-set Nutrient Medians for Imputation
    medians: Dict[str, float] = {}
    for feat in FEATURE_ORDER:
        median_val = float(X_train[feat].median())
        medians[feat] = round(median_val, 2)

    logger.info(f"Computed Training Medians for Imputation: {medians}")

    # Save medians.json
    with open(MEDIANS_PATH, "w", encoding="utf-8") as f:
        json.dump(medians, f, indent=2)
    logger.info(f"Saved medians to: {MEDIANS_PATH}")

    # 3. Impute missing values in train and test sets using training medians
    X_train_clean = X_train.copy()
    X_test_clean = X_test.copy()

    for feat in FEATURE_ORDER:
        X_train_clean[feat] = X_train_clean[feat].fillna(medians[feat])
        X_test_clean[feat] = X_test_clean[feat].fillna(medians[feat])

    for flag in FLAG_ORDER:
        X_train_clean[flag] = X_train_clean[flag].fillna(False).astype(float)
        X_test_clean[flag] = X_test_clean[flag].fillna(False).astype(float)

    # 4. Train Multi-Class Classifier with Class Imbalance Weighting
    logger.info("Training Class-Balanced Random Forest / Gradient Boosting Classifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_split=4,
        class_weight="balanced",  # Critical for addressing skewed grade distributions
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train_clean, y_train)

    # 5. Evaluate on Test Split
    y_pred = model.predict(X_test_clean)

    accuracy = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")
    weighted_f1 = f1_score(y_test, y_pred, average="weighted")

    classes = sorted(list(np.unique(y)))
    cm = confusion_matrix(y_test, y_pred, labels=classes)
    report_dict = classification_report(y_test, y_pred, labels=classes, output_dict=True)

    # Log Detailed Performance Metrics
    logger.info("=" * 60)
    logger.info("MODEL EVALUATION RESULTS (TEST SET):")
    logger.info(f"Overall Accuracy:  {accuracy * 100:.2f}%")
    logger.info(f"Macro F1-Score:    {macro_f1 * 100:.2f}%")
    logger.info(f"Weighted F1-Score: {weighted_f1 * 100:.2f}%")
    logger.info("-" * 60)
    logger.info("Per-Class Breakdown:")
    for c in classes:
        metrics = report_dict.get(c, {})
        p = float(metrics.get("precision", 0.0)) * 100
        r = float(metrics.get("recall", 0.0)) * 100
        f = float(metrics.get("f1-score", 0.0)) * 100
        support = int(metrics.get("support", 0))
        logger.info(f"  Grade {c}: Precision={p:5.1f}%, Recall={r:5.1f}%, F1={f:5.1f}% (Support: {support:4d})")
    
    logger.info("-" * 60)
    logger.info(f"Confusion Matrix (Rows=True, Cols=Predicted, Classes={classes}):")
    for idx, row in enumerate(cm):
        logger.info(f"  True {classes[idx]}: {list(row)}")
    logger.info("=" * 60)

    # 6. Save Model to model/health_model.pkl
    joblib.dump(model, MODEL_PATH)
    logger.info(f"Saved trained health model artifact to: {MODEL_PATH}")

    # 7. Save Metrics Summary to JSON for report generation
    metrics_summary = {
        "accuracy": round(float(accuracy), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "classes": classes,
        "confusion_matrix": cm.tolist(),
        "classification_report": report_dict,
        "medians": medians,
        "total_samples": len(X),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)

    return model, metrics_summary


if __name__ == "__main__":
    train_and_evaluate()
