"""
backend/routers/simulate.py
===========================
POST /simulate — runs BB84 simulation and logs to DB.

Simulation strategy (tiered by num_qubits):
  - num_qubits <= 500 : Qiskit Aer  (full quantum circuit, ~3-6s)
  - num_qubits > 500  : NumPy statistical simulator (~0.001s)
                        Physically identical outputs (same physics model).
                        Used for large requests to keep API responsive.

The NumPy simulator is NOT a shortcut — it implements the same statistical
physics as the Qiskit circuit. It's used in production for the ML training
dataset (50,000 rows) for the same reason.
"""

import sys
import os
import uuid
import numpy as np
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from backend.schemas   import SimulateRequest, SimulateResponse
from backend.models    import SimulationRun
from backend.database  import get_db
from ml.inference      import compute_features

# Qiskit simulator (high-fidelity, slower)
try:
    from bb84_simulator import simulate_bb84 as _qiskit_simulate
    _QISKIT_AVAILABLE = True
    print("[simulate] Qiskit simulator loaded OK")
except ImportError as _e:
    _QISKIT_AVAILABLE = False
    print(f"[simulate] WARNING: Qiskit simulator not available: {_e}")

# NumPy statistical simulator (fast, same physics)
try:
    from ml.generate_dataset import fast_simulate_bb84 as _fast_sim
    _FAST_SIM_AVAILABLE = True
    print("[simulate] NumPy fast simulator loaded OK")
except ImportError as _e:
    _FAST_SIM_AVAILABLE = False
    print(f"[simulate] WARNING: NumPy fast simulator not available: {_e}")

# Threshold: above this, use NumPy simulator for acceptable response times
_QISKIT_QUBIT_LIMIT = 500

router = APIRouter(prefix="/simulate", tags=["simulation"])


def _run_fast_simulation(
    num_qubits: int,
    noise_level: float,
    attack_probability: float,
    seed: int | None,
) -> dict:
    """
    NumPy statistical simulator for num_qubits > 500.
    Returns same dict schema as simulate_bb84().
    """
    rng            = np.random.default_rng(seed)
    nq             = np.array([num_qubits])
    noise          = np.array([noise_level])
    attack         = np.array([attack_probability])

    qber_obs, sifted = _fast_sim(nq, noise, attack, rng)

    return {
        "qber":               float(round(qber_obs[0], 6)),
        "initial_key_length": num_qubits,
        "sifted_key_length":  int(sifted[0]),
    }


@router.post("", response_model=SimulateResponse)
def run_simulation(
    req: SimulateRequest,
    db: Session = Depends(get_db),
):
    """
    Run a BB84 QKD simulation.

    Routing:
      num_qubits <= 500  -> Qiskit Aer (quantum circuit simulation)
      num_qubits > 500   -> NumPy statistical simulator (same physics, instant)

    Both return identical response formats.
    Computes eve_qber_contribution and logs to DB.
    """
    use_qiskit = req.num_qubits <= _QISKIT_QUBIT_LIMIT and _QISKIT_AVAILABLE

    if not use_qiskit and not _FAST_SIM_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="No simulator available. Ensure bb84_simulator or "
                   "ml/generate_dataset.py is importable."
        )

    # Run appropriate simulator
    try:
        if use_qiskit:
            result = _qiskit_simulate(
                num_qubits=req.num_qubits,
                noise_level=req.noise_level,
                attack_probability=req.attack_probability,
                seed=req.seed,
            )
        else:
            result = _run_fast_simulation(
                num_qubits=req.num_qubits,
                noise_level=req.noise_level,
                attack_probability=req.attack_probability,
                seed=req.seed,
            )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {exc}"
        )

    qber              = result["qber"]
    sifted_key_length = result["sifted_key_length"]

    # Compute derived feature
    features         = compute_features(qber, req.noise_level, sifted_key_length)
    eve_contribution = float(features[0, 3])

    # Ground truth: attack if attack_probability >= 0.3
    actual_attack = (req.attack_probability >= 0.3)

    # Write to DB (non-fatal if DB unavailable)
    session_id = str(uuid.uuid4())
    try:
        row = SimulationRun(
            session_id            = session_id,
            timestamp             = datetime.now(timezone.utc),
            num_qubits            = req.num_qubits,
            noise_level           = req.noise_level,
            attack_probability    = req.attack_probability,
            final_qber            = qber,
            sifted_key_length     = sifted_key_length,
            eve_qber_contribution = eve_contribution,
            actual_attack_status  = actual_attack,
        )
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()

    return SimulateResponse(
        session_id            = session_id,
        qber                  = qber,
        initial_key_length    = result["initial_key_length"],
        sifted_key_length     = sifted_key_length,
        eve_qber_contribution = round(eve_contribution, 6),
        noise_level           = req.noise_level,
        attack_probability    = req.attack_probability,
    )
