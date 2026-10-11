# Complete Usage Example: From Observation to SeQUeNCe Run

This example traces a single quantum-memory scenario from a declared hypothetical
profile through model construction, channel simulation, export, and a SeQUeNCe
network run. Every parameter is labelled as coming from data, from a computation, or
from an explicit assumption.

## Step 1: Declare the profile

This example uses a **hypothetical** defect-spin profile. No experimental data is
claimed. All parameters are declared assumptions.

```python
import json

profile = {
    "name": "SYNTHETIC_SOFTWARE_SCENARIO_NOT_A_MEASURED_MATERIAL",
    "family": "spin_defect",
    "storage_model": "markov",
    "evidence_kind": "hypothetical",
    "provenance": [
        {
            "kind": "chosen_software_test_parameters",
            "not_a_material_prediction": True
        }
    ],
    "temperatures_K": {
        "write": 4.2,
        "storage": 4.2,
        "read": 4.2
    },
    "rates": {
        "population": {
            "kind": "constant",
            "rate_s_inv": 30,        # Assumption: Γ₁ = 30 s⁻¹
            "valid_temperature_K": [1, 300]
        },
        "pure_dephasing": {
            "kind": "constant",
            "rate_s_inv": 50,        # Assumption: Γ_φ = 50 s⁻¹
            "valid_temperature_K": [1, 300]
        },
        "erasure": {
            "kind": "constant",
            "rate_s_inv": 12,        # Assumption: erasure rate = 12 s⁻¹
            "valid_temperature_K": [1, 300]
        }
    },
    "io": {
        "eta_write": 0.8,            # Assumption: write efficiency
        "eta_read": 0.7,             # Assumption: read efficiency
        "write_depolarizing_p": 0.01, # Assumption: write depolarisation
        "read_depolarizing_p": 0.02,  # Assumption: read depolarisation
        "write_duration_s": 0.0001,
        "read_duration_s": 0.0002,
        "thermal_transition_s": 0,   # No thermal ramp
        "logical_encoding": "abstract_qubit",
        "protocol": "supplied_effective_write_read_channel",
        "bandwidth_Hz": None,
        "wavelength_nm": None,       # Assumption: no optical protocol specified
        "modes": 1
    },
    "noise_budget": [
        "phenomenological_relaxation",
        "independent_markov_dephasing",
        "write_depolarization",
        "read_depolarization",
        "independent_erasure"
    ],
    "network_activity": {
        "attempt_rate_Hz": 0,
        "coherence_loss_per_attempt": 0
    },
    "control": {},
    "detuning_Hz": 7,                # Assumption: 7 Hz detuning
    "equilibrium_excited_population": 0
}

with open("my_profile.json", "w") as f:
    json.dump(profile, f, indent=2)
```

### Parameter provenance

| Parameter | Source | Value |
|---|---|---|
| Γ₁ (population) | Assumption | 30 s⁻¹ |
| Γ_φ (pure dephasing) | Assumption | 50 s⁻¹ |
| Erasure rate | Assumption | 12 s⁻¹ |
| η_write | Assumption | 0.8 |
| η_read | Assumption | 0.7 |
| Write depolarisation | Assumption | 0.01 |
| Read depolarisation | Assumption | 0.02 |
| Temperature | Assumption | 4.2 K |
| Detuning | Assumption | 7 Hz |
| Wavelength | Not specified | None |
| Storage protocol | Not specified | "supplied_effective_write_read_channel" |

**No parameter comes from experimental data.** The profile is explicitly labelled
`evidence_kind: hypothetical`.

## Step 2: Simulate the channel

```bash
wqml simulate my_profile.json --times 0,0.001,0.01,0.03 --out samples.json
```

This generates 4 channel samples at ages 0, 1, 10, and 30 ms. Each sample contains:

- Kraus operators (6 operators for a 2→3 dimensional channel)
- Choi matrix (vectorized)
- CPTP validation (trace preservation and complete positivity)
- Metrics: conditional average fidelity, retrieval success probability

The Markov model computes:

```
T₂ = 1/(Γ₁/2 + Γ_φ) = 1/(15 + 50) = 1/65 ≈ 15.4 ms
```

At each age, the storage decoherence is:

```
L(t) = exp(-(Γ₁/2 + Γ_φ) · t) = exp(-65 · t)
```

The write/read depolarisation and erasure are applied once at retrieval.

## Step 3: Export a network device

```bash
wqml export samples.json --allow-hypothetical --out device.json
```

The `--allow-hypothetical` flag is required because the profile declares
`evidence_kind: hypothetical`. This prevents accidental export of unvalidated models
as experimental results.

## Step 4: Run a SeQUeNCe network simulation

With SeQUeNCe installed:

```bash
pip install "westquant-memory-lab[network]"
```

Run a two-node workload:

```bash
wqml network device.json device.json memorylab/examples/network_workload.json --allow-hypothetical
```

Or via the Python API:

```python
import numpy as np
from memorylab.network import load_device

device = load_device("device.json", allow_hypothetical=True)

# Input: a Bell-diagonal state
input_state = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex)

# Retrieve at 1 ms storage age
result = device.retrieve(input_state, age_s=0.001, rng=np.random.default_rng(42))

if result["success"]:
    retrieved = result["density_matrix"]
    fidelity = np.real(np.trace(retrieved @ input_state))
    print(f"Retrieved with fidelity: {fidelity:.6f}")
else:
    print("State lost (erasure channel)")
```

## Step 5: What the channel does

The complete write-store-read channel is:

```
E_t(ρ) = η(t) · Φ_t(ρ) + (1 - η(t)) · Tr(ρ) |e⟩⟨e|
```

where:
- `Φ_t` is the conditional depolarised channel (storage decoherence + write/read depolarisation)
- `η(t)` is the retrieval success probability (erasure branch)
- `|e⟩` is the erasure state

The channel is CPTP from a 2-dimensional input to a 3-dimensional output (qubit + erasure).

## What is NOT claimed

- This is not a material prediction. The profile is hypothetical.
- The T₂ value (15.4 ms) is a model output under declared assumptions, not a measured coherence time.
- The write/read efficiencies are assumptions, not derived from optical data.
- The wavelength and storage protocol are not specified.
- No hardware validation is claimed.

## Using real experimental data

To use real experimental data instead of a hypothetical profile, the profile must
declare `evidence_kind: experimental` or `evidence_kind: curated_experimental` and
provide provenance with source identifiers and checksums. See the Teller et al.
baseline (`examples/teller2025_baseline.json`) for a complete example using licensed
open data from Zenodo record 14929997.
