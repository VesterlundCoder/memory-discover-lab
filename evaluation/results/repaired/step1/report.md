# Step 1: matched workflow comparison

## Executed results

Compared 13 profiles at 73 age points and 90 processed experimental fidelity values.
Maximum full-channel Choi discrepancy: 1.3103e-14; gate 1e-08.
Maximum six-state output discrepancy: 1.18278e-14.

| Dataset | Direct mean | WestQuant mean | Maximum discrepancy |
|---|---:|---:|---:|
| 4.csv | 0.9510824229 | 0.9510824229 | 0 |
| 8a.csv | 0.9140479475 | 0.9140479475 | 0 |

## Matched scope and interpretation

The baseline was written independently using NumPy/SciPy Liouvillian exponentiation; it does not import the lab's channel construction. Both arms receive identical reviewed conditions. The baseline also verifies raw source hashes, so it is not intentionally deprived of source integrity.
The direct script and framework agree within the stated numerical gate. This checks preservation of the specified equations across the integration boundary. It establishes neither new physics nor general superiority over custom scripts.
WestQuant contributes reusable condition/evidence contracts, channel export and orchestration. Those capabilities can also be implemented by custom scripts or domain-specific plugins in an existing workflow engine. The integration decision therefore rests on reusable domain semantics, not the assertion that provenance or caching is new.

## Local construction timing

Warm median: WestQuant 0.030606 s; direct script 0.051871 s. 5 randomized-order repeats per arm.
These timings do not equalize full export, metadata or validation work. They exclude data ingestion, output IO, network events and downstream solvers. They cannot establish an end-to-end speedup. Native thread settings and machine details are recorded in the run environment; cross-machine performance is not assessed.

## Related tools: documentary comparison

| Tool | Existing capability | WestQuant relationship | Execution in step 1 |
|---|---|---|---|
| NumPy/SciPy script baseline | Explicit data parsing and supplied Lindblad/channel equations | Independent executable baseline; equivalent reviewed input assumptions | Executed matched numerical comparison |
| QuTiP | Open-system evolution and channel representations | Underlying solver; memory evidence and device contracts supplied by integration code | Documentation audit in step 1; earlier article controls are separate |
| PyCCE | CCE/gCCE spin-bath dynamics and supplied couplings | Underlying spin solver; model convergence and material inputs remain application responsibilities | Documentation audit only in step 1 |
| PySCF | Electronic-structure calculations | Underlying electronic solver; electronic results do not by themselves identify a lifetime or optical instrument | Documentation/context only in step 1 |
| SeQUeNCe | Event-driven quantum-network components, protocols and applications | Downstream network engine; WestQuant exports a declared memory channel | Documentation audit in step 1; earlier article workload is separate |
| AiiDA | General provenance graphs, workflow orchestration and calculation caching | Potential host for WestQuant domain contracts; provenance and caching are not claimed as new | Documentation audit only; AiiDA was not run |

## Primary documentation

- NumPy/SciPy script baseline: https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.expm.html
- QuTiP: https://qutip.readthedocs.io/en/stable/guide/guide.html
- PyCCE: https://pycce.readthedocs.io/en/latest/tutorial.html
- PySCF: https://doi.org/10.1063/5.0006074
- SeQUeNCe: https://github.com/sequence-toolbox/SeQUeNCe
- AiiDA: https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/provenance/index.html

## Remaining evidence

No independent AiiDA run, researcher-effort study, all-elements benchmark, external reproducibility exercise or second-family physical validation is supplied by this comparison. The ablation and performance commands evaluate different questions and their output must be reported separately.

Reproduce from the repository root:

```bash
python scripts/evaluate_system.py step1 --out evaluation/results/step1-new
```
