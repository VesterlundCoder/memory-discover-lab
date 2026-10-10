# Reproducibility instructions

## Tested environment

Use Linux and **Python 3.12**. The clean environments tested for the repair used Python 3.12.14, NumPy 2.5.3, SciPy 1.18.1 and Matplotlib 3.10.8. The full environment also uses QuTiP 5.3.1, SeQUeNCe 1.2.0, PyCCE 1.1.1 and PySCF 2.14.0. Complete installed dependency pins are `requirements-lock-core.txt` (14 distributions) and `requirements-lock-full.txt` (131 distributions); the editable project is installed separately. These files describe the tested Linux environment, not universal wheels or a guarantee for untested Python/platform combinations. Python patch versions and OS details are recorded in actual results. No ML library is required.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements-lock-core.txt -c lab/constraints-tested.txt -r requirements-paper.txt -e ./lab
python -m unittest discover -s lab/tests -v
python -m unittest discover -s evaluation/tests -v
python scripts/reproduce_system.py --out reproductions/my-system --reference-root evaluation/results/repaired --allow-source-change
```

The core suite runs 75 lab tests with seven optional-backend skips, plus 18 evaluation/regression tests without skips. The full installation passes all 93 tests. A skipped test is not a passed backend validation. There are no tests requiring private source-lock files or a previous synthetic-demo run.

## Offline system evaluation

The four-pathway runner verifies unchanged, bundled experimental bytes before use. It runs the matched step-1 comparison, explicitly synthetic step-2 control, seven selected contract faults, and the full 108-job local worker experiment. It also runs the physical step-2 descriptor and requires its `blocked_missing_reviewed_data` status and exit code 2. No second-family experimental result is manufactured.

The repaired reference is `evaluation/results/repaired/step1` through `step4`. Historical outputs remain archived separately. Each run includes its own evaluation and lab source hashes, configuration, UTC timestamp and environment. Compare full scientific output with:

```bash
python scripts/verify_evaluation.py --reference evaluation/results/repaired/step4 --actual reproductions/my-system/step4 --require-same-source
```

Numerical tolerance is 1e-10 absolute and relative. Full channels, model configuration, seeds, counts and evidence gates are checked. Paths, time stamps, wall/CPU times, RSS measurements and source-dependent IDs are execution metadata and are not expected to be byte equal. Step 4's portable channel payload must exist; legacy summary-only records cannot substitute for it. Source/environment provenance is still retained and source fingerprints are reported separately.

## Offline paper numerical replay

```bash
python -m pip install -c requirements-lock-full.txt -c lab/constraints-tested.txt -r requirements-paper.txt -e './lab[all]'
python scripts/reproduce.py --out reproductions/my-paper
```

With no flags, the script uses `reproductions/latest`. It refuses a nonempty output tree and checks dependencies/input hashes before running. It recomputes the Teller data consistency/holdout/window analyses, reviewed operating-point channel, QuTiP verification and four seeded SeQUeNCe workloads; the PR2026 classical decay fits; the reviewed reference-table calculations; synthetic spin/count controls; and the hypothetical network workload. It then regenerates figures/tables and checks ten reporting invariants. Fresh logs and a machine-readable scope record are written under the chosen output tree. Archived article evidence is not overwritten.

**Scope:** this replays licensed measurement files and retained reviewed transcriptions. It does not reacquire/review primary-paper text, reconstruct original photon counts, repeat hardware experiments or recreate the 201-entry molecular source-collection audit. That historical audit remains attributed to the original source snapshot; offline replay records zero newly acquired molecular observations. The numerical-replay reporting mode explicitly enforces that exclusion.

## Wider remote source acquisition

```bash
python scripts/reproduce.py --online --out reproductions/new-source-snapshot
```

This selects the original acquisition adapters, requiring Zenodo, the pinned molecular GitHub source and primary-paper endpoints. It verifies the pinned dataset locks and retains the newly obtained metadata. Endpoint denial/changed bytes remain explicit failures. Remote source availability is not required by the quickstart or offline CI. Unlicensed source caches and primary-paper copies remain excluded from Git tracking.

## Figures and tables

A clean clone includes the numerical/fit outputs needed for figure-only regeneration. Measurement curves come from the licensed bundle if processed local files are absent:

```bash
python scripts/make_figures.py
python scripts/make_tables.py
python scripts/verify_results.py
```

The figure builder verifies/loads inputs before writing and stages all plots before replacement. A missing input produces an actionable error without replacing `architecture.pdf`. PDF creation/modification timestamps are suppressed. Two runs in the pinned validation environment produced identical bytes for all five PDFs and five PNGs. Cross-version font/plotting equivalence is not assumed. `SHA256SUMS` describes delivered bytes; it is not a claim that noisy measurements, hardware or timing records are reproducible.

## Optional-backend compatibility

PyCCE 1.1.1 directly imports removed NumPy/SciPy names. Use the lab adapter (`memorylab.common.optional_import('pycce')`), which restores the same Unicode dtype alias and SciPy `isintlike` utility before importing PyCCE. A direct `import pycce` in a fresh process may fail in this pinned environment. The compatibility layer does not alter a spin Hamiltonian; the optional single-spin analytical check tests the calculation separately. The Linux PySCF `/proc/self/statm` compatibility fallback preserves RSS/VMS units when numeric PID paths are inaccessible.

## PDFs and container

```bash
make pdf
make system-paper-pdf
```

PDF compilation requires TeX Live, `pdflatex`, Latin Modern, `microtype`, `amsmath`, `booktabs`, `longtable`, `graphicx`, `hyperref` and `enumitem`. For Debian/Ubuntu, install `texlive-latex-extra lmodern`; Poppler (`poppler-utils`) supports visual inspection. PDFs are already included; numerical replay does not require LaTeX. The separate ReportLab step-1 report also needs `fonts-dejavu-core`.

The Dockerfile pins Python 3.12.14 and installs the core dependency constraints; its default command runs the four software pathways. It needs writable `/results`. Docker was not available in the author validation environment, so the image build is not claimed as executed. The underlying clean Linux commands were executed. The `.dockerignore` preserves bundled measurement inputs and repaired reference evidence.

## Scientific limitations

Teller MC widths lack shared covariance; its operating-point channel is nonunique and does not identify T2. PR2026 classical retrieval scales are not homogeneous spin T2. The step-2 control's residual scale and optical interface are hypothetical. Rate-box bounds are conditional deterministic bounds, not prediction confidence intervals. The local performance study covers small models/workers only; timings and machine peaks are not portable scientific outputs. Independent colleague-led reproduction and scientific/release review (steps 5 and 6) remain pending.
