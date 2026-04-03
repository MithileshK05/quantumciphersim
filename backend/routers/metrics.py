from fastapi import APIRouter, Query
import random
from ml.inference import predict

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"]
)

@router.get("/")
def get_live_metrics(
    noise_level: float = Query(0.0),
    attack_probability: float = Query(0.0),
    model_type: str = Query("gradient_boosting"),
    auto_mitigate: bool = Query(False),
    active_protocol: str = Query("BB84")
):
    """
    Simulates a live datastream of the QKD channel for the React Query polling hook.
    Unified Architectural Patch v2:
    - PA activates on attack_probability > 0.5 (not ML threat level) for determinism
    - Thermal noise injected into ALL outputs to prevent frozen telemetry graphs
    - E91 and BB84 mitigation paths both guarantee non-zero, fluctuating key rates
    """
    # ── Protocol Selection ───────────────────────────────────────────────────
    # E91 entanglement correlations make intercept-resend harder but NOT immune.
    # With no mitigation: Eve degrades fidelity by 50%. With mitigation: full bypass.
    if active_protocol == "E91" and auto_mitigate:
        effective_attack = 0.0          # Fully shielded by entanglement routing
    elif active_protocol == "E91":
        effective_attack = attack_probability * 0.5  # Partial resistance only
    else:
        effective_attack = attack_probability

    # ── Base QBER Calculation ────────────────────────────────────────────────
    # base_qber = noise/2 + effective_attack*0.25
    base_qber = (noise_level / 2.0) + (effective_attack * 0.25)

    # Add +/- 15% fluctuation to the base QBER for visual realism
    fluctuation = random.uniform(-0.15, 0.15) * base_qber if base_qber > 0 else random.uniform(0, 0.008)
    current_qber = max(0.001, min(1.0, base_qber + fluctuation))

    # Base Key Rate (perfect scenario = 0.5 because 50% basis match probability)
    base_key_rate = max(0.0, 0.5 - (current_qber * 2.5))

    # ── ML Inference for Threat Detection ───────────────────────────────────
    sifted_key_length = int(base_key_rate * 2500)
    try:
        prediction = predict(current_qber, noise_level, sifted_key_length, model_type)
    except Exception:
        prediction = {"threat_level": "LOW", "confidence_score": 0.0, "model_used": model_type, "eve_contribution": 0.0}

    # ── Mitigation Engine ────────────────────────────────────────────────────
    # PATCH v2 FIX: PA activates when attack_probability > 0.5 (attack is ON),
    # NOT when ML says "HIGH". This prevents the ML re-classification causing
    # PA to silently deactivate after QBER drops, killing the key rate.
    mitigation_status = "NONE"
    final_key_rate = base_key_rate

    if auto_mitigate:
        if active_protocol == "E91":
            # E91: Entanglement routing shields the channel completely
            mitigation_status = "E91_ACTIVE"
            # Restore healthy baseline QBER for E91 shielded state
            safe_qber = noise_level / 2.0
            current_qber = safe_qber
            # E91 is more efficient than BB84: higher base key rate
            final_key_rate = max(0.35, 0.48 - (safe_qber * 1.2))

        elif active_protocol == "BB84" and attack_probability > 0.5:
            # BB84 Privacy Amplification: activates when actively under attack
            mitigation_status = "PA_ACTIVE"
            # Reset QBER to safe baseline (channel cleaned up by PA)
            safe_qber = noise_level / 2.0
            current_qber = safe_qber
            # PA compresses the key by ~15% due to hash function overhead
            pa_base_rate = max(0.15, 0.5 - (safe_qber * 2.5))
            final_key_rate = pa_base_rate * 0.85

    # ── THERMAL NOISE INJECTION (Telemetry Unfreeze Patch) ──────────────────
    # CRITICAL: Always inject small random noise AFTER mitigation sets values.
    # This guarantees backend NEVER returns identical consecutive payloads,
    # preventing React Query cache from suppressing re-renders and freezing graphs.
    thermal_qber = random.uniform(-0.006, 0.006)
    current_qber = max(0.001, min(0.99, current_qber + thermal_qber))

    thermal_kr = random.uniform(-0.025, 0.025)
    if mitigation_status != "NONE":
        # Mitigated: floor at 0.01 to always show active defense
        current_key_rate = max(0.01, final_key_rate + thermal_kr)
    else:
        current_key_rate = max(0.0, final_key_rate + thermal_kr)

    # ── Status Resolution ────────────────────────────────────────────────────
    status = "SECURE"
    if active_protocol == "E91" and mitigation_status == "E91_ACTIVE":
        status = "SECURE (E91 SHIELDED)"
    elif active_protocol == "E91" and effective_attack > 0.0:
        status = "COMPROMISED (BELL VIOLATION)"
    elif mitigation_status == "PA_ACTIVE":
        status = "MITIGATED (PA ACTIVE)"
    elif current_qber > 0.11 or effective_attack > 0.0:
        status = "COMPROMISED"

    return {
        "qber": round(current_qber, 4),
        "key_rate": round(current_key_rate, 4),
        "sifted_key_length": sifted_key_length,
        "noise_level": noise_level,
        "status": status,
        "mitigation_status": mitigation_status,
        "active_protocol": active_protocol,
        "attack_probability": attack_probability,
        "threat_level": prediction["threat_level"],
        "confidence_score": prediction["confidence_score"],
        "model_used": prediction["model_used"],
        "eve_contribution": prediction["eve_contribution"]
    }
