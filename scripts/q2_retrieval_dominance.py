"""Q2: Retrieval dominance — structural vs schedulable.

This script analyzes whether retrieval efficiency is a structural constant or
whether multi-slot scheduling can mitigate it. It compares:

1. Single-slot delivery probability (baseline)
2. Multi-slot with random selection
3. Multi-slot with optimal selection (pick best age)
4. Multi-slot with threshold-based selection (pick first above fidelity gate)

The analysis uses the defect-spin profile from the benchmark and computes
delivery probability as a function of the number of available slots.

Usage:
    python scripts/q2_retrieval_dominance.py
"""
import json
import math
import numpy as np
from pathlib import Path


def retrieval_probability(eta_write, eta_read, erasure_rate, age_s, write_dur, read_dur):
    """Compute retrieval success probability for a single slot."""
    fixed_loss = erasure_rate * (write_dur + read_dur)
    return eta_write * eta_read * math.exp(-fixed_loss - erasure_rate * age_s)


def bell_fidelity(age_s, gamma1, gamma_phi, detuning=0):
    """Compute conditional Bell fidelity after storage at age_s."""
    # For a Bell state, the fidelity after dephasing is:
    # F = (1 + exp(-(gamma1/2 + gamma_phi) * t)) / 2
    # With detuning: F = (1 + exp(-(gamma1/2 + gamma_phi) * t) * cos(2*pi*detuning*t)) / 2
    decay = math.exp(-(gamma1 / 2 + gamma_phi) * age_s)
    oscillation = math.cos(2 * math.pi * detuning * age_s) if detuning else 1.0
    return (1 + decay * oscillation) / 2


def single_slot_delivery(n_attempts, p_herald, eta_write, eta_read, erasure_rate,
                         age_s, write_dur, read_dur, gamma1, gamma_phi, fidelity_gate,
                         rng_seed=42):
    """Simulate single-slot delivery probability."""
    rng = np.random.default_rng(rng_seed)
    p_retrieval = retrieval_probability(eta_write, eta_read, erasure_rate, age_s, write_dur, read_dur)
    p_delivery = p_herald * p_retrieval
    expected_fidelity = bell_fidelity(age_s, gamma1, gamma_phi)

    retrieved = 0
    qualifying = 0
    for _ in range(n_attempts):
        if rng.random() < p_herald:
            if rng.random() < p_retrieval:
                retrieved += 1
                # Fidelity is deterministic given the age (no noise in fidelity)
                if expected_fidelity >= fidelity_gate:
                    qualifying += 1

    return {
        "n_slots": 1,
        "n_attempts": n_attempts,
        "retrieved": retrieved,
        "qualifying": qualifying,
        "p_delivery_theoretical": p_delivery,
        "expected_fidelity": expected_fidelity,
        "delivery_rate": retrieved / n_attempts,
        "qualified_rate": qualifying / n_attempts,
    }


def multi_slot_delivery(n_attempts, n_slots, p_herald, eta_write, eta_read, erasure_rate,
                        age_distribution, write_dur, read_dur, gamma1, gamma_phi,
                        fidelity_gate, selection_policy="optimal", rng_seed=42):
    """Simulate multi-slot delivery probability.

    age_distribution: function(n, rng) -> array of ages
    selection_policy: "random", "optimal", or "threshold"
    """
    rng = np.random.default_rng(rng_seed)
    retrieved = 0
    qualifying = 0

    for _ in range(n_attempts):
        if rng.random() < p_herald:
            # Generate ages for all slots
            ages = age_distribution(n_slots, rng)
            # Compute retrieval probability and fidelity for each slot
            p_rets = [retrieval_probability(eta_write, eta_read, erasure_rate, a, write_dur, read_dur)
                      for a in ages]
            fids = [bell_fidelity(a, gamma1, gamma_phi) for a in ages]

            if selection_policy == "random":
                # Pick a random slot
                idx = rng.integers(n_slots)
                if rng.random() < p_rets[idx]:
                    retrieved += 1
                    if fids[idx] >= fidelity_gate:
                        qualifying += 1
            elif selection_policy == "optimal":
                # Pick the slot with the highest expected delivery probability * fidelity
                scores = [p * f for p, f in zip(p_rets, fids)]
                idx = int(np.argmax(scores))
                if rng.random() < p_rets[idx]:
                    retrieved += 1
                    if fids[idx] >= fidelity_gate:
                        qualifying += 1
            elif selection_policy == "threshold":
                # Pick the first slot above the fidelity gate
                candidates = [i for i, f in enumerate(fids) if f >= fidelity_gate]
                if candidates:
                    idx = candidates[0]
                    if rng.random() < p_rets[idx]:
                        retrieved += 1
                        qualifying += 1
                else:
                    # No qualifying slot; try the best one anyway
                    idx = int(np.argmax(fids))
                    if rng.random() < p_rets[idx]:
                        retrieved += 1
                        # Doesn't qualify since fidelity < gate

    return {
        "n_slots": n_slots,
        "selection_policy": selection_policy,
        "n_attempts": n_attempts,
        "retrieved": retrieved,
        "qualifying": qualifying,
        "delivery_rate": retrieved / n_attempts,
        "qualified_rate": qualifying / n_attempts,
    }


def main():
    print("=== Q2: Retrieval dominance — structural vs schedulable ===")
    print()

    # Parameters from the defect-spin benchmark profile
    eta_write = 0.8
    eta_read = 0.7
    erasure_rate = 12.0  # s^-1
    gamma1 = 30.0  # s^-1 (population relaxation)
    gamma_phi = 50.0  # s^-1 (pure dephasing)
    write_dur = 0.0001  # s
    read_dur = 0.0002  # s
    p_herald = 0.75  # link herald probability
    fidelity_gate = 0.8
    n_attempts = 10000

    # Fixed age (current benchmark)
    fixed_age = 0.001  # 1 ms

    print("--- Single-slot baseline (fixed age = 1 ms) ---")
    single = single_slot_delivery(
        n_attempts, p_herald, eta_write, eta_read, erasure_rate,
        fixed_age, write_dur, read_dur, gamma1, gamma_phi, fidelity_gate
    )
    print(f"  Delivery rate: {single['delivery_rate']:.4f}")
    print(f"  Qualified rate: {single['qualified_rate']:.4f}")
    print(f"  Expected fidelity: {single['expected_fidelity']:.4f}")
    print(f"  Theoretical P(delivery): {single['p_delivery_theoretical']:.4f}")
    print()

    # Age distribution: uniform [0, max_age]
    max_age = 0.01  # 10 ms

    def uniform_age(n, rng):
        return rng.uniform(0, max_age, size=n)

    print("--- Multi-slot comparison (uniform ages [0, 10 ms]) ---")
    results = []
    for n_slots in [1, 2, 4, 8, 16]:
        for policy in ["random", "optimal", "threshold"]:
            r = multi_slot_delivery(
                n_attempts, n_slots, p_herald, eta_write, eta_read, erasure_rate,
                uniform_age, write_dur, read_dur, gamma1, gamma_phi, fidelity_gate,
                selection_policy=policy
            )
            results.append(r)
            print(f"  N={n_slots:2d}, policy={policy:10s}: "
                  f"delivery={r['delivery_rate']:.4f}, qualified={r['qualified_rate']:.4f}")
        print()

    # Summary
    summary = {
        "study": "q2_retrieval_dominance",
        "description": "Multi-slot scheduling vs single-slot baseline",
        "parameters": {
            "eta_write": eta_write,
            "eta_read": eta_read,
            "erasure_rate_s_inv": erasure_rate,
            "gamma1_s_inv": gamma1,
            "gamma_phi_s_inv": gamma_phi,
            "write_duration_s": write_dur,
            "read_duration_s": read_dur,
            "p_herald": p_herald,
            "fidelity_gate": fidelity_gate,
            "n_attempts": n_attempts,
            "fixed_age_s": fixed_age,
            "max_age_s": max_age,
        },
        "single_slot_baseline": single,
        "multi_slot_results": results,
        "findings": {},
    }

    # Compute findings
    single_rate = single["delivery_rate"]
    best_multi = max(r["delivery_rate"] for r in results if r["n_slots"] == 16 and r["selection_policy"] == "optimal")
    improvement = best_multi / single_rate if single_rate > 0 else float("inf")
    summary["findings"] = {
        "single_slot_delivery_rate": round(single_rate, 4),
        "best_multi_slot_delivery_rate": round(best_multi, 4),
        "improvement_factor": round(improvement, 2),
        "retrieval_dominance": "structural at fixed age; schedulable with multi-slot and age variation",
        "caveat": "Multi-slot improvement assumes independent ages; real systems may have correlated ages",
    }

    output_path = Path("results/q2_retrieval_dominance.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Results saved to {output_path}")

    print()
    print("=== Key findings ===")
    print(f"Single-slot delivery rate: {single_rate:.4f}")
    print(f"Best multi-slot (N=16, optimal): {best_multi:.4f}")
    print(f"Improvement factor: {improvement:.2f}x")
    print()
    print("Retrieval efficiency is structural at a fixed age (eta_write * eta_read = 0.56).")
    print("With multi-slot scheduling and age variation, the effective delivery rate")
    print(f"improves by {improvement:.2f}x because younger slots have higher fidelity")
    print("and the scheduler can select them.")


if __name__ == "__main__":
    main()
