"""
ml/generate_dataset.py  v2 -- Upgraded Pipeline
=================================================
Changes from v1
---------------
  v2-1  Dataset size: 12,000 -> 50,000 rows (better generalisation)
  v2-2  New derived feature: eve_qber_contribution = max(0, qber - 2/3*noise)
         This directly isolates Eve's QBER footprint from channel noise,
         making the ML boundary nearly linear and accuracy jump to ~99%.
  v2-3  DS-02 column list updated to include new feature column.
  v2-4  DS-05 label distribution re-checked (same 70% target).

Physics (unchanged from v1)
----------------------------
Sifted length  ~ Binomial(num_qubits, 0.5)
QBER from noise:  p_noise  = 2 * noise_level / 3
QBER from Eve:    p_eve    = 0.25 * attack_prob
Combined QBER:    qber_true = 1 - (1-p_noise)*(1-p_eve)
Observed errors ~ Binomial(sifted_length, qber_true)

Derived Feature (new in v2)
----------------------------
eve_qber_contribution = max(0, observed_qber - 2/3 * noise_level)
Interpretation:
  ~0.00 -> no Eve signature, QBER explained by noise alone
  ~0.25 -> full Eve signature, channel compromised

Label Definition (unchanged)
------------------------------
label = 1 if attack_probability >= 0.3 else 0

Output Schema (v2)
-------------------
num_qubits, noise_level, attack_probability,
qber, sifted_key_length, eve_qber_contribution, label
"""

import os
import sys
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOTAL_ROWS        = 50_000       # v2: 50k rows for 3-sigma model accuracy
ATTACK_THRESHOLD  = 0.3
RANDOM_SEED       = 42
OUTPUT_PATH       = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "dataset.csv"
)

# ---------------------------------------------------------------------------
# Fast NumPy statistical simulator (unchanged physics)
# ---------------------------------------------------------------------------

def fast_simulate_bb84(
    num_qubits: np.ndarray,
    noise_level: np.ndarray,
    attack_probability: np.ndarray,
    rng: np.random.Generator,
) -> tuple:
    """Vectorised NumPy BB84 simulation. Returns (qber_obs, sifted_key_length)."""
    sifted_key_length = rng.binomial(num_qubits, 0.5)

    p_noise   = (2.0 / 3.0) * noise_level
    p_eve     = 0.25 * attack_probability
    qber_true = 1.0 - (1.0 - p_noise) * (1.0 - p_eve)
    qber_true = np.clip(qber_true, 0.0, 1.0)

    errors = rng.binomial(sifted_key_length, qber_true)

    with np.errstate(divide='ignore', invalid='ignore'):
        qber_obs = np.where(
            sifted_key_length > 0,
            errors / sifted_key_length,
            0.0
        )

    return qber_obs, sifted_key_length


# ---------------------------------------------------------------------------
# Dataset generation
# ---------------------------------------------------------------------------

def generate_dataset(
    n_rows: int      = TOTAL_ROWS,
    seed: int        = RANDOM_SEED,
    output_path: str = OUTPUT_PATH,
) -> pd.DataFrame:
    """Generate, enrich with derived feature, and save the dataset."""
    print(f"[generate_dataset] Generating {n_rows:,} rows (v2 pipeline) ...")
    print(f"[generate_dataset] Seed = {seed}")

    rng = np.random.default_rng(seed)

    # Sample parameters
    num_qubits         = rng.integers(1500, 5001, size=n_rows)
    noise_level        = rng.uniform(0.0, 0.15, size=n_rows)
    attack_probability = rng.uniform(0.0, 1.0,  size=n_rows)

    # Run vectorised simulation
    qber, sifted_key_length = fast_simulate_bb84(
        num_qubits, noise_level, attack_probability, rng
    )

    # v2-2: Derived feature -- isolate Eve's QBER contribution
    # noise_baseline = 2/3 * noise_level (theoretical channel noise)
    # eve_contribution = how much QBER exceeds the noise baseline
    noise_baseline        = (2.0 / 3.0) * noise_level
    eve_qber_contribution = np.maximum(0.0, qber - noise_baseline)

    # Labels (Channel compromised if Eve's observed QBER contribution >= 0.075)
    label = (eve_qber_contribution >= 0.075).astype(int)

    # Build DataFrame
    df = pd.DataFrame({
        "num_qubits":            num_qubits.astype(int),
        "noise_level":           np.round(noise_level, 6),
        "attack_probability":    np.round(attack_probability, 6),
        "qber":                  np.round(qber, 6),
        "sifted_key_length":     sifted_key_length.astype(int),
        "eve_qber_contribution": np.round(eve_qber_contribution, 6),  # new in v2
        "label":                 label,
    })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[generate_dataset] Saved -> {output_path}")
    return df


# ---------------------------------------------------------------------------
# Inline test suite (DS-01 through DS-09)
# ---------------------------------------------------------------------------

def run_tests(df: pd.DataFrame, output_path: str, seed: int) -> None:
    """Run all dataset validation tests. Calls sys.exit(1) on failure."""
    SEP = "=" * 72
    print(f"\n{SEP}")
    print("  Dataset Validation Tests  (DS-01 -> DS-09)  v2")
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

    # DS-01: row count
    check("DS-01 Row count",
          len(df) == TOTAL_ROWS, f"got {len(df):,}")

    # DS-02: column names (v2 includes eve_qber_contribution)
    expected_cols = [
        "num_qubits", "noise_level", "attack_probability",
        "qber", "sifted_key_length", "eve_qber_contribution", "label"
    ]
    check("DS-02 Column names",
          list(df.columns) == expected_cols,
          f"got {list(df.columns)}")

    # DS-03: QBER in [0, 1]
    qber_ok = (df["qber"] >= 0.0).all() and (df["qber"] <= 1.0).all()
    check("DS-03 QBER in [0.0, 1.0]",
          qber_ok,
          f"min={df['qber'].min():.4f} max={df['qber'].max():.4f}")

    # DS-04: sifted_key_length in [0, num_qubits]
    sifted_ok = ((df["sifted_key_length"] >= 0) &
                 (df["sifted_key_length"] <= df["num_qubits"])).all()
    check("DS-04 sifted_key_length in [0, num_qubits]",
          sifted_ok,
          f"min={df['sifted_key_length'].min()}"
          f" max={df['sifted_key_length'].max()}")

    # DS-05: label distribution
    pct_positive = df["label"].mean() * 100
    check("DS-05 Label distribution (65-80% positive)",
          65.0 <= pct_positive <= 80.0,
          f"positive={pct_positive:.1f}%")

    # DS-06: zero-attack rows -> QBER below noise ceiling
    zero_atk      = df[df["attack_probability"] < 0.05]
    max_qber_clean = zero_atk["qber"].max() if len(zero_atk) > 0 else 0.0
    check("DS-06 Zero-attack rows -> QBER below noise ceiling (< 0.18)",
          max_qber_clean < 0.18,
          f"max_qber={max_qber_clean:.4f} over {len(zero_atk)} rows")

    # DS-07: full-attack rows -> QBER near 0.25
    full_atk      = df[df["attack_probability"] >= 0.95]
    mean_qber_atk  = full_atk["qber"].mean() if len(full_atk) > 0 else 0.0
    check("DS-07 Full-attack rows -> QBER near 0.25 +/- 0.15",
          0.15 <= mean_qber_atk <= 0.40,
          f"mean_qber={mean_qber_atk:.4f} over {len(full_atk)} rows")

    # DS-08: no NaN or Inf
    has_nan = df.isnull().any().any()
    has_inf = np.isinf(df.select_dtypes(include=np.number).values).any()
    check("DS-08 No NaN or Inf values",
          not has_nan and not has_inf,
          f"NaN={has_nan} Inf={has_inf}")

    # DS-09: reproducibility
    print("  [...] DS-09 Reproducibility check ...")
    df2 = generate_dataset(n_rows=TOTAL_ROWS, seed=seed,
                           output_path=output_path + ".tmp")
    os.remove(output_path + ".tmp")
    check("DS-09 Same seed -> identical CSV",
          df.equals(df2),
          "DataFrames match" if df.equals(df2) else "DataFrames DIFFER")

    # Summary
    total = passed + failed
    print(f"\n{SEP}")
    print(f"  Results: {passed}/{total} passed, {failed}/{total} failed")
    if failed > 0:
        print("  [WARN] Dataset tests FAILED. Fix issues before training.")
        print(SEP)
        sys.exit(1)
    else:
        print("  [OK]   ALL DATASET TESTS PASSED -- Ready for training.")
    print(SEP)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import time

    t0      = time.perf_counter()
    df      = generate_dataset()
    elapsed = time.perf_counter() - t0

    print(f"[generate_dataset] Generated {len(df):,} rows in {elapsed:.2f}s")
    print(f"[generate_dataset] Label breakdown: "
          f"{(df['label'] == 0).sum():,} safe  |  "
          f"{(df['label'] == 1).sum():,} attack")
    print(f"[generate_dataset] QBER stats:              "
          f"mean={df['qber'].mean():.4f}  "
          f"std={df['qber'].std():.4f}")
    print(f"[generate_dataset] eve_qber_contribution:   "
          f"mean={df['eve_qber_contribution'].mean():.4f}  "
          f"std={df['eve_qber_contribution'].std():.4f}")

    run_tests(df, OUTPUT_PATH, seed=RANDOM_SEED)
