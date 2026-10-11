# WestQuant 0.7.0: unified scientific software release

This tag freezes the computational source and existing study designs used by the
EPJ Quantum Technology system-manuscript revision. It introduces no new hardware
experiment or parameter study. Earlier manuscripts and results retained in this
checkout are historical; the revised manuscript and fresh release evidence are
distributed alongside this software archive.

## Clean reproduction

Use Python 3.12.14 and create an isolated environment. Install the exact external
runtime snapshot, then this checkout without dependency resolution:

```bash
git checkout v0.7.0
python -m venv /tmp/westquant-release-env
/tmp/westquant-release-env/bin/pip install -r requirements-release-v070.txt
/tmp/westquant-release-env/bin/pip install --no-deps -e ./lab
/tmp/westquant-release-env/bin/python scripts/reproduce_release.py \
  --tag v0.7.0 --out /tmp/westquant-release-replay
```

The output path must be fresh and outside the checkout. The runner requires a
clean tagged HEAD, validates runtime pins, runs the combined tests once, denies
external sockets/DNS in workers, executes all existing study stages and repeats
them in a fresh confirmation tree. It preserves the expected Bradley Ramsey-X
mismatch and the unresolved physical-case descriptor. The manifest records source
and configuration hashes, the tag commit, tests and complete replay comparisons.
One numerical thread is used per process. No runtime or metadata equality is
misrepresented as scientific equality.

The local installation of the source package is excluded from the external lock:
its identity is the checked tag and source hashes. The runtime includes optional
PySCF and MaxwellBloch adapters as well as both network simulator stacks.

## Minimal user workflow

```bash
python scripts/reproduce.py --skip-tests --out /tmp/westquant-paper
python scripts/example_source_to_network.py \
  --baseline /tmp/westquant-paper/lab/baselines/teller2025 \
  --out /tmp/westquant-network-example
```

The example uses the reviewed source-constrained 18 microsecond operating point.
It does not extrapolate a lifetime or infer single-photon performance from the
weak-coherent-probe experiment.
