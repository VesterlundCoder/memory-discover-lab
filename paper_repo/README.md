# WestQuant Memory Discovery Lab — research article and reproducibility bundle

**David Vesterlund — WestQuant, Vesterlund Ventures, Sweden. 10 October 2026.**

This repository accompanies *WestQuant Memory Discovery Lab: An Evidence-Aware Framework from Experimental Data to Quantum-Memory Simulation*. Its contribution is an executable source-to-model workflow with explicit physical and evidence boundaries. It is an English scientific manuscript based on actual reruns of version 0.7.0, with analytical verification, processed experimental-data reanalysis, retained negative diagnostics and event-simulator integration.

It does not report new hardware experiments, a validated new-material lifetime, or better-than-SOTA performance.

## Files

| Path | Contents |
|---|---|
| `paper.tex`, `paper.pdf` | Full model, methods, executed results, figures and bibliography |
| `supplement/supplement.tex`, `supplement/supplement.pdf` | Interfaces, reference conditions, diagnostics, work counts and reproducibility details |
| `lab/` | Evaluated Python package, tests, configurations, cached input data and detailed outputs |
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
- All 124 automated tests pass. No new-material superiority is inferred from these software checks.

## Reproduce

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for environment setup and individual commands. With dependencies installed:

```bash
python scripts/reproduce.py
make pdf
```

The default uses pinned cached artifacts and checksums. `--online` requests a fresh source retrieval; it is not the archived source snapshot. For a quick check of the archived reporting outputs:

```bash
python scripts/verify_results.py
```

PDF compilation uses the already included figures and tables. The standalone `.tex` download needs its companion `figures/` directory from this bundle.

## Provenance and publication status

The evaluated software archive SHA-256 is `c64b94a573def9d999b65be7201947e9c2ce4e496aaf201650d7c1e3d44733aa`. `evidence/study_manifest.json` records the source archive and the fresh validation scope. The accompanying `SHA256SUMS` covers the final repository payload. Study results are retrospective, not prospectively preregistered.

This is a local repo-ready delivery. No remote repository, DOI or peer-review acceptance is asserted. The manuscript draft has not undergone independent scientific review. The complete `lab/` tree preserves historical outputs for source continuity; only the selected files in `evidence/` and their detailed underlying outputs are used as this article's fresh result snapshot.

See [DATA_SOURCES.md](DATA_SOURCES.md) and [LICENSE_NOTICES.md](LICENSE_NOTICES.md). Third-party caches are excluded by `.gitignore`; keeping them in this local bundle does not assign a public redistribution license. No new license is imposed on the author's code by this delivery. AI-assisted coding and drafting are disclosed in the article.
