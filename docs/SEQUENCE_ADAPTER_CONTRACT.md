# SeQUeNCe Adapter Contract — v0.7.1

This document describes the contract between WestQuant's memory-channel model and the
SeQUeNCe network simulator adapter (`memorylab/sequence_adapter.py`).

## Scope

The adapter uses SeQUeNCe's event kernel and density-matrix manager. It does not use
SeQUeNCe's routing stack, link-generation protocol, or physical-channel models. The
benchmark scope is:

- Two nodes, one memory slot per node
- Fixed storage age per run
- Common random numbers (shared logical trace) supplied to both simulators
- External logical clock for timing

The adapter is not a full network simulation. It is a controlled channel-application
test that checks density-matrix agreement between WestQuant's exported channel and
SeQUeNCe's density-matrix manager.

## When write, storage, and read occur

The adapter applies the complete write-store-read channel as a single operation at the
moment of retrieval. The sequence is:

1. **Write** — the input state is accepted into the memory at the write time.
2. **Storage** — the state ages for the declared storage duration. No event fires
   during storage; the age is a parameter, not a simulated wait.
3. **Read** — the stored state is retrieved at the read time. The channel is applied
   once, producing either a retrieved density matrix or an erasure outcome.

The adapter does not decompose the channel into separate write, storage, and read
events inside SeQUeNCe. The full effective channel (including write/read
depolarisation, storage decoherence, and erasure) is applied as one CPTP map.

## Seconds to picoseconds

SeQUeNCe's internal time unit is picoseconds. The adapter converts WestQuant's
SI-unit seconds to picoseconds by multiplying by 10¹². The conversion is exact; no
rounding is applied. Times that are not representable in picoseconds (e.g. sub-femtosecond
durations) are rejected with an explicit error rather than silently rounded.

The storage age, write duration, and read duration are all converted. The logical
clock that drives the event sequence uses the same picosecond timeline.

## Channel semantics: initial state vs. time step

The exported channel describes the **complete evolution from the initial state** to
the output state at the declared age. It is not a per-tick time step. The adapter
applies the channel once to the original input density matrix. Applying the same
channel incrementally at each network tick would count the noise twice and may be
invalid at coherence revivals. The API rejects incremental application.

## Loss and false-positive detections

Loss is represented as an erasure branch in the channel. The Kraus decomposition
includes an erasure operator that maps any input to the vacuum/erasure state |e⟩.
The adapter samples acceptance from the retrieval success probability:

- If the random draw succeeds, the conditional channel is applied and the retrieved
  density matrix is returned.
- If the random draw fails, the adapter returns an erasure outcome. No density matrix
  is produced.

False-positive detections (background registering as signal when retrieval failed)
are modelled by the protocol instrument (`memorylab/protocol.py`), not by the channel
itself. The protocol instrument uses an exclusive first-click model: a true retrieved
signal wins over background; background can register only if signal retrieval failed.
Double clicks are excluded. Signal noise already represented by the input channel
must not include this source.

## Entanglement preservation

When two qubits form a joint entangled state, the adapter applies the local channel
to one qubit while preserving the entangled structure. The joint density matrix is
treated as a single object. The local channel acts as:

```
ρ_AB → (E ⊗ I)(ρ_AB)
```

where E is the memory channel and I is the identity on the other qubit. The adapter
does not trace out and re-prepare the partner qubit. The Choi matrix of the local
channel is applied via tensor product to preserve correlations.

The adapter checks that the partial trace over the partner qubit is unchanged by the
local operation. If the joint state's entanglement is corrupted by an incorrect
application, the adapter reports a density-matrix error.

## Decoherence responsibility

WestQuant and SeQUeNCe must not apply the same noise twice. The responsibility
split is:

| Source | Who handles it |
|---|---|
| Storage decoherence (T₁, T₂, T_φ) | WestQuant's channel (applied once at retrieval) |
| Write/read depolarisation | WestQuant's channel |
| Erasure / retrieval loss | WestQuant's channel (sampled acceptance) |
| Link loss, detector inefficiency | SeQUeNCe's component models (if configured) |
| Routing, queueing delays | SeQUeNCe's event kernel (not in benchmark scope) |

The adapter does not enable SeQUeNCe's built-in memory decoherence models. If a
SeQUeNCe memory component is configured with its own decoherence, that would double
count the noise. The adapter's memory component is a passive store: it holds the
density matrix and applies the WestQuant channel at retrieval time only.

The adapter explicitly disables SeQUeNCe's `quantum_memory` decoherence update. The
memory slot is a passive container. All physics comes from the WestQuant channel
applied at the retrieval event.

## Common random numbers

Both SeQUeNCe and QuNetSim receive the same pre-generated event trace from WestQuant.
The trace specifies:

- The random seed for each attempt
- The storage age for each attempt
- The input state for each attempt

Identical outcomes between the two simulators partly follow from this shared trace.
This is not an independent test of the simulators' stochastic protocols. It is a test
of whether both simulators apply the same channel correctly given the same inputs.

## Version

This contract applies to WestQuant v0.7.1 with SeQUeNCe v1.2.0.
