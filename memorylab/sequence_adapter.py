"""SeQUeNCe 1.2 density-manager adapter and finite-point two-node event workload.

No default Memory noise is composed a second time. This is a real SeQUeNCe
kernel workload, not the stock routing stack or a reproduction of a Bell test.
"""
import math
import importlib.metadata
import numpy as np
from .channels import apply, validate_state
from .common import finite, MissingData
from .network import wilson


def apply_to_manager(manager, key, channel):
    """Apply a conditional channel to one key, preserving its entire joint state.

    Loss must be sampled/handled by the owning protocol before this call.
    """
    state = manager.get(key)
    keys = list(state.keys)
    if key not in keys or len(keys) > 8:
        raise ValueError("Missing key or density-state budget exceeded")
    index = keys.index(key)
    full = []
    for k in channel.conditional_kraus:
        operator = np.array([[1]], complex)
        for j in range(len(keys)):
            operator = np.kron(operator, k if j == index else np.eye(2))
        full.append(operator)
    rho = apply(full, validate_state(state.state))
    validate_state(rho)
    manager.set(keys, rho)
    return rho


def seconds_to_ps(value):
    t = finite(value, "event duration", 0)
    ticks = round(t*1e12)
    if abs(t-ticks/1e12) > 1e-15:
        raise ValueError("Duration is not representable in SeQUeNCe picoseconds")
    return ticks


def run_link(left, right, workload, simulation_seed):
    from sequence.kernel.timeline import Timeline
    from sequence.kernel.event import Event
    from sequence.kernel.process import Process
    n = workload["attempts"]
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 1_000_000:
        raise ValueError("Attempt budget is 1..1000000")
    interval = finite(workload["attempt_interval_s"], "interval", 1e-12)
    age = finite(workload["storage_age_s"], "age", 1e-12)
    probability = finite(workload["link_herald_probability"], "link probability", 0, 1)
    threshold = finite(workload["minimum_Bell_fidelity"], "Bell threshold", 0, 1)
    cl, cr = left.channel_at(age), right.channel_at(age)
    if age >= interval:
        raise ValueError("This single-slot workload requires age < attempt interval")
    age_ticks, interval_ticks = seconds_to_ps(age), seconds_to_ps(interval)
    if age_ticks < 1 or interval_ticks < 1:
        raise ValueError("Event ticks must be positive")
    timeline = Timeline(stop_time=n*interval_ticks+1, formalism="density_matrix")
    manager = timeline.quantum_manager
    keys = [manager.new(), manager.new()]
    bell = np.array([1, 0, 0, 1], complex)/math.sqrt(2)
    initial = np.outer(bell, bell.conj())
    joint = [np.kron(a, b) for a in cl.conditional_kraus for b in cr.conditional_kraus]
    expected_output = apply(joint, initial)
    expected_fidelity = float(np.real(bell.conj() @ expected_output @ bell))
    rng = np.random.default_rng(simulation_seed)

    class Protocol:
        heralded = 0
        retrieved = 0
        qualifying = 0
        max_density_error = 0.0
        fidelities = []
        events = []

        def attempt(self, index):
            if rng.random() < probability:
                self.heralded += 1
                manager.set(keys, initial)
                timeline.schedule(Event(timeline.now()+age_ticks, Process(self, "retrieve", [index])))
            if index+1 < n:
                timeline.schedule(Event((index+1)*interval_ticks, Process(self, "attempt", [index+1])))

        def retrieve(self, index):
            success = rng.random() < cl.success_probability and rng.random() < cr.success_probability
            if success:
                apply_to_manager(manager, keys[0], cl)
                rho = apply_to_manager(manager, keys[1], cr)
                error = float(np.max(np.abs(rho-expected_output)))
                self.max_density_error = max(self.max_density_error, error)
                fidelity = float(np.real(bell.conj() @ rho @ bell))
                self.fidelities.append(fidelity)
                self.retrieved += 1
                self.qualifying += int(fidelity >= threshold)
            # Reset both keys after erasure or consumption; no stale entanglement.
            manager.set(keys, np.eye(4)/4)
            if len(self.events) < 20:
                self.events.append({"attempt": index, "readout_time_ps": timeline.now(),
                                    "success": success})

    protocol = Protocol()
    timeline.schedule(Event(0, Process(protocol, "attempt", [0])))
    timeline.init()
    timeline.run()
    return {"schema": "westquant_sequence_workload_v1", "status": "success",
            "simulator": "SeQUeNCe", "version": importlib.metadata.version("sequence"),
            "seed": simulation_seed, "attempts": n, "events_executed": timeline.run_counter,
            "heralded": protocol.heralded, "retrieved_pairs": protocol.retrieved,
            "quality_qualified_pairs": protocol.qualifying,
            "analytic_conditional_Bell_fidelity": expected_fidelity,
            "observed_conditional_Bell_fidelity": float(np.mean(protocol.fidelities)) if protocol.fidelities else None,
            "max_density_error_against_analytic": protocol.max_density_error if protocol.retrieved else None,
            "retrieved_fraction_95CI": wilson(protocol.retrieved, n),
            "expected_success_probability": probability*cl.success_probability*cr.success_probability,
            "qualified_rate_per_s": protocol.qualifying/(n*interval),
            "attempt_interval_s": interval, "storage_age_s": age, "sample_events": protocol.events,
            "scope": "two local channels on an ideal loaded Bell pair; event-kernel integration",
            "network_assumptions": ["ideal input Bell pair and independent nodes",
                "ideal heralded signal loss; fluorescence false positives not modeled",
                "no fiber/filter/detector loss beyond supplied interface", "single memory slot per node",
                "no routing, entanglement swap, dead time, or preparation overhead"],
            "measured_network_performance": False}
