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
- All 75 automated tests pass. No new-material superiority is inferred from these software checks.

## Reproduce

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for environment setup and individual commands. With dependencies installed:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ./lab
python scripts/evaluate_system.py step1 --out evaluation/results/my-step1
python scripts/verify_results.py
```

Step 1 automatically fetches its two pinned input files and verifies their SHA256. See [evaluation/README.md](evaluation/README.md) for steps 1–4, optional solver installation and full article reproduction with `python scripts/reproduce.py --online`. The public clone contains source adapters and reporting evidence; full third-party caches are excluded. For a quick check of the archived reporting outputs:

```bash
python scripts/verify_results.py
```

PDF compilation uses the already included figures and tables. The standalone `.tex` download needs its companion `figures/` directory from this bundle.

## Provenance and publication status

The evaluated software archive SHA-256 is `c64b94a573def9d999b65be7201947e9c2ce4e496aaf201650d7c1e3d44733aa`. `evidence/study_manifest.json` records the source archive and the fresh validation scope. The accompanying `SHA256SUMS` covers the final repository payload. Study results are retrospective, not prospectively preregistered.

The code and article materials are published at https://github.com/VesterlundCoder/memory-discover-lab. No DOI or peer-review acceptance is asserted. The manuscript draft has not undergone independent scientific review. The private archive preserves the complete historical `lab/` tree; only the selected files in `evidence/` and their detailed underlying outputs are used as this article's fresh result snapshot.

See [DATA_SOURCES.md](DATA_SOURCES.md) and [LICENSE_NOTICES.md](LICENSE_NOTICES.md). Third-party caches are excluded by `.gitignore`; keeping them in this local bundle does not assign a public redistribution license. The repository owner's existing MIT license is preserved; third-party inputs retain their own licenses. AI-assisted coding and drafting are disclosed in the article.

## Additional system-paper evaluations

The runnable evaluation package implements steps 1–4. Step 1 has been executed on 73 channel-age points and 90 processed fidelities: maximum full-Choi discrepancy is below 2e-14. A second-family software control, seven constructed-fault ablations and the local performance/robustness experiment also pass (108 cold jobs across workers 1, 2 and 4). The second experimental physical case and independent external reproduction remain pending. See [evaluation/README.md](evaluation/README.md) and the retained [step-1 report](evaluation/results/step1-executed/report.md). These outputs supplement the original article snapshot.
