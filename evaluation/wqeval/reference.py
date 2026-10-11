"""Independent NumPy/SciPy reference; deliberately imports no memorylab code.

Column-vectorized Liouvillian exponentiation and matrix-unit Choi assembly
provide a different numerical description from the lab's Kraus composition.
This script baseline is not a claim about all possible handwritten workflows.
"""
import math
import numpy as np
from scipy.linalg import expm

I = np.eye(2, dtype=complex)
Z = np.diag([1., -1.]).astype(complex)
MINUS = np.array([[0, 1], [0, 0]], complex)

def rate(spec, temperature):
    lo, hi = spec["valid_temperature_K"]
    if not lo <= temperature <= hi:
        raise ValueError("Reference temperature outside declared interval")
    if spec["kind"] == "constant":
        return float(spec["rate_s_inv"])
    if spec["kind"] != "phenomenological_temperature":
        raise ValueError("Unsupported reference model")
    result = spec.get("base_s_inv", 0) + spec.get("direct_s_inv_K_inv", 0)*temperature
    result += spec.get("raman_at_reference_s_inv", 0)*(temperature/spec.get("reference_K", 1))**spec.get("raman_exponent", 7)
    if spec.get("orbach_s_inv", 0):
        x = spec["orbach_gap_K"]/temperature if temperature else math.inf
        result += spec["orbach_s_inv"]/math.expm1(x) if x < 700 else 0
    return result

def dissipator(op):
    product = op.conj().T @ op
    return np.kron(op.conj(), op)-0.5*(np.kron(I, product)+np.kron(product.T, I))

def stage(spec, name, duration):
    t = spec["temperatures_K"][name]
    g1 = rate(spec["rates"]["population"], t)
    gp = rate(spec["rates"]["pure_dephasing"], t)
    if name == "storage":
        a = spec.get("network_activity", {})
        gp += a.get("attempt_rate_Hz", 0)*a.get("coherence_loss_per_attempt", 0)
    pe = spec.get("equilibrium_excited_population", 0)
    if spec.get("thermal_detailed_balance"):
        from scipy.constants import h, k
        x = h*spec["qubit_frequency_Hz"]/(k*t) if t else math.inf
        pe = 1/(1+math.exp(x)) if x < 700 else 0
    ghz = np.diag([0., spec.get("detuning_Hz", 0)])
    generator = -2j*np.pi*(np.kron(I, ghz)-np.kron(ghz.T, I))
    generator += g1*(1-pe)*dissipator(MINUS)+g1*pe*dissipator(MINUS.conj().T)
    generator += gp/2*dissipator(Z)
    return expm(duration*generator)

def depolarizing(p):
    identity_vector = I.reshape(-1, order="F")
    return (1-p)*np.eye(4)+p/2*np.outer(identity_vector, identity_vector)

def superoperator(spec, age):
    if spec["storage_model"] == "measured_operating_point":
        pt = spec["point"]
        if age != pt["end_to_end_age_s"]:
            raise ValueError("Reference permits only the calibrated age")
        if any(t != pt["temperature_K"] for t in spec["temperatures_K"].values()):
            raise ValueError("Reference permits only calibrated temperature")
        return depolarizing(2*(1-pt["conditional_average_fidelity"])), pt["signal_retrieval_probability"]
    if spec["storage_model"] != "markov":
        raise ValueError("Independent comparison reference supports Markov and fixed-point cases")
    io = spec["io"]
    w = depolarizing(io["write_depolarizing_p"]) @ stage(spec, "write", io["write_duration_s"])
    s = stage(spec, "storage", age)
    r = depolarizing(io["read_depolarizing_p"]) @ stage(spec, "read", io["read_duration_s"])
    exponent = rate(spec["rates"]["erasure"], spec["temperatures_K"]["storage"])*age
    for name in ("write", "read"):
        exponent += rate(spec["rates"]["erasure"], spec["temperatures_K"][name])*io[name+"_duration_s"]
    return r @ s @ w, io["eta_write"]*io["eta_read"]*math.exp(-exponent)

def action(superop, rho):
    return (superop @ np.asarray(rho).reshape(-1, order="F")).reshape((2, 2), order="F")

def choi_from_super(superop, eta=None):
    d = 2 if eta is None else 3
    j = np.zeros((2*d, 2*d), complex)
    for a in range(2):
        for b in range(2):
            unit = np.zeros((2, 2), complex); unit[a, b] = 1
            out = action(superop, unit)
            if eta is not None:
                erasure = np.zeros((3, 3), complex)
                erasure[:2, :2] = eta*out
                erasure[2, 2] = (1-eta)*np.trace(unit)
                out = erasure
            j += np.kron(unit, out)
    return j

def state_probes():
    states = []
    for vector in ([1,0],[0,1],[1,1],[1,-1],[1,1j],[1,-1j]):
        v = np.asarray(vector, complex); v /= np.linalg.norm(v)
        states.append(np.outer(v, v.conj()))
    return states

def average_fidelity(superop):
    return float(np.mean([np.trace(rho @ action(superop, rho)).real for rho in state_probes()]))

def evaluate(spec, times):
    return [{"age_s": age, "superoperator": s, "choi": choi_from_super(s, eta),
             "conditional_choi": choi_from_super(s), "average_fidelity": average_fidelity(s),
             "acceptance": eta} for age in times for s, eta in [superoperator(spec, age)]]

def parse_fidelities(path, cells, base):
    data = np.loadtxt(path, delimiter=";", comments="#")
    if data.shape != (3, 6*cells) or not np.isfinite(data).all():
        raise ValueError("Reference data layout mismatch")
    values = np.full((6, cells), np.nan)
    for infidelity, basis_value, cell_value in data.T:
        if int(basis_value) != basis_value or int(cell_value) != cell_value:
            raise ValueError("Noninteger index")
        b, c = int(basis_value), int(cell_value)-base
        if not 0 <= b < 6 or not 0 <= c < cells or not 0 <= infidelity <= 1 or not np.isnan(values[b,c]):
            raise ValueError("Invalid reference index")
        values[b,c] = 1-infidelity
    if np.isnan(values).any():
        raise ValueError("Incomplete reference input")
    return values
