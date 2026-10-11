"""Provider-neutral adapters and a reproducible two-node entanglement workload.

Absolute-age channels are applied ONCE. No Markov assumption is imposed on revivals.
"""
import math
import numpy as np
from .channels import MemoryChannel, apply, validate_state
from .common import finite, MissingData, read_json, write_json


class MemoryDevice:
    def __init__(self, channels, allow_hypothetical=False):
        if not channels:
            raise ValueError("No channel samples")
        self.channels = {}
        for row in channels:
            channel = MemoryChannel.from_serialized(row) if isinstance(row, dict) else row
            if channel.metadata["input_evidence_kind"] in {"hypothetical", "unknown"} and not allow_hypothetical:
                raise MissingData("Hypothetical/unknown-evidence network use requires explicit opt-in")
            age = channel.metadata["storage_age_s"]
            if age in self.channels:
                raise ValueError("Duplicate storage ages")
            self.channels[age] = channel

    def channel_at(self, age_s):
        age = finite(age_s, "age_s", 0)
        if age not in self.channels:
            raise MissingData("No exact age sample; calculate the model on the requested age grid")
        return self.channels[age]

    def retrieve(self, initial_density_matrix, age_s, rng, subsystem=None):
        channel = self.channel_at(age_s)
        rho = validate_state(initial_density_matrix)
        if subsystem is None:
            if rho.shape != (2, 2):
                raise ValueError("Single-qubit retrieval needs a 2x2 state")
            kraus = channel.conditional_kraus
        else:
            if rho.shape != (4, 4) or subsystem not in (0, 1):
                raise ValueError("Two-qubit retrieval needs subsystem 0 or 1")
            kraus = [np.kron(k, np.eye(2)) if subsystem == 0 else np.kron(np.eye(2), k)
                     for k in channel.conditional_kraus]
        if rng.random() >= channel.success_probability:
            return {"success": False, "density_matrix": None, "age_s": age_s,
                    "read_latency_s": channel.metadata["optical_interface"]["read_duration_s"]}
        return {"success": True, "density_matrix": apply(kraus, rho), "age_s": age_s,
                "read_latency_s": channel.metadata["optical_interface"]["read_duration_s"]}

    def apply_increment(self, *args, **kwargs):
        raise UnsupportedOperation("Age tables may be non-Markovian; preserve input and apply at final retrieval")


class UnsupportedOperation(RuntimeError):
    pass


def export(channels, output, allow_hypothetical=False):
    device = MemoryDevice(channels, allow_hypothetical)
    bundle = {"schema": "westquant_memory_device_v1",
              "adapter": "provider_neutral_density_matrix_and_erasure",
              "third_party_network_simulator_integration": "call MemoryDevice from your simulator's event hooks",
              "samples": [device.channels[t].serialize() for t in sorted(device.channels)],
              "no_age_interpolation_or_extrapolation": True, "validated_for_hardware": False}
    write_json(output, bundle)
    return {"output": str(output), "samples": len(device.channels)}


def load_device(path, allow_hypothetical=False):
    return MemoryDevice(read_json(path)["samples"], allow_hypothetical)


def wilson(successes, trials):
    if trials < 1:
        return [None, None]
    z, p = 1.959963984540054, successes/trials
    den = 1+z*z/trials
    center = (p+z*z/(2*trials))/den
    half = z*math.sqrt(p*(1-p)/trials+z*z/(4*trials*trials))/den
    return [max(0, center-half), min(1, center+half)]


def link_benchmark(left, right, workload, simulation_seed):
    """Attempt -> herald -> fixed storage age -> retrieval. Not a full repeater simulator."""
    n = workload["attempts"]
    if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 10_000_000:
        raise ValueError("Bounded positive integer attempts required")
    prob = finite(workload["link_herald_probability"], "link probability", 0, 1)
    interval = finite(workload["attempt_interval_s"], "attempt interval", 1e-15)
    age = workload["storage_age_s"]
    finite(workload["minimum_Bell_fidelity"], "minimum_Bell_fidelity", 0, 1)
    cl, cr = left.channel_at(age), right.channel_at(age)
    bell = np.array([1, 0, 0, 1], complex)/math.sqrt(2)
    rho = np.outer(bell, bell.conj())
    joint = [np.kron(a, b) for a in cl.conditional_kraus for b in cr.conditional_kraus]
    output = apply(joint, rho)
    fidelity = float(np.real(bell.conj() @ output @ bell))
    rng = np.random.default_rng(simulation_seed)
    # Independent state-independent heralding, exactly as declared in the channel contract.
    heralded = int(rng.binomial(n, prob))
    retrieved = int(rng.binomial(heralded, cl.success_probability*cr.success_probability))
    qualifying = retrieved if fidelity >= workload["minimum_Bell_fidelity"] else 0
    return {"attempts": n, "heralded": heralded, "retrieved_pairs": retrieved,
            "quality_qualified_pairs": qualifying, "conditional_Bell_fidelity":
                fidelity if cl.success_probability*cr.success_probability > 0 else None,
            "retrieved_fraction_95CI": wilson(retrieved, n),
            "qualified_rate_per_s": qualifying/(n*interval),
            "mean_success_probability_per_attempt": prob*cl.success_probability*cr.success_probability,
            "readout_latency_s": max(cl.metadata["optical_interface"]["read_duration_s"],
                                     cr.metadata["optical_interface"]["read_duration_s"]),
            "assumptions": ["independent trials", "no queue/capacity contention",
                            "fixed age after heralding", "independent two-node memories"],
            "workload_scope": "two-node channel benchmark, not SeQUeNCe/NetSquid"}
