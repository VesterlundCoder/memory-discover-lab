# Reproducibility instructions

## Public clone and private archive

A fresh GitHub clone omits third-party caches with unverified redistribution permissions. Start with `python scripts/evaluate_system.py step1 --out evaluation/results/new-step1` after the core installation in README.md; its two pinned sources are fetched automatically. Full article reproduction in a fresh clone uses `python scripts/reproduce.py --online`. The offline commands below apply after retrieval or to the original private archive. Figure-only regeneration needs the detailed source/fit outputs produced by full numerical reproduction.

## Environment

The recorded runtime is Linux, Python 3.12.14, NumPy 2.5.3, SciPy 1.18.1, QuTiP 5.3.1, PySCF 2.14.0, PyCCE 1.1.1, ASE 3.29.0, MaxwellBloch 0.12.0, SeQUeNCe 1.2.0 and pandas 2.3.3. Figure generation used Matplotlib 3.10.8. See the environment object in the result summaries for other installed optional packages. Optional software installation may require network access and compatible wheels or compilers.

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e './lab[all]'
python -m pip install numpy==2.5.3 scipy==1.18.1 pandas==2.3.3 matplotlib==3.10.8
```

The package's declared Python support starts at 3.10; the listed study runtime is the actually tested one. No ML packages or training services are required. A PySCF container compatibility fallback reads `/proc/self/statm` page counts if numeric PID paths are inaccessible; it does not change the electronic-structure equations.

## Full numerical reproduction

```bash
python scripts/reproduce.py
```

This runs the following commands from `lab/` and stops on a nonzero exit status:

```bash
python -m memorylab reproduce examples/teller2025_baseline.json --out baselines/teller2025 --offline
python -m memorylab.t2lab run --offline --sequence
python -m unittest discover -s tests -v
```

It copies the newly produced result summaries into `evidence/`, regenerates all figures and supplementary tables, and runs reporting invariants. Complete logs go into `evidence/paper_*_reproduction.log` and `evidence/paper_test_results.log`. Reproduction replaces these selected outputs; retain an untouched copy of this bundle if the exact delivered bytes are needed.

Offline means no remote source download, not no installed dependencies. It verifies the archived source checksums and fails on missing/corrupted source artifacts. `python scripts/reproduce.py --online` downloads sources through the implemented adapters and may create a different metadata snapshot. The source-lock manifests retain URLs, revisions, licenses and hashes. Do not silently relabel a refreshed snapshot as the original.

## Figures and tables only

```bash
python scripts/make_figures.py
python scripts/make_tables.py
python scripts/verify_results.py
```

These reuse existing numerical outputs. They do not rerun physical experiments. The constructive mean-fidelity nonidentifiability example performs direct Kraus propagation and is included in the figure-generation script. The generated CSVs preserve numeric diagnostics; the underlying JSON retains the full precision, issue flags and conditions.

## Compile the PDFs

TeX Live with `pdflatex`, Latin Modern, `microtype`, `amsmath`, `booktabs`, `longtable`, `graphicx` and `hyperref` is sufficient. Build from the repository root:

```bash
make pdf
```

This compiles each source twice to resolve references. No BibTeX run is required because the main source contains its numbered bibliography. Figures must remain in `figures/`; supplementary generated tables must remain in `tables/`. PDF rendering/inspection used Poppler `pdftoppm` and `pdfinfo`. Numerical reproduction and PDF compilation are separate operations.

## Scope and uncertainty

The Teller holdout assumes independent supplied MC uncertainty widths; shared covariance is not available. Its finite-point channel is an isotropic approximation and cannot be extrapolated to estimate T2. The derived acceptance omits several optical/detection losses. Network intervals describe simulation sampling at fixed parameters.

The PR2026 fits use released Gaussian-error quantities. Their apparent scales are not spin T2; all eight outputs withhold physical T2. Parametric bootstrap intervals condition on the model and exclude shared systematics/model error. The count-control interval concerns one synthetic instance, not calibrated coverage or prediction error. Deterministic rate-box ranges are bounds under supplied coefficients, not confidence intervals.

Exact counts, seeds and source pointers are in the Supplement and `evidence/claim_result_map.json`. The original article snapshot did not include a runtime/scalability benchmark or second network-simulator cross-validation. The separate evaluation addendum now includes a bounded local worker/checkpoint benchmark; independent environment validation and a second experimental physical case remain pending.

## Evaluation addendum PDF

`python scripts/make_evaluation_report.py` renders the executed evaluation results. It requires ReportLab (`python -m pip install reportlab`) and the DejaVu Sans fonts under `/usr/share/fonts/truetype/dejavu/` (Debian/Ubuntu package `fonts-dejavu-core`). The PDF is already included. This report supplements the original manuscript; it does not relabel a software control as a physical measurement.
