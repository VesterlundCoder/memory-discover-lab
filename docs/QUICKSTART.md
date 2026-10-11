# Quickstart Guide

This guide gets you from `pip install` to your first quantum-memory channel simulation in under 5 minutes.

## 1. Install

```bash
pip install westquant-memory-lab
```

This installs the core package with NumPy and SciPy. Optional backends (QuTiP, PySCF, PyCCE, SeQUeNCe, etc.) are installed with extras:

```bash
pip install "westquant-memory-lab[all]"  # everything
pip install "westquant-memory-lab[quantum,network]"  # QuTiP + SeQUeNCe only
```

## 2. Check your environment

```bash
wqml doctor
```

This prints a JSON report showing which backends are available. Core (numpy, scipy) always works. Optional backends show `not installed` until you install the corresponding extra.

## 3. Simulate your first channel

```bash
wqml simulate examples/atomic_ensemble_profile.json --times 0,0.001,0.01,0.1,1 --out samples.json
```

This generates 5 channel samples at ages 0, 1, 10, 100, and 1000 ms. Each sample contains Kraus operators, a Choi matrix, CPTP validation, and fidelity/acceptance metrics.

## 4. Export a network device

```bash
wqml export samples.json --allow-hypothetical --out device.json
```

This serializes the channel samples into a network-consumable device JSON.

## 5. Retrieve a state through the channel

```python
import numpy as np
from memorylab.network import load_device

device = load_device("device.json", allow_hypothetical=True)
input_state = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex)
result = device.retrieve(input_state, age_s=0.001, rng=np.random.default_rng(42))

if result["success"]:
    print(f"Retrieved state fidelity: {np.real(np.trace(result['density_matrix'] @ input_state)):.6f}")
else:
    print("State lost (erasure)")
```

## What you get

Each channel sample contains:

| Field | Description |
|---|---|
| `kraus` | Kraus operators for the conditional channel |
| `choi` | Choi matrix (vectorized) |
| `cptp` | Complete positivity and trace preservation checks |
| `metrics` | Conditional fidelity, acceptance probability, target overlap |
| `metadata` | Age, temperatures, evidence kind, provenance |

## Next steps

- [Tutorial](TUTORIAL.md) — Full walkthrough from data import to network simulation
- [Getting Started](GETTING_STARTED.md) — 5-command guide from install to first channel
- [Model Contract](MODEL_CONTRACT.md) — Physical model definitions and inference boundaries
- [Data Sources](DATA_SOURCES.md) — Source data provenance and licensing
