# Open Questions for Continued Research — v0.7.1

This document formulates the five open questions identified in the v0.7.1 release.
Each question states what is known, what is unknown, what would be needed to address
it, and what the current codebase already provides as a foundation.

These are research directions, not implementation bugs. They do not block the v0.7.1
release or the correspondence with reviewers. They define the scope of future work.

---

## Q1: Convergence scaling — 1× → 10× → 100×

### What is known

The protocol test (`evaluation/config/validation_extension/protocol.json`) validates
the complete effective write/store/read instrument across 56 channel-age points and
336 state-probe comparisons. The maximum numerical error is 1.44×10⁻¹⁵, satisfying
the 10⁻¹⁰ tolerance.

The convergence study (`evaluation/config/validation_extension/convergence.json`)
checks five axes:
- Independent solver (expm vs spectral): max error 1.44×10⁻¹⁵
- Control resolution (8 → 128 substeps): max error 2.33×10⁻⁵ at 128 substeps
- Cluster order (1 → 4): converges
- Pair cutoff (5 → 40 Å): converges
- Bath size (2 → 8 spins): converges
- Time grid (33 → 257 points): converges

The current configuration uses a 4-spin exact bath with cluster orders 1–4 and bath
sizes 2–8. The convergence certificate (`memorylab/convergence_guard.py`) requires
all five axes to pass before a spin model can be labelled a material prediction.

### What is unknown

1. **Does 10× scaling resolve all undecided configurations?** The current convergence
   study uses a 4-spin bath. At 10× (40 spins), the exact diagonalisation may become
   intractable and CCE may need to take over. The transition point where exact bath
   gives way to CCE is not mapped.

2. **Is 100× needed?** For materials with dense spin environments (e.g. high-abundance
   ¹H hosts), a 100-spin bath may be required for convergence. The current code caps
   exact baths at 8 spins and delegates to PyCCE for larger baths. Whether PyCCE at
   cluster order 4 with a 100-spin bath converges to the same tolerance is unknown.

3. **What is the computational cost scaling?** Exact diagonalisation scales as O(N³)
   in bath size for the eigenvalue problem, but the coherence calculation requires
   tracing over the bath, which scales as O(2^N) in the worst case. CCE scales as
   O(N^k) where k is the cluster order. The crossover point is not characterised.

4. **Does convergence degrade at longer storage ages?** The current convergence study
   uses `max_age_s = 0.0004` (0.4 ms). At longer ages, revivals may appear and the
   cluster expansion may need higher orders to capture them.

### What would be needed

- A scaling study that runs the convergence study at 1×, 10×, and 100× bath sizes
  with both exact and CCE methods, recording:
  - Maximum coherence error at each scale
  - Wall-clock time at each scale
  - The crossover point where CCE becomes more efficient than exact
  - Whether the 10⁻¹⁰ tolerance is met at each scale
- Extension of the convergence certificate to record the scale factor and the
  method used at each scale
- A decision rule for when to switch from exact to CCE based on bath size and
  available compute

### What the codebase already provides

- `memorylab/convergence_guard.py` — the certificate structure and validation logic
- `memorylab/spin.py` — exact coherence calculation with CPMG support
- `memorylab/backends.py` — PyCCE adapter for cluster expansion
- `evaluation/config/validation_extension/convergence.json` — the current study config
- `evaluation/results/validation_extension/selected/convergence/` — current results

### Proposed experiment

```python
# Conceptual scaling study (not yet implemented)
scales = [1, 10, 100]  # bath size multiplier
methods = ["exact", "pycce"]
for scale in scales:
    for method in methods:
        bath_size = 4 * scale
        if method == "exact" and bath_size > 20:
            continue  # exact is intractable beyond ~20 spins
        # Run convergence study at this scale and method
        # Record: max_error, wall_time, converged_axes
```

---

## Q2: Retrieval dominance — structural or schedulable?

### What is known

The retrieval success probability in the current model is:

```
P_retrieval = η_write · η_read · exp(-Γ_erasure · (t_write + t_read + t_storage))
```

This multiplies directly into the delivery probability. In the two-node benchmark,
the expected success probability per attempt is:

```
P_delivery = P_herald · P_retrieval_left · P_retrieval_right
```

For the defect-spin profile (η_write=0.8, η_read=0.7, erasure rate=12 s⁻¹):
- At age 0: P_retrieval ≈ 0.56
- At age 0.03 s: P_retrieval ≈ 0.42

This means retrieval efficiency is a dominant factor in delivery probability,
especially at short storage ages where decoherence is negligible.

The protocol instrument (`memorylab/protocol.py`) adds false-positive detections
on top of this, but does not change the retrieval probability itself.

### What is unknown

1. **Is retrieval efficiency a structural constant or can scheduling mitigate it?**
   In the current model, η_write and η_read are fixed parameters. In a real system,
   retrieval efficiency may depend on:
   - The storage age (younger memories may retrieve more efficiently)
   - The number of prior readout attempts (readout-induced decoherence)
   - The input state (state-dependent readout)
   - The scheduling of write and read pulses (temporal-mode matching)

2. **Can multiplexing improve effective retrieval?** If multiple memory slots are
   available, a scheduler could choose the slot with the highest expected retrieval
   efficiency. The current benchmark uses a single slot per node. A multi-slot
   benchmark would test whether slot selection can compensate for low per-slot
   efficiency.

3. **Is the erasure model too pessimistic?** The current model treats erasure as
   a constant-rate Poisson process. In practice, erasure may be age-dependent
   (e.g. due to spectral diffusion) or attempt-dependent (e.g. due to detector
   dead time). A more detailed erasure model could change the retrieval dominance
   picture.

4. **Does the order of operations matter?** The current model applies the complete
   write-store-read channel as a single CPTP map. If the write and read channels
   are applied separately (with the storage channel in between), the composition
   order could affect the result. The current code composes as read ∘ storage ∘ write,
   which is the physical order. Whether a different scheduling (e.g. read before
   write in a quantum repeater protocol) changes the dominance is unknown.

### What would be needed

- An age-dependent retrieval efficiency model where η_read = η_read(age, n_attempts)
- A multi-slot memory model with slot selection
- A scheduling policy that chooses the optimal slot and readout time
- A benchmark comparing single-slot vs multi-slot delivery probability
- Analysis of whether the retrieval dominance persists under optimal scheduling

### What the codebase already provides

- `memorylab/models.py` — the channel composition and retrieval probability formula
- `memorylab/network.py` — `MemoryDevice.retrieve()` with age-specific channels
- `memorylab/protocol.py` — the readout instrument with false positives
- `memorylab/sequence_adapter.py` — the two-node benchmark with single slot per node
- `memorylab/qunetsim_adapter.py` — the QuNetSim transport with single slot

### Proposed experiment

```python
# Conceptual multi-slot study (not yet implemented)
n_slots = [1, 2, 4, 8]
for n in n_slots:
    # Each slot has an independent age drawn from a uniform distribution
    # The scheduler picks the slot with the highest expected fidelity
    # Compare:
    #   - Single-slot delivery probability (baseline)
    #   - Multi-slot with random selection
    #   - Multi-slot with optimal selection (pick best age)
    #   - Multi-slot with threshold-based selection (pick first above fidelity gate)
```

---

## Q3: NetSquid and QuISP adapters — scope and feasibility

### What is known

The current release includes two network-simulator adapters:
- `memorylab/sequence_adapter.py` — SeQUeNCe 1.2.0
- `memorylab/qunetsim_adapter.py` — QuNetSim 0.1.2 with custom QuTiP backend

Both adapters use the same contract:
- Apply the WestQuant channel once at retrieval time
- Use the simulator's native event kernel for timing
- Feed both simulators the same pre-generated random trace
- Report density-matrix error against the analytic expected output

The benchmark shows both simulators agree to 2.465×10⁻¹⁵ (max mean density error),
satisfying the 10⁻¹⁰ tolerance.

### What is unknown

1. **NetSquid adapter feasibility.** NetSquid is a discrete-event quantum network
   simulator with a proprietary licence (free for academic use). Its API differs
   from SeQUeNCe and QuNetSim:
   - NetSquid uses a component-based architecture with connection models
   - NetSquid has its own quantum state formalism (Stabilizer or DM)
   - NetSquid's noise models are built-in and would need to be disabled to avoid
     double-counting with WestQuant's channel

   The adapter would need to:
   - Create a NetSquid quantum memory component that holds the density matrix
   - Apply the WestQuant channel at retrieval time
   - Disable NetSquid's built-in decoherence
   - Use NetSquid's event scheduler for timing

2. **QuISP adapter feasibility.** QuISP is a quantum network simulator built on
   OMNeT++ with a focus on protocol-level simulation. Its state representation is
   stabilizer-based, which may not support general density matrices. The adapter
   would need to:
   - Check whether QuISP can represent the erasure channel (3-outcome measurement)
   - Determine whether QuISP's stabilizer formalism is compatible with the
     WestQuant channel's Kraus operators
   - If not, use QuISP's density-matrix mode (if available) or limit the adapter
     to stabilizer-preserving channels

3. **Licence compatibility.** NetSquid's licence may restrict redistribution of
   adapter code that imports NetSquid. The adapter would need to be an optional
   extra with a clear licence notice.

4. **Cross-simulator equivalence.** Adding NetSquid and QuISP would extend the
   benchmark from 2 to 4 simulators. The key question is whether all 4 agree
   on the same channel application given the same trace. If they don't, the
   discrepancy would reveal simulator-specific assumptions.

### What would be needed

- A NetSquid adapter (`memorylab/netsquid_adapter.py`) that:
  - Creates a passive memory component
  - Applies the WestQuant channel at retrieval
  - Disables built-in noise
  - Reports density-matrix error
- A QuISP adapter (`memorylab/quisp_adapter.py`) that:
  - Checks formalism compatibility
  - Uses density-matrix mode if available
  - Falls back to stabilizer-only channels if not
- Extended benchmark configs with 4 simulators
- A `netsquid` and `quisp` optional extra in `pyproject.toml`
- Licence review for both simulators

### What the codebase already provides

- `memorylab/sequence_adapter.py` — the adapter contract and SeQUeNCe implementation
- `memorylab/qunetsim_adapter.py` — the QuNetSim implementation with custom backend
- `evaluation/config/validation_extension/crosssim_larger.json` — the benchmark config
- `docs/SEQUENCE_ADAPTER_CONTRACT.md` — the documented adapter contract

### Proposed approach

1. Check NetSquid licence terms and API documentation
2. Prototype a minimal NetSquid adapter that creates a memory and applies a channel
3. Run the existing benchmark config with the NetSquid adapter
4. Compare results against SeQUeNCe and QuNetSim
5. Repeat for QuISP if the stabilizer formalism is compatible

---

## Q4: Routing stack — full routing comparison

### What is known

The current benchmark uses SeQUeNCe's event kernel and density-matrix manager but
not its routing stack. The benchmark scope is explicitly stated as:

> "two local channels on an ideal loaded Bell pair; event-kernel integration"

The `sequence_adapter.py` creates a `Timeline`, a `quantum_manager`, and schedules
events directly. It does not use SeQUeNCe's `Node`, `Router`, `RuleSet`, or
`EntanglementProtocol` classes. The benchmark has:

- No routing (only two nodes, direct link)
- No entanglement swapping
- No repeater queue
- No capacity contention
- No dead-time model
- No fiber propagation delay

This is a deliberate scope choice: the benchmark tests whether both simulators
apply the same channel correctly, not whether they implement the same protocol.

### What is unknown

1. **Does the WestQuant channel integrate with SeQUeNCe's routing stack?** The
   channel is currently applied via `apply_to_manager()`, which directly modifies
   the quantum manager's state. SeQUeNCe's routing protocols expect to interact
   with memory components, not the manager directly. A routing-integrated adapter
   would need to:
   - Create a SeQUeNCe `QuantumMemory` component that uses the WestQuant channel
   - Register the memory with a `Node`
   - Let the `Router` and `RuleSet` drive the protocol
   - Apply the WestQuant channel when the protocol requests retrieval

2. **How do routing delays affect the channel?** In a routed network, the storage
   age is not fixed — it depends on when entanglement is generated on both links
   and when the swap occurs. The WestQuant channel requires an exact age sample
   (no interpolation). A routing-integrated benchmark would need to:
   - Generate age samples from the routing protocol's timing distribution
   - Export a channel for each possible age
   - Apply the correct channel at the actual retrieval time

3. **Can the channel handle asynchronous retrieval?** In a repeater chain, the
   two memories at a node may be written at different times (one from each link).
   The current benchmark assumes both memories are written simultaneously. An
   asynchronous model would need:
   - Per-memory age tracking
   - Channel application at each memory's actual age
   - A swap operation that combines the two memories

4. **What is the performance impact of routing?** Routing adds queueing delays,
   swap latency, and classical communication overhead. These may dominate the
   delivery probability at long distances. A routing benchmark would quantify
   this.

### What would be needed

- A routing-integrated SeQUeNCe adapter that uses `Node`, `Router`, and `RuleSet`
- A multi-hop topology (chain or star) with WestQuant memories at each node
- An age-sampling protocol that generates ages from the routing timing
- A channel export that covers the full range of possible ages
- A benchmark comparing direct-link vs routed delivery probability
- Analysis of whether routing delays or channel decoherence dominates

### What the codebase already provides

- `memorylab/sequence_adapter.py` — the event-kernel adapter (foundation for routing)
- `memorylab/network.py` — `MemoryDevice` with age-specific channels
- `memorylab/channels.py` — Kraus operators and Choi matrices for channel export
- `evaluation/config/validation_extension/crosssim_larger.json` — the current benchmark

### Proposed approach

1. Extend `sequence_adapter.py` with a `RoutedProtocol` class that uses SeQUeNCe's
   `Node` and `Router`
2. Create a 3-node chain topology (A — B — C) with WestQuant memories at B
3. Generate ages from the link-generation timing distribution
4. Export channels for the full age range
5. Compare delivery probability against the direct-link benchmark
6. Identify whether routing or decoherence is the bottleneck

---

## Q5: Material-specific bath validation — requirements and gaps

### What is known

The convergence guard (`memorylab/convergence_guard.py`) requires:
- A convergence certificate with all five axes passed
- An independent physical model review
- The profile must not be `hypothetical`
- The requested times must be within the validated domain

The current release validates:
- Synthetic spin convergence (4-spin bath, cluster orders 1–4)
- Protocol instrument (hypothetical defect-spin profile)
- Cross-simulator benchmark (hypothetical defect-spin profile)

No material-specific bath has been validated. The experimental audit status for the
protocol test is `inconclusive_missing_matched_fidelity_and_clock_review`.

### What is unknown

1. **What constitutes a material-specific bath validation?** The convergence guard
   requires "independent physical model review" but does not specify what this means
   in practice. For a real material (e.g. Pr³⁺:Y₂SiO₅), validation would need:
   - A crystal structure with verified atomic positions
   - Isotope abundances and nuclear spin data from reviewed sources
   - A bath model that matches the experimental conditions (temperature, field,
     isotope enrichment)
   - A coherence curve that matches experimental data within the validated domain
   - An independent verification that the bath model's hyperfine couplings are
     correct (e.g. from DFT or experimental EPR)

2. **What is the gap between the synthetic test and a material validation?** The
   synthetic test uses a 4-spin bath with declared couplings. A material validation
   would need:
   - Real crystal structure (from CIF or experimental data)
   - Real isotope abundances (from CIAAW or NIST)
   - Real hyperfine couplings (from DFT or EPR)
   - Real temperature and magnetic field conditions
   - Comparison against experimental T₂ or coherence curves

3. **Can the Teller et al. data support a bath validation?** The Teller baseline
   reproduces state fidelities (path mean 0.951, time-bin mean 0.914) but does not
   identify a unique T₂ or validate a bath model. The Teller data provides:
   - State fidelities at specific storage ages
   - Spatial and temporal holdout statistics
   - SeQUeNCe network runs with 87/400000 retrieved pairs

   It does not provide:
   - A coherence curve L(t)
   - Hyperfine couplings
   - Isotope-specific bath structure

4. **Can the Bradley et al. data support a bath validation?** The Bradley data
   (NV/¹³C diamond) provides Ramsey and Hahn echo observables. A bath validation
   would need:
   - The ¹³C bath structure around the NV center
   - The NV hyperfine tensor
   - Comparison of computed L(t) against Bradley's Ramsey/echo data
   - Convergence of the bath model at the experimental conditions

   The Bradley data was not available in the local cache during testing. The
   defect-spin profile used in the benchmark is hypothetical, not Bradley-derived.

5. **What is the role of matched protocol tomography?** The protocol test's
   experimental audit status is `inconclusive_missing_matched_fidelity_and_clock_review`.
   A material validation would need:
   - Matched protocol tomography (same input states, same measurements)
   - A reviewed clock calibration (same time reference)
   - A fidelity comparison under the same conditions

### What would be needed

- A material-specific profile with:
  - Real crystal structure (CIF file)
  - Real isotope abundances (from CIAAW)
  - Real hyperfine couplings (from DFT or EPR)
  - `evidence_kind: experimental` or `curated_experimental`
  - A convergence certificate from an independent review
- A coherence curve comparison against experimental data
- A protocol tomography comparison under matched conditions
- A clock calibration review
- Extension of the convergence guard to record the material identity and the
  independent review reference

### What the codebase already provides

- `memorylab/convergence_guard.py` — the certificate structure
- `memorylab/spin.py` — exact bath coherence with CPMG
- `memorylab/backends.py` — PyCCE adapter for cluster expansion
- `memorylab/experimental.py` — experimental data reanalysis
- `memorylab/t2assessment.py` — T₂ inference gates
- `baselines/teller2025/` — Teller baseline results
- `t2_data/` — Rodríguez-Moldes Pr data

### Proposed approach

1. Obtain the Bradley et al. NV/¹³C data from 4TU.ResearchData
2. Build a material-specific profile with real ¹³C bath positions
3. Run the convergence study at the experimental conditions
4. Compare computed L(t) against Bradley's Ramsey/echo data
5. If convergence is achieved and the coherence matches, issue a convergence
   certificate with `independent_physical_model_review: True`
6. Run the protocol test with the material-specific profile
7. Compare against the experimental fidelity data

---

## Summary

| Question | Status | Blocks release? | Next step |
|---|---|---|---|
| Q1: Convergence scaling | Open | No | Run 1×/10×/100× scaling study |
| Q2: Retrieval dominance | Open | No | Build multi-slot memory model |
| Q3: NetSquid/QuISP adapters | Open | No | Check NetSquid licence and API |
| Q4: Routing stack | Open | No | Extend adapter with Node/Router |
| Q5: Material bath validation | Open | No | Obtain Bradley data and build profile |

None of these questions block the v0.7.1 release or the correspondence with
reviewers. They define the research scope for the next development phase.
