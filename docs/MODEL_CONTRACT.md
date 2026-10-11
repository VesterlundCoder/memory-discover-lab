# Model Contract — v0.7.1

Every material candidate has its own id, family, composition, charge, electron spin,
site-specific isotopes, geometry, host material, and provenance. Missing properties
are unknown. Candidate generation does not prove binding, metastability, or memory
function.

Observations and simulator recipes are different objects. A simulator recipe selects
a physics model and states which observations, computations, or assumptions motivate
the parameters. The result is a computation even when the input is experimental.

## Families

| Family | Implemented storage descriptions | Boundary |
|---|---|---|
| Atomic ensemble | Markov channel; conditional coherence table | Effective write/read channel must be specified; MaxwellBloch provides separate classical field propagation |
| Trapped atom/ion | Markov channel; coherence table | Geometry/electronics can be computed with PySCF; no lifetimes are automatically derived |
| Rare-earth ion in solid | Markov channel; exact small spin bath; PyCCE; coherence table | Host, spin levels, optical protocol efficiency, and couplings must be specified |
| Spin defect | Same four storage descriptions | Structure-specific hyperfine tensors required; model sources must be independent |
| Molecular spin | Same four storage descriptions | A drug fragment or NMR spectrum is not automatically a quantum memory |
| Negative ion | Markov channel or coherence table; photodetachment with given environmental overlap | The overlap is an input parameter; the tool does not solve the continuum-electron wavefunction |

There are six family branches and several reuse the same physics models. The family
name does not magically change the Hamiltonian. AFC/EIT/DLCZ, detailed optical cavities,
quantum dots, optomechanical memories, and general non-Markovian process tensors are
not fully implemented here.

## Molecular data flow

For molecular-spin candidates, the contract distinguishes five layers that must not
be conflated:

1. **Molecular structure** — geometry, charge, spin multiplicity from PySCF or
   experimental structure. This determines electronic structure but not coherence.
2. **Computed couplings** — hyperfine tensors, g-tensor, zero-field splitting from
   PySCF or imported from ORCA/QE. These are electronic-structure outputs, not
   spin-bath dynamics.
3. **Assumed environment** — host matrix, isotope composition, temperature, magnetic
   field. These are declared assumptions, not derived from the molecule.
4. **Computed coherence** — spin-bath evolution from PyCCE or exact small-bath
   diagonalisation. This yields L(t) under the assumed environment.
5. **Optical memory function** — write/read efficiency, wavelength, storage protocol,
   retrieval model. These are separate from spin coherence.

Molecular data or a coherence curve does not automatically determine write/read
efficiency, wavelength, or memory protocol. A T_m value from a molecular-qubit
dataset is a phase-memory time under the dataset's conditions, not an optical-memory
retrieval efficiency.

## Storage, temperature, and noise

Internally, the framework uses seconds, Hz, tesla, kelvin, and angstrom. A tensor
field also has a coordinate frame. Hz and rad/s are converted with 2π. PyCCE receives
ms, kHz, G, and rad/ms/G. An isotope swap identifies the atomic site; the isotope mass
does not create a hyperfine tensor.

The Markov model uses population relaxation Γ₁ and **pure** dephasing Γφ. At constant
temperature, T₂ = 1/(Γ₁/2 + Γφ). When temperature changes, declared temperature models
and validity ranges apply. A constant coefficient over a range is an explicit model
assumption. A temperature ramp is not accepted as a free change: `thermal_transition_s`
must be zero in this version. Different fixed temperatures during write, storage, and
read are allowed, but the transition's feasibility is not validated.

Exact spin bath:

- H₀ = H_b + m₀ A·I and H₁ = H_b + m₁ A·I in the pure central-spin dephasing
  approximation.
- Nuclear Zeeman, hyperfine, quadrupole, and supplied pairwise spin couplings are
  included.
- L(t) = Tr[U₀ ρ_b U₁†], with thermal bath density at the specified storage
  temperature.
- Ideal CPMG pulses switch the branches. The logical control frame resets at readout.
- The dimension is bounded; larger baths require CCE and a convergence study.
- Transverse central-spin couplings and phonons must be modelled separately.

The PyCCE adapter supports conventional CCE for normalised pure coherence. gCCE
requires a more complete density-matrix reconstruction and is not accepted by this
adapter. Increase cluster order, bath radius, and connectivity radius and compare L(t)
before drawing material conclusions. The bath's default isotope constants come from
PyCCE's reference table; compare them against reviewed nuclear data before using them
as experimental evidence.

Coherence tables retain complex phase and revivals. They must start with L(0)=1, have
|L|≤1, and match temperature and control. Linear interpolation is used only within the
table. A table that already includes population relaxation is not accepted as an
independent dephasing contribution.

## Channel and network

Write and read depolarisation, the storage channel, and state-independent loss are
composed. The output channel is CPTP from one qubit to three states: 0, 1, and
erasure. Choi matrix and Kraus operators are exported. Conditional average qubit
fidelity, conditional entanglement fidelity, and retrieval probability are separate
metrics.

Fidelity uses the **squared** Uhlmann/Jozsa convention, not QuTiP's root fidelity.
`unconditional_target_overlap` is the success probability times the conditional average
overlap. At zero retrieval, conditional fidelity is undefined and reported as null.

The network adapter provides density matrices and heralded loss outcomes. Two qubits
can be treated as a joint entangled density matrix. An age channel is applied once to
the original state. Incremental application of the same age channel would count noise
twice and may be invalid at revivals; the API rejects that operation.

The built-in two-node benchmark has independent link attempts and fixed storage age.
It has no repeater queue, capacity contention, routing, or dead-time model. SeQUeNCe,
QuNetSim, NetSquid, and WestQuant-Network need to call this API from their respective
event handlers. Their version-specific classes are not included in the package.

## External computations

PySCF computes vertical HF/DFT energy and optional TDA at a given geometry. The cache
covers geometry, charge, 2S, recipe, and backend version. Born–Oppenheimer electronics
do not depend on the isotope mass at the same nuclear geometry. Isotope spin and host
environment must be connected through their own models.

ORCA and QE adapters write real input files and run a specified local binary with a
timeout. QE requires cell, pseudopotentials, and k-points. PyCCE can import ORCA/QE
coupling data; coordinate frame and atom positions need review after import. ORCA/QE
binaries are not included and were not run in this verification.

PyCCE 1.1.1 uses two removed API names. The adapter restores NumPy's `unicode_` as
`str_` and SciPy's moved `isintlike`. This changes dtype/input checking, not the
Hamiltonian. This compatibility is checked against an exact single-spin solution.

MaxwellBloch provides classical pulse/field propagation in the backend's own
normalised units. A physical scale factor must be chosen for connection to SI units.
No qubit fidelity or quantum-memory efficiency is invented from a classical field
curve.

## Convergence guard

Before a spin model is labelled as a material prediction, the convergence guard checks
profile identity, bath convergence, and cluster-order convergence. A model that has
not converged is labelled `computed` with an explicit `convergence_status` field. It is
not promoted to `evaluated_reference` or `experimental`.

## Protocol instrument

The protocol instrument models the complete effective write/store/read process with
explicit readout false positives. A true retrieved signal wins over background;
background can register only if signal retrieval failed. This exclusive first-click
model excludes double clicks. Signal noise already represented by the input channel
must not include this source. The protocol test's registered maximum density-matrix
error is approximately 1.44×10⁻¹⁵, which satisfies the 10⁻¹⁰ tolerance.
