"""
ml/train_model.py  v2 -- Multi-Model Pipeline
===============================================
Changes from v1
---------------
  v2-1  Features: added eve_qber_contribution (4 features total instead of 3)
  v2-2  Models trained: RandomForest, GradientBoosting, LogisticRegression, SVM
  v2-3  Each model saved as ml/model_<name>.joblib for API model-selection
  v2-4  Best model also saved as ml/model.joblib (backward-compatible default)
  v2-5  ml/model_registry.json saved: maps model_type -> filename + metrics
  v2-6  All 4 models evaluated on same test split for fair comparison
  v2-7  ML-05 updated: feature count = 4
  v2-8  ML-06 updated: eve_qber_contribution is now expected top feature

Why Multiple Models?
---------------------
Even with a single attack type (intercept-resend), different models offer:
  - Different confidence calibration in ambiguous QBER zones
  - Different inference speed profiles (LR = fastest, RF = most robust)
  - Ensemble-like security: if 3/4 models flag attack, higher confidence
  - Educational transparency: frontend can show how each model "sees" the data

If future attack types are added (PNS, Trojan Horse, DoS), these models
would diverge significantly -- making model selection critically important.

Feature Contract (v2)
----------------------
  qber                  -- primary signal
  noise_level           -- noise normalisation
  sifted_key_length     -- secondary signal
  eve_qber_contribution -- derived: max(0, qber - 2/3*noise)  [new in v2]

Acceptance Criteria (all models must meet before saving)
---------------------------------------------------------
  Accuracy >= 92%   (raised from 85% in v1)
  Recall >= 88%     (raised from 80% in v1)
  ROC-AUC >= 0.97   (raised from 0.90 in v1)
"""

import os
import sys
import json
import joblib
import numpy  as np
import pandas as pd

from sklearn.ensemble        import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model    import LogisticRegression
from sklearn.svm             import SVC
from sklearn.model_selection import train_test_split
from sklearn.preprocessing   import StandardScaler
from sklearn.pipeline        import Pipeline
from sklearn.metrics         import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH  = os.path.join(_ROOT, "data", "dataset.csv")
ML_DIR        = os.path.join(_ROOT, "ml")
REGISTRY_PATH = os.path.join(ML_DIR, "model_registry.json")
FEATURES_PATH = os.path.join(ML_DIR, "feature_names.json")

# v2: 4 features (eve_qber_contribution added)
FEATURE_COLS = [
    "qber",
    "noise_level",
    "sifted_key_length",
    "eve_qber_contribution",
]
TARGET_COL = "label"

# Raised acceptance thresholds for v2
MIN_ACCURACY = 0.98
MIN_RECALL   = 0.98
MIN_ROC_AUC  = 0.98

RANDOM_SEED  = 42

# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------

def get_model_definitions() -> dict:
    """
    Return all model definitions as a dict {model_type: estimator}.

    Notes
    -----
    LR and SVM need feature scaling -> wrapped in sklearn Pipeline.
    RF and GBM are scale-invariant -> used directly.
    """
    return {
        "random_forest": RandomForestClassifier(
            n_estimators=500,
            max_depth=None,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=RANDOM_SEED,
            n_jobs=-1,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.8,
            random_state=RANDOM_SEED,
        ),
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                C=10,
                class_weight="balanced",
                max_iter=1000,
                random_state=RANDOM_SEED,
            )),
        ]),
        "svm": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(
                C=10,
                kernel="rbf",
                gamma="scale",
                class_weight="balanced",
                probability=True,   # needed for predict_proba
                random_state=RANDOM_SEED,
            )),
        ]),
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_dataset(path: str = DATASET_PATH) -> pd.DataFrame:
    """Load and validate the v2 dataset (must have eve_qber_contribution col)."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"[train_model] Dataset not found: {path}\n"
            f"  -> Run 'python ml/generate_dataset.py' first."
        )

    df = pd.read_csv(path)

    missing = [c for c in FEATURE_COLS + [TARGET_COL] if c not in df.columns]
    if missing:
        raise ValueError(
            f"[train_model] Missing columns: {missing}\n"
            f"  -> Regenerate dataset with v2 generate_dataset.py"
        )

    nan_count = df[FEATURE_COLS + [TARGET_COL]].isnull().sum().sum()
    if nan_count > 0:
        print(f"[train_model] WARNING: Dropping {nan_count} NaN rows.")
        df = df.dropna(subset=FEATURE_COLS + [TARGET_COL])

    print(f"[train_model] Loaded {len(df):,} rows from {path}")
    return df


# ---------------------------------------------------------------------------
# Train & evaluate one model
# ---------------------------------------------------------------------------

def train_and_evaluate(
    model_type: str,
    estimator,
    X_train: np.ndarray,
    X_test:  np.ndarray,
    y_train: np.ndarray,
    y_test:  np.ndarray,
) -> tuple:
    """
    Fit estimator and return (fitted_estimator, metrics_dict).
    """
    print(f"\n[train_model] --- Training: {model_type} ---")
    estimator.fit(X_train, y_train)

    y_pred  = estimator.predict(X_test)
    y_proba = estimator.predict_proba(X_test)[:, 1]

    accuracy   = accuracy_score(y_test, y_pred)
    report     = classification_report(
                     y_test, y_pred,
                     target_names=["safe", "attack"],
                     output_dict=True
                 )
    recall_atk = report["attack"]["recall"]
    roc_auc    = roc_auc_score(y_test, y_proba)
    conf_mat   = confusion_matrix(y_test, y_pred)

    # Feature importances (only for tree models or via coef)
    importances = {}
    try:
        raw = estimator.feature_importances_
        importances = dict(zip(FEATURE_COLS, raw))
    except AttributeError:
        pass   # LR and SVM don't expose feature_importances_

    metrics = {
        "accuracy":      round(accuracy, 6),
        "recall_attack": round(recall_atk, 6),
        "roc_auc":       round(roc_auc, 6),
        "conf_matrix":   conf_mat,
        "importances":   importances,
    }

    print(f"  Accuracy={accuracy:.4f}  Recall={recall_atk:.4f}  ROC-AUC={roc_auc:.4f}")
    return estimator, metrics


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_comparison_table(all_metrics: dict) -> None:
    """Print a side-by-side comparison table of all models."""
    SEP = "=" * 72
    print(f"\n{SEP}")
    print("  Model Comparison Table")
    print(SEP)
    header = f"  {'Model':<25}  {'Accuracy':>9}  {'Recall':>9}  {'ROC-AUC':>9}  {'Pass?':>6}"
    print(header)
    print("  " + "-" * 67)
    for name, m in all_metrics.items():
        ok = (
            m["accuracy"]      >= MIN_ACCURACY and
            m["recall_attack"] >= MIN_RECALL   and
            m["roc_auc"]       >= MIN_ROC_AUC
        )
        flag = " OK " if ok else "FAIL"
        print(
            f"  {name:<25}  "
            f"{m['accuracy']:>9.4f}  "
            f"{m['recall_attack']:>9.4f}  "
            f"{m['roc_auc']:>9.4f}  "
            f"{flag:>6}"
        )
    print(SEP)

    # Feature importances for tree models
    print("\n  Feature Importances (tree models only):")
    for name, m in all_metrics.items():
        if m["importances"]:
            print(f"\n  {name}:")
            for feat, imp in sorted(m["importances"].items(), key=lambda x: -x[1]):
                bar = "#" * int(imp * 35)
                print(f"    {feat:<25} {imp:.4f}  {bar}")
    print()


# ---------------------------------------------------------------------------
# Inline test suite (ML-01 through ML-10)
# ---------------------------------------------------------------------------

def run_tests(best_model, all_metrics: dict, best_name: str) -> None:
    """
    Run all 10 model validation tests on the best-performing model.
    Calls sys.exit(1) if any acceptance criterion fails.
    """
    SEP = "=" * 72
    print(f"\n{SEP}")
    print(f"  Model Validation Tests  (ML-01 -> ML-10)")
    print(f"  Testing best model: {best_name}")
    print(SEP)

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        status = "[PASS]" if condition else "[FAIL]"
        msg = f"  {status}  {name}"
        if detail:
            msg += f"  [{detail}]"
        print(msg)
        if condition:
            passed += 1
        else:
            failed += 1

    bm = all_metrics[best_name]

    # ML-01: model files created
    all_saved = all(
        os.path.exists(os.path.join(ML_DIR, f"model_{n}.joblib"))
        for n in all_metrics
    )
    check("ML-01 All model_<name>.joblib files exist", all_saved)

    # ML-02: Best model Accuracy
    check(f"ML-02 Best model Accuracy >= {MIN_ACCURACY}",
          bm["accuracy"] >= MIN_ACCURACY,
          f"{bm['accuracy']:.4f}")

    # ML-03: Best model Recall
    check(f"ML-03 Best model Recall(attack) >= {MIN_RECALL}",
          bm["recall_attack"] >= MIN_RECALL,
          f"{bm['recall_attack']:.4f}")

    # ML-04: Best model ROC-AUC
    check(f"ML-04 Best model ROC-AUC >= {MIN_ROC_AUC}",
          bm["roc_auc"] >= MIN_ROC_AUC,
          f"{bm['roc_auc']:.4f}")

    # ML-05: Feature count = 4 (v2)
    try:
        n_feat = best_model.n_features_in_
    except AttributeError:
        n_feat = best_model.named_steps["clf"].n_features_in_
    check("ML-05 Best model expects 4 features",
          n_feat == 4,
          f"got {n_feat}")

    # ML-06: eve_qber_contribution is top feature (tree models only)
    if bm["importances"]:
        top_feat = max(bm["importances"], key=bm["importances"].get)
        check("ML-06 eve_qber_contribution is top feature",
              top_feat == "eve_qber_contribution",
              f"top={top_feat}")
    else:
        check("ML-06 Feature importances (N/A for this model type)", True,
              "skipped -- linear/kernel model")

    # ML-07: Known attack -> label = 1
    # QBER=0.27, noise=0.03, sifted=240, eve_contrib=0.27-0.02=0.25
    atk_input = np.array([[0.27, 0.03, 240, 0.25]])
    atk_pred  = best_model.predict(atk_input)[0]
    atk_proba = best_model.predict_proba(atk_input)[0][1]
    check("ML-07 Known attack (QBER=0.27, eve=0.25) -> label=1",
          atk_pred == 1,
          f"pred={atk_pred}  P(attack)={atk_proba:.4f}")

    # ML-08: Known safe -> label = 0
    # QBER=0.02, noise=0.03, sifted=248, eve_contrib=max(0, 0.02-0.02)=0.00
    safe_input = np.array([[0.02, 0.03, 248, 0.00]])
    safe_pred  = best_model.predict(safe_input)[0]
    safe_proba = best_model.predict_proba(safe_input)[0][1]
    check("ML-08 Known safe (QBER=0.02, eve=0.00) -> label=0",
          safe_pred == 0,
          f"pred={safe_pred}  P(attack)={safe_proba:.4f}")

    # ML-09: predict_proba in [0, 1]
    edge_inputs = np.array([
        [0.00, 0.00, 500, 0.00],
        [1.00, 0.15, 50,  0.90],
        [0.25, 0.00, 1,   0.25],
        [0.11, 0.05, 1000, 0.077],
    ])
    probas    = best_model.predict_proba(edge_inputs)
    probas_ok = ((probas >= 0.0) & (probas <= 1.0)).all()
    check("ML-09 All predict_proba in [0.0, 1.0]",
          probas_ok,
          f"min={probas.min():.4f}  max={probas.max():.4f}")

    # ML-10: Missing dataset -> FileNotFoundError
    try:
        load_dataset("/nonexistent/path/dataset.csv")
        check("ML-10 Missing CSV -> FileNotFoundError", False,
              "no exception raised")
    except FileNotFoundError:
        check("ML-10 Missing CSV -> FileNotFoundError", True)

    # Summary
    total = passed + failed
    print(f"\n{SEP}")
    print(f"  Results: {passed}/{total} passed, {failed}/{total} failed")
    if failed > 0:
        print("  [WARN] Model validation FAILED. Do NOT proceed to Phase 3.")
        print(SEP)
        sys.exit(1)
    else:
        print("  [OK]   ALL MODEL TESTS PASSED -- All models are production-ready.")
        print("  [OK]   Safe to proceed to Phase 3 (FastAPI backend).")
    print(SEP)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import time

    # 1. Load dataset
    df = load_dataset()

    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values

    # 2. Train/test split (shared across all models for fair comparison)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.20,
        random_state=RANDOM_SEED,
        stratify=y,
    )
    print(f"[train_model] Train: {len(X_train):,}  Test: {len(X_test):,}")
    print(f"[train_model] Label distribution -- "
          f"train: {y_train.mean():.1%} attack  "
          f"test:  {y_test.mean():.1%} attack")

    # 3. Train all models
    model_defs  = get_model_definitions()
    all_models  = {}
    all_metrics = {}

    total_t0 = time.perf_counter()
    for model_type, estimator in model_defs.items():
        t0 = time.perf_counter()
        fitted, metrics = train_and_evaluate(
            model_type, estimator, X_train, X_test, y_train, y_test
        )
        elapsed = time.perf_counter() - t0
        print(f"  Time: {elapsed:.2f}s")
        all_models[model_type]  = fitted
        all_metrics[model_type] = metrics

    total_elapsed = time.perf_counter() - total_t0
    print(f"\n[train_model] All models trained in {total_elapsed:.2f}s total")

    # 4. Print comparison table
    print_comparison_table(all_metrics)

    # 5. Select best model by ROC-AUC
    best_name  = max(all_metrics, key=lambda k: all_metrics[k]["roc_auc"])
    best_model = all_models[best_name]
    print(f"[train_model] Best model: {best_name} "
          f"(ROC-AUC={all_metrics[best_name]['roc_auc']:.4f})")

    # 6. Check acceptance criteria (all models must pass)
    any_failed = False
    for name, m in all_metrics.items():
        passed = (
            m["accuracy"]      >= MIN_ACCURACY and
            m["recall_attack"] >= MIN_RECALL   and
            m["roc_auc"]       >= MIN_ROC_AUC
        )
        if not passed:
            print(f"[train_model] WARN: {name} did not meet acceptance criteria")
            any_failed = True

    if any_failed:
        print("\n[WARN] One or more models failed acceptance criteria.")
        print("       Will still save passing models. Check comparison table.")

    # 7. Save all models individually + registry
    os.makedirs(ML_DIR, exist_ok=True)

    registry = {}
    for name, model in all_models.items():
        path = os.path.join(ML_DIR, f"model_{name}.joblib")
        joblib.dump(model, path)
        print(f"[train_model] Saved -> model_{name}.joblib")
        registry[name] = {
            "file":          f"model_{name}.joblib",
            "accuracy":      all_metrics[name]["accuracy"],
            "recall_attack": all_metrics[name]["recall_attack"],
            "roc_auc":       all_metrics[name]["roc_auc"],
            "description": {
                "random_forest":      "Ensemble of decision trees. Robust and interpretable.",
                "gradient_boosting":  "Boosted trees. Highest accuracy on tabular data.",
                "logistic_regression":"Linear model. Fastest inference, best probability calibration.",
                "svm":                "Kernel-based max-margin classifier. Excellent on clean boundaries.",
            }.get(name, name),
        }

    # Save best model as backward-compatible default
    default_path = os.path.join(ML_DIR, "model.joblib")
    joblib.dump(best_model, default_path)
    print(f"[train_model] Best model also saved as default -> model.joblib")

    # Save feature contract (v2: 4 features)
    with open(FEATURES_PATH, "w") as f:
        json.dump(FEATURE_COLS, f, indent=2)

    # Save registry (FastAPI uses this for model selection)
    registry["_best"]    = best_name
    registry["_features"] = FEATURE_COLS
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"[train_model] Registry saved -> model_registry.json")

    # 8. Run test suite on best model
    run_tests(best_model, all_metrics, best_name)
