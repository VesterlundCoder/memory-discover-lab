# WestQuant Memory Discovery Lab — research article and reproducibility bundle

## Archival reproduction identity

The DQS archive preparation reproduces scientific source commit
`2c6bb71fac1a8b6561c2dfea89d280f2866155ae` with Python 3.12.15 and the pinned
distributions in `requirements-release-v070.txt`. The new run passes 109 tests
and the canonical/confirmation comparisons. This archival branch changes citation
metadata and documentation only; scientific code remains identical to that commit.

For this replay, check out the full commit above and pass it to
`scripts/reproduce_release.py --tag 2c6bb71fac1a8b6561c2dfea89d280f2866155ae`.
The legacy public `v0.7.0` tag resolves to a different tree and has not been moved.
Earlier article/execution snapshots are retained in `HISTORY.md`; the new replay
and separately manifested sensitivity studies are supplied in the companion data
archive. DOI links will be added after the approved deposition is published.
Companion data and reproduction materials:
[10.5281/zenodo.23732317](https://doi.org/10.5281/zenodo.23732317).
The manuscript files retained in this code snapshot are historical. The revised
DQS manuscript and Additional File 1 are supplied in the companion data archive.

**David Vesterlund — WestQuant, Vesterlund Ventures, Sweden. 10 October 2026.**

This repository accompanies *WestQuant Memory Discovery Lab: An Evidence-Aware Framework from Experimental Data to Quantum-Memory Simulation*. Its contribution is an executable source-to-model workflow with explicit physical and evidence boundaries. It is an English scientific manuscript covering the original version-0.6.0 reruns and the subsequent Bradley, complete-protocol, convergence and two-simulator studies. It retains analytical verification, processed experimental-data reanalysis, negative diagnostics and revision-specific source identities.

It does not report new hardware experiments, a validated new-material lifetime, or better-than-SOTA performance. ML for T2 is a separate project; no ML training is performed here.

## Files

| Path | Contents |
|---|---|
| `paper.tex`, `paper.pdf` | Full model, methods, executed results, figures and bibliography |
| `supplement/supplement.tex`, `supplement/supplement.pdf` | Interfaces, reference conditions, diagnostics, work counts and reproducibility details |
| `lab/` | Evaluated Python package, tests, configurations, dataset adapters and detailed outputs |
| `evidence/` | Article result snapshot, actual rerun logs, source-archive identity and claim-to-result map |
| `figures/` | Five original figures and four validation-extension figures in PDF and PNG |
| `tables/` | Supplementary LaTeX tables and CSV counterparts generated from JSON |
| `scripts/` | Reproduction, figure/table generation and reporting verification |

## Executed headline results

- Ninety released state-fidelity scalars reproduce path and time-bin means 0.9510824229 and 0.9140479475. These are processed values, not independent raw-count experiments.
- A within-dataset spatial holdout gives maximum approximate standardized discrepancy 2.3417.
- Eight simple classical retrieval-decay fits yield six model mismatches and two inconclusive results. None identifies homogeneous physical spin T2.
- Ten primary-text-reviewed coherence references coexist with 201 provisional molecular entries; incomplete records are not promoted to physical predictions.
- Deterministic Hamiltonian controls and a known-generator count experiment verify specified models. The latter recovers 0.979663 ms from a 1 ms synthetic generator.
- A calibrated but nonunique fixed-point channel produces 87 retrieved pairs in 400,000 ideal-input SeQUeNCe attempts. These are simulated outcomes under incomplete optical assumptions.
- The original and repair test records remain historical. In the latest extension environment, 109 tests ran: 107 passed and two optional backend tests were skipped. A fresh offline replay matched 359 JSON records and 11 exact RNG arrays. No new-material superiority is inferred.

## Reproduce

Use **Linux / Python 3.12** for the tested environment. From a clean clone:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements-lock-core.txt -c lab/constraints-tested.txt -r requirements-paper.txt -e ./lab
python scripts/reproduce_system.py --out reproductions/my-system --reference-root evaluation/results/repaired --allow-source-change
python scripts/verify_results.py
```

This runs steps 1–4 without external source downloads, including the explicitly hypothetical step-2 control. The separate physical step-2 descriptor must remain blocked until reviewed experimental inputs are supplied. The licensed, unchanged experimental inputs are tracked under `data/experimental/`, with attribution and checksums. No private cache or previous run is needed.

To rerun the paper's numerical analyses and event simulations offline:

```bash
python -m pip install -c requirements-lock-full.txt -c lab/constraints-tested.txt -r requirements-paper.txt -e './lab[all]'
python scripts/reproduce.py --out reproductions/my-paper
```

This verifies bundled measurement bytes and recomputes fits, channel/network controls, figures and reporting checks in a fresh output tree. It reuses reviewed paper transcriptions and reference tables. It excludes reacquisition of the unlicensed molecular collection and rechecking unbundled primary-paper bytes. `--online` explicitly invokes the wider original source-acquisition workflow and requires those remote servers. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md), [evaluation/README.md](evaluation/README.md) and [REPRODUCTION_REPAIR.md](REPRODUCTION_REPAIR.md) for exact scope and validation.

PDF compilation uses the included figures, tables and section files: `make pdf`. Use the complete repository source tree rather than the standalone `.tex` download. For the updated claim checks and English figure regeneration, see [REPRODUCIBILITY.md](REPRODUCIBILITY.md#current-manuscript-and-validation-extension).

## Provenance and publication status

The original evaluated software archive SHA-256 is `c64b94a573def9d999b65be7201947e9c2ce4e496aaf201650d7c1e3d44733aa`. `evidence/study_manifest.json` records the source archive and the fresh validation scope. The accompanying `SHA256SUMS` covers the final repository payload. Study results are retrospective, not prospectively preregistered.

The code and article materials are published at https://github.com/VesterlundCoder/memory-discover-lab. No DOI or peer-review acceptance is asserted. The manuscript draft has not undergone independent scientific review. The private archive preserves the complete historical `lab/` tree; only the selected files in `evidence/` and their detailed underlying outputs are used as this article's fresh result snapshot.

See [DATA_SOURCES.md](DATA_SOURCES.md) and [LICENSE_NOTICES.md](LICENSE_NOTICES.md). Verified CC BY 4.0 measurement files are bundled with attribution. Other third-party caches are excluded by `.gitignore`; cache possession does not grant redistribution rights. The repository owner's existing MIT license is preserved; third-party inputs retain their own licenses. AI-assisted coding and drafting are disclosed in the article.

## Additional system-paper evaluations

The runnable evaluation package implements steps 1–4. Step 1 has been executed on 73 channel-age points and 90 processed fidelities: maximum full-Choi discrepancy is below 2e-14. A second-family software control, seven constructed-fault ablations and the local performance/robustness experiment also pass (108 cold jobs across workers 1, 2 and 4). A [second measured observable case: Bradley 2022 NV0 Ramsey](evaluation/results/bradley2022-nv0/report_sv.md) has now been executed on 24 experimental points with an explicit effective Hamiltonian and matched conditions. Its heldout envelope diagnostic passes, but its fixed-frequency X diagnostic fails; the strict microscopic physical-validation task and independent external reproduction remain pending. See [evaluation/README.md](evaluation/README.md) and the retained [step-1 report](evaluation/results/step1-executed/report.md). The original steps 1–4, Bradley case and subsequent validation extension are integrated into the main manuscript and Supplement. The standalone dossier in evaluation/paper/ retains the historical steps 1–4. The original numerical snapshot and initial system records remain traceable.

## New executed validation extension (10 October 2026)

The [Swedish result report](evaluation/results/validation_extension/REPORT_SV.md) and [extension reproduction instructions](evaluation/README.md#protocol-convergence-and-second-network-simulator) document joint time-dependent protocol checks, spin-bath convergence and native SeQUeNCe/QuNetSim executions. Numerical results: 56 channel-age points, 336 state probes, 69 coherence calls and a larger 256-run paired simulator study with 131,072 attempts. All 128 larger paired comparisons passed. A fresh offline replay compared every archived native run and RNG trace.

Joint experimental validation remains inconclusive because matched fidelity data are missing. The converged baths are synthetic; no material prediction is authorized. QuNetSim uses a custom QuTiP density backend and shared external logical time, so physical network timing is not cross-validated. These results are included in the current article and Supplement. `evidence/article_update_claim_map.json` connects five updated claim groups to checked result bytes; `evidence/article_release_verification.json` records the manuscript build and page review.
