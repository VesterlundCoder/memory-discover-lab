# Clean-clone reproduction repair and paper evidence

The reviewer inspected `de52b32`. The later documentation commit `f2f6514` had already added source-consistent step-2/step-3 confirmations, but the clean-clone acquisition and test defects still required code changes. This repair is software version **0.6.1**. Historical v0.6.0 results remain archived and are not silently relabeled as current-code results.

## Disposition of all twelve findings

| Finding | Change | Executed check or remaining scope |
|---|---|---|
| 1. Step 1 requires Zenodo | Bundle unchanged `4.csv`, `8a.csv` and the other licensed numerical files with attribution and SHA256; prefer them before network | Step 1 passes from a clean clone with external DNS/sockets denied; corrupt and missing bytes are rejected |
| 2. Default reproduction fails on private offline cache | Default `reproduce.py` uses licensed numerical replay and a fresh output tree | Clean isolated full environment completes default replay and ten reporting invariants without external network |
| 3. Figure builder raises `StopIteration` after overwrite | Validate/load inputs first; use bundled curves; stage figures before replacement | Missing-input regression returns exit 2 and preserves an existing `architecture.pdf`; clean figure-only run succeeds |
| 4. Two tests require absent files | Database gate uses explicit synthetic temporary rows; synthetic counts are tracked under tests/fixtures | 75 lab tests succeed in full environment without `lab/t2_data/source_lock.json` or previous synthetic-demo output |
| 5. Optional tests crash in core installation | QuTiP and SeQUeNCe tests have explicit availability skips | Core lab suite: 68 pass, 7 optional skips, 0 failures; evaluation/regression suite: 18 pass |
| 6. Step 2 differs from saved synthetic result | One-command runner explicitly selects the synthetic case and separately checks the physical pending descriptor | Synthetic curve gate passes; physical descriptor must return exit 2 and `blocked_missing_reviewed_data`. Physical validation remains incomplete |
| 7. Archived source differs from HEAD | Rerun all four pathways with one source content identity; retain old snapshots separately | Current repair outputs and a second confirmation share the hashes below; four strict source/scientific comparisons pass |
| 8. Runtime/path fields prevent byte comparison | Add scientific comparator and mandatory step-4 portable full channel/configuration payload | Second complete execution matches scientifically; altered metric/channel and source-mismatch controls fail as intended |
| 9. Architecture PDF is not byte reproducible | Remove PDF creation/modification timestamps; constrain plotting dependencies | All five figure PDFs and five PNGs are byte-identical between two runs; delivered checksums regenerated |
| 10. Quickstart/Docker/CI are unconstrained | Python 3.12 documented; core/full installed dependency pins plus tested constraints used | Clean isolated core/full installation succeeds on Python 3.12.14; Dockerfile updated, image build not executed |
| 11. CI depends on Zenodo | Bundle required data; deny external network during core/system and paper jobs after package installation | Equivalent author-operated clean-clone jobs pass locally; GitHub execution is verified separately after publication |
| 12. Direct PyCCE import fails | Document adapter-only compatibility path and its exact aliases | Fresh direct import fails at SciPy `isintlike`; adapter import succeeds; optional analytical PyCCE test passes |

## Executed validation

A local candidate Git repository was created from the public deliverable files and cloned to an empty working tree, with no ignored source caches, source-lock file, processed data tree or generated synthetic-demo directory. Isolated core and full virtual environments were installed. Dependencies were retrieved before execution; execution then used a test-only socket/DNS denial shim permitting loopback for the downloader's local-server tests.

- Core: 75 lab tests run, **68 passed and 7 skipped**, and all **18 evaluation/regression tests passed**.
- Full `[all]`: **75 lab tests and 18 evaluation/regression tests passed**, with no skips.
- Two complete system passes: 73 channel-age comparisons and 90 processed fidelities per pass; maximum full-Choi discrepancy **1.3103013043660781e-14**; the 41-point synthetic step-2 curve and hypothetical network control; seven rejected faults with seven valid positive controls; **108 cold jobs and 108 checkpoint reuses per pass**.
- Four strict source/scientific comparison reports pass, including full step-4 channel/configuration payloads. The selected 1e-10 absolute/relative equality tolerance is a numerical reproducibility gate, not an experimental error bar.
- The physical step-2 descriptor remains blocked in both passes. The network optical interface of the synthetic case remains hypothetical.
- Default paper replay completes: 87 retrieved pairs in 400,000 Teller SeQUeNCe attempts; six mismatching and two inconclusive classical PR decay fits; reviewed-table and synthetic controls; 321 retrieved pairs in the separate 2,000-trial hypothetical SeQUeNCe case; **ten reporting checks**.
- Two figure-only runs produce the same bytes for **ten files**. The input-error regression confirms that an existing architecture figure survives failure.

The repair system runs are reproduction controls performed while other author-validation tasks could be active. Their measured wall times are preserved, but do not establish a new performance improvement. The original bounded benchmark remains attributed to its original source/environment snapshot. Robustness probes are separate from the 108 cold jobs per pass.

The first remote repair CI run, [38058979906](https://github.com/VesterlundCoder/memory-discover-lab/actions/runs/38058979906), passed the full offline paper replay and both core test suites, but failed the step-2 comparison of individual Kraus entries. Across the local and GitHub runners, the compared imaginary entries were 6.78807969042818e-08 and 5.623973985928678e-08. Kraus decompositions are not unique; phases and unitary mixtures of operators can encode the same map. The comparator now reconstructs and compares full and conditional Choi matrices at the unchanged 1e-10 numerical tolerance. It also checks consistency with the stored full Choi matrix, and preserves basis, vectorization, metrics and physical configuration. Three added regressions accept gauge-equivalent decompositions and reject changed conditional maps and changed operators hidden behind an unchanged stored Choi matrix. The original failure and its source identity are retained in `evidence/repair/first_remote_ci_failure.txt` and `pre_gauge_history.json`.

## Source and record identity

The repaired runs share:

- Evaluation source SHA256: `254b1bbb8a1d3c95d28b63e69d40c3a7afcbc2aa76b4b14a2bf8a727c9ead1e9`.
- Lab source SHA256: `99b0ef35caf1791653ce2b9c029514b21e9340ed58198194e291bccc4095e62f`.

These content identities are checked against actual Python files before publication. A candidate local Git commit is recorded in `evidence/repair/manifest.json`; it identifies the clean local test tree, not a GitHub release. The published Git commit and subsequent CI run identify the remote version separately. Documentation/figure files do not enter the two Python source fingerprints.

| Evidence | Location |
|---|---|
| Current four-pathway summaries, inputs/configs, CSVs and portable channels | `evaluation/results/repaired/step1` through `step4` |
| Physical pending descriptor outcome | `evaluation/results/repaired/step2-physical-pending/summary.json` |
| Four source/scientific comparison reports | `evidence/repair/step1-comparison.json` through `step4-comparison.json` |
| Raw execution/test/install logs and paper replay outputs | `evidence/repair/` |
| Overall scope and work counts | `evidence/repair/manifest.json` |
| Figure hashes and repeatability result | `evidence/repair/figure_reproducibility.json` |
| Numerical replay's claim-to-result map | `evidence/repair/paper-claim_result_map.json` |
| Complete installed dependency pins | `requirements-lock-core.txt`, `requirements-lock-full.txt` |
| Data provenance, unchanged bytes and attribution | `data/experimental/manifest.json`, `ATTRIBUTION.md` |

## Reproduction boundary

Offline replay verifies bundled released measurement bytes and uses retained reviewed primary-paper transcriptions and reference tables. It does not reacquire the molecular collection with unspecified license, reverify unbundled primary-paper PDFs, reproduce hardware, establish a homogeneous T2 from classical retrieval, or independently review the transcriptions. Its fresh molecular-observation count is **zero**. The historical 201-entry collection audit remains a historical source result, not an offline replay outcome.

The Docker build was not run because Docker was unavailable. TeX compilation and visual PDF review are recorded separately. The optional online acquisition path is retained but external endpoints were not retested during the denied-network repair validation. These limits are explicit, and author-operated CI does not complete the colleagues' independent reproduction and scientific/release review (steps 5 and 6).
