# WestQuant Memory Discovery Lab — research article and reproducibility bundle

**David Vesterlund — WestQuant, Vesterlund Ventures, Sweden. 10 October 2026.**

This repository accompanies *WestQuant Memory Discovery Lab: An Evidence-Aware Framework from Experimental Data to Quantum-Memory Simulation*. Its contribution is an executable source-to-model workflow with explicit physical and evidence boundaries. It is an English scientific manuscript based on actual reruns of version 0.6.0, with analytical verification, processed experimental-data reanalysis, retained negative diagnostics and event-simulator integration.

It does not report new hardware experiments, a validated new-material lifetime, or better-than-SOTA performance. ML for T2 is a separate project; no ML training is performed here.

## Files

| Path | Contents |
|---|---|
| `paper.tex`, `paper.pdf` | Full model, methods, executed results, figures and bibliography |
| `supplement/supplement.tex`, `supplement/supplement.pdf` | Interfaces, reference conditions, diagnostics, work counts and reproducibility details |
| `lab/` | Evaluated Python package, tests, configurations, dataset adapters and detailed outputs |
| `evidence/` | Article result snapshot, actual rerun logs, source-archive identity and claim-to-result map |
| `figures/` | Five reproducible scientific figures in PDF and PNG |
| `tables/` | Supplementary LaTeX tables and CSV counterparts generated from JSON |
| `scripts/` | Reproduction, figure/table generation and reporting verification |

## Executed headline results

- Ninety released state-fidelity scalars reproduce path and time-bin means 0.9510824229 and 0.9140479475. These are processed values, not independent raw-count experiments.
- A within-dataset spatial holdout gives maximum approximate standardized discrepancy 2.3417.
- Eight simple classical retrieval-decay fits yield six model mismatches and two inconclusive results. None identifies homogeneous physical spin T2.
- Ten primary-text-reviewed coherence references coexist with 201 provisional molecular entries; incomplete records are not promoted to physical predictions.
- Deterministic Hamiltonian controls and a known-generator count experiment verify specified models. The latter recovers 0.979663 ms from a 1 ms synthetic generator.
- A calibrated but nonunique fixed-point channel produces 87 retrieved pairs in 400,000 ideal-input SeQUeNCe attempts. These are simulated outcomes under incomplete optical assumptions.
- The original 75 tests and seven system tests passed. The repair revision adds eleven regression tests: 75 lab tests and 18 evaluation tests pass in the full environment; seven optional tests are skipped in the core environment. No new-material superiority is inferred.

## Reproduce

Use **Linux / Python 3.12** for the tested environment. From a clean clone:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements-lock-core.txt -c lab/constraints-tested.txt -r requirements-paper.txt -e ./lab
python scripts/reproduce_system.py --out reproductions/my-system --reference-root evaluation/results/repaired
python scripts/verify_results.py
```

This runs steps 1–4 without external source downloads, including the explicitly hypothetical step-2 control. The separate physical step-2 descriptor must remain blocked until reviewed experimental inputs are supplied. The licensed, unchanged experimental inputs are tracked under `data/experimental/`, with attribution and checksums. No private cache or previous run is needed.

To rerun the paper's numerical analyses and event simulations offline:

```bash
python -m pip install -c requirements-lock-full.txt -c lab/constraints-tested.txt -r requirements-paper.txt -e './lab[all]'
python scripts/reproduce.py --out reproductions/my-paper
```

This verifies bundled measurement bytes and recomputes fits, channel/network controls, figures and reporting checks in a fresh output tree. It reuses reviewed paper transcriptions and reference tables. It excludes reacquisition of the unlicensed molecular collection and rechecking unbundled primary-paper bytes. `--online` explicitly invokes the wider original source-acquisition workflow and requires those remote servers. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md), [evaluation/README.md](evaluation/README.md) and [REPRODUCTION_REPAIR.md](REPRODUCTION_REPAIR.md) for exact scope and validation.

PDF compilation uses the already included figures and tables. The standalone `.tex` download needs its companion `figures/` directory from this bundle.

## Provenance and publication status

The evaluated software archive SHA-256 is `c64b94a573def9d999b65be7201947e9c2ce4e496aaf201650d7c1e3d44733aa`. `evidence/study_manifest.json` records the source archive and the fresh validation scope. The accompanying `SHA256SUMS` covers the final repository payload. Study results are retrospective, not prospectively preregistered.

The code and article materials are published at https://github.com/VesterlundCoder/memory-discover-lab. No DOI or peer-review acceptance is asserted. The manuscript draft has not undergone independent scientific review. The private archive preserves the complete historical `lab/` tree; only the selected files in `evidence/` and their detailed underlying outputs are used as this article's fresh result snapshot.

See [DATA_SOURCES.md](DATA_SOURCES.md) and [LICENSE_NOTICES.md](LICENSE_NOTICES.md). Verified CC BY 4.0 measurement files are bundled with attribution. Other third-party caches are excluded by `.gitignore`; cache possession does not grant redistribution rights. The repository owner's existing MIT license is preserved; third-party inputs retain their own licenses. AI-assisted coding and drafting are disclosed in the article.

## Additional system-paper evaluations

The runnable evaluation package implements steps 1–4. Step 1 has been executed on 73 channel-age points and 90 processed fidelities: maximum full-Choi discrepancy is below 2e-14. A second-family software control, seven constructed-fault ablations and the local performance/robustness experiment also pass (108 cold jobs across workers 1, 2 and 4). A [second measured observable case: Bradley 2022 NV0 Ramsey](evaluation/results/bradley2022-nv0/report_sv.md) has now been executed on 24 experimental points with an explicit effective Hamiltonian and matched conditions. Its heldout envelope diagnostic passes, but its fixed-frequency X diagnostic fails; the strict microscopic physical-validation task and independent external reproduction remain pending. See [evaluation/README.md](evaluation/README.md) and the retained [step-1 report](evaluation/results/step1-executed/report.md). The original steps 1–4 are integrated into the main manuscript and Supplement; the new measured-observable case is documented separately, with a complete execution dossier in evaluation/paper/. The original numerical snapshot and initial system records remain traceable.
