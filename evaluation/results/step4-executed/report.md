# Step 4: executed local performance and robustness

Status: pass. Nine cold studies; 108 cold jobs and 108 terminal-result checkpoint reuses.

| Workers | Jobs/study | Repeats | Cold median, s | Cold min-max, s | Resume median, s |
|---:|---:|---:|---:|---:|---:|
| 1 | 12 | 3 | 3.86744 | 3.80890-3.91006 | 0.01814 |
| 2 | 12 | 3 | 1.97810 | 1.91655-2.06654 | 0.01741 |
| 4 | 12 | 3 | 1.17817 | 1.12987-1.22860 | 0.01817 |

Results and configuration identities match across all worker counts and repeats. Worker subprocesses use one native numerical thread. These bounded models include startup and artifact IO and do not establish large-scale or cross-machine scalability.

Parent peak RSS and largest terminated child peak RSS are separately recorded in performance.csv, not aggregated into a concurrent-memory peak. Missing-parameter status is missing_data; a real process timeout is timeout. Both are failures, not physics results. Resume from one completed partial checkpoint succeeds; no forced-crash or power-loss test was performed.

Reproduce: `python scripts/evaluate_system.py step4 --out evaluation/results/new-step4`.
