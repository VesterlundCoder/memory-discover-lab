# Historical WestQuant article evidence

Moved out of Additional File 1 on 28 October 2026. These are historical snapshots, not the canonical v0.7.0 result set. Source text is preserved verbatim below; older test totals, DOI statements and comparisons describe their original snapshots. This file is prepared for inclusion in the repository; it has not been pushed.

## Former S8–S9

```latex
\section{Historical system evaluation: executed protocol}
\label{sec:systemprotocol}
Steps 1, 3 and 4 have executed results at their stated software scope. Step 2 has an executed synthetic second-family case, whereas its experimental physical objective remains blocked. The four historical selected records share evaluation-source fingerprint
\par\noindent\begin{minipage}{\linewidth}\centering\small\texttt{d8fc6d2ecb580e0ba1c8881ffbd542d087c}\\\texttt{493b7621cb89509948e595211ec92}.\end{minipage}\par
Their common lab-source fingerprint is
\par\noindent\begin{minipage}{\linewidth}\centering\small\texttt{9c4490acf2e5a42e8e10007989eeb94b5e4}\\\texttt{06b17f5d187ca310847581ee2edb7}.\end{minipage}\par
These fingerprints identify source content, not hardware or an external scientific endorsement. Steps 2 and 3 were confirmed with the published implementation after their initial runs; the initial outputs remain archived. Table generation asserts the shared fingerprint and expected numerical/status gates without overwriting the original run records. The configuration digest and UTC timestamp of each selected record are in \code{evidence/system\_evaluation\_claim\_map.json}. Generated table files are under \code{evaluation/paper/}.

\subsection{Step 1: independent reference equations and matched inputs}
The reference \code{evaluation/wqeval/reference.py} imports NumPy/SciPy without importing \code{memorylab}. For column vectorization and Hamiltonian $G=\mathrm{diag}(0,\delta)$ in Hz, it uses
\[
\mathcal L=-2\pi i(I\otimes G-G^{\mathsf T}\otimes I)
+\sum_J\left[J^*\otimes J-\tfrac12 I\otimes J^\dagger J
-\tfrac12(J^\dagger J)^{\mathsf T}\otimes I\right].
\]
The jump operators are $\sqrt{\Gamma_1(1-p_e)}\,|0\rangle\langle1|$, $\sqrt{\Gamma_1p_e}\,|1\rangle\langle0|$, and $\sqrt{\Gamma_\phi/2}\,Z$. The stage superoperator is $\exp(t\mathcal L)$. Write and read stages include their specified depolarizing maps, and storage adds the declared network-activity dephasing. The reference constructs $C=\sum_{a,b}|a\rangle\langle b|\otimes\mathcal E(|a\rangle\langle b|)$ by matrix-unit propagation, including an orthogonal erasure outcome for the full channel. It computes six Pauli-eigenstate outputs and their mean target fidelity independently of the lab's Kraus construction.

The four joint parameter choices $(\Gamma_1,\delta,p_e)$ are $(0,0,0)$, $(0.05,123,0.1)$, $(10,-500,0.5)$ and $(100,1000,0.9)$, with rates in s$^{-1}$ and detunings in Hz. Each is combined with storage temperatures 4.2, 10 and 80 K and ages $[0,10^{-6},10^{-4},10^{-3},10^{-2},10^{-1}]$ s. Write/read stages remain at 4.2 K, last $10^{-4}/2\times10^{-4}$ s and use acceptance 0.8/0.7 and depolarization 0.01/0.02. The pure-dephasing rate is $0.01+0.001T+0.001(T/10)^3$ s$^{-1}$, erasure rate 0.01 s$^{-1}$, and storage activity contributes $10\times0.002=0.02$ s$^{-1}$. Rate validity is declared over 1--300 K. These are chosen software profiles, not fitted material parameters. The measured Teller point supplies the thirteenth profile and its sole supported age of 18 $\mu$s at 3 K, giving $12\times6+1=73$ channel-age points.

The two experimental input files are \code{4.csv} and \code{8a.csv} from record 14929997:v1. Their SHA-256 hashes, original download URLs and data-license metadata are pinned in \code{evaluation/data/teller\_sources.json}. Both parsers use the same checked bytes. The path file yields 30 values and mean 0.9510824228990328; the time-bin file yields 60 values and mean 0.9140479475068066. The discrepancy is zero for every processed value. The comparison threshold is $10^{-8}$ for the full Choi matrix, six states, average fidelity, acceptance and processed values. This threshold is numerical, not an experimental accuracy margin.

Both timing arms are warmed up before five repeats, with their order randomized by seed 20261010. All 73 channel constructions are included in each repeat. \code{construction\_timing.csv} retains every measured duration and actual order. The arms do not perform equal amounts of metadata, export, validation or metric-construction work. File IO, source retrieval, network events, fits and electronic structure are excluded. Native thread environment variables are recorded but were not constrained for step 1. The medians cannot be interpreted as a fair end-to-end speedup or engineering-effort reduction. \code{related\_tools\_audit.json} distinguishes executed comparison from documentary context; AiiDA, PySCF, PyCCE, QuTiP and SeQUeNCe were not separately timed here. Existing AiiDA provenance and caching are not presented as new contributions.

\subsection{Step 2: synthetic control, curve gate and physical stop}
The model/curve comparison requires the observable \code{complex\_pure\_dephasing\_coherence}, explicit exclusion of population relaxation, source hashes, curve reviewer, normalization and observable mapping. A measured case additionally requires reviewed model-parameter provenance, a nonhypothetical model and exact equality of full declared experimental conditions between curve and model. The fixed-model runner accepts \code{exact\_spin\_bath} or optional \code{pycce}; it fits zero parameters. The initial curve value must be unity, magnitudes must lie in the unit disk and a strictly increasing finite grid must start at zero. No silent clipping of noisy or unnormalized measurements is provided.

The executed control has one $^{13}$C nuclear spin $I=1/2$, central logical projections $\pm1/2$, laboratory $A_{zz}=4000$ Hz and $\nu_z=214163.9829$ Hz, zero other couplings, 4.2 K and zero pulses. Forty-one equally spaced ages span 0--1 ms. An independent closed-form Gibbs-initialized FID produces the curve; the finite Hamiltonian solver supplies the comparison. Every complex residual is divided by the chosen scale 0.01, and the maximum must be at most three. The observed maximum is $3.7192473\times10^{-12}$. This chosen scale is not an experimental SEM, and the gate has no calibrated statistical false-positive rate. The 75--100 $\mu$s crossing bracket differs from the earlier 101-point control's 90--100 $\mu$s bracket solely because the grids differ; both are sampled numerical brackets and both detect revivals.

All write/store/read temperatures are hypothetically 4.2 K. The supplied interface has acceptance 0.8/0.7, depolarization 0.01/0.02 and durations 100/200 $\mu$s, with the independent rate models retained from the example. Export requires \code{--allow-hypothetical}. At 500 $\mu$s, the provider-neutral two-node workload has 10,000 trials, herald probability 0.1, 1 ms interval, Bell-fidelity threshold 0.8 and seed 20261010. It yields 1020 heralds and 313 retrieved/quality-qualified pairs. Conditional Bell fidelity is 0.9559176317211326; the retrieved-fraction Wilson interval is [0.0280630600,0.0348969001]. The simulated qualified rate is 31.3 s$^{-1}$ under these supplied assumptions, not measured network performance. This workload is not the earlier 2000-trial SeQUeNCe control.

The separate pending descriptor targets a molecular reference at DOI 10.1039/C8SC04122A. Running it returns \code{blocked\_missing\_reviewed\_data} and exit code two, with no physical validation and no network export. Required inputs are a reviewed normalized curve with measurement uncertainties, fixed Hamiltonian and tensor frames, field/temperature/isotopes/pulses, separation of relaxation from pure dephasing, and independent optical-interface review. Reported molecular phase-memory time alone does not satisfy these requirements. Thus no independently parameterized second-family physical validation or new-material lifetime is supplied by this original step-2 pathway. The subsequent Bradley observable case is described separately below.

\subsection{Step 3: individual fault interventions}
The suite creates local copies of inputs and explicitly unsafe bypasses without modifying production guards. Each invalid case has a valid positive control that must succeed. Rejection alone would be insufficient if every valid input also failed. All seven positive controls and all seven guarded rejections pass; the deliberate bypasses accept all seven cases.
\input{evaluation/paper/faults.tex}

The age bypass changes the declared sole point age before evaluating a tenfold longer age, thereby illustrating an unsupported extrapolation rather than measuring its physical error. The temperature bypass changes the declared point temperature by 1 K, again with no experimentally known extrapolation error. Noise independence is counted as an unsupported declaration; evidence promotion counts two age samples. The rate-definition example has $\Gamma_1=10$ s$^{-1}$ and correct independent $\Gamma_\phi=20$ s$^{-1}$, giving 40 ms. Treating total coherence rate 25 s$^{-1}$ as pure dephasing gives 33.333 ms instead. The modified-source case changes a chosen value from 0.001 to 1 s; it exercises the new evaluation source contract, whereas the other six cases exercise existing lab guards.

In the incremental-application control, the 1 ms complete channel includes write/read depolarization as well as storage; applying it twice produces maximum density-element discrepancy 0.0972467329 relative to applying it once. A separate units control converts 1 ms correctly to 0.001 s and contrasts it with an omitted conversion to 1 s; its maximum element discrepancy is 0.1322008762. These consequences have different units and scientific meanings. Neither their average nor seven out of seven represents a general material-prediction accuracy or real-world researcher error rate. Equivalent guards may be implemented in other frameworks.

\subsection{Step 4: workload, timing scope and robustness}
The native runner workload has Markov and one-spin exact-bath models, detunings $[0,123,500]$ Hz, two replicates and six ages $[0,10^{-4},5\times10^{-4},10^{-3},2\times10^{-3},5\times10^{-3}]$ s. Replicates have distinct deterministic seed streams; they are not independent hardware measurements or stochastic bath realizations in this deterministic workload. The Cartesian count is $2\times3\times2=12$ jobs per study. Master seed is 20261010. Three repeats independently randomize worker order among 1, 2 and 4. Worker count is excluded from physics identity, allowing a direct consistency check across scheduling choices.

Each cold study runs in a separate output directory and an isolated measurement process. OMP, MKL, OpenBLAS and NumExpr thread limits are one in those benchmark subprocesses. Per-job timeout is 60 s, driver timeout 600 s and max-run budget 24. The measured interval includes process startup, actual channel construction and artifact IO. The warm interval reuses terminal-result checkpoints; it is not electronic-structure memoization. Nine cold studies complete 108 jobs, and nine warm passes reuse 108 results. The scientific digest, excluding durations and output paths but including configuration identities and channel data, is identical across all nine studies.
\input{evaluation/paper/performance.tex}

The reported bounds are observed ranges from three repeats, not confidence intervals. Separate resource measurements use process usage counters: parent maximum RSS is 34.578125--37.078125 MiB and the largest terminated child's maximum is 63.238281--66.414063 MiB. The metric is not peak total memory across concurrent workers. Child CPU seconds and each measurement's raw counters remain in the retained summary. Performance applies to this Linux environment and small supplied models, not general CCE, electronic structure, all elements or cluster-scale workloads.

Three additional robustness probes are distinct from the 108 cold jobs. A profile without write temperature produces \code{missing\_data}. A real worker process with a $10^{-6}$ s timeout produces \code{timeout}; this deadline intentionally tests termination and is not a solve-time estimate. A precompleted valid job followed by the full study completes all 12 jobs with exactly one checkpoint reused. Thus robustness adds one missing-data worker, one timeout worker and 12 successful calculations across the partial/restarted study. No forced-kill during an atomic write, power-loss, corruption or concurrent cache-writer experiment was performed. Failed terminal checkpoints are preserved as failures, not retried or counted as successful physics results.

\subsection{Core fresh-checkout CI and traceable work units}
GitHub Actions run 38051481969 at commit \code{de52b32f0c34a05cf4f6a0c01bca6ee087e6cb67} uses Ubuntu 24.04 and Python 3.12.15. It installs the core editable package with NumPy 2.5.3 and SciPy 1.18.1, passes seven evaluation tests, automatically retrieves/checks both pinned experimental files, and reruns the matched comparison. Its maximum full-Choi discrepancy is $1.3214015\times10^{-14}$ versus the $10^{-8}$ gate. \code{evidence/core\_ci\_job.log} and \code{core\_ci\_verification.json} preserve the log and summary; the log hash is checked. This core CI result is additional environment evidence, not full optional-backend reproduction or colleague-led independent scientific review. CSV bytes are preserved and automatic Git line-ending conversion is disabled to protect source hashes.

At that historical system-evaluation snapshot, the original 75 tests plus seven additional evaluation tests constituted 82 distinct local passing tests. Repeating controls, CI tests, numerical ages or Monte Carlo trials does not increase that count. Work units remain separate: 73 channel-age comparisons, 90 processed data values, 41 synthetic coherence ages, 10,000 provider-neutral network trials, seven selected invalid contracts with seven positive controls, 108 cold worker jobs and 108 checkpoint reuses. No new hardware experiment or ML training run is counted. Steps 5 and 6 remain the author's and colleagues' full independent reproduction and scientific/release review tasks.

\section{Historical reproduction and claim traceability}
The source archive used for this study has SHA-256
\par\noindent\begin{minipage}{\linewidth}\centering\small\texttt{c64b94a573def9d999b65be7201947e9c}\\\texttt{2ce4e496aaf201650d7c1e3d44733aa}.\end{minipage}\par
The code and article are now public at \url{https://github.com/VesterlundCoder/memory-discover-lab}. The core CI release commit is recorded above; the original private source-archive hash remains a separate provenance identifier. No software DOI or peer-review acceptance is asserted.
The repository root contains the manuscript, figures, tables, evidence, scripts and evaluated source in \code{lab/}. \code{REPRODUCIBILITY.md} supplies constrained Python 3.12 setup and LaTeX requirements. The current public clone uses default offline licensed numerical replay with \path{scripts/reproduce.py}; \code{--online} explicitly selects wider source acquisition. Section~\ref{sec:repair} defines the excluded molecular acquisition and unbundled paper-byte checks. Fresh replay outputs go into a separate directory and do not replace archived article evidence.

\code{scripts/verify\_results.py} checks the reanalysis values, count controls, model statuses and simulated counts, and emits a claim-to-result JSON map. These checks protect the reporting pipeline; they are not extra experimental measurements. Every headline claim links to an executed result or log; the later manuscript update has a separate generated claim map described below. Detailed fit outputs retain status, seed, bootstrap success, conditions and limitations. Files predating this article remain under \code{lab/} as historical source outputs and are not all fresh experimental validations. The \code{evidence/} directory is the article's selected result snapshot.

The system-paper tables and claim map are regenerated with \code{python} \path{scripts/document_system_evaluation.py}; the numerical result files are left intact. The complete manuscript can be built using \code{make pdf}. Numerical reproduction does not require LaTeX; PDF compilation does not require running the simulator. Figures require Matplotlib. No ML libraries are needed. The original archived software test logs record Python 3.12.14, NumPy 2.5.3, SciPy 1.18.1, QuTiP 5.3.1, PySCF 2.14.0, PyCCE 1.1.1 and SeQUeNCe 1.2.0. Optional-adapter test execution does not replace application-specific physical validation.

The four evaluation commands use fresh \code{--out} directories: \code{python scripts/evaluate\_system.py step1}, \code{step3} and \code{step4}, plus \code{step2 --config evaluation/data/software\_control/case.json --allow-hypothetical}. The pending physical descriptor is the default for \code{step2} and returns exit two. Full commands and source contracts are in \code{evaluation/README.md}; manuscript-ready evaluation prose is under \code{evaluation/paper/}.

Future candidate evaluation should retain these distinctions: independently review units, definitions and conditions; anchor Hamiltonian and noise parameters; establish numerical convergence; reproduce time-resolved optical fidelity, success and noise; and assess any proposed improvement under matched operating conditions. The present study supplies the workflow and controls for such work without claiming those future outcomes.

```


## Former S10

```latex
\section{Historical clean-clone reproduction repair}
\label{sec:repair}
The review of commit \code{de52b32} identified clean-clone acquisition, test and figure-generation failures. The later documentation commit retained confirmations, but the executable repair is version 0.6.1. It changes source acquisition, test fixtures and reporting/reproduction interfaces without changing the microscopic equations. Historical source identities and results are retained separately. Current outputs are in \path{evaluation/results/repaired/}; the repair manifest, execution/test logs, four comparison reports and paper replay claim map are under \path{evidence/repair/}.

\subsection{Inputs, execution mode and scientific scope}
The tracked bundle contains ten Teller CSV files and seven PR2026 OUT/NPZ files. Their unchanged bytes are verified against SHA256, and Teller replay additionally checks the original reviewed MD5 locks. The two data records declare CC BY 4.0; creator names, DOI, URLs, fixed revisions and license links are retained in \path{data/experimental/ATTRIBUTION.md} and \path{manifest.json}. Unused \code{3a.csv}, primary-paper PDFs and the unlicensed molecular raw collection are not bundled.

The default \path{scripts/reproduce.py} uses these licensed numerical inputs and retained reviewed paper transcriptions. It writes a fresh tree, refuses a nonempty output directory and verifies required dependencies/data before execution. It reexecutes the Teller consistency, holdout, readout-window, channel, QuTiP and four SeQUeNCe analyses; PR curve fits; reference-table, exact-bath and count controls; and the hypothetical network workload. It then regenerates figures/tables and runs ten reporting checks. Archived article evidence is not replaced. Records explicitly distinguish verified measurement bytes from unbundled reviewed paper references.

Offline replay does not reacquire the 201-entry molecular source collection or reverify unbundled paper bytes. Its freshly acquired molecular-observation count is zero, and its reporting mode checks that exclusion. The historical count remains attributed to the original archive. \code{--online} explicitly selects the wider original acquisition adapters and requires the external endpoints. That path was not rerun in the denied-network repair validation; denied endpoints and changed bytes remain failures.

\subsection{Clean clone and installed environments}
An author-operated local candidate Git repository was cloned into an empty tree, with no ignored source cache, processed-data tree, molecular source-lock file or preceding synthetic-demo output. Isolated core and full virtual environments were installed on Linux/Python 3.12.14. After installation, a test-only Python socket/DNS shim denied external destinations and allowed loopback for local HTTP download tests. This verifies absence of external retrieval during the tested commands; it is not a general security sandbox. Complete installed dependency constraints cover 14 core and 131 full distributions, with the editable project installed separately. CI and Docker use the constraints, and the recommended runtime is Python 3.12. Other Python/platform combinations are not claimed tested.

The database test now supplies temporary synthetic provisional rows, while the synthetic count fixture is a tracked owned input. Optional QuTiP/SeQUeNCe checks have availability skips. The core environment runs 75 lab tests: 68 pass and seven are skipped; all 18 evaluation/regression tests pass. The isolated full environment passes 75 plus 18 tests with no skips. The eleven added regressions cover offline inputs, corruption, validation before writes, preservation of figures on missing input, metadata exclusion, changed scientific output, nested channel changes and strict source mismatch, plus three Kraus-map consistency controls described below. A skipped test is not a passing solver validation.

\subsection{Historical execution identity and numerical comparisons}
Two complete system passes share evaluation-source SHA256
\par\noindent\begin{minipage}{\linewidth}\centering\small\texttt{254b1bbb8a1d3c95d28b63e69d40c3a7}\\\texttt{afcbc2aa76b4b14a2bf8a727c9ead1e9}.\end{minipage}\par
Their lab-source SHA256 is
\par\noindent\begin{minipage}{\linewidth}\centering\small\texttt{99b0ef35caf1791653ce2b9c029514b21e}\\\texttt{9340ed58198194e291bccc4095e62f}.\end{minipage}\par
These content fingerprints identify the archived repair revision. Later lab/evaluation extensions have their own source fingerprints; they are not expected to equal these historical identities. The candidate local Git identity, UTC times, full configuration and installed environment remain in original outputs; they are not relabeled as a remote release.

Each pass performs 73 channel-age comparisons and 90 processed fidelity comparisons. The full-Choi discrepancy remains $1.3103013\times10^{-14}$. The 41-point synthetic step-2 control and hypothetical network gate pass, with physical validation false. Seven faults are rejected and all seven valid positive controls pass. Each local benchmark pass completes 108 cold jobs and 108 terminal-checkpoint reuses, giving 216 of each over the two passes; robustness probes are counted separately. The physical descriptor returns exit 2 with \code{blocked\_missing\_reviewed\_data} in both passes. The paper replay gives 87 retrieved pairs in 400,000 Teller attempts, six mismatching and two inconclusive PR fits, and 321 retrieved pairs in the separate 2000-trial hypothetical SeQUeNCe case.

\path{scripts/verify_evaluation.py} compares scientific fields, configuration, input hashes and seeds at $10^{-10}$ absolute and relative tolerance. Step 4 requires \code{scientific\_results.json}, containing the complete channel/configuration payload with execution-derived IDs and environment removed. Source fingerprints are separately reported and optionally required to match. Timestamps, paths, timing, RSS/CPU and diagnostic path strings are excluded from numerical equality. Changed metrics/channels are rejected. Legacy step-4 summaries with source-dependent digests alone are insufficient for portable cross-version channel comparison. All four strict source/scientific comparisons pass. Runtime records remain evidence of execution, not portable physical predictions; repair wall times do not establish a performance improvement, and other author-validation tasks could be active.

The first remote repair CI run (38058979906) passed the full offline paper replay and core test suites, but rejected individual Kraus entries in the step-2 comparison. Across runners their imaginary entries differed by about $1.16\times10^{-8}$ although the maps were equivalent. Since Kraus decompositions are nonunique, equality now uses $J=\sum_k\mathrm{vec}(K_k)\mathrm{vec}(K_k)^\dagger$, reconstructed separately for the full and conditional maps, at the unchanged $10^{-10}$ tolerance. The stored full Choi matrix is also checked for consistency. Basis, vectorization, physical configuration and metrics remain compared. Three additional regressions accept phase/unitary changes of Kraus representation and reject a changed conditional map or operators inconsistent with the stored Choi matrix. The negative CI result and former source identity are archived rather than omitted.

\subsection{Figures, optional imports and unexecuted scope}
The figure builder validates/loads inputs before writing and stages plots before replacement. Missing-input regression returns exit 2 and preserves an existing architecture figure. PDF creation/modification timestamps are removed; two figure-only runs in the constrained environment are byte identical for all five PDFs and five PNGs. No equivalence across untested plotting/font versions is assumed. Delivered byte checksums are regenerated separately from numerical equality.

In a fresh process, direct PyCCE 1.1.1 import fails at the removed SciPy \code{isintlike} location. The adapter restores the same SciPy utility and NumPy Unicode dtype alias before import; adapter import and the independent one-spin analytical test pass. This compatibility route is documented. The pinned Dockerfile is updated but Docker was unavailable, so no image-build result is claimed. TeX sources were compiled and PDFs visually inspected separately. Author-operated clean clones/CI do not complete colleagues' independent reproduction or scientific/release review, and no improved material lifetime is established.


```


## Former S15

```latex
\section{Historical extension replay and claim mapping}
The extension's actual source base is git commit \code{985c8fe}; the source changes were uncommitted when the selected computations ran. Their content identities, rather than that base alone, identify the executed implementation: lab hash
\par\noindent\begin{minipage}{\linewidth}\centering\small\texttt{3852565376c2a529bb33bc9394cf96061}\\\texttt{eeee147e19b4f4bbc2da724cf224f5a},\end{minipage}\par
and evaluation hash
\par\noindent\begin{minipage}{\linewidth}\centering\small\texttt{ecc4ea6d77ca774a7f9cd3ed6f91285a5}\\\texttt{d5632a041ecdaa79ff829a5464cc373}.\end{minipage}\par
The published result commit is \href{https://github.com/VesterlundCoder/memory-discover-lab/commit/935817372520428e88398235ad58ee3d9817e2ba}{\code{9358173}}. Manuscript/plotting scripts are outside the lab/evaluation fingerprints; at that revision the reporting generator checked the corresponding source content identities. Historical Bradley, repair and original-paper executions retain their own fingerprints and are not relabeled as executions at the new commit.

The extension environment is Linux/Python 3.12.14, NumPy 2.3.5, SciPy 1.16.3, Matplotlib 3.10.8, PyCCE 1.1.1, SeQUeNCe 1.2.0, QuNetSim 0.1.2, QuTiP 5.3.1 and QuTiP-QIP 0.4.2. Its 126-distribution snapshot is \path{evaluation/config/validation_extension/requirements-tested.txt}. Install it in a separate Python 3.12 environment from older snapshots. PyCCE compatibility uses the retained SciPy utility and NumPy Unicode alias documented in Section~\ref{sec:repair}; installed dependency source is not patched.

After installation, use a fresh output directory:
\begin{quote}\small
\code{export OMP\_NUM\_THREADS=1 OPENBLAS\_NUM\_THREADS=1 MKL\_NUM\_THREADS=1}\\
\code{export WQ\_BLOCK\_EXTERNAL\_NETWORK=1}\\
\code{export PYTHONPATH="\$PWD/scripts/network\_guard:\$PWD/lab"}\\
\code{python scripts/run\_validation\_extension.py --count}\\
\code{python scripts/run\_validation\_extension.py --out reproductions/my-extension}\\
\code{python scripts/verify\_validation\_extension.py}\\
\code{--reference evaluation/results/validation\_extension/selected}\\
\code{--actual reproductions/my-extension}
\end{quote}
The last three lines form one command. \code{--resume} requires matching configuration and code fingerprints. Every native run JSON and RNG array is retained in the two \code{raw\_runs\_and\_traces.zip} files; their uncompressed duplicates are ignored by git. A fresh offline replay checked \ReplayRecords{} JSON records and \ReplayArrays{} exact RNG arrays, with equal scientific contents at absolute/relative tolerance $10^{-10}$. Runtime, timestamps/platform provenance and ZIP-container bytes are excluded, but per-archive integrity and each archived scientific record are checked.

The historical extension environment ran 34 evaluation tests plus 75 lab tests: 107 passed and two optional PySCF/MaxwellBloch tests were skipped. Eleven extension tests cover noise/efficiency distinctions, false-positive limits, double counting, independent noncommuting propagation, certificate identity/time limits, explicit PyCCE pairs/Zeeman conventions, independent RNG streams and joint-state preservation/consumption in the custom backend. Historical full optional tests are a separate snapshot. That historical system regression explicitly permits changed source hashes while comparing all four full scientific payloads; its strict pending physical case remains blocked. All replay/test checks are author-operated and not independent scientific review.

\path{scripts/document_article_update.py} validates retained numerical values, status limitations, raw-data/result/archive hashes, source fingerprints, run counts and test logs, then generates two LaTeX tables, number macros and \path{evidence/article_update_claim_map.json}. The original ten-claim and system-evaluation maps remain historical. Extension figures are generated in English by \code{scripts/plot\_validation\_extension.py --language en} and \path{scripts/plot_article_bradley.py}; earlier Swedish figures remain unchanged. \code{make pdf} builds the article and this Supplement from included assets. TeX compilation and complete rendered-page inspection are recorded separately in the corresponding manuscript-release evidence. These checks establish a complete report of the executed study; no new experimental data, independent material review or journal acceptance is implied.

```


## Former S16

```latex
\section{Historical evaluation and provenance migration}
\label{sec:systemeval}
These additional evaluations address a matched computational reference, a second-family case pathway, controlled contract ablations and local execution performance. All four pathways were exercised, but the physical objective of step 2 was not completed: its executed molecular-spin case is synthetic. the historical comparison table below and the Supplement distinguish mathematical/software verification from experimental evidence. Configuration and source hashes, actual seeds and failure statuses are retained in a separate system-evaluation claim map. The four selected records share one evaluation-source fingerprint; confirmations of steps 2 and 3 use the published evaluation implementation. No machine-learning training or new hardware experiment is included.

\subsection{Step 1: matched direct-script comparison}
A separately written reference imports NumPy/SciPy without importing the lab's channel-construction routines. It builds the column-vectorized Lindblad generator and evaluates its matrix exponential, then independently forms the conditional qubit map and the erasure-inclusive qubit-to-qutrit Choi matrix. Both arms receive identical input conditions and conventions. Six Pauli eigenstates, full Choi matrices, conditional average fidelity and state-independent acceptance are compared with tolerance $10^{-8}$. Both source parsers check the same raw SHA-256 hashes; the direct arm is not deprived of source-integrity checks.

The workload has the calibrated Teller operating point and twelve hypothetical Markov profiles: four joint choices of population rate, detuning and equilibrium population, each at three storage temperatures and six ages. These are 73 channel-age points, not 73 independent experiments. Two independent parsers also reproduce the same 90 released processed fidelities, with zero discrepancy. Maximum full-Choi, six-state output and average-fidelity errors are $1.3103\times10^{-14}$, $1.1828\times10^{-14}$ and $3.9968\times10^{-15}$, respectively; acceptance agrees exactly.
\input{supplement/historical_comparison.tex}

Five randomized-order warm construction repeats per arm, with seed 20261010, give medians 0.054380 s for the lab and 0.099634 s for the direct implementation. These timings do not equalize metadata, export, validation or metric-construction work and exclude source retrieval, file IO, fitting and network events. They are descriptive local measurements, not evidence of end-to-end speed superiority or saved researcher effort. AiiDA already provides provenance and caching~\href{https://doi.org/10.1038/s41597-020-00638-4}{Huber et al. (2020)}; it was assessed through documentation, not run as a comparator. Equivalent domain contracts could be implemented in custom scripts or workflow-engine plugins. The matched result verifies numerical preservation across the supplied integration boundary, rather than establishing superiority over existing frameworks.

\subsection{Step 2: second-family pathway and its unresolved physical baseline}
The case runner accepts a hashed complex pure-dephasing curve, a separately supplied spin Hamiltonian and reviewed temperature, field/frame, isotope/composition and pulse conditions. It compares a fixed model with the curve without fitting parameters. A total echo envelope cannot be silently relabeled as pure dephasing; optical write/read review is a separate requirement. Missing optical information permits a coherence comparison but blocks network export. An unsuccessful curve gate also blocks export. Hypothetical inputs require explicit network opt-in and retain hypothetical evidence.

The executed control uses one supplied $^{13}$C spin at 4.2 K, longitudinal hyperfine $A_{zz}=4000$ Hz, nuclear Zeeman frequency $\nu_z=214163.9829$ Hz and no pulses. The 41 ages span 0--1 ms. Its independent closed-form curve is
\begin{equation}
L_{\rm ref}(t)=\cos(\pi A_{zz}t)-iP\sin(\pi A_{zz}t),\qquad
P=-\tanh\!\left(\frac{h\nu_z}{2k_BT}\right).
\end{equation}
The declared complex-residual scale is 0.01 and the gate is $\max_t|L_{\rm model}-L_{\rm ref}|/0.01\leq3$. This scale is chosen for a software control, not a measured SEM. The maximum scaled residual is $3.72\times10^{-12}$. Revivals occur; a first sampled $1/e$ crossing is bracketed by 75--100 $\mu$s on this coarser grid. Neither this bracket nor the residual is a statistical $T_2$ prediction error.

With explicitly hypothetical optical parameters, the provider-neutral two-node workload uses 10,000 attempts, herald probability 0.1, age 500 $\mu$s and seed 20261010. It gives 1020 heralds, 313 retrieved pairs and conditional Bell fidelity 0.9559176317. This is the lab's channel benchmark, not another SeQUeNCe or NetSquid run. A molecular reference~\href{https://doi.org/10.1039/C8SC04122A}{Lin et al. (2019)} is retained as a prospective physical case, but its missing reviewed curve and Hamiltonian produce a blocked status. Consequently, this original step-2 control establishes software-path consistency only. The subsequent distinct-family observable comparison in the Bradley observable case in the main article uses measured data with calibrated effective dynamics, retains a failed $X$ diagnostic and does not complete the strict physical-model baseline.

\subsection{Step 3: constructed contract ablations}
Seven selected invalid inputs test age and temperature extrapolation of a measured point, reuse of a total coherence rate as pure dephasing, unreviewed noise independence, hypothetical network use without opt-in, incremental use of an absolute-age map, and modified source bytes. Six protections belong to the existing lab; the source-hash contract in this suite belongs to the evaluation layer. Each has a passing positive control and an isolated deliberately unsafe bypass; no production guard is modified. All seven invalid cases are rejected and all bypasses accept the constructed cases.

The consequences have distinct units. Reusing a total coherence rate of 25 s$^{-1}$ as pure dephasing while also adding $\Gamma_1/2=5$ s$^{-1}$ changes the specified 40 ms to 33.333 ms, a 16.667\% conditional error. Applying a complete age map twice gives maximum density-element error 0.097247 in the chosen control. Omitting the ms-to-s conversion produces maximum density-element discrepancy 0.132201 in an additional unit control. Other rows count unsupported conditions or evidence promotion, rather than physical prediction errors. The Supplement reports each case separately. This selected fault coverage does not estimate researcher error incidence or establish that another framework cannot implement equivalent guards.

\subsection{Step 4: local performance, checkpoint reuse and robustness}
The native study runner evaluates two supplied models (Markov and finite bath), three detunings and two replicates on six ages, giving 12 jobs per cold study. Worker counts 1, 2 and 4 are ordered randomly for each of three repeats using seed 20261010. Each cold study has a separate output directory; a subsequent warm pass reuses its terminal-result checkpoints. Native numerical threads are limited to one per worker. Nine cold studies complete 108 jobs; nine warm passes reuse 108 checkpoints. Configuration identities and serialized channel results match across all worker counts and repeats.
\input{supplement/historical_performance.tex}

Cold medians decrease from 3.8674 s at one worker to 1.9781 s at two and 1.1782 s at four. These bounded local results include process startup, calculation and artifact IO, and do not establish cluster-scale or cross-machine scalability. Parent peak RSS is 34.578--37.078 MiB, and the largest terminated child's peak is 63.238--66.414 MiB; these maxima are separate measurements, not aggregate concurrent memory. Missing-parameter and real process-timeout probes yield failure statuses \code{missing\_data} and \code{timeout}. Restart after one normally completed checkpoint completes the study with exactly one resumed result. No forced-crash, power-loss or filesystem-corruption test was performed.

A fresh GitHub Actions checkout at the recorded release commit installs the core package, passes seven evaluation tests and retrieves the two pinned experimental files automatically before rerunning step 1. Its maximum full-Choi discrepancy is $1.3214\times10^{-14}$, also below the same gate. This checks the core clone/install/retrieval path; it does not replace full optional-backend reproduction or colleague-led physical and scientific review.

\subsection{Historical clean-clone repair and numerical replay}
A subsequent v0.6.1 repair addressed reproducibility failures in a fresh public clone. Seventeen unchanged, licensed measurement files are bundled with attribution and content hashes. The default paper replay recomputes the numerical analyses and network controls offline into a separate result tree, while retaining reviewed paper transcriptions as inputs. It excludes reacquisition of the molecular collection and reverification of unbundled primary-paper bytes. The historical 201-entry source audit is therefore not a fresh offline result.

An author-operated clean clone with isolated Python 3.12 core/full environments was tested with external DNS and sockets denied after installation. The core suite passes 68 lab and 18 evaluation tests with seven optional skips; the full environment passes all 93 tests. Two system passes each execute 108 cold jobs and 108 checkpoint reuses. All four full scientific-payload comparisons pass at absolute/relative tolerance $10^{-10}$. Ten reporting checks pass; five PDF/PNG figure pairs regenerate identically. The strict physical second-family descriptor remains blocked. These are reproduction controls, not a new performance comparison or independent scientific review. The Supplement and repair dossier retain methods, source identities and all twelve reviewed findings.

\subsection{Earlier source and environment identities}
The public repository includes source, configurations, licensed measurement inputs, results, figure/table scripts, claim mappings and this Supplement. External datasets retain their own DOIs~\href{https://doi.org/10.5281/zenodo.14929997}{Teller dataset}, \href{https://doi.org/10.5281/zenodo.21532904}{Pr dataset}, \href{https://doi.org/10.4121/16887658.v3}{Bradley dataset} and license notices. Unlicensed third-party caches remain excluded from Git. The original snapshot was reproduced from the software archive with SHA-256
\par\noindent\begin{minipage}{\linewidth}\centering\small
\texttt{c64b94a573def9d999b65be7201947e9c}\\
\texttt{2ce4e496aaf201650d7c1e3d44733aa}
\end{minipage}\par
Bradley and the validation extension retain separate execution/source identities. Source and article materials are available at \url{https://github.com/VesterlundCoder/memory-discover-lab}. The historical core-CI record identifies commit \href{https://github.com/VesterlundCoder/memory-discover-lab/commit/de52b32f0c34a05cf4f6a0c01bca6ee087e6cb67}{\code{de52b32}}; each subsequent result identifies its own source/configuration fingerprints. No software DOI or peer-review acceptance is asserted.

The archived full environment uses NumPy 2.5.3, SciPy 1.18.1 and PySCF 2.14.0; the extension uses NumPy 2.3.5, SciPy 1.16.3 and QuNetSim 0.1.2, without PySCF/MaxwellBloch. Both record Python 3.12.14, PyCCE 1.1.1, QuTiP 5.3.1 and SeQUeNCe 1.2.0. Exact runtime pins are retained per revision. The extension ran with uncommitted source changes on base \code{985c8fe}; its actual lab/evaluation content hashes identify the executed implementation, subsequently published at \href{https://github.com/VesterlundCoder/memory-discover-lab/commit/935817372520428e88398235ad58ee3d9817e2ba}{\code{9358173}}. \path{scripts/document_article_update.py} checks its retained claims and generates number macros, two tables and \path{evidence/article_update_claim_map.json}. PDF compilation is separate from numerical replay. The Supplement supplies exact commands, seeds, compatibility details and evidence pointers. AI-assisted coding and drafting were used; scientific responsibility remains with the named author.

```


## Superseded original S17 provenance

```latex
\section{Unified software-release reproduction}
\label{sec:unifiedrelease}
The authoritative main-article result set is \path{evaluation/results/release_v070}. Every numerical stage was executed from a clean checkout of the annotated software tag \code{v0.7.0}, commit
\begin{quote}\small\code{a6cca59bf513e98273ab7f869abde8c0d0f778f2}\end{quote}
The tag and its original commit identity are preserved in \path{releases/v0.7.0/westquant-v0.7.0.bundle}, permitting an exact checkout independent of the repository mirror's commit metadata. The public release branch mirrors the same software tree. The tag is not moved after this completed replay. Earlier source identities, test counts and execution histories in this Supplement describe historical snapshots, not inputs to the current main-article results.

\subsection{One runtime and one replay command}
Python 3.12.14 uses the exact external distributions in \path{requirements-release-v070.txt}. Install the source package separately from the checked tag. The selected numerical environment includes NumPy 2.3.5, SciPy 1.16.3, PyCCE 1.1.1, QuTiP 5.3.1, SeQUeNCe 1.2.0, QuNetSim 0.1.2, PySCF 2.14.0 and MaxwellBloch 0.12.0. Optional backends are included in the same runtime; the combined 109-test suite passes with zero skips.
\begin{quote}\small
\begin{verbatim}
git clone westquant-v0.7.0.bundle /tmp/wq-release
cd /tmp/wq-release
git checkout v0.7.0
python -m venv /tmp/wq-env
/tmp/wq-env/bin/pip install -r requirements-release-v070.txt
/tmp/wq-env/bin/pip install --no-deps -e ./lab
/tmp/wq-env/bin/python scripts/reproduce_release.py \
  --tag v0.7.0 --out /tmp/wq-replay
\end{verbatim}
\end{quote}
The runner requires clean HEAD equal to the tag and a fresh output directory outside the checkout. It checks runtime pins, executes the combined tests once, recomputes licensed paper analyses, E1--E4, Bradley, joint protocol controls, bath refinements, pilot/larger native runs and the source-to-network example, then repeats the studies in a separate confirmation tree. Worker environments set external-DNS/socket denial, deterministic hashing and one numerical thread per process. Loopback permits local server tests. Source cleanliness and HEAD are checked again after execution.

\subsection{Confirmation and retained outputs}
The four system comparisons include complete serialized channel payloads and scientific tables. The Bradley negative Ramsey-$X$ result and the executable example reproduce. The extension comparison covers 359 JSON records and 11 exact random arrays, with absolute and relative tolerance $10^{-10}$. Choi matrices compare channels independently of their nonunique Kraus representations. Raw archives are hash-verified before their individual run records and random inputs are compared. ZIP-container bytes, timestamps and execution timings are excluded from scientific equality.

The manifest records the source commit, lab/evaluation/configuration hashes, runtime lock, test total and per-file result hashes. Uncompressed native-run/trace duplicates are omitted from the delivered tree because the checked archives retain the identical records. Cache duplicates and SQLite working databases are omitted; licensed inputs and observation exports remain available. The release is an author-operated reproduction on one machine, without independent scientific review, a new hardware experiment or a new parameter-study design.

\subsection{Current execution metadata}
The E4 study performs 108 cold jobs and 108 checkpoint reuses over one, two and four workers, with complete scientific payload agreement. Its fresh performance table and robustness records are retained under \path{canonical/system/step4}. Table~\ref{tab:releaseperformance} reports the fresh descriptive timings. Earlier timing values in the historical section are not current benchmarks.
\input{supplement/current_performance.tex} The current reported runtime and memory metadata are descriptive measurements on one machine and do not establish cross-machine or cluster scaling. The smaller synthetic controls include 202 bath-time evaluations and four rate-box corners; these are solver work counts, not independent experimental samples.

\subsection{Article compilation and supplementary-file structure}
Additional file 1 is this PDF and its editable LaTeX source. The article source package includes figure PDFs, tables, section files, licenses, provenance and this supplement. Run \code{make pdf} to compile both documents without rerunning numerical studies. \path{scripts/document_release.py} regenerates the main-article numbers and tables from the unified result set. Earlier reporting scripts remain with their historical snapshots. The build and rendered-page inspection are recorded separately from computational replay.

```


## Superseded original execution timings

```latex
\begin{table}[tbp]\caption{Unified-release descriptive execution times.}\centering\small\begin{tabular}{rrrr}\toprule Workers & Cold median (s) & Observed range (s) & Resume median (s)\\\midrule
1 & 4.3278 & 4.1071--4.4937 & 0.03482\\
2 & 3.0029 & 2.4436--3.7751 & 0.02286\\
4 & 1.4221 & 1.4026--2.0297 & 0.06059\\
\bottomrule\end{tabular}\label{tab:releaseperformance}\end{table}
```


## Original replay identity

```latex
The supplied S17 reported a6cca59... and Python 3.12.14. The revised article instead reports the newly executed, separately verified 2c6bb71... replay on Python 3.12.15; no original tag has been moved.
```
