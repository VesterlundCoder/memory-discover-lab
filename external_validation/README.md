# External re-execution of WestQuant Memory Discovery Lab v0.6

Date: 10 October 2026. Performed by an AI assistant (Claude, Anthropic) at the
author's request, in a cloud environment the author did not control. This is a
computational re-execution and an independent recomputation from released data.
It is not a replication by an independent research group and involves no hardware.

Known memory used as the test case: Pr3+:Y2SiO5 memory array, Teller et al.,
Phys. Rev. X 15, 031053 (2025), data doi:10.5281/zenodo.14929997.

## Files

| Path | Content |
|---|---|
| `external_validation.tex` | Section for the paper; `\input{external_validation}`. One `\ref{sec:results-teller}` label must be adjusted. |
| `external_validation_preview.pdf` | The section compiled stand-alone (without Latin Modern, which this machine lacks). |
| `scripts/compare_outputs.py` | Byte and value comparison of a re-run tree against the archived tree. |
| `scripts/independent_check.py` | Recomputation of the Teller operating point with NumPy/SciPy only. |
| `scripts/extra_seeds.py` | The lab's SeQUeNCe workload for 40 seeds not in the archive. |
| `results/` | Comparison tables, the 25 independent checks, the extra-seed run, step-1 outputs. |
| `logs/` | Unedited logs of every command (absolute scratch paths shortened). |
| `environment/` | `pip freeze` of the three environments and system information. |

## Process, in the order it was done

1. Recorded SHA-256 of the zip (`c64b94a5...d44733aa`), unpacked it (457 files).
   Kept one copy untouched as reference; made a working copy per environment.
2. Environment A: CPython 3.12.3 (system). Environment B: CPython 3.12.13
   (installed with uv; 3.12.14, the author's version, was not available).
   `pip install -c constraints-tested.txt -e '.[all]'`; all 15 pins installed exactly.
3. `python -m memorylab doctor`: all optional packages import; no ORCA or QE binary.
4. `python -m unittest discover -s tests -v`: 75 of 75 pass in A and B.
5. `python -m memorylab reproduce examples/teller2025_baseline.json --out baselines/teller2025 --offline`: exit 0 in A and B.
6. `python -m memorylab.t2lab run --offline --sequence`: exit 0 in A and B.
7. `scripts/compare_outputs.py <reference> <working copy> baselines t2_runs t2_data`:
   65 files; A 61 byte-identical, B 62; no numerical difference in either.
8. `python scripts/verify_lab.py --cross-backend`: A fails (unittest loader, Python 3.12.3);
   B passes, 86 tests, maximum Choi difference 3.9968e-15 over 18 operating-point pairs.
9. `python -m memorylab pipeline examples/pipeline_full.json`: `dataset_failure`
   (this machine's network policy blocks the data sources). With `--skip-fetch`: success, 16 candidates.
10. `scripts/independent_check.py`: 25 of 25 checks agree with the lab's numbers.
11. Article audit: extracted text of the cached `paper.pdf` and `supplement.pdf`
    with `pdftotext`; checked fidelities, efficiencies, window fraction, times, temperature, wavelength.
12. `scripts/extra_seeds.py`: 40 new seeds x 100 000 attempts; 790 pairs against 796.6 expected.
13. Public repository, commit `de52b32`, clean export; copied the archive's
    `baselines/teller2025/cache`, `fetch_manifest.json`, `t2_data` and
    `t2_runs/synthetic_demo` into `lab/`; `python scripts/reproduce.py` (offline): exit 0, 63 s;
    176 of 186 files in `SHA256SUMS` unchanged. `evaluate_system.py step1`: pass.

## Not done

- `make pdf`: this machine lacks the Latin Modern LaTeX package.
- Online fetch of any source: blocked by this machine's network policy, so the
  cached bytes were checked against their recorded SHA-256 only.
- ORCA, Quantum ESPRESSO: no binaries.
- Evaluation steps 2-4 of the public repository were run earlier in a core-only
  install; their outputs are not byte-comparable with the committed ones (timestamps, paths, timings).
