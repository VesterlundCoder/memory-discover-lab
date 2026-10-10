# System evaluation 1–4: paper evidence

This dossier and its LaTeX/PDF counterpart are integrated into the main manuscript and Supplement. The historical experiment reanalyses remain distinct from the new system evaluation. All reported numerical results are retrospective. No new material or hardware improvement is established.

| Step | Executed scope | Outcome | Physical limit |
|---|---|---|---|
| 1 | Independent matched NumPy/SciPy reference; 73 channel-age points; 90 processed experimental fidelities | Pass, max full-Choi error 1.3103013e-14 | Numerical/data consistency, not new hardware or speed superiority |
| 2 | 41-point synthetic molecular-spin FID; hypothetical provider-neutral network workload | Curve gate passes; 313 retrieved pairs / 10000 trials | Second experimental physical-family baseline is blocked pending reviewed data |
| 3 | Seven constructed invalid contracts with seven valid positive controls; isolated unsafe bypasses | All selected faults rejected and all positive controls pass | Not real-world error incidence or material-prediction accuracy |
| 4 | Nine bounded local cold studies, 108 cold jobs, 108 checkpoint reuses | Identical scientific digests across workers 1, 2, 4; robustness probes pass | One environment and small models; no cluster-scale claim |

## Manuscript artifacts

- `paper.tex` / `paper.pdf`: full model, original experimental analyses and integrated system evaluation section.
- `supplement/supplement.tex` / `.pdf`: complete configurations, equations, gates, work counts, fault consequences and reproduction scope.
- `evaluation/paper/System_Evaluation_1_4.tex` / `evaluation/reports/System_Evaluation_1_4.pdf`: standalone complete execution dossier.
- `evidence/system_evaluation_claim_map.json`: claim-to-result pointers, hashes and per-run configuration identities.
- `evidence/core_ci_job.log` / `core_ci_verification.json`: fresh-checkout core installation, tests and automatic source retrieval evidence.

## Source-consistent selected runs

Initial step-2 and step-3 records remain under `step2-software-control` and `step3-executed`. Their confirmations use the published evaluation implementation and preserve the same numerical outcomes. The selected four summaries share evaluation-source SHA256 `d8fc6d2ecb580e0ba1c8881ffbd542d087c493b7621cb89509948e595211ec92` and lab-source SHA256 `9c4490acf2e5a42e8e10007989eeb94b5e406b17f5d187ca310847581ee2edb7`. Hash equality is checked when generating paper evidence.

| Run | Status | UTC timestamp | Configuration SHA256 |
|---|---|---|---|
| step1-executed | pass | 2026-10-10T11:36:09.705458+00:00 | `74bac2f28395431cfeedf02b5e7ed21c27da7d5864df54617b9f2f1e08786726` |
| step2-confirmation | model_curve_gate_pass | 2026-10-10T12:30:18.120846+00:00 | `219d11349c2fdce2876e11a9cfdb5953ed53050ffaa8577de132aa2154f6130a` |
| step3-confirmation | pass | 2026-10-10T12:30:18.696014+00:00 | `2873ab9cb0e7e3dd01565ede71e1ff3df0324b90b1b930a005de7eef4945e18a` |
| step4-executed | pass | 2026-10-10T11:35:34.038224+00:00 | `72da011eb9fdd13d07e2073f258c07533a7d9723963af2ed44042dead165d02e` |

## Exact configurations

### step1-executed

```json
{
  "population_rates_s_inv": [
    0,
    0.05,
    10,
    100
  ],
  "storage_temperatures_K": [
    4.2,
    10,
    80
  ],
  "detunings_Hz": [
    0,
    123,
    -500,
    1000
  ],
  "excited_populations": [
    0,
    0.1,
    0.5,
    0.9
  ],
  "times_s": [
    0,
    1e-06,
    0.0001,
    0.001,
    0.01,
    0.1
  ],
  "seed": 20261010,
  "timing_repeats": 5,
  "tolerance": 1e-08
}
```

### step2-confirmation

```json
{
  "observable": "complex_pure_dephasing_coherence",
  "includes_population_relaxation": false,
  "evidence_kind": "hypothetical",
  "curve": {
    "path": "curve.csv",
    "sha256": "a81c91ccf8bb1c862ab730420a0a4cc4d95003825de999bd5b7c400807adb40a"
  },
  "model": {
    "path": "model.json",
    "sha256": "4a964e5d2f2463816d2fa4db02fb10126536a61054d704b5a90cf8f6f262c46c"
  },
  "review": {
    "reviewer": "software_control_generator",
    "source_location": "scripts/make_second_family_control.py",
    "normalization": "L(0)=1",
    "observable_mapping": "closed-form pure-dephasing FID; no experimental observations"
  },
  "conditions": {
    "temperature_K": 4.2,
    "control": {
      "cpmg_pulses": 0
    },
    "field_and_frame": "specified nuclear Zeeman vector in lab frame",
    "composition_and_isotopes": "one explicitly hypothetical C-13 spin"
  },
  "gate": {
    "kind": "max_complex_residual_over_sem",
    "threshold": 3
  },
  "optical_interface_review": {
    "reviewer": "software_control_generator",
    "source_location": "chosen example profile",
    "evidence_kind": "hypothetical"
  },
  "network_workload": {
    "attempts": 10000,
    "link_herald_probability": 0.1,
    "attempt_interval_s": 0.001,
    "storage_age_s": 0.0005,
    "minimum_Bell_fidelity": 0.8
  },
  "seed": 20261010
}
```

### step3-confirmation

```json
{
  "suite": "constructed_contract_faults_v1",
  "seed": 20261010
}
```

### step4-executed

```json
{
  "workers": [
    1,
    2,
    4
  ],
  "timing_repeats": 3,
  "times_s": [
    0,
    0.0001,
    0.0005,
    0.001,
    0.002,
    0.005
  ],
  "replicates": 2,
  "detunings_Hz": [
    0,
    123,
    500
  ],
  "seed": 20261010,
  "max_runs": 24,
  "job_timeout_s": 60,
  "driver_timeout_s": 600
}
```

## Statistical and physical interpretation

No step reports a percentage prediction error for unseen molecules. The step-1 tolerance is numerical; the step-2 residual denominator is an arbitrarily chosen control scale; its sampled crossing bracket is a grid bracket, not a confidence interval. The constructed 16.667% rate-definition error is conditional on specified synthetic rates. The step-4 timing ranges are three observed minima/maxima, not confidence intervals. Its memory counters are separate parent and largest terminated child peaks, not aggregate concurrent peak memory.

The provider-neutral step-2 network example is not the earlier SeQUeNCe experimental-point workload or its separate 2000-trial hypothetical control. There are two Pr experimental data analyses in the original paper; neither completes the different-family physical objective of step 2.

## Fresh-checkout verification

GitHub Actions [run 38051481969](https://github.com/VesterlundCoder/memory-discover-lab/actions/runs/38051481969) at commit `de52b32f0c34a05cf4f6a0c01bca6ee087e6cb67` passes installation, seven core evaluation tests, automatic pinned experimental-file retrieval and step 1 on Ubuntu 24.04 / Python 3.12.15 / NumPy 2.5.3 / SciPy 1.18.1. Its maximum full-Choi discrepancy is 1.3214015338344021e-14. The retained local suite has 75 original tests plus seven evaluation tests; confirmations and CI repetitions do not increase the distinct-test count. This core CI check is not full optional-backend or colleague-led independent reproduction.

## Reproduction and publication gates

```bash
python scripts/document_system_evaluation.py
make pdf
make system-paper-pdf
```

These commands validate reporting inputs and regenerate tables/PDFs; they do not rerun physics. Numerical commands and source contracts are in `evaluation/README.md`. Fresh output directories are mandatory. The default step-2 physical descriptor returns blocked status and exit 2; this is expected and cannot be counted as a successful physical baseline.

Steps 5 and 6 remain colleague-led full reproduction, scientific review and release/archive decisions. Additional real data, time-resolved write/read validation and solver convergence are required before unknown combinations can be judged experimentally.

## Clean-clone repair revision

The historical selected records above remain attached to their original source fingerprints. Current-code reruns are in `evaluation/results/repaired/`, with a second full confirmation in `evaluation/results/repaired-confirmation/`. See `REPRODUCTION_REPAIR.md` and `evidence/repair/manifest.json`. The current quickstart is offline, constrained to tested dependencies, and needs no private cache. The full repair protocol is also integrated into the main manuscript, Supplement and standalone dossier.
