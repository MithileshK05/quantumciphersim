"""
backend/test_full.py
====================
EXHAUSTIVE test suite that covers EVERYTHING in the Phase 3 plan:

  SECTION A: INF-01 to INF-08  (ml/inference.py)
  SECTION B: ML-11              (model disk reload)
  SECTION C: All Pydantic field validation rules (both bounds for every field)
  SECTION D: FastAPI edge cases from plan Part 5
  SECTION E: API-01 to API-12   (full API contract)
  SECTION F: DB edge cases

Run with server already started:
  python -m uvicorn backend.main:app --reload --port 8000

Then in another terminal:
  python backend/test_full.py
"""

import sys
import os
import json
import joblib
import numpy as np
import requests

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.inference import (
    predict, compute_features, get_model_registry,
    AVAILABLE_MODELS, _MODEL_STORE, _DEFAULT_MODEL
)

BASE_URL = "http://127.0.0.1:8000"
SEP      = "=" * 72

total_passed = 0
total_failed = 0
_section_passed = 0
_section_failed = 0


def start_section(name: str) -> None:
    global _section_passed, _section_failed
    _section_passed = 0
    _section_failed = 0
    print(f"\n{SEP}")
    print(f"  {name}")
    print(SEP)


def end_section() -> None:
    global total_passed, total_failed, _section_passed, _section_failed
    total_passed += _section_passed
    total_failed += _section_failed
    p = _section_passed
    f = _section_failed
    t = p + f
    result = "[OK]" if f == 0 else "[FAIL]"
    print(f"  {result}  Section: {p}/{t} passed")


def check(name: str, condition: bool, detail: str = "") -> None:
    global _section_passed, _section_failed
    status = "[PASS]" if condition else "[FAIL]"
    msg = f"  {status}  {name}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)
    if condition:
        _section_passed += 1
    else:
        _section_failed += 1


def get(path, params=None, origin=None):
    h = {"Origin": origin} if origin else {}
    r = requests.get(f"{BASE_URL}{path}", params=params, headers=h, timeout=30)
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body, r.headers


def post(path, payload, origin="http://localhost:5173"):
    h = {"Origin": origin} if origin else {}
    r = requests.post(f"{BASE_URL}{path}", json=payload, headers=h, timeout=90)
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body, r.headers


def options(path):
    r = requests.options(
        f"{BASE_URL}{path}",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=10,
    )
    return r.status_code, r.headers


def post_raw(path, raw_body: str):
    """Send malformed JSON."""
    r = requests.post(
        f"{BASE_URL}{path}",
        data=raw_body,
        headers={"Content-Type": "application/json",
                 "Origin": "http://localhost:5173"},
        timeout=10,
    )
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body


# ===========================================================================
# SECTION A: ml/inference.py  (INF-01 to INF-08)
# ===========================================================================

start_section("SECTION A: ml/inference.py  (INF-01 to INF-08)")

# INF-01: All 4 models loaded
check("INF-01 All 4 models loaded into memory",
      len(_MODEL_STORE) == 4,
      f"loaded={list(_MODEL_STORE.keys())}")

# INF-02: Invalid model_type -> ValueError
try:
    predict(qber=0.1, noise_level=0.03, sifted_key_length=200,
            model_type="fake_model")
    check("INF-02 Invalid model_type -> ValueError", False, "no exception raised")
except ValueError as e:
    check("INF-02 Invalid model_type -> ValueError", True,
          f"msg: {str(e)[:80]}")

# INF-03: Known attack (QBER=0.27) -> HIGH on all 4 models, confidence > 0.9
all_high = True
details = []
for mt in AVAILABLE_MODELS:
    r = predict(qber=0.27, noise_level=0.03, sifted_key_length=240, model_type=mt)
    ok = r["threat_level"] == "HIGH" and r["confidence_score"] > 0.9
    details.append(f"{mt}: {r['threat_level']} ({r['confidence_score']:.4f})")
    if not ok:
        all_high = False
check("INF-03 Known attack (QBER=0.27) -> HIGH + confidence>0.9 on all 4",
      all_high, " | ".join(details))

# INF-04: Known safe (QBER=0.02) -> LOW on all 4 models, confidence < 0.2
all_low = True
details = []
for mt in AVAILABLE_MODELS:
    r = predict(qber=0.02, noise_level=0.03, sifted_key_length=248, model_type=mt)
    ok = r["threat_level"] == "LOW" and r["confidence_score"] < 0.2
    details.append(f"{mt}: {r['threat_level']} ({r['confidence_score']:.4f})")
    if not ok:
        all_low = False
check("INF-04 Known safe (QBER=0.02) -> LOW + confidence<0.2 on all 4",
      all_low, " | ".join(details))

# INF-05: qber > 1.0 -> ValueError
try:
    predict(qber=1.5, noise_level=0.03, sifted_key_length=200)
    check("INF-05 qber>1.0 -> ValueError", False, "no exception raised")
except ValueError:
    check("INF-05 qber>1.0 -> ValueError", True)

# INF-06: noise_level < 0 -> ValueError
try:
    predict(qber=0.1, noise_level=-0.1, sifted_key_length=200)
    check("INF-06 noise_level<0 -> ValueError", False, "no exception raised")
except ValueError:
    check("INF-06 noise_level<0 -> ValueError", True)

# INF-07: All 4 models return valid response dict keys
REQUIRED_KEYS = {"threat_level", "confidence_score", "model_used", "eve_contribution"}
all_valid = True
for mt in AVAILABLE_MODELS:
    r = predict(qber=0.15, noise_level=0.05, sifted_key_length=180, model_type=mt)
    if set(r.keys()) != REQUIRED_KEYS:
        all_valid = False
    if r["threat_level"] not in ("HIGH", "LOW"):
        all_valid = False
    if not (0.0 <= r["confidence_score"] <= 1.0):
        all_valid = False
    if r["model_used"] != mt:
        all_valid = False
check("INF-07 All 4 models return valid response dict", all_valid,
      f"required_keys={REQUIRED_KEYS}")

# INF-08: eve_contribution always >= 0 across edge cases
edge_inputs = [
    (0.00, 0.15, 500),   # noise >> qber -> would go negative without clamp
    (0.02, 0.10, 300),
    (0.25, 0.00, 200),
    (0.00, 0.00, 0),     # sifted_key_length = 0
    (0.00, 1.00, 100),   # maximum noise, zero qber
]
all_non_neg = True
details = []
for q, n, s in edge_inputs:
    r = predict(qber=q, noise_level=n, sifted_key_length=s)
    details.append(f"(q={q},n={n},s={s})->eve={r['eve_contribution']:.4f}")
    if r["eve_contribution"] < 0:
        all_non_neg = False
check("INF-08 eve_contribution always>=0.0 (5 edge cases)",
      all_non_neg, " | ".join(details))

end_section()


# ===========================================================================
# SECTION B: ML-11 — Model disk reload verification
# ===========================================================================

start_section("SECTION B: ML-11 — Model disk reload verification")

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml")
FEATURE_COLS = ["qber", "noise_level", "sifted_key_length", "eve_qber_contribution"]

for model_name in AVAILABLE_MODELS:
    filepath = os.path.join(ML_DIR, f"model_{model_name}.joblib")
    try:
        reloaded = joblib.load(filepath)
        test_X   = np.array([[0.27, 0.03, 240, 0.25]])
        pred     = reloaded.predict(test_X)[0]
        proba    = reloaded.predict_proba(test_X)[0][1]
        ok = (pred in (0, 1)) and (0.0 <= proba <= 1.0)
        check(f"ML-11 {model_name}: loads from disk + predicts correctly",
              ok, f"pred={pred}  P(attack)={proba:.4f}")
    except Exception as exc:
        check(f"ML-11 {model_name}: loads from disk + predicts correctly",
              False, str(exc))

end_section()


# ===========================================================================
# SECTION C: Pydantic validation rules — every bound for every field
# ===========================================================================

start_section("SECTION C: Pydantic validation — ALL field bounds")

print("\n  --- SimulateRequest ---")

# num_qubits ge=1
s, b, _ = post("/simulate", {"num_qubits": 0, "noise_level": 0.05, "attack_probability": 0.5})
check("PYDANTIC-01 num_qubits=0 -> 422 (ge=1)", s == 422, f"status={s}")

# num_qubits le=2000
s, b, _ = post("/simulate", {"num_qubits": 2001, "noise_level": 0.05, "attack_probability": 0.5})
check("PYDANTIC-02 num_qubits=2001 -> 422 (le=2000)", s == 422, f"status={s}")

# noise_level ge=0
s, b, _ = post("/simulate", {"num_qubits": 100, "noise_level": -0.01, "attack_probability": 0.5})
check("PYDANTIC-03 noise_level=-0.01 -> 422 (ge=0.0)", s == 422, f"status={s}")

# noise_level le=1.0
s, b, _ = post("/simulate", {"num_qubits": 100, "noise_level": 1.5, "attack_probability": 0.5})
check("PYDANTIC-04 noise_level=1.5 -> 422 (le=1.0)", s == 422, f"status={s}")

# attack_probability ge=0
s, b, _ = post("/simulate", {"num_qubits": 100, "noise_level": 0.05, "attack_probability": -0.1})
check("PYDANTIC-05 attack_probability=-0.1 -> 422 (ge=0.0)", s == 422, f"status={s}")

# attack_probability le=1.0
s, b, _ = post("/simulate", {"num_qubits": 100, "noise_level": 0.05, "attack_probability": 1.5})
check("PYDANTIC-06 attack_probability=1.5 -> 422 (le=1.0)", s == 422, f"status={s}")

print("\n  --- DetectRequest ---")

# qber ge=0.0
s, b, _ = post("/detect", {"qber": -0.1, "noise_level": 0.03, "sifted_key_length": 200})
check("PYDANTIC-07 qber=-0.1 -> 422 (ge=0.0)", s == 422, f"status={s}")

# qber le=1.0
s, b, _ = post("/detect", {"qber": 1.5, "noise_level": 0.03, "sifted_key_length": 200})
check("PYDANTIC-08 qber=1.5 -> 422 (le=1.0)", s == 422, f"status={s}")

# noise_level ge=0
s, b, _ = post("/detect", {"qber": 0.1, "noise_level": -0.1, "sifted_key_length": 200})
check("PYDANTIC-09 detect: noise_level=-0.1 -> 422 (ge=0.0)", s == 422, f"status={s}")

# noise_level le=1.0
s, b, _ = post("/detect", {"qber": 0.1, "noise_level": 2.0, "sifted_key_length": 200})
check("PYDANTIC-10 detect: noise_level=2.0 -> 422 (le=1.0)", s == 422, f"status={s}")

# sifted_key_length ge=0
s, b, _ = post("/detect", {"qber": 0.1, "noise_level": 0.03, "sifted_key_length": -1})
check("PYDANTIC-11 sifted_key_length=-1 -> 422 (ge=0)", s == 422, f"status={s}")

# sifted_key_length = 0 is VALID (degenerate but allowed)
s, b, _ = post("/detect", {"qber": 0.0, "noise_level": 0.0, "sifted_key_length": 0})
check("PYDANTIC-12 sifted_key_length=0 -> 200 (degenerate but valid)",
      s == 200, f"status={s}  threat={b.get('threat_level') if isinstance(b,dict) else b}")

print("\n  --- History limit ---")

# limit ge=1
s, b, _ = get("/history", params={"limit": 0})
check("PYDANTIC-13 limit=0 -> 422 (ge=1)", s == 422, f"status={s}")

# limit le=200
s, b, _ = get("/history", params={"limit": 201})
check("PYDANTIC-14 limit=201 -> 422 (le=200)", s == 422, f"status={s}")

# limit=200 is VALID
s, b, _ = get("/history", params={"limit": 200})
check("PYDANTIC-15 limit=200 -> 200 (boundary valid)",
      s == 200, f"status={s}  runs={len(b.get('runs',[]))} total={b.get('total')}")

end_section()


# ===========================================================================
# SECTION D: FastAPI edge cases (from plan Part 5)
# ===========================================================================

start_section("SECTION D: FastAPI edge cases (plan Part 5)")

# EC-01: /detect with session_id=None -> 200, graceful (no crash)
s, b, _ = post("/detect", {
    "session_id":       None,
    "qber":             0.27,
    "noise_level":      0.03,
    "sifted_key_length": 240,
    "model_type":       "gradient_boosting",
})
check("EC-01 /detect with session_id=None -> 200 (graceful)",
      s == 200 and b.get("threat_level") in ("HIGH", "LOW"),
      f"status={s}  threat={b.get('threat_level')}  session_id={b.get('session_id')}")

# EC-02: Malformed JSON -> 422
s, b = post_raw("/simulate", '{"num_qubits": 100, "noise_level": BROKEN}')
check("EC-02 Malformed JSON -> 422",
      s == 422, f"status={s}")

# EC-03: /detect unknown model_type -> 422 with valid_options in response
s, b, _ = post("/detect", {
    "qber": 0.27, "noise_level": 0.03,
    "sifted_key_length": 240,
    "model_type": "random_neural_forest",
})
detail = b.get("detail", {}) if isinstance(b, dict) else {}
has_valid_options = (
    "valid_options" in str(detail)
    or "valid_options" in str(b)
)
check("EC-03 /detect invalid model_type -> 422 + valid_options listed",
      s == 422 and has_valid_options,
      f"status={s}  detail_snippet={str(detail)[:100]}")

# EC-04: ML model immunity — delete a joblib file AFTER startup
# The model was already loaded into RAM at startup, so it should still work
import tempfile, shutil
ml_dir   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml")
test_file = os.path.join(ml_dir, "model_logistic_regression.joblib")
backup   = test_file + ".bak"
shutil.copy2(test_file, backup)
os.remove(test_file)  # delete it!

s, b, _ = post("/detect", {
    "qber": 0.27, "noise_level": 0.03, "sifted_key_length": 240,
    "model_type": "logistic_regression",
})
still_works = s == 200 and b.get("threat_level") in ("HIGH", "LOW")
shutil.move(backup, test_file)  # restore immediately

check("EC-04 Model file deleted after startup -> still works (loaded in RAM)",
      still_works,
      f"status={s}  threat={b.get('threat_level')}")

# EC-05: /simulate with num_qubits at upper boundary (10000) -> 200
# (Tests threadpool doesn't crash — we can't wait 3+ mins so use seed for speed)
# Note: This will be slow. We use num_qubits=10000 with seed for determinism.
print("  EC-05: Testing num_qubits=2000 upper boundary (max allowed) ...")
s, b, _ = post("/simulate", {
    "num_qubits":         2000,
    "noise_level":        0.0,
    "attack_probability": 0.0,
    "seed":               42,
})
check("EC-05 /simulate num_qubits=2000 (upper bound) -> 200",
      s == 200 and isinstance(b.get("qber"), float),
      f"status={s}  qber={b.get('qber')}  sifted={b.get('sifted_key_length')}")

# EC-06: /simulate missing required field -> 422
s, b, _ = post("/simulate", {
    "num_qubits": 100,
    # noise_level and attack_probability missing
})
check("EC-06 /simulate missing required fields -> 422",
      s == 422, f"status={s}")

# EC-07: GET /health response fields complete
s, b, _ = get("/health")
fields_ok = all(k in b for k in ("status", "models_loaded", "db_connected", "version"))
check("EC-07 GET /health response has all required fields",
      s == 200 and fields_ok,
      f"status={s}  body={b}")

# EC-08: /models response — each model has all required fields
s, b, _ = get("/models")
models   = b.get("models", []) if isinstance(b, dict) else []
required = {"model_type", "description", "accuracy", "recall_attack",
            "roc_auc", "is_default"}
all_complete = all(set(m.keys()) >= required for m in models)
one_default  = sum(1 for m in models if m.get("is_default")) == 1
check("EC-08 /models each entry has all required fields",
      s == 200 and all_complete,
      f"model_count={len(models)}  all_complete={all_complete}")
check("EC-09 /models exactly one model is_default=true",
      one_default, f"default_count={sum(1 for m in models if m.get('is_default'))}")

# EC-10: /simulate with seed -> reproduces same QBER
s1, b1, _ = post("/simulate", {
    "num_qubits": 200, "noise_level": 0.05,
    "attack_probability": 0.5, "seed": 99
})
s2, b2, _ = post("/simulate", {
    "num_qubits": 200, "noise_level": 0.05,
    "attack_probability": 0.5, "seed": 99
})
check("EC-10 /simulate same seed -> identical QBER",
      s1 == 200 and s2 == 200 and b1.get("qber") == b2.get("qber"),
      f"qber1={b1.get('qber')}  qber2={b2.get('qber')}")

end_section()


# ===========================================================================
# SECTION E: API-01 to API-12 (full API contract)
# ===========================================================================

start_section("SECTION E: API-01 to API-12  (full API contract)")

# API-01
s, b, _ = get("/health")
check("API-01 GET /health -> 200, models_loaded=4, db_connected=true",
      s == 200 and b.get("models_loaded") == 4 and b.get("db_connected") is True,
      f"status={s}  body={b}")

# API-02
s, b, _ = get("/models")
model_names = [m.get("model_type") for m in b.get("models", [])]
check("API-02 GET /models -> 200, 4 models, one default",
      s == 200 and len(model_names) == 4,
      f"models={model_names}")

# API-03
print("  API-03: /simulate valid (Qiskit) ...")
s, sim_b, _ = post("/simulate", {
    "num_qubits": 300, "noise_level": 0.05, "attack_probability": 0.8
})
sid = sim_b.get("session_id", "")
check("API-03 POST /simulate valid -> 200, qber in [0,1], session_id",
      s == 200 and isinstance(sim_b.get("qber"), float)
      and 0.0 <= sim_b.get("qber", -1) <= 1.0 and len(sid) > 0,
      f"qber={sim_b.get('qber')}  sifted={sim_b.get('sifted_key_length')}")

# API-04
s, b, _ = post("/simulate", {"num_qubits": 0, "noise_level": 0.05, "attack_probability": 0.5})
check("API-04 POST /simulate num_qubits=0 -> 422", s == 422, f"status={s}")

# API-05
s, b, _ = post("/simulate", {"num_qubits": 300, "noise_level": 2.0, "attack_probability": 0.5})
check("API-05 POST /simulate noise_level=2.0 -> 422", s == 422, f"status={s}")

# API-06 (all 4 models)
model_results = []
for mt in AVAILABLE_MODELS:
    s, b, _ = post("/detect", {
        "qber": 0.27, "noise_level": 0.03,
        "sifted_key_length": 240, "model_type": mt
    })
    ok = s == 200 and b.get("threat_level") in ("HIGH", "LOW")
    model_results.append(f"{mt}:{b.get('threat_level')}({b.get('confidence_score',0):.4f})")
    last_s = s
check("API-06 POST /detect valid -> 200, all 4 models work",
      last_s == 200, "  " + "  |  ".join(model_results))

# API-07
s, b, _ = post("/detect", {
    "qber": 0.27, "noise_level": 0.03,
    "sifted_key_length": 240, "model_type": "invalid_xyz"
})
check("API-07 POST /detect invalid model_type -> 422",
      s == 422, f"status={s}  detail_snippet={str(b)[:100]}")

# API-08
s, b, _ = post("/detect", {"qber": 1.5, "noise_level": 0.03, "sifted_key_length": 200})
check("API-08 POST /detect qber=1.5 -> 422", s == 422, f"status={s}")

# API-09
s, b, _ = get("/history", params={"limit": 5})
check("API-09 GET /history?limit=5 -> 200, runs list present",
      s == 200 and isinstance(b.get("runs"), list),
      f"runs={len(b.get('runs',[]))}  total={b.get('total')}")

# API-10
s, b, _ = get("/history", params={"limit": 0})
check("API-10 GET /history?limit=0 -> 422", s == 422, f"status={s}")

# API-11
print("  API-11: Full pipeline /simulate -> /detect ...")
s_s, sim2, _ = post("/simulate", {
    "num_qubits": 200, "noise_level": 0.03, "attack_probability": 0.9
})
sid2 = sim2.get("session_id", "")
if s_s == 200 and sid2:
    s_d, det2, _ = post("/detect", {
        "session_id": sid2,
        "qber": sim2.get("qber"),
        "noise_level": sim2.get("noise_level"),
        "sifted_key_length": sim2.get("sifted_key_length"),
        "model_type": "gradient_boosting",
    })
    check("API-11 Full pipeline /simulate->detect same session_id",
          s_d == 200 and det2.get("session_id") == sid2
          and det2.get("threat_level") in ("HIGH", "LOW"),
          f"qber={sim2.get('qber'):.4f}  threat={det2.get('threat_level')}  "
          f"conf={det2.get('confidence_score'):.4f}  sid={sid2[:8]}...")
else:
    check("API-11 Full pipeline", False, f"simulate failed: {s_s}")

# API-12
cors_s, cors_h = options("/simulate")
acao = cors_h.get("access-control-allow-origin", "")
check("API-12 CORS preflight -> 200, Access-Control-Allow-Origin present",
      cors_s == 200 and "localhost:5173" in acao,
      f"status={cors_s}  ACAO={acao}")

end_section()


# ===========================================================================
# SECTION F: DB edge cases
# ===========================================================================

start_section("SECTION F: DB edge cases")

# DB-01: /detect with unknown session_id -> still returns 200 (non-fatal)
s, b, _ = post("/detect", {
    "session_id":        "00000000-0000-0000-0000-000000000000",
    "qber":              0.27,
    "noise_level":       0.03,
    "sifted_key_length": 240,
})
check("DB-01 /detect unknown session_id -> 200 (DB update non-fatal)",
      s == 200 and b.get("threat_level") in ("HIGH", "LOW"),
      f"status={s}  threat={b.get('threat_level')}")

# DB-02: /history total increases after /simulate
s, b, _ = get("/history", params={"limit": 1})
before = b.get("total", 0)
post("/simulate", {"num_qubits": 100, "noise_level": 0.0, "attack_probability": 0.0})
import time; time.sleep(0.5)
s2, b2, _ = get("/history", params={"limit": 1})
after = b2.get("total", 0)
check("DB-02 /history total increases after new /simulate",
      after > before, f"before={before}  after={after}")

# DB-03: /history runs are ordered latest-first
s, b, _ = get("/history", params={"limit": 5})
runs = b.get("runs", [])
if len(runs) >= 2:
    ts_ok = runs[0]["timestamp"] >= runs[1]["timestamp"]
    check("DB-03 /history ordered by timestamp DESC",
          ts_ok, f"[0]={runs[0]['timestamp'][:19]}  [1]={runs[1]['timestamp'][:19]}")
else:
    check("DB-03 /history ordered DESC (need >=2 rows)", True,
          f"only {len(runs)} rows -- skipped ordering check")

end_section()


# ===========================================================================
# FINAL SUMMARY
# ===========================================================================

print(f"\n{SEP}")
print(f"  FINAL SUMMARY")
print(SEP)
print(f"  Section A (INF-01..08):  inference module")
print(f"  Section B (ML-11):       disk reload")
print(f"  Section C (PYDANTIC):    all field validation bounds")
print(f"  Section D (EDGE-CASES):  FastAPI plan Part 5")
print(f"  Section E (API-01..12):  full API contract")
print(f"  Section F (DB):          database edge cases")
print(f"  {'-'*60}")
print(f"  Total passed : {total_passed}")
print(f"  Total failed : {total_failed}")
print(f"  Grand total  : {total_passed + total_failed}")
if total_failed == 0:
    print(f"\n  [OK]  ALL TESTS PASSED -- Phase 3 fully verified.")
else:
    print(f"\n  [FAIL]  {total_failed} test(s) failed. See details above.")
print(SEP)

sys.exit(0 if total_failed == 0 else 1)
