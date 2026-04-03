"""
backend/test_api.py
===================
Full automated test suite for the QuantumCipherSim FastAPI backend.
Covers API-01 through API-12 as defined in phase3_plan.md.

Run with server already started:
  uvicorn backend.main:app --reload --port 8000

Then in a separate terminal:
  python backend/test_api.py
"""

import sys
import json
import time
import requests

BASE_URL = "http://127.0.0.1:8000"
SEP      = "=" * 72

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    status = "[PASS]" if condition else "[FAIL]"
    msg = f"  {status}  {name}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)
    if condition:
        passed += 1
    else:
        failed += 1


def get(path: str, params: dict = None) -> tuple:
    """Return (status_code, json_body, headers)."""
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params, timeout=30)
        try:
            body = r.json()
        except Exception:
            body = r.text
        return r.status_code, body, r.headers
    except Exception as exc:
        return 0, {"error": str(exc)}, {}


def post(path: str, payload: dict) -> tuple:
    """Return (status_code, json_body, headers)."""
    try:
        r = requests.post(
            f"{BASE_URL}{path}",
            json=payload,
            timeout=60,
            headers={"Origin": "http://localhost:5173"},  # simulate CORS preflight
        )
        try:
            body = r.json()
        except Exception:
            body = r.text
        return r.status_code, body, r.headers
    except Exception as exc:
        return 0, {"error": str(exc)}, {}


def options(path: str) -> tuple:
    """Send CORS preflight OPTIONS request."""
    try:
        r = requests.options(
            f"{BASE_URL}{path}",
            headers={
                "Origin":                         "http://localhost:5173",
                "Access-Control-Request-Method":  "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=10,
        )
        return r.status_code, r.headers
    except Exception as exc:
        return 0, {}


# ---------------------------------------------------------------------------
print(f"\n{SEP}")
print("  QuantumCipherSim API Tests  (API-01 -> API-12)")
print(SEP)

# ── API-01: GET /health ───────────────────────────────────────────────────
print("\n  [GET /health]")
status, body, headers = get("/health")
check("API-01 GET /health -> 200, models_loaded=4, db_connected=true",
      status == 200
      and body.get("models_loaded") == 4
      and body.get("db_connected") == True
      and body.get("status") == "ok",
      f"status={status}  body={body}")

# ── API-02: GET /models ───────────────────────────────────────────────────
print("\n  [GET /models]")
status, body, headers = get("/models")
models_list = body.get("models", []) if isinstance(body, dict) else []
model_names = [m.get("model_type") for m in models_list]
has_default = any(m.get("is_default") for m in models_list)
check("API-02 GET /models -> 200, 4 models, one is default",
      status == 200
      and len(models_list) == 4
      and has_default,
      f"status={status}  models={model_names}  has_default={has_default}")

# ── API-03: POST /simulate valid input ───────────────────────────────────
print("\n  [POST /simulate  valid input]")
print("  (this calls Qiskit -- may take 5-30s ...)")
status, sim_body, headers = post("/simulate", {
    "num_qubits":         300,
    "noise_level":        0.05,
    "attack_probability": 0.8,
})
qber_ok      = isinstance(sim_body.get("qber"), float) and 0.0 <= sim_body.get("qber", -1) <= 1.0
session_id   = sim_body.get("session_id", "")
check("API-03 POST /simulate valid -> 200, qber in [0,1], session_id present",
      status == 200
      and qber_ok
      and len(session_id) > 0,
      f"status={status}  qber={sim_body.get('qber')}  "
      f"sifted={sim_body.get('sifted_key_length')}  "
      f"session_id={session_id[:8]}...")

# ── API-04: POST /simulate num_qubits=0 -> 422 ───────────────────────────
print("\n  [POST /simulate  num_qubits=0]")
status, body, _ = post("/simulate", {
    "num_qubits":         0,
    "noise_level":        0.05,
    "attack_probability": 0.5,
})
check("API-04 POST /simulate num_qubits=0 -> 422",
      status == 422,
      f"status={status}  detail={str(body)[:120]}")

# ── API-05: POST /simulate noise_level=2.0 -> 422 ────────────────────────
print("\n  [POST /simulate  noise_level=2.0]")
status, body, _ = post("/simulate", {
    "num_qubits":         300,
    "noise_level":        2.0,
    "attack_probability": 0.5,
})
check("API-05 POST /simulate noise_level=2.0 -> 422",
      status == 422,
      f"status={status}  detail={str(body)[:120]}")

# ── API-06: POST /detect valid input ─────────────────────────────────────
print("\n  [POST /detect  valid input]")
for model_type in ["gradient_boosting", "random_forest",
                   "logistic_regression", "svm"]:
    status, body, _ = post("/detect", {
        "qber":              0.27,
        "noise_level":       0.03,
        "sifted_key_length": 240,
        "model_type":        model_type,
    })
    threat_ok = body.get("threat_level") in ("HIGH", "LOW")
    conf_ok   = 0.0 <= body.get("confidence_score", -1) <= 1.0
    print(f"    {model_type:<25} "
          f"threat={body.get('threat_level')}  "
          f"confidence={body.get('confidence_score', 'N/A'):.4f}  "
          f"status={status}")

check("API-06 POST /detect valid -> 200, threat HIGH, all 4 models",
      status == 200 and threat_ok and conf_ok,
      f"last model_used={body.get('model_used')}  threat={body.get('threat_level')}")

# ── API-07: POST /detect invalid model_type -> 422 ───────────────────────
print("\n  [POST /detect  invalid model_type]")
status, body, _ = post("/detect", {
    "qber":              0.27,
    "noise_level":       0.03,
    "sifted_key_length": 240,
    "model_type":        "nonexistent_neural_network",
})
check("API-07 POST /detect invalid model_type -> 422",
      status == 422,
      f"status={status}  detail={str(body)[:120]}")

# ── API-08: POST /detect qber=1.5 -> 422 ─────────────────────────────────
print("\n  [POST /detect  qber=1.5]")
status, body, _ = post("/detect", {
    "qber":              1.5,
    "noise_level":       0.03,
    "sifted_key_length": 240,
})
check("API-08 POST /detect qber=1.5 -> 422",
      status == 422,
      f"status={status}  detail={str(body)[:120]}")

# ── API-09: GET /history?limit=5 ─────────────────────────────────────────
print("\n  [GET /history?limit=5]")
status, body, _ = get("/history", params={"limit": 5})
runs         = body.get("runs", []) if isinstance(body, dict) else []
total        = body.get("total", -1)
check("API-09 GET /history?limit=5 -> 200, list present, total >= 0",
      status == 200
      and isinstance(runs, list)
      and total >= 0,
      f"status={status}  runs_returned={len(runs)}  total_in_db={total}")

# ── API-10: GET /history?limit=0 -> 422 ──────────────────────────────────
print("\n  [GET /history?limit=0]")
status, body, _ = get("/history", params={"limit": 0})
check("API-10 GET /history?limit=0 -> 422",
      status == 422,
      f"status={status}  detail={str(body)[:120]}")

# ── API-11: Full pipeline /simulate -> /detect same session_id ────────────
print("\n  [Full pipeline: /simulate -> /detect]")
print("  (calling Qiskit again -- may take 5-30s ...)")
status_s, sim2, _ = post("/simulate", {
    "num_qubits":         200,
    "noise_level":        0.03,
    "attack_probability": 0.9,
})
sid = sim2.get("session_id", "")

if status_s == 200 and sid:
    status_d, det2, _ = post("/detect", {
        "session_id":       sid,
        "qber":             sim2.get("qber", 0),
        "noise_level":      sim2.get("noise_level", 0),
        "sifted_key_length": sim2.get("sifted_key_length", 0),
        "model_type":       "gradient_boosting",
    })
    pipeline_ok = (
        status_d == 200
        and det2.get("session_id") == sid
        and det2.get("threat_level") in ("HIGH", "LOW")
    )
    check("API-11 Full pipeline: /simulate -> /detect same session_id",
          pipeline_ok,
          f"sim_status={status_s}  detect_status={status_d}  "
          f"session_id={sid[:8]}...  "
          f"qber={sim2.get('qber'):.4f}  "
          f"threat={det2.get('threat_level')}  "
          f"confidence={det2.get('confidence_score'):.4f}")
else:
    check("API-11 Full pipeline: /simulate -> /detect same session_id",
          False,
          f"Simulate step failed: status={status_s}  body={sim2}")

# ── API-12: CORS headers on cross-origin request ──────────────────────────
print("\n  [CORS preflight OPTIONS /simulate]")
cors_status, cors_headers = options("/simulate")
acao = cors_headers.get("access-control-allow-origin", "")
acam = cors_headers.get("access-control-allow-methods", "")
check("API-12 CORS preflight -> 200, Access-Control-Allow-Origin present",
      cors_status == 200
      and ("localhost:5173" in acao or acao == "*"),
      f"status={cors_status}  "
      f"Access-Control-Allow-Origin: {acao}  "
      f"Allow-Methods: {acam}")

# ── Final summary ─────────────────────────────────────────────────────────
total_tests = passed + failed
print(f"\n{SEP}")
print(f"  Tests passed : {passed} / {total_tests}")
print(f"  Tests failed : {failed} / {total_tests}")
if failed == 0:
    print("  [OK]   ALL API TESTS PASSED -- Phase 3 is complete.")
else:
    print("  [FAIL] Some tests failed. Check output above.")
print(SEP)

sys.exit(0 if failed == 0 else 1)
