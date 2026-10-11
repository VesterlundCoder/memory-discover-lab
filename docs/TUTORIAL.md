# Tutorial: From Experimental Data to Network Simulation

This tutorial walks through the full WestQuant workflow: installing the package, importing open experimental data, building a quantum-memory channel, exporting it, and running a network simulation.

## Prerequisites

- Python 3.10+ (3.12+ for SeQUeNCe)
- Internet access for the first data fetch (offline mode available after caching)

## Step 1: Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "westquant-memory-lab[quantum,network]"
```

Verify your installation:

```bash
wqml doctor
```

You should see `numpy`, `scipy`, `qutip`, and `sequence` all reporting `import_ok: true`.

## Step 2: Import open experimental data

WestQuant bundles example data plans that fetch open datasets with checksummed source locking. The simplest is the molecular qubit dataset from the MTD-group on GitHub:

```bash
wqml datasets examples/data_plan.json
```

This fetches three sources:
1. **Molecular Qubit Dataset** (GitHub) — 421 molecular spin-relaxation observations
2. **Cr host matrix data** (Zenodo 6828667) — figure-extracted data files
3. **CIAAW isotopic abundances** (ciaaw.org) — 289 isotope abundance observations

All fetched files are checksummed (SHA-256) and stored in a SQLite catalog. You can inspect the catalog:

```bash
wqml catalog data/catalog.sqlite --table observations --out data/observations.json
```

## Step 3: Generate candidates

Generate candidate memory configurations from the catalog:

```bash
wqml generate examples/new_combinations.json --out data/generated_candidates.json
```

This produces 16 candidate combinations with explicit charge, spin, and isotope variations. Each candidate is labelled `hypothetical` — it is not a validated material.

## Step 4: Simulate a channel

Simulate a quantum-memory channel for a hypothetical atomic ensemble:

```bash
wqml simulate examples/atomic_ensemble_profile.json --times 0,0.001,0.01,0.1,1 --out samples.json
```

Output:
```
{
  "samples": 5,
  "output": "samples.json"
}
```

Each sample contains:
- **Kraus operators** — the conditional channel decomposition
- **Choi matrix** — vectorized for numerical verification
- **CPTP checks** — complete positivity and trace preservation
- **Metrics** — conditional average fidelity, retrieval success probability

Example metrics at each age:

```
Sample 0: age=     0.0 ms  fidelity=0.985094  acceptance=0.559998  CPTP_error=9.99e-16
Sample 1: age=     1.0 ms  fidelity=0.985073  acceptance=0.559993  CPTP_error=3.97e-16
Sample 2: age=    10.0 ms  fidelity=0.984886  acceptance=0.559942  CPTP_error=1.55e-15
Sample 3: age=   100.0 ms  fidelity=0.983020  acceptance=0.559439  CPTP_error=1.55e-15
Sample 4: age=  1000.0 ms  fidelity=0.964753  acceptance=0.554426  CPTP_error=6.66e-16
```

All samples pass CPTP validation (trace preservation error < 1e-15, positive Choi eigenvalues).

## Step 5: Export a network device

```bash
wqml export samples.json --allow-hypothetical --out device.json
```

The `--allow-hypothetical` flag is required because the input profile declares `evidence_kind: hypothetical`. This prevents accidental export of unvalidated models as experimental results.

## Step 6: Run a network simulation

With SeQUeNCe installed (`pip install "westquant-memory-lab[network]"`):

```bash
wqml network device.json device.json examples/network_workload.json --allow-hypothetical
```

This runs a two-node network workload with the exported memory device on both ends.

## Step 7: Use the Python API

For programmatic access:

```python
import numpy as np
from memorylab.models import evaluate
from memorylab.network import load_device

# Simulate a channel
profile = {
    "family": "atomic_ensemble",
    "storage_model": "markov",
    "evidence_kind": "hypothetical",
    "provenance": [{"kind": "software_test"}],
    "temperatures_K": {"write": 4.2, "storage": 4.2, "read": 4.2},
    "rates": {
        "population": {"kind": "constant", "rate_s_inv": 0.05, "valid_temperature_K": [1, 300]},
        "pure_dephasing": {"kind": "constant", "rate_s_inv": 0.01, "valid_temperature_K": [1, 300]},
        "erasure": {"kind": "constant", "rate_s_inv": 0.01, "valid_temperature_K": [1, 300]},
    },
    "io": {
        "eta_write": 0.8, "eta_read": 0.7,
        "write_depolarizing_p": 0.01, "read_depolarizing_p": 0.02,
        "write_duration_s": 0.0001, "read_duration_s": 0.0002,
        "thermal_transition_s": 0,
        "logical_encoding": "abstract_qubit",
        "protocol": "supplied_effective_write_read_channel",
    },
    "noise_budget": ["phenomenological_relaxation", "independent_markov_dephasing",
                     "write_depolarization", "read_depolarization", "independent_erasure"],
}

samples = evaluate(profile, [0.0, 0.001, 0.01, 0.1, 1], backend="analytic")
print(f"Generated {len(samples)} samples")
print(f"First sample fidelity: {samples[0]['metrics']['conditional_average_fidelity']:.6f}")
```

## Step 8: Reproduce a bundled baseline

WestQuant includes a complete baseline from Teller et al. (PRX 15, 031053, 2025):

```bash
wqml reproduce examples/teller2025_baseline.json --out baselines/teller2025
```

This reproduces:
- 90 state-fidelity scalars (path mean 0.9511, time-bin mean 0.9140)
- Spatial holdout (max z = 2.34, below threshold 3)
- Calibrated operating-point channel (fidelity 0.967, acceptance 0.014)
- 4 SeQUeNCe runs (87 retrieved pairs in 400,000 attempts)
- Analytic/QuTiP Choi agreement (error < 1e-17)

## Understanding evidence kinds

Every observation and result in WestQuant carries an `evidence_kind` label:

| Kind | Meaning |
|---|---|
| `experimental` | Directly measured in a hardware experiment |
| `curated_experimental` | Processed from raw experimental data |
| `fit_to_experiment` | Model fitted to experimental data |
| `evaluated_reference` | Reviewed reference value from primary text |
| `computed` | Numerical result from a solver |
| `hypothetical` | Synthetic control with declared parameters |
| `unknown` | Unresolved evidence (units or conditions unclear) |

The framework never promotes a computed result to an experimental measurement. A `fit_to_experiment` decay scale is not a physical spin $T_2$ unless independently validated.

## Troubleshooting

### "BackendUnavailable: Install the corresponding optional extra"

You tried to use a backend that isn't installed. Install the extra:

```bash
pip install "westquant-memory-lab[quantum]"  # for QuTiP
pip install "westquant-memory-lab[network]"  # for SeQUeNCe
```

### "MissingData: Memory recipe lacks storage_model"

Your profile JSON is missing a required field. Check the example profiles in `examples/` for the correct schema.

### "Offline artifact missing"

You used `--offline` but the cached data isn't present. Run without `--offline` first to fetch and cache the data.

## Next steps

- [Model Contract](MODEL_CONTRACT.md) — Physical model definitions
- [Data Sources](DATA_SOURCES.md) — Source data provenance
- [Extending](EXTENDING.md) — How to add new model families
