"""
bb84_simulator.py
=================
Standalone simulation of the BB84 Quantum Key Distribution (QKD) protocol.

Features
--------
* Alice prepares random qubits in Z-basis (|0>, |1>) or X-basis (|+>, |->).
* Bob measures in a random basis.
* Classical sifting phase retains only matching-basis bits.
* Parameterised depolarising noise (Qiskit Aer) simulates fibre-optic loss.
* Intercept-resend eavesdropper (Eve) controlled by attack_probability.
* Returns QBER, initial_key_length, sifted_key_length, alice_key, bob_key.

Fixes applied (v2)
------------------
  FIX-1  _alice_prepare now returns QuantumCircuit(1) — no stray classical bit.
  FIX-2  Noise model now targets Qiskit 1.x basis gates ("id","rz","sx","x")
         so depolarising error is actually attached to executed instructions.
  FIX-3  AerSimulator for Eve created ONCE per simulate_bb84 call, not per qubit.
  FIX-4  AerSimulator for Bob created ONCE per simulate_bb84 call, not per qubit.
  FIX-5  Eve re-encodes into QuantumCircuit(1) — no classical register included,
         eliminating the register-conflict when Bob adds his own bit later.
  FIX-6  main() now runs a comprehensive test suite covering best-case,
  FIX-7  seed_simulator passed to both AerSimulator constructors so Qiskit Aer's
         internal RNG is also seeded — full end-to-end reproducibility (TC-15).
         worst-case, partial attacks, zero noise, high noise, and invalid inputs.

Dependencies
------------
    pip install qiskit qiskit-aer numpy
"""

import random
import numpy as np
from typing import Optional

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_noise_model(noise_level: float) -> Optional[NoiseModel]:
    """
    Build a depolarising noise model using Qiskit 1.x basis gate names.

    FIX-2: Previous version targeted {"u","u1","u2","u3","h"} which are NOT
    in the Qiskit 1.x default basis set, so noise was silently ignored.
    Correct basis gates after transpilation are: "id", "rz", "sx", "x".

    Parameters
    ----------
    noise_level : float
        Depolarising error probability in [0.0, 1.0].
        0.0 → perfect channel (returns None for zero overhead).

    Returns
    -------
    NoiseModel | None
    """
    if noise_level <= 0.0:
        return None

    noise_model = NoiseModel()
    dep_error = depolarizing_error(noise_level, 1)

    # FIX-2: Qiskit 1.x compiles single-qubit gates into these basis gates.
    # Adding noise to all of them guarantees the error is actually applied.
    single_qubit_basis_gates = ["id", "rz", "sx", "x"]
    noise_model.add_all_qubit_quantum_error(dep_error, single_qubit_basis_gates)
    return noise_model


def _alice_prepare(bit: int, basis: int) -> QuantumCircuit:
    """
    Prepare Alice's qubit state as a bare quantum circuit (NO classical bit).

    FIX-1: Previous version created QuantumCircuit(1, 1). That stray classical
    bit caused a register conflict when _bob_measure or _eve_intercept later
    appended their own measure(0, 0) — both writing to classical bit 0 of two
    different registers, leading to ambiguous counts.

    Encoding:
        Z-basis (basis=0): bit=0 → |0⟩,  bit=1 → |1⟩
        X-basis (basis=1): bit=0 → |+⟩,  bit=1 → |−⟩

    Parameters
    ----------
    bit   : int — 0 or 1
    basis : int — 0 (Z-basis) or 1 (X-basis)

    Returns
    -------
    QuantumCircuit — 1 qubit, NO classical bits
    """
    qc = QuantumCircuit(1)      # FIX-1: bare qubit, no classical register
    if bit == 1:
        qc.x(0)
    if basis == 1:
        qc.h(0)
    return qc


def _eve_intercept(
    qc: QuantumCircuit,
    eve_sim: AerSimulator,
) -> QuantumCircuit:
    """
    Eve performs an intercept-resend attack.

    She measures Alice's qubit in a random basis on her own noiseless device,
    then re-encodes what she observed and sends a fresh qubit to Bob.

    FIX-3: eve_sim is passed in (created once per simulation call) rather than
            instantiated here on every intercepted qubit.
    FIX-5: Returned circuit is QuantumCircuit(1) — no classical bit — to avoid
            register conflicts when _bob_measure appends its measurement.

    Parameters
    ----------
    qc      : QuantumCircuit — Alice's prepared qubit (1 qubit, no clbits)
    eve_sim : AerSimulator  — pre-built noiseless simulator for Eve

    Returns
    -------
    QuantumCircuit — Eve's re-encoded qubit (1 qubit, NO classical bits)
    """
    eve_basis = random.randint(0, 1)

    # --- Eve's measurement circuit (adds its own temporary clbit) ---
    eve_qc = QuantumCircuit(1, 1)      # fresh circuit with 1 qubit + 1 clbit
    eve_qc.compose(qc, inplace=True)   # apply Alice's gates on top
    if eve_basis == 1:
        eve_qc.h(0)
    eve_qc.measure(0, 0)

    compiled  = transpile(eve_qc, eve_sim)
    counts    = eve_sim.run(compiled, shots=1).result().get_counts()
    eve_bit   = int(list(counts.keys())[0])

    # --- Eve re-prepares her fresh qubit (no classical register) ---
    # FIX-5: QuantumCircuit(1) — Bob will attach his own clbit later
    new_qc = QuantumCircuit(1)
    if eve_bit == 1:
        new_qc.x(0)
    if eve_basis == 1:
        new_qc.h(0)

    return new_qc


def _bob_measure(
    qc: QuantumCircuit,
    basis: int,
    bob_sim: AerSimulator,
) -> int:
    """
    Bob measures the received qubit in his chosen basis.

    FIX-4: bob_sim is passed in (created once per simulation call) rather than
            instantiated here on every qubit.

    Parameters
    ----------
    qc      : QuantumCircuit — qubit received (no classical bits)
    basis   : int            — 0 (Z) or 1 (X)
    bob_sim : AerSimulator   — pre-built simulator (may carry noise model)

    Returns
    -------
    int — Bob's measurement outcome (0 or 1)
    """
    # Bob creates a fresh measurement circuit
    meas_qc = QuantumCircuit(1, 1)      # 1 qubit + own clbit
    meas_qc.compose(qc, inplace=True)   # apply received qubit's gates
    if basis == 1:
        meas_qc.h(0)                    # rotate X-basis → Z-basis for measurement
    meas_qc.measure(0, 0)

    compiled = transpile(meas_qc, bob_sim)
    counts   = bob_sim.run(compiled, shots=1).result().get_counts()
    return int(list(counts.keys())[0])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def simulate_bb84(
    num_qubits: int        = 200,
    noise_level: float     = 0.02,
    attack_probability: float = 0.0,
    seed: Optional[int]    = None,
) -> dict:
    """
    Simulate the BB84 QKD protocol end-to-end.

    Parameters
    ----------
    num_qubits         : int   — total qubits Alice transmits (must be ≥ 1)
    noise_level        : float — depolarising error rate in [0.0, 1.0]
    attack_probability : float — probability each qubit intercepted by Eve
                                 0.0 = no eavesdropper  |  1.0 = full attack
    seed               : int | None — optional RNG seed for reproducibility

    Returns
    -------
    dict:
        qber               : float — Quantum Bit Error Rate on sifted key
        initial_key_length : int   — num_qubits sent by Alice
        sifted_key_length  : int   — key bits after basis sifting
        alice_key          : list  — Alice's sifted bits
        bob_key            : list  — Bob's sifted bits (may differ from Alice's)

    Raises
    ------
    ValueError — if num_qubits < 1 or any float param is out of [0, 1]
    """
    # --- Input validation ---
    if num_qubits < 1:
        raise ValueError(f"num_qubits must be ≥ 1, got {num_qubits}")
    if not (0.0 <= noise_level <= 1.0):
        raise ValueError(f"noise_level must be in [0.0, 1.0], got {noise_level}")
    if not (0.0 <= attack_probability <= 1.0):
        raise ValueError(
            f"attack_probability must be in [0.0, 1.0], got {attack_probability}"
        )

    # --- Reproducibility (FIX-7) ---
    # Both Python's random module AND Qiskit Aer's internal RNG must be seeded.
    # random.seed()  → controls basis choices, attack decisions (classical layer)
    # seed_simulator → controls shot sampling inside AerSimulator (quantum layer)
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)   # numpy RNG used internally by some Aer paths
    aer_seed = seed  # may be None (non-deterministic) or int (deterministic)

    # --- FIX-3 & FIX-4: Build simulators ONCE per call, reuse per qubit ---
    noise_model = _build_noise_model(noise_level)
    eve_sim = AerSimulator(seed_simulator=aer_seed)                 # noiseless
    bob_sim = (AerSimulator(noise_model=noise_model,
                            seed_simulator=aer_seed)
               if noise_model
               else AerSimulator(seed_simulator=aer_seed))          # noisy / clean

    # ── Step 1: Alice generates random bits + bases ──────────────────────────
    alice_bits  = [random.randint(0, 1) for _ in range(num_qubits)]
    alice_bases = [random.randint(0, 1) for _ in range(num_qubits)]

    # ── Step 2: Bob picks random measurement bases ───────────────────────────
    bob_bases   = [random.randint(0, 1) for _ in range(num_qubits)]
    bob_results = []

    # ── Step 3: Quantum transmission (qubit-by-qubit) ────────────────────────
    for i in range(num_qubits):
        qc = _alice_prepare(alice_bits[i], alice_bases[i])

        if random.random() < attack_probability:
            qc = _eve_intercept(qc, eve_sim)

        bob_bit = _bob_measure(qc, bob_bases[i], bob_sim)
        bob_results.append(bob_bit)

    # ── Step 4: Classical sifting ─────────────────────────────────────────────
    alice_sifted, bob_sifted = [], []
    for i in range(num_qubits):
        if alice_bases[i] == bob_bases[i]:
            alice_sifted.append(alice_bits[i])
            bob_sifted.append(bob_results[i])

    sifted_key_length = len(alice_sifted)

    # ── Step 5: QBER ──────────────────────────────────────────────────────────
    if sifted_key_length == 0:
        qber = 0.0
    else:
        errors = sum(a != b for a, b in zip(alice_sifted, bob_sifted))
        qber   = errors / sifted_key_length

    return {
        "qber":               round(qber, 6),
        "initial_key_length": num_qubits,
        "sifted_key_length":  sifted_key_length,
        "alice_key":          alice_sifted,
        "bob_key":            bob_sifted,
    }


# ---------------------------------------------------------------------------
# FIX-6: Comprehensive test suite (best-case, worst-case, edge cases)
# ---------------------------------------------------------------------------

def _print_result(label: str, result: dict, expected_qber_range: tuple) -> bool:
    """Pretty-print one test result and return True if QBER is in expected range."""
    qber_pct = result["qber"] * 100
    lo, hi   = expected_qber_range
    passed   = lo <= qber_pct <= hi
    status   = "✅ PASS" if passed else "❌ FAIL"
    print(
        f"  {status}  {label:<45}"
        f"  QBER={qber_pct:5.2f}%  sifted={result['sifted_key_length']:>4}"
        f"  (expected {lo:.0f}–{hi:.0f}%)"
    )
    return passed


def main():
    """
    FIX-6: Run a full suite of test scenarios instead of only 0% and 100%.

    Test coverage
    -------------
    TC-01  BEST CASE  — zero noise, no Eve        → QBER ≈ 0 %
    TC-02  REALISTIC  — low noise, no Eve          → QBER ≈ 0–6 %
    TC-03  WORST CASE — high noise, no Eve         → QBER ≈ 0–20 %
    TC-04  FULL EVE   — zero noise, full attack    → QBER ≈ 23–27 %
    TC-05  FULL EVE   — realistic noise + Eve      → QBER ≈ 25–32 %
    TC-06  PARTIAL    — 50% Eve probability        → QBER ≈ 10–20 %
    TC-07  TINY       — single qubit (edge case)   → must not crash
    TC-08  LARGE      — 1000 qubits (scale test)   → QBER stable
    TC-09  INVALID    — bad noise_level             → ValueError raised
    TC-10  INVALID    — bad attack_probability      → ValueError raised
    TC-11  INVALID    — zero qubits                → ValueError raised
    TC-12  SEED       — same seed → same result    → deterministic output
    """
    SEP  = "=" * 78
    SEP2 = "-" * 78
    N    = 300    # qubit count for most tests (speed vs. statistical stability)

    print(SEP)
    print("  QuantumCipherSim — BB84 Simulator v2   FULL TEST SUITE")
    print(SEP)

    passed_total = 0
    failed_total = 0

    # ── Functional Tests ────────────────────────────────────────────────────
    print("\n── Functional Tests ──────────────────────────────────────────────────")

    tests = [
        # label                     num_q  noise   atk    qber_lo  qber_hi
        # TC-01..03: No Eve — QBER driven only by channel depolarising noise.
        # TC-04..06: With Eve — theory predicts ~25% base + noise contribution.
        # Ranges are 3-sigma bounds: σ=√(p·q/n), with n≈145 sifted bits.
        # Do NOT pass seed= here: functional tests must sample randomly to
        # verify statistical properties, not one lucky/unlucky deterministic draw.
        ("TC-01 Zero noise, no Eve",     N, 0.00, 0.00,    0.0,   2.0),
        ("TC-02 Low noise,  no Eve",     N, 0.03, 0.00,    0.0,   8.0),
        ("TC-03 High noise, no Eve",     N, 0.15, 0.00,    0.0,  22.0),
        # Full Eve: theoretical QBER=25%, 3σ≈±11% → range 14–36%
        ("TC-04 Full Eve,   zero noise", N, 0.00, 1.00,   14.0,  37.0),
        # Full Eve + 3% noise: QBER≈28%, 3σ≈11% → range 15–40%
        ("TC-05 Full Eve,   low noise",  N, 0.03, 1.00,   15.0,  40.0),
        # 50% Eve: QBER≈12.5%, 3σ≈9% → range 3–22%
        ("TC-06 Partial Eve (50%)",      N, 0.03, 0.50,    3.0,  22.0),
        # Single qubit: sifted key may be 0, any QBER valid — just must not crash
        ("TC-07 Single qubit",           1, 0.03, 0.50,    0.0, 100.0),
        # Large scale: more sifted bits → tighter variance, keep 23–30%
        ("TC-08 Large scale (1000 q)",1000, 0.03, 1.00,   21.0,  31.0),
    ]

    for label, nq, noise, atk, lo, hi in tests:
        result = simulate_bb84(num_qubits=nq, noise_level=noise,
                               attack_probability=atk)  # no seed: statistical test
        ok = _print_result(label, result, (lo, hi))
        if ok:
            passed_total += 1
        else:
            failed_total += 1

    # ── Edge-Case / Input Validation Tests ──────────────────────────────────
    print(f"\n{SEP2}")
    print("── Input Validation Tests (must raise ValueError) ────────────────────")

    invalid_cases = [
        ("TC-09 noise_level = -0.1",       dict(num_qubits=10, noise_level=-0.1,  attack_probability=0.5)),
        ("TC-10 noise_level = 1.5",        dict(num_qubits=10, noise_level=1.5,   attack_probability=0.5)),
        ("TC-11 attack_probability = -0.5",dict(num_qubits=10, noise_level=0.05,  attack_probability=-0.5)),
        ("TC-12 attack_probability = 2.0", dict(num_qubits=10, noise_level=0.05,  attack_probability=2.0)),
        ("TC-13 num_qubits = 0",           dict(num_qubits=0,  noise_level=0.05,  attack_probability=0.0)),
        ("TC-14 num_qubits = -5",          dict(num_qubits=-5, noise_level=0.05,  attack_probability=0.0)),
    ]

    for label, kwargs in invalid_cases:
        try:
            simulate_bb84(**kwargs)
            print(f"  ❌ FAIL  {label:<45}  (no exception raised — should have!)")
            failed_total += 1
        except ValueError as exc:
            print(f"  ✅ PASS  {label:<45}  ValueError: {exc}")
            passed_total += 1

    # ── Determinism / Seed Test ──────────────────────────────────────────────
    print(f"\n{SEP2}")
    print("── Seed Reproducibility Test ─────────────────────────────────────────")

    r1 = simulate_bb84(num_qubits=100, noise_level=0.03,
                       attack_probability=0.5, seed=7)
    r2 = simulate_bb84(num_qubits=100, noise_level=0.03,
                       attack_probability=0.5, seed=7)
    same = (r1["alice_key"] == r2["alice_key"] and r1["qber"] == r2["qber"])
    status = "✅ PASS" if same else "❌ FAIL"
    print(f"  {status}  TC-15 Same seed (7) → identical alice_key & QBER: {same}")
    if same:
        passed_total += 1
    else:
        failed_total += 1

    r3 = simulate_bb84(num_qubits=100, noise_level=0.03,
                       attack_probability=0.5, seed=99)
    different = (r1["alice_key"] != r3["alice_key"])
    status = "✅ PASS" if different else "❌ FAIL"
    print(f"  {status}  TC-16 Different seed → different alice_key: {different}")
    if different:
        passed_total += 1
    else:
        failed_total += 1

    # ── Final Summary ────────────────────────────────────────────────────────
    total = passed_total + failed_total
    print(f"\n{SEP}")
    print("  FINAL SUMMARY")
    print(SEP)
    print(f"  Tests passed : {passed_total} / {total}")
    print(f"  Tests failed : {failed_total} / {total}")

    if failed_total == 0:
        print("\n  🎉  ALL TESTS PASSED — Foundation is SOLID. Ready for Phase 2.")
    else:
        print("\n  ⚠️  Some tests failed — review output above before proceeding.")
    print(SEP)


if __name__ == "__main__":
    main()
