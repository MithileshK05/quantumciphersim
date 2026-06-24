import time
import random
from fastapi import APIRouter, Query
from ml.inference import predict
from backend.models import SimulationRun

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"]
)

# ── Per-state cooldown tracker ───────────────────────────────────────────────
# Key: (protocol, attack_probability_bucket, auto_mitigate)
# Value: unix timestamp of last DB write for that state
# Ensures at most one snapshot every SNAPSHOT_INTERVAL seconds per unique state.
_last_snapshot: dict = {}
SNAPSHOT_INTERVAL = 10   # seconds between DB writes for the same state


def _should_snapshot(protocol: str, attack_prob: float, auto_mitigate: bool) -> bool:
    """Return True if enough time has elapsed to write a new DB snapshot."""
    bucket = round(attack_prob, 1)   # 1.0, 0.0, 0.5, etc.
    key    = (protocol, bucket, auto_mitigate)
    now    = time.time()
    last   = _last_snapshot.get(key, 0)
    if now - last >= SNAPSHOT_INTERVAL:
        _last_snapshot[key] = now
        return True
    return False


def _write_snapshot(noise_level, attack_probability, current_qber,
                    sifted_key_length, prediction):
    """
    Write one simulation snapshot to PostgreSQL.

    Uses SessionLocal() directly rather than FastAPI's Depends(get_db).
    The generator-based Depends() lifecycle caused silent rollbacks when
    commit/rollback were called manually inside the same sync endpoint.
    This function owns its session completely: open -> commit -> close.
    """
    from backend.database import SessionLocal   # local import avoids circular
    db = SessionLocal()
    try:
        run = SimulationRun(
            noise_level           = noise_level,
            attack_probability    = attack_probability,
            final_qber            = round(current_qber, 4),
            sifted_key_length     = sifted_key_length,
            eve_qber_contribution = prediction["eve_contribution"],
            ml_prediction         = prediction["threat_level"],
            confidence_score      = round(prediction["confidence_score"], 4),
            model_used            = prediction["model_used"],
            actual_attack_status  = attack_probability > 0.5,
        )
        db.add(run)
        db.commit()
        print(f"[history] OK  qber={current_qber:.4f} "
              f"atk={attack_probability} threat={prediction['threat_level']}")
    except Exception as exc:
        print(f"[history] FAIL {exc}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


@router.get("/")
def get_live_metrics(
    noise_level:        float = Query(0.0),
    attack_probability: float = Query(0.0),
    model_type:         str   = Query("gradient_boosting"),
    auto_mitigate:      bool  = Query(False),
    active_protocol:    str   = Query("BB84"),
):
    """
    Live QKD channel datastream for the React Query polling hook.
    Writes DB snapshots every 10 s per unique state via _write_snapshot().
    """
    # ── Protocol selection ───────────────────────────────────────────────────
    if active_protocol == "E91" and auto_mitigate:
        effective_attack = 0.0
    elif active_protocol == "E91":
        effective_attack = attack_probability * 0.5
    else:
        effective_attack = attack_probability

    # ── QBER calculation ─────────────────────────────────────────────────────
    base_qber   = (noise_level / 2.0) + (effective_attack * 0.25)
    fluctuation = (random.uniform(-0.15, 0.15) * base_qber
                   if base_qber > 0 else random.uniform(0, 0.008))
    current_qber  = max(0.001, min(1.0, base_qber + fluctuation))
    base_key_rate = max(0.0, 0.5 - (current_qber * 2.5))

    # ── ML inference ─────────────────────────────────────────────────────────
    sifted_key_length = int(base_key_rate * 2500)
    try:
        prediction = predict(current_qber, noise_level, sifted_key_length, model_type)
    except Exception:
        prediction = {
            "threat_level":     "LOW",
            "confidence_score": 0.0,
            "model_used":       model_type,
            "eve_contribution": 0.0,
        }

    # ── Mitigation engine ────────────────────────────────────────────────────
    mitigation_status = "NONE"
    final_key_rate    = base_key_rate

    if auto_mitigate:
        if active_protocol == "E91":
            mitigation_status = "E91_ACTIVE"
            safe_qber    = noise_level / 2.0
            current_qber = safe_qber
            final_key_rate = max(0.35, 0.48 - (safe_qber * 1.2))
        elif active_protocol == "BB84" and attack_probability > 0.5:
            mitigation_status = "PA_ACTIVE"
            safe_qber    = noise_level / 2.0
            current_qber = safe_qber
            pa_base_rate = max(0.15, 0.5 - (safe_qber * 2.5))
            final_key_rate = pa_base_rate * 0.85

    # ── Thermal noise injection (telemetry unfreeze) ─────────────────────────
    current_qber     = max(0.001, min(0.99,
                           current_qber + random.uniform(-0.006, 0.006)))
    thermal_kr       = random.uniform(-0.025, 0.025)
    current_key_rate = (max(0.01, final_key_rate + thermal_kr)
                        if mitigation_status != "NONE"
                        else max(0.0, final_key_rate + thermal_kr))

    # ── Status resolution ────────────────────────────────────────────────────
    status = "SECURE"
    if   active_protocol == "E91" and mitigation_status == "E91_ACTIVE":
        status = "SECURE (E91 SHIELDED)"
    elif active_protocol == "E91" and effective_attack > 0.0:
        status = "COMPROMISED (BELL VIOLATION)"
    elif mitigation_status == "PA_ACTIVE":
        status = "MITIGATED (PA ACTIVE)"
    elif current_qber > 0.11 or effective_attack > 0.0:
        status = "COMPROMISED"

    # ── DB snapshot ──────────────────────────────────────────────────────────
    if _should_snapshot(active_protocol, attack_probability, auto_mitigate):
        _write_snapshot(noise_level, attack_probability, current_qber,
                        sifted_key_length, prediction)

    return {
        "qber":               round(current_qber, 4),
        "key_rate":           round(current_key_rate, 4),
        "sifted_key_length":  sifted_key_length,
        "noise_level":        noise_level,
        "status":             status,
        "mitigation_status":  mitigation_status,
        "active_protocol":    active_protocol,
        "attack_probability": attack_probability,
        "threat_level":       prediction["threat_level"],
        "confidence_score":   prediction["confidence_score"],
        "model_used":         prediction["model_used"],
        "eve_contribution":   prediction["eve_contribution"],
    }
