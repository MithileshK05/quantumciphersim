"""
ml/inference.py
===============
Bridge layer between the trained ML models and the FastAPI backend.

Why This Module Exists
----------------------
FastAPI route handlers must never directly import joblib, numpy, or touch
feature engineering. All ML concerns are isolated here. This means:
  - Improving the model = retrain + restart. No backend code changes.
  - Adding a feature = update compute_features() here only.
  - Swapping Random Forest for XGBoost = retrain. No API changes.

Responsibilities
----------------
1. Load all 4 models from disk into memory at module import time.
2. Expose compute_features() for feature engineering (eve_qber_contribution).
3. Expose predict() as the single public inference entry point.
4. Validate all inputs before touching the model.

Feature Contract (must match ml/feature_names.json)
----------------------------------------------------
  [0] qber                  -- raw observed QBER
  [1] noise_level           -- depolarising noise parameter
  [2] sifted_key_length     -- number of sifted key bits
  [3] eve_qber_contribution -- derived: max(0, qber - 2/3*noise_level)

Public API
----------
  predict(qber, noise_level, sifted_key_length, model_type) -> dict
  get_model_registry() -> dict
  AVAILABLE_MODELS -> list[str]

Tests: INF-01 through INF-08 (run via __main__ block below)
"""

import os
import json
import joblib
import numpy as np
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ML_DIR        = os.path.dirname(os.path.abspath(__file__))
_REGISTRY_PATH = os.path.join(_ML_DIR, "model_registry.json")
_FEATURES_PATH = os.path.join(_ML_DIR, "feature_names.json")

# ---------------------------------------------------------------------------
# Model registry + feature contract (loaded once at import time)
# ---------------------------------------------------------------------------

def _load_registry() -> dict:
    if not os.path.exists(_REGISTRY_PATH):
        raise FileNotFoundError(
            f"[inference] model_registry.json not found at {_REGISTRY_PATH}\n"
            f"  -> Run 'python ml/train_model.py' first."
        )
    with open(_REGISTRY_PATH) as f:
        return json.load(f)


def _load_feature_names() -> list:
    if not os.path.exists(_FEATURES_PATH):
        raise FileNotFoundError(
            f"[inference] feature_names.json not found at {_FEATURES_PATH}\n"
            f"  -> Run 'python ml/train_model.py' first."
        )
    with open(_FEATURES_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Load all models into memory at import time (once per process)
# ---------------------------------------------------------------------------

def _load_all_models(registry: dict) -> dict:
    """
    Load every model listed in the registry from disk into RAM.
    Fails fast with a clear message if any file is missing.

    Returns
    -------
    dict { model_type: fitted_estimator }
    """
    store = {}
    for model_type, info in registry.items():
        if model_type.startswith("_"):
            continue   # skip _best, _features meta-keys
        filepath = os.path.join(_ML_DIR, info["file"])
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"[inference] Model file missing: {filepath}\n"
                f"  -> Run 'python ml/train_model.py' to regenerate."
            )
        store[model_type] = joblib.load(filepath)
    return store


# Module-level singletons (loaded once when FastAPI imports this module)
_REGISTRY      = _load_registry()
_FEATURE_NAMES = _load_feature_names()
_MODEL_STORE   = _load_all_models(_REGISTRY)
_DEFAULT_MODEL = _REGISTRY.get("_best", "gradient_boosting")

# Public constant: list of valid model type strings
AVAILABLE_MODELS: list = [k for k in _REGISTRY if not k.startswith("_")]


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def compute_features(
    qber: float,
    noise_level: float,
    sifted_key_length: int,
) -> np.ndarray:
    """
    Compute the 4-feature input vector for ML inference.

    Derived feature (eve_qber_contribution):
        = max(0, qber - 2/3 * noise_level)
        Interpretation:
          ~0.00 -> QBER fully explained by channel noise, no Eve signature
          ~0.25 -> QBER far above noise baseline, Eve likely present

    Parameters
    ----------
    qber              : float -- observed Quantum Bit Error Rate [0, 1]
    noise_level       : float -- depolarising noise parameter [0, 1]
    sifted_key_length : int   -- number of sifted key bits [>= 0]

    Returns
    -------
    np.ndarray of shape (1, 4) ready for model.predict()
    """
    eve_qber_contribution = max(0.0, qber - (2.0 / 3.0) * noise_level)

    return np.array([[
        qber,
        noise_level,
        sifted_key_length,
        eve_qber_contribution,
    ]], dtype=float)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validate_inputs(
    qber: float,
    noise_level: float,
    sifted_key_length: int,
    model_type: str,
) -> None:
    """
    Raise ValueError if any input is out of valid range.
    FastAPI will catch this and return a 422 response.
    """
    if not (0.0 <= qber <= 1.0):
        raise ValueError(
            f"qber must be in [0.0, 1.0], got {qber}"
        )
    if not (0.0 <= noise_level <= 1.0):
        raise ValueError(
            f"noise_level must be in [0.0, 1.0], got {noise_level}"
        )
    if sifted_key_length < 0:
        raise ValueError(
            f"sifted_key_length must be >= 0, got {sifted_key_length}"
        )
    if model_type not in _MODEL_STORE:
        raise ValueError(
            f"Unknown model_type '{model_type}'. "
            f"Valid options: {AVAILABLE_MODELS}"
        )


# ---------------------------------------------------------------------------
# Public inference API
# ---------------------------------------------------------------------------

def predict(
    qber: float,
    noise_level: float,
    sifted_key_length: int,
    model_type: Optional[str] = None,
) -> dict:
    """
    Run eavesdropper detection for a given set of BB84 metrics.

    Parameters
    ----------
    qber              : float -- observed QBER from /simulate
    noise_level       : float -- noise_level used in simulation
    sifted_key_length : int   -- sifted key length from /simulate
    model_type        : str   -- which ML model to use
                                 (default: best model from registry)

    Returns
    -------
    dict:
        threat_level     : "HIGH" | "LOW"
        confidence_score : float  -- P(eavesdropper present) in [0, 1]
        model_used       : str    -- model_type actually used
        eve_contribution : float  -- derived feature value (>= 0)

    Raises
    ------
    ValueError  -- invalid input or unknown model_type
    RuntimeError -- model prediction returned unexpected shape
    """
    if model_type is None:
        model_type = _DEFAULT_MODEL

    # Validate
    _validate_inputs(qber, noise_level, sifted_key_length, model_type)

    # Feature engineering
    X = compute_features(qber, noise_level, sifted_key_length)
    eve_contribution = float(X[0, 3])

    # Inference
    model = _MODEL_STORE[model_type]

    try:
        label       = int(model.predict(X)[0])
        proba_array = model.predict_proba(X)

        if proba_array.shape != (1, 2):
            raise RuntimeError(
                f"Unexpected predict_proba shape: {proba_array.shape}"
            )

        confidence_score = float(proba_array[0, 1])   # P(attack)

    except Exception as exc:
        raise RuntimeError(
            f"[inference] Model '{model_type}' prediction failed: {exc}"
        ) from exc

    # Sanity-check confidence
    confidence_score = float(np.clip(confidence_score, 0.0, 1.0))

    threat_level = "HIGH" if label == 1 else "LOW"

    return {
        "threat_level":     threat_level,
        "confidence_score": round(confidence_score, 6),
        "model_used":       model_type,
        "eve_contribution": round(eve_contribution, 6),
    }


def get_model_registry() -> dict:
    """
    Return the full model registry for the GET /models endpoint.

    Returns
    -------
    dict with keys = model_type, values = {file, accuracy, recall_attack,
                                            roc_auc, description, is_default}
    """
    result = {}
    for model_type, info in _REGISTRY.items():
        if model_type.startswith("_"):
            continue
        result[model_type] = {
            "model_type":    model_type,
            "description":   info.get("description", ""),
            "accuracy":      info.get("accuracy", 0.0),
            "recall_attack": info.get("recall_attack", 0.0),
            "roc_auc":       info.get("roc_auc", 0.0),
            "is_default":    (model_type == _DEFAULT_MODEL),
        }
    return result


# ---------------------------------------------------------------------------
# Test suite: INF-01 through INF-08
# ---------------------------------------------------------------------------

def _run_inference_tests() -> None:
    """
    Standalone test suite for ml/inference.py.
    Run with: python ml/inference.py
    """
    import sys

    SEP    = "=" * 72
    passed = 0
    failed = 0

    print(f"\n{SEP}")
    print("  Inference Module Tests  (INF-01 -> INF-08)")
    print(SEP)

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        status = "[PASS]" if condition else "[FAIL]"
        msg    = f"  {status}  {name}"
        if detail:
            msg += f"  [{detail}]"
        print(msg)
        if condition:
            passed += 1
        else:
            failed += 1

    # INF-01: All models loaded
    check("INF-01 All models loaded into memory",
          len(_MODEL_STORE) == 4,
          f"loaded={list(_MODEL_STORE.keys())}")

    # INF-02: Invalid model_type -> ValueError
    try:
        predict(qber=0.1, noise_level=0.03,
                sifted_key_length=200, model_type="nonexistent_model")
        check("INF-02 Invalid model_type -> ValueError", False,
              "no exception raised")
    except ValueError as e:
        check("INF-02 Invalid model_type -> ValueError", True, str(e)[:50])

    # INF-03: Known attack input -> HIGH threat, all 4 models
    all_high = True
    for mt in AVAILABLE_MODELS:
        r = predict(qber=0.27, noise_level=0.03,
                    sifted_key_length=240, model_type=mt)
        if r["threat_level"] != "HIGH" or r["confidence_score"] < 0.8:
            all_high = False
    check("INF-03 Known attack (QBER=0.27) -> HIGH on all 4 models",
          all_high,
          f"models tested={AVAILABLE_MODELS}")

    # INF-04: Known safe input -> LOW threat, all 4 models
    all_low = True
    for mt in AVAILABLE_MODELS:
        r = predict(qber=0.02, noise_level=0.03,
                    sifted_key_length=248, model_type=mt)
        if r["threat_level"] != "LOW" or r["confidence_score"] > 0.2:
            all_low = False
    check("INF-04 Known safe (QBER=0.02) -> LOW on all 4 models",
          all_low,
          f"models tested={AVAILABLE_MODELS}")

    # INF-05: qber > 1.0 -> ValueError
    try:
        predict(qber=1.5, noise_level=0.03, sifted_key_length=200)
        check("INF-05 qber > 1.0 -> ValueError", False, "no exception raised")
    except ValueError:
        check("INF-05 qber > 1.0 -> ValueError", True)

    # INF-06: noise_level < 0 -> ValueError
    try:
        predict(qber=0.1, noise_level=-0.1, sifted_key_length=200)
        check("INF-06 noise_level < 0 -> ValueError", False,
              "no exception raised")
    except ValueError:
        check("INF-06 noise_level < 0 -> ValueError", True)

    # INF-07: All 4 models return valid response dicts
    valid_keys = {"threat_level", "confidence_score", "model_used",
                  "eve_contribution"}
    all_valid  = True
    for mt in AVAILABLE_MODELS:
        r = predict(qber=0.15, noise_level=0.05,
                    sifted_key_length=180, model_type=mt)
        if set(r.keys()) != valid_keys:
            all_valid = False
        if r["threat_level"] not in ("HIGH", "LOW"):
            all_valid = False
        if not (0.0 <= r["confidence_score"] <= 1.0):
            all_valid = False
        if r["model_used"] != mt:
            all_valid = False
    check("INF-07 All 4 models return valid response dict",
          all_valid,
          f"keys={valid_keys}")

    # INF-08: eve_contribution always >= 0
    inputs = [
        (0.00, 0.15, 500),   # noise >> qber -> would go negative without clamp
        (0.02, 0.10, 300),
        (0.25, 0.00, 200),
        (0.00, 0.00, 0),     # edge: sifted_key_length = 0
    ]
    all_non_negative = True
    for q, n, s in inputs:
        r = predict(qber=q, noise_level=n, sifted_key_length=s)
        if r["eve_contribution"] < 0.0:
            all_non_negative = False
    check("INF-08 eve_contribution always >= 0.0",
          all_non_negative,
          f"tested {len(inputs)} edge cases")

    # Summary
    total = passed + failed
    print(f"\n{SEP}")
    print(f"  Results: {passed}/{total} passed, {failed}/{total} failed")
    if failed > 0:
        print("  [WARN] Inference tests FAILED. Do NOT start FastAPI.")
        print(SEP)
        sys.exit(1)
    else:
        print("  [OK]   ALL INFERENCE TESTS PASSED -- inference.py is ready.")
    print(SEP)


if __name__ == "__main__":
    _run_inference_tests()
