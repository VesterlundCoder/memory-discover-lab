# Getting Started: From Install to First Channel in 5 Commands

This guide gets you from zero to a verified quantum-memory channel in five commands.

## Prerequisites

- Python 3.10 or later
- pip (comes with Python)

## The 5 commands

### 1. Install the package

```bash
pip install westquant-memory-lab
```

This pulls in NumPy and SciPy automatically. No heavy quantum dependencies are required for the core workflow.

### 2. Check your environment

```bash
wqml doctor
```

You'll see a JSON report. The key fields are:

```json
{
  "environment": {
    "python": "3.14.8",
    "packages": {
      "numpy": "2.5.4",
      "scipy": "1.18.1",
      "qutip": null
    }
  },
  "capabilities": {
    "numpy": {"import_ok": true, "version": "2.5.4"},
    "scipy": {"import_ok": true, "version": "1.18.1"},
    "qutip": {"import_ok": false, "error": "Install the corresponding optional extra."}
  }
}
```

Core backends (numpy, scipy) are always available. Optional backends show `not installed` until you add the extras.

### 3. Simulate a channel

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

### 4. Export a network device

```bash
wqml export samples.json --allow-hypothetical --out device.json
```

### 5. Retrieve a state through the channel

```python
python -c "
import numpy as np
from memorylab.network import load_device
device = load_device('device.json', allow_hypothetical=True)
state = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex)
result = device.retrieve(state, age_s=0.001, rng=np.random.default_rng(42))
if result['success']:
    fidelity = np.real(np.trace(result['density_matrix'] @ state))
    print(f'Retrieved with fidelity: {fidelity:.6f}')
else:
    print('State lost (erasure channel)')
"
```

## What just happened

1. **Install** — You installed the core package with NumPy and SciPy.
2. **Doctor** — You verified which backends are available.
3. **Simulate** — You generated 5 quantum-channel samples at ages 0–1000 ms. Each sample is a complete CPTP channel with Kraus operators, a Choi matrix, and fidelity/acceptance metrics.
4. **Export** — You serialized the channel samples into a network-consumable device JSON.
5. **Retrieve** — You loaded the device and retrieved a quantum state through the channel at 1 ms age. The channel has an erasure branch, so some attempts return `success: False`.

## What the channel looks like

Each sample in `samples.json` contains:

```
Sample 0: age=     0.0 ms  fidelity=0.985094  acceptance=0.559998  CPTP_error=9.99e-16
Sample 1: age=     1.0 ms  fidelity=0.985073  acceptance=0.559993  CPTP_error=3.97e-16
Sample 2: age=    10.0 ms  fidelity=0.984886  acceptance=0.559942  CPTP_error=1.55e-15
Sample 3: age=   100.0 ms  fidelity=0.983020  acceptance=0.559439  CPTP_error=1.55e-15
Sample 4: age=  1000.0 ms  fidelity=0.964753  acceptance=0.554426  CPTP_error=6.66e-16
```

- **Fidelity** is the conditional average fidelity of the retrieved state given successful retrieval.
- **Acceptance** is the retrieval success probability (the complement is the erasure probability).
- **CPTP error** is the trace-preservation error; values below 1e-15 confirm the channel is completely positive and trace preserving.

## Installing optional backends

For QuTiP channel verification, SeQUeNCe network simulation, or PySCF electronic structure:

```bash
pip install "westquant-memory-lab[quantum]"      # QuTiP
pip install "westquant-memory-lab[network]"       # SeQUeNCe
pip install "westquant-memory-lab[chemistry]"    # PySCF + ASE
pip install "westquant-memory-lab[spin]"         # PyCCE
pip install "westquant-memory-lab[all]"          # everything
```

## Where to go next

- [Quickstart](QUICKSTART.md) — More detailed 5-minute guide
- [Tutorial](TUTORIAL.md) — Full walkthrough from data import to network simulation
- [Model Contract](MODEL_CONTRACT.md) — Physical model definitions and inference boundaries
