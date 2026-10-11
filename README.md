# WestQuant Memory Discovery Lab

**Evidence-aware quantum-memory modelling and network integration.**

[![PyPI version](https://badge.fury.io/py/westquant-memory-lab.svg)](https://pypi.org/project/westquant-memory-lab/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

WestQuant connects versioned experimental source data to typed observations, condition-matched coherence references, explicit quantum channels (Kraus operators with erasure), and native network-simulator adapters (SeQUeNCe and QuNetSim). Its contribution is an executable evidence contract across these interfaces, with retained failure outcomes and reproducible study identities.

**Latest release: v0.7.0** — available on [PyPI](https://pypi.org/project/westquant-memory-lab/0.7.0/) and the [v0.7.0 git tag](https://github.com/VesterlundCoder/memory-discover-lab/tree/release/v0.7.0).

> **Software verification is not hardware validation.** The framework preserves distinctions between experimental observations, curated observations, evaluated references, computed results, hypothetical controls, and unknown evidence. It does not claim universal simulator validation, new material discovery, or improved hardware performance.

## Installation

```bash
pip install westquant-memory-lab
```

For the full quantum-memory workflow with all backends:

```bash
pip install "westquant-memory-lab[all]"
```

Optional extras (install only what you need):

| Extra | Packages | Use case |
|---|---|---|
| `quantum` | QuTiP 5.3.1 | Open-system evolution, channel verification |
| `chemistry` | PySCF 2.14.0, ASE 3.29.0 | Electronic structure calculations |
| `spin` | PyCCE 1.1.1, pandas | Spin-bath dynamics, cluster expansion |
| `propagation` | MaxwellBloch 0.12.0 | Optical propagation |
| `datasets` | openpyxl, pynmrstar | Dataset importers |
| `network` | SeQUeNCe 1.2.0, pandas | Native network simulation |
| `all` | All of the above | Complete workflow |

**Requirements:** Python 3.10+. The full workflow with SeQUeNCe requires Python 3.12+.

## Quick start

New to WestQuant? See the **[Getting Started guide](docs/GETTING_STARTED.md)** — from install to your first verified channel in 5 commands.

```bash
# Check your environment
wqml doctor

# Run the bundled Teller et al. baseline (open data)
wqml reproduce examples/teller2025_baseline.json --out baselines/teller2025

# Or run a full pipeline
wqml pipeline examples/pipeline_full.json --out runs/my_lab
```

### Example: `wqml doctor` output

```json
{
  "environment": {
    "python": "3.14.8",
    "platform": "macOS-26.6.2-arm64",
    "packages": {
      "numpy": "2.5.4",
      "scipy": "1.18.1",
      "qutip": "5.3.1",
      "pyscf": "2.14.0",
      "pycce": "1.1.1",
      "ase": "3.29.0",
      "sequence": "1.2.0"
    }
  },
  "capabilities": {
    "numpy": {"import_ok": true, "version": "2.5.4"},
    "scipy": {"import_ok": true, "version": "1.18.1"},
    "qutip": {"import_ok": true, "version": "5.3.1"},
    "pyscf": {"import_ok": true, "version": "2.14.0"},
    "pycce": {"import_ok": true, "version": "1.1.1"},
    "ase": {"import_ok": true, "version": "3.29.0"},
    "sequence": {"import_ok": true, "version": "1.2.0"}
  }
}
```

Optional backends not installed report `{"import_ok": false, "error": "Install the corresponding optional extra."}` — this is expected, not a failure.

### Example: `wqml simulate` output

```bash
wqml simulate examples/atomic_ensemble_profile.json --times 0,0.001,0.01,0.1,1 --out samples.json
```

```json
{
  "samples": 5,
  "output": "samples.json"
}
```

Each sample contains Kraus operators, a Choi matrix, CPTP validation, and metrics:

```
Sample 0: age=     0.0 ms  fidelity=0.985094  acceptance=0.559998  CPTP_error=9.99e-16
Sample 1: age=     1.0 ms  fidelity=0.985073  acceptance=0.559993  CPTP_error=3.97e-16
Sample 2: age=    10.0 ms  fidelity=0.984886  acceptance=0.559942  CPTP_error=1.55e-15
Sample 3: age=   100.0 ms  fidelity=0.983020  acceptance=0.559439  CPTP_error=1.55e-15
Sample 4: age=  1000.0 ms  fidelity=0.964753  acceptance=0.554426  CPTP_error=6.66e-16
```

- **Fidelity** — conditional average fidelity given successful retrieval
- **Acceptance** — retrieval success probability (complement is erasure)
- **CPTP error** — trace preservation error; values below 1e-15 confirm complete positivity and trace preservation

## Key features

### Evidence-aware data contracts

Every observation retains its evidence kind: `experimental`, `curated_experimental`, `fit_to_experiment`, `evaluated_reference`, `computed`, `hypothetical`, or `unknown`. The framework never promotes a computed result to an experimental measurement, and never converts a bare formula or isotope mass into a coherence time.

### Condition-matched reference queries

Coherence references require material identity, coherence definition, and condition matching (temperature, protocol, isotope, host). No interpolation or extrapolation across missing conditions.

### Explicit quantum channels

The write-store-read channel is constructed as a CPTP map with erasure:

```
E_t(rho) = eta(t) * Phi_t(rho) + (1 - eta(t)) * Tr(rho) |e><e|
```

Kraus operators, Choi matrices, and numerical validity (complete positivity, trace preservation) are checked at each step.

### Native network-simulator adapters

- **SeQUeNCe**: Event-driven simulation with native density-matrix manager
- **QuNetSim**: Layered quantum-network framework with QuTiP density backend

The adapters apply sampled absolute-age channels once to the original input and reject missing age samples — no interpolation or extrapolation.

### Reproducible execution

- SQLite catalog with immutable record identities
- Content hashes for source artifacts
- Configuration and source fingerprints for every run
- Checkpoint and resume logic
- 124 passing tests, 1 skipped (v0.7.0)

## Architecture

```
memorylab/
    catalog.py          # SQLite catalog with typed observations
    channels.py         # Kraus operators, Choi matrices, erasure channels
    models.py           # Markov dynamics, finite baths, model dispatch
    spin.py             # Nuclear spin-bath evolution, CPMG, CCE
    network.py          # Network device export and retrieval
    sequence_adapter.py # SeQUeNCe native adapter
    runner.py            # Bounded worker processes, checkpoints
    calibration.py      # Observation binding and condition matching
    t2assessment.py     # T2 inference gates and diagnostics
    t2curves.py         # Curve fitting and model mismatch detection
    experimental.py     # Experimental data reanalysis
    datasets.py         # Source synchronization and verification
    pipeline.py         # Full pipeline orchestration
    cli.py              # Command-line interface (wqml)
    screening/          # Candidate screening and nuclear data
```

## Command reference

```bash
wqml doctor                                    # Check environment and capabilities
wqml datasets <plan.json>                       # Synchronize data sources
wqml catalog <catalog.sqlite>                   # Inspect the SQLite catalog
wqml generate <plan.json>                       # Generate candidate combinations
wqml run <study.json> --out <dir>               # Run a parameter study
wqml simulate <profile.json> --times <list>     # Simulate channel samples
wqml export <samples.json> --out <device.json>  # Export network device
wqml network <device.json> <device.json> <workload.json>  # Run network workload
wqml reproduce <baseline.json> --out <dir>      # Reproduce a bundled baseline
wqml pipeline <plan.json> --out <dir>           # Run the full pipeline
```

## Python API

```python
import numpy as np
from memorylab.network import load_device

# Load an exported memory device
device = load_device("runs/device.json", allow_hypothetical=True)

# Retrieve at a specific storage age
input_state = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex)
result = device.retrieve(input_state, age_s=0.01, rng=np.random.default_rng(17))

if result["success"]:
    retrieved_state = result["density_matrix"]
```

## Evidence model

The framework distinguishes seven evidence kinds and enforces their boundaries:

| Evidence kind | Description | Example |
|---|---|---|
| `experimental` | Directly measured | Teller et al. state fidelities |
| `curated_experimental` | Processed from raw experimental data | Inverse-variance calibrated means |
| `fit_to_experiment` | Model fitted to experimental data | Pr decay curve fits |
| `evaluated_reference` | Reviewed reference value | Ortu et al. 230 ms Eu/YSO |
| `computed` | Numerical result | QuTiP channel evolution |
| `hypothetical` | Synthetic control | Markov profile with declared rates |
| `unknown` | Unresolved evidence | Molecular entry without reviewed curve |

## Validated scope

The v0.7.0 release validates:

- 336 state probes across 56 channel-age points (numerical agreement below 10^-15)
- 128 paired SeQUeNCe/QuNetSim comparisons (below 10^-10 tolerance)
- 124 passing tests, 1 skipped
- 359 JSON records and 11 exact random-trace arrays checked in replay
- Open rare-earth (Pr³⁺:Y₂SiO₅) and diamond-spin (¹³C/NV) dataset reanalysis

## Limitations

- Matched experimental protocol tomography, material-specific bath validation, and native physical-latency comparison remain explicit requirements for broader predictions
- NetSquid and QuISP adapters are not evaluated in this release
- The framework does not claim universal simulator validation
- No new material or improved hardware performance is claimed

## Documentation

- [Getting Started](docs/GETTING_STARTED.md) — From install to first channel in 5 commands
- [Quickstart](docs/QUICKSTART.md) — 5-minute guide to the core workflow
- [Tutorial](docs/TUTORIAL.md) — Full walkthrough from data import to network simulation
- [Model Contract](docs/MODEL_CONTRACT.md) — Physical model definitions and inference boundaries
- [Data Sources](docs/DATA_SOURCES.md) — Source data provenance and licensing
- [Extending](docs/EXTENDING.md) — How to add new model families and adapters

## Citation

If you use WestQuant in your research, please cite:

```bibtex
@software{vesterlund2026westquant,
  author = {Vesterlund, David},
  title = {{WestQuant Memory Discovery Lab}},
  version = {0.7.0},
  year = {2026},
  url = {https://github.com/VesterlundCoder/memory-discover-lab}
}
```

## License

MIT License. Copyright (c) 2026 David Vesterlund.

## Acknowledgements

WestQuant builds on PySCF, PyCCE, QuTiP, MaxwellBloch, SeQUeNCe, and QuNetSim. The author thanks the cited experimental-data and open-source software contributors for making their work available.
