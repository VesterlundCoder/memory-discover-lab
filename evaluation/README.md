# System-paper evaluations (steps 1–4)

These evaluations extend the original v0.6.0 article snapshot. They do not silently alter the manuscript's reported results. Step 1 is an executed comparison; step 2 remains physically pending; step 3 is a constructed-fault experiment; the full local step-4 workload and a smaller smoke workload have been executed. None validates a new material or establishes better-than-SOTA performance.

## Install and run

From the repository root, with Python 3.12:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements-lock-core.txt -c lab/constraints-tested.txt -r requirements-paper.txt -e ./lab
python scripts/evaluate_system.py step1 --offline --out reproductions/my-step1
python -m unittest discover -s evaluation/tests -v
python scripts/evaluate_system.py step3 --out reproductions/my-step3
python scripts/evaluate_system.py step4 --out reproductions/my-step4
```

Step 1 copies its two pinned input files from tracked, licensed `data/experimental/teller2025/` into a local ignored cache and checks SHA256 before either parser consumes them. A clean clone needs no Zenodo connection. `--offline` forbids downloads if both bundled and local inputs are missing. Corrupt bytes are rejected; they are never silently replaced. `python scripts/evaluate_system.py fetch --offline` checks/prefills the cache. Always choose a fresh output directory.

One command runs all four software pathways and the separate blocked physical descriptor:

```bash
python scripts/reproduce_system.py --out reproductions/my-system --reference-root evaluation/results/repaired --allow-source-change
```

Exit status 2 from the standalone physical descriptor is intentional. The one-command runner verifies that exact blocked status; it does not call the case physically validated. The synthetic step-2 configuration is named explicitly below.

Paper numerical replay uses the full tested environment and the bundled licensed measurement files:

```bash
python -m pip install -c requirements-lock-full.txt -c lab/constraints-tested.txt -r requirements-paper.txt -e './lab[all]'
python scripts/reproduce.py --out reproductions/my-paper
make pdf
```

Replay recomputes the numerical analyses and network controls, using retained reviewed transcriptions/reference tables. The wider unlicensed molecular-source acquisition and unbundled paper-byte verification are outside this offline mode. `python scripts/reproduce.py --online --out reproductions/new-source-snapshot` explicitly selects the original remote acquisition path. Missing/changed remote inputs remain failures.

## Step 1: matched direct-script comparison

`wqeval/reference.py` imports NumPy/SciPy, not `memorylab`. It exponentiates a column-vectorized qubit Lindblad generator and constructs a qubit-to-qutrit erasure Choi matrix independently. It uses the same reviewed point, physical conventions and supplied software controls as the lab. Both parsers verify the input hashes. The gate compares full Choi matrices, six Pauli eigenstate outputs, conditional average fidelity, acceptance and processed source values. There is one calibrated experimental operating point and twelve hypothetical Markov profiles, yielding 73 channel-age points. No T2 is inferred from the calibrated point.

Timings randomize arm order with a fixed seed, warm up both arms and record five repeats. They time local construction only. Export, metadata and validation costs are not equalized. These measurements are descriptive and cannot establish speed superiority or saved researcher effort. `results/step1-executed/report.md` and `summary.json` retain actual results; `related_tools_audit.json` distinguishes documentation from execution. AiiDA already supplies provenance and caching; the lab's contribution is domain-specific condition and evidence contracts, which could also be implemented as workflow-engine plugins.

## Step 2: another family's audited physical baseline

### Executed measured-observable companion case

The [Swedish case report](results/bradley2022-nv0/report_sv.md) documents Bradley et al. 2022, Fig. 3b: C-13 Ramsey storage in heralded NV0 at 4 K. Licensed original source bytes are bundled under `data/experimental/bradley2022/`. The companion workflow compares transverse Bloch length and signed X directly, without fabricating normalized complex coherence. It uses a calibrated stretched envelope and a fixed effective Hamiltonian frequency from the separate NMR measurement, with matching field, isotope, pulse and charge-selection conditions.

```bash
python -m pip install -r evaluation/data/bradley2022_nv0/requirements-tested.txt -e ./lab
python scripts/evaluate_bradley_nv0.py --out reproductions/bradley-nv0 --plot
```

Use a separate environment for this tested dependency snapshot. There are 24 measured points: 14 calibration and 10 heldout, across two separate series. The maximum heldout residual divided by the reported error is 2.428 for Bloch length (passes threshold 3) and 3.158 for X (fails). Exit code 2 is expected and retains both results. The split is retrospective; source error bars do not include our calibration uncertainty. The same-machine offline confirmation matches the full scientific summary and CSV exactly. This case does not validate a microscopic spin bath, isolate population relaxation, or supply an optical interface. Physical validation and network export remain false. Independent scientific review remains pending.

### Original strict physical contract (still pending)

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

## Integrated manuscript and complete execution dossier

The main article and Supplement now include all four system evaluations. [The complete dossier](paper/README.md) lists exact configurations, source fingerprints, run dates, statistical limits and claim pointers. Steps 2 and 3 have confirmations using the same evaluation-source fingerprint as the selected step-1 and step-4 records. The distinct-family physical case remains blocked; its pending run is retained. Regenerate reporting tables with `python scripts/document_system_evaluation.py`, compile the manuscript/Supplement with `make pdf`, and compile the standalone dossier with `make system-paper-pdf`. Core GitHub CI success is retained in `evidence/core_ci_verification.json`; it does not replace colleague-led scientific reproduction.

## Compare fresh scientific results

```bash
python scripts/verify_evaluation.py --reference evaluation/results/repaired/step3 --actual reproductions/my-system/step3 --require-same-source
python scripts/verify_evaluation.py --reference evaluation/results/repaired/step4 --actual reproductions/my-system/step4 --require-same-source
```

The comparator checks full scientific fields, configuration, seeds and input hashes at absolute/relative tolerance 1e-10. Step 4 compares the complete `scientific_results.json` channel/configuration payload. Source-derived run IDs and digests are not portable across code/environment changes, so they are recorded separately. Timestamps, local paths, wall times, RSS/CPU measurements and diagnostic path strings are excluded from numeric equality. Every output retains its original provenance. Source fingerprints are reported and optionally required to match. Historical step-4 summaries alone lack the portable payload and cannot establish cross-version channel equality; use the repaired reference.

The CI core job runs both suites and all four system pathways with external sockets/DNS blocked after dependency installation. The paper job installs the constrained full environment and replays licensed paper numerics with the same denial. These are author-operated clean checkouts, not colleagues' independent scientific review.

## Protocol, convergence and second network simulator

The executed extension and its limits are documented in [REPORT_SV.md](results/validation_extension/REPORT_SV.md). Its selected result tree is `results/validation_extension/selected/`; all native per-run JSON and shared RNG arrays are retained inside each cross-simulator stage's SHA256-checked ZIP archive. The uncompressed duplicates are ignored by git.

Use a separate Python 3.12 environment for the pinned extension snapshot:

```bash
python3.12 -m venv .venv-extension
source .venv-extension/bin/activate
python -m pip install -r evaluation/config/validation_extension/requirements-tested.txt -e ./lab
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export WQ_BLOCK_EXTERNAL_NETWORK=1
export PYTHONPATH="$PWD/scripts/network_guard:$PWD/lab"
python scripts/run_validation_extension.py --count
python scripts/run_validation_extension.py --out reproductions/my-extension
python scripts/verify_validation_extension.py --reference evaluation/results/validation_extension/selected --actual reproductions/my-extension
```

Stages run in order: protocol, convergence, pilot, larger. Each native network stage uses a fresh child process. `--stage protocol` runs the instrument checks alone; `--stage larger` includes its prerequisites. `--resume` rejects changed configuration or source fingerprints. The experimental audit is inconclusive and cannot be promoted by numerical success. The material gate is applied to profiles explicitly declaring `prediction_purpose: material_prediction`.

For a regression against older archived system results, use `scripts/reproduce_system.py --out reproductions/my-historical-regression --reference-root evaluation/results/repaired --allow-source-change`. This explicitly permits different source hashes while comparing full scientific fields and reporting both revisions. Without the flag, comparison requires identical source. The new extension verifier always requires identical lab/evaluation/configuration fingerprints.
