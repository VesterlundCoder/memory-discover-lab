# SeQUeNCe–QuNetSim Cross-Simulator Benchmark — v0.7.1

## Overview

This benchmark compares the SeQUeNCe and QuNetSim network simulators when both are
fed the same WestQuant memory channel and the same pre-generated event trace. The
purpose is to verify that both simulators apply the same channel correctly given the
same inputs, not to independently test their stochastic protocols.

## Simulator versions

| Simulator | Version | Backend |
|---|---|---|
| SeQUeNCe | 1.2.0 | Native event kernel + density-matrix manager |
| QuNetSim | 0.1.2 | Custom QuTiP density backend (not the stock EQSN backend) |
| QuTiP | 5.3.1 | Open-system solvers for QuNetSim's density matrices |

QuNetSim's custom QuTiP backend replaces its default EQSN backend. This gives
density-matrix-level state representation comparable to SeQUeNCe's manager. QuNetSim's
wall-clock sleeps are scheduling machinery, not simulated physical storage time. The
shared logical trace supplies ages.

## Parameter combinations

The benchmark sweeps 16 parameter combinations:

| Parameter | Values |
|---|---|
| Background rate (s⁻¹) | 0, 5000 |
| Storage age (s) | 0, 0.001, 0.01, 0.03 |
| Link herald probability | 0.25, 0.75 |

Total: 2 × 4 × 2 = 16 combinations.

## Seeds

Eight seeds are used: 2101, 2102, 2103, 2104, 2105, 2106, 2107, 2108.

Master seed: 20261010.

## Run structure

| Quantity | Value |
|---|---|
| Parameter combinations | 16 |
| Seeds | 8 |
| Paired comparisons | 128 |
| Total runs (both simulators) | 256 |
| Attempts per run | 512 |
| Total attempts | 131,072 |
| Attempt interval | 0.04 s |

Each paired comparison runs the same configuration on both SeQUeNCe and QuNetSim with
the same pre-generated random trace. The trace specifies the random seed, storage
age, and input state for each attempt.

## Metrics

### Density-matrix error

The maximum mean density-matrix error across all 128 paired comparisons is
**2.465×10⁻¹⁵**, which satisfies the declared tolerance of 10⁻¹⁰.

### Accepted pairs

Total retrieved pairs across all arms: **18,126**.

### Conditional Bell fidelity

The expected Bell fidelity varies with storage age:

| Storage age | Expected Bell fidelity |
|---|---|
| 0 s | 0.934 |
| 0.001 s | 0.862 |
| 0.01 s | 0.457 |
| 0.03 s | 0.308 |

### Quality-qualified throughput

Quality-qualified pairs are those with Bell fidelity above the 0.8 gate. At longer
storage ages (0.01 s and 0.03 s), the Bell fidelity drops below the gate, so
quality-qualified pairs are zero. The qualified rate per second is reported per arm.

## Results

| Metric | Value |
|---|---|
| Status | PASS |
| Planned arm runs | 256 |
| Successful arm runs | 256 |
| Failed arm runs | 0 |
| Paired comparisons | 128 |
| Max mean density error | 2.465×10⁻¹⁵ |
| All counts and logical traces identical | True |
| Total retrieved pairs | 18,126 |
| Native SeQUeNCe events | 98,344 |
| Native QuNetSim quantum packet transfers | 32,808 |
| Hardware validated | False |
| Evidence kind | Hypothetical |

## Configuration

- **Profile:** `defect_spin_profile.json` (hypothetical, SHA-256: d87d94a2...)
- **Rates:** population 30 s⁻¹, pure dephasing 50 s⁻¹, erasure 12 s⁻¹
- **IO:** η_write 0.8, η_read 0.7, write depolarisation 0.01, read depolarisation 0.02
- **Detector:** exclusive signal-then-background model, window 10 μs
- **Minimum Bell fidelity gate:** 0.8
- **Density tolerance:** 10⁻¹⁰
- **Prospectively preregistered:** No

## Links

| Resource | Path |
|---|---|
| Configuration | `evaluation/config/validation_extension/crosssim_larger.json` |
| Per-comparison results | `evaluation/results/validation_extension/selected/larger/paired_comparison.csv` |
| Summary | `evaluation/results/validation_extension/selected/larger/summary.json` |
| Raw runs and traces | `evaluation/results/validation_extension/selected/larger/raw_runs_and_traces.zip` |
| Verification code | `memorylab/sequence_adapter.py`, `memorylab/qunetsim_adapter.py` |

## Scope and limitations

The benchmark covers:

- Two nodes with one memory slot each
- Fixed storage age per run
- Common random numbers (shared logical trace) supplied to both simulators
- External logical clock for timing

The benchmark does **not** cover:

- Routing stack or link-generation protocol
- Repeater queues, capacity contention, or dead-time models
- Finite fiber propagation
- Detector double clicks
- Network timing equivalence

## Important caveat: shared event trace

Identical outcomes between the two simulators partly follow from the fact that both
simulators are fed the same pre-generated event trace. The trace specifies the random
seed, storage age, and input state for each attempt. This is **not** an independent
test of the simulators' stochastic protocols. It is a test of whether both simulators
apply the same WestQuant channel correctly given the same inputs.

If the simulators had different random-number generators or different event
scheduling, the outcomes would differ even if the channel physics were identical.
This benchmark does not claim that the simulators are equivalent in general; it claims
that they agree on this specific channel application under this specific trace.

## Reproduction

To reproduce this benchmark:

```bash
# Install with both network simulators
pip install "westquant-memory-lab[crosssim]"

# Run the benchmark
python -m memorylab.evaluation.run_crosssim evaluation/config/validation_extension/crosssim_larger.json
```

The benchmark requires the evaluation configs and results from the GitHub release
archive, not from the PyPI wheel. See [REPRODUCIBILITY.md](../REPRODUCIBILITY.md) for
the full reproduction instructions.
