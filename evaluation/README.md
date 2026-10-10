# System-paper evaluations (steps 1–4)

These evaluations extend the original v0.6.0 article snapshot. They do not silently alter the manuscript's reported results. Step 1 is an executed comparison; step 2 remains physically pending; step 3 is a constructed-fault experiment; the full local step-4 workload and a smaller smoke workload have been executed. None validates a new material or establishes better-than-SOTA performance.

## Install and run

From the repository root, with Python 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ./lab
python scripts/evaluate_system.py step1 --out evaluation/results/my-step1
python -m unittest discover -s evaluation/tests -v
python scripts/evaluate_system.py step3 --out evaluation/results/my-step3
python scripts/evaluate_system.py step4 --out evaluation/results/my-step4
```

The first step-1 run automatically retrieves the two pinned Zenodo files into a local ignored cache. It checks SHA256 before either parser consumes them and fails if bytes change. `python scripts/evaluate_system.py fetch` prefetches them. Source URLs and hashes are in `data/teller_sources.json`; online access to Zenodo is required on a fresh clone. A cached run needs no network. Always choose a fresh output directory. Exit status 2 means a gate failed or a case is blocked; a missing parameter is never a successful reproduction.

Full original article reproduction needs the optional backends and additional online source retrieval:

```bash
python -m pip install -c lab/constraints-tested.txt -e './lab[all]'
python scripts/reproduce.py --online
make pdf
```

This is a first-run retrieval, not independent external validation. Full caches with unverified redistribution permissions are deliberately absent from the public repository. The private archive retains its original inputs. Raw source changes, endpoint availability, and optional solver compatibility can affect reproduction. Record new snapshots separately.

## Step 1: fair direct-script comparison

`wqeval/reference.py` imports NumPy/SciPy, not `memorylab`. It exponentiates a column-vectorized qubit Lindblad generator and constructs a qubit-to-qutrit erasure Choi matrix independently. It uses the same reviewed point, physical conventions and supplied software controls as the lab. Both parsers verify the input hashes. The gate compares full Choi matrices, six Pauli eigenstate outputs, conditional average fidelity, acceptance and processed source values. There is one calibrated experimental operating point and twelve hypothetical Markov profiles, yielding 73 channel-age points. No T2 is inferred from the calibrated point.

Timings randomize arm order with a fixed seed, warm up both arms and record five repeats. They time local construction only. Export, metadata and validation costs are not equalized. These measurements are descriptive and cannot establish speed superiority or saved researcher effort. `results/step1-executed/report.md` and `summary.json` retain actual results; `related_tools_audit.json` distinguishes documentation from execution. AiiDA already supplies provenance and caching; the lab's contribution is domain-specific condition and evidence contracts, which could also be implemented as workflow-engine plugins.

## Step 2: another family's audited physical baseline

Run the pending descriptor:

```bash
python scripts/evaluate_system.py step2 --out evaluation/results/physical-case-pending
```

It intentionally returns a blocked result and exit 2. A reported molecular Tm is not enough to reconstruct a Hamiltonian, distinguish population relaxation, or specify optical readout.

A complete software-only control is provided:

```bash
python scripts/make_second_family_control.py
python scripts/evaluate_system.py step2 \
  --config evaluation/data/software_control/case.json \
  --allow-hypothetical --out evaluation/results/my-software-control
```

The curve is a closed-form, thermal, one-spin FID `cos(pi*A*t) - i*polarization*sin(pi*A*t)` and is compared with finite-Hamiltonian exponentiation. Its uncertainties are chosen gate scales, not measured SEMs. Its optical interface is hypothetical. It is never reported as a physical baseline. The network workload is the existing provider-neutral two-node channel benchmark, not a separately executed SeQUeNCe experiment.

To supply real data, copy the control case descriptor and replace its sources and evidence. CSV columns must be `time_s,real,imag,sem_complex`, where SEM is a reviewed scale for the complex residual. Use a strictly increasing time grid beginning at zero and normalized pure-dephasing coherence. A total Hahn-echo envelope is not accepted without a reviewed conversion separating population relaxation and mapping the observable. Nonphysical/noisy unnormalized curves need an explicit upstream treatment; do not clip them silently.

Required case fields:

| Field | Contract |
|---|---|
| `curve`, `model` | Local path relative to descriptor and exact SHA256 |
| `observable` | `complex_pure_dephasing_coherence` |
| `includes_population_relaxation` | Exactly `false` |
| `evidence_kind` | `measured` or `hypothetical` |
| `review` | Reviewer, source location, normalization and observable mapping |
| `model_review` | For measured cases: reviewer, source location, parameter scope |
| `conditions` | Temperature, control, field/frame, composition/isotopes |
| model `experimental_conditions` | Exact copy of reviewed case conditions for measured cases |
| model `evidence_kind` | Hypothetical/unknown cannot pass as physical validation |
| model `storage_model` | `exact_spin_bath` or optional `pycce` |
| `gate` | `max_complex_residual_over_sem` and positive threshold |
| `optical_interface_review` | Optional separate reviewer/source/evidence declaration |
| `network_workload`, `seed` | Required only for network use |

The fixed-model gate fits zero parameters. It is a consistency diagnostic, not a confidence interval, p-value or identification of a unique model. A mismatch blocks channel export. Missing optical review still allows coherence comparison but blocks network export. Hypothetical optical parameters require explicit opt-in and propagate hypothetical evidence to the complete channel. A sampled 1/e crossing is a numerical bracket, not a prediction error bar or homogeneous T2.

## Step 3: constructed fault ablations

Seven deliberately invalid inputs exercise native age, temperature, rate-definition, independence, evidence and absolute-age protections, plus the new source-hash contract. Each has a valid positive control and a local unsafe bypass. The production guards are never modified. The table records the consequences under the bypass. An additional unit-conversion omission control measures the effect of treating 1 ms as 1 s. This constructed coverage is not an estimate of researcher error frequency and is not evidence that other frameworks cannot implement equivalent guards.

## Step 4: performance and robustness

The default performs three randomized-order repeats for workers 1, 2 and 4 on 12 jobs per study (two models, three detunings and two replicates). Native threads are limited to one in benchmark subprocesses. Each cold run has a separate output directory; the warm pass reuses terminal-result checkpoints. All serialized channels and configuration identities must match across worker counts and repeats. It also exercises a missing parameter, a real process timeout and resume from a normally completed partial checkpoint.

```bash
python scripts/evaluate_system.py step4 \
  --config evaluation/config/performance_smoke.json \
  --out evaluation/results/my-performance-smoke
```

Reports include cold/resume wall times, throughput, parent peak RSS and the largest terminated child's peak RSS separately. Those memory measurements are not aggregate concurrent process peaks. Timeout and missing-data results are terminal failures, not numerical results; reusing such a checkpoint does not retry a calculation. Partial-checkpoint resume is not a forced-kill, power-loss or filesystem-corruption test. The smoke workload is two jobs at workers 1 and 2, one repeat; it cannot support a scalability claim. The full local workload has also passed (nine cold studies, 108 cold jobs and 108 checkpoint reuses). Larger-scale performance, additional machines and independent environment validation remain to be performed.

## Remaining colleague work

Step 5: independently reproduce the selected experiments in a clean environment, verify source retrieval and physical mappings, and retain logs. Step 6: review novelty, manuscript claims and release/archive identifiers. This repository upload supplies reviewable code and evidence, not peer-review acceptance.

## Optional container and CI

```bash
docker build -t memory-discover-lab .
docker run --rm -v "$PWD/container-results:/results" memory-discover-lab
```

The container contains the core NumPy/SciPy lab; optional solvers and LaTeX need the separate full setup. Container build/run has not been independently verified here. GitHub Actions runs the seven core evaluation tests and the matched comparison, retaining its result artifact. CI source retrieval requires Zenodo availability.
