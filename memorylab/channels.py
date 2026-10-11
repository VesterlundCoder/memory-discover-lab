"""Quantum channels in column-vectorization convention, including an explicit erasure flag."""
from dataclasses import dataclass
import math
import numpy as np
from .common import finite, NumericalFailure

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], complex)
Y = np.array([[0, -1j], [1j, 0]], complex)
Z = np.diag([1, -1]).astype(complex)


def encode(a):
    a = np.asarray(a, dtype=complex)
    return {"real": a.real.tolist(), "imag": a.imag.tolist()}


def decode(a):
    return np.asarray(a["real"], float) + 1j*np.asarray(a["imag"], float)


def choi(kraus):
    vectors = [np.asarray(k, complex).reshape(-1, order="F") for k in kraus]
    return sum(np.outer(v, v.conj()) for v in vectors)


def check_cptp(kraus, tolerance=1e-9):
    if not kraus or len({k.shape for k in kraus}) != 1:
        raise NumericalFailure("Empty or incompatible Kraus list")
    if any(not np.isfinite(k).all() or k.ndim != 2 for k in kraus):
        raise NumericalFailure("Nonfinite/nonmatrix Kraus operator")
    output_dim, input_dim = kraus[0].shape
    tp = sum(k.conj().T @ k for k in kraus)
    error = float(np.max(np.abs(tp - np.eye(input_dim))))
    eigmin = float(np.linalg.eigvalsh(choi(kraus)).min())
    if error > tolerance or eigmin < -tolerance:
        raise NumericalFailure(f"Channel is not CPTP: TP error={error}, Choi minimum={eigmin}")
    return {"input_dimension": input_dim, "output_dimension": output_dim,
            "tp_max_error": error, "choi_min_eigenvalue": eigmin}


def compress(kraus):
    output_dim, input_dim = kraus[0].shape
    vals, vectors = np.linalg.eigh(choi(kraus))
    if vals.min() < -1e-9:
        raise NumericalFailure("Nonpositive Choi matrix")
    return [(math.sqrt(float(v))*vectors[:, i]).reshape((output_dim, input_dim), order="F")
            for i, v in enumerate(vals) if v > 1e-14]


def compose(after, before):
    """after o before, with rank compression to avoid exponential Kraus-list growth."""
    return compress([a @ b for a in after for b in before])


def apply(kraus, rho):
    rho = np.asarray(rho, complex)
    if rho.shape != (kraus[0].shape[1],)*2:
        raise ValueError("Input state has incompatible dimensions")
    return sum(k @ rho @ k.conj().T for k in kraus)


def validate_state(rho):
    rho = np.asarray(rho, complex)
    if rho.ndim != 2 or rho.shape[0] != rho.shape[1] or not np.isfinite(rho).all():
        raise ValueError("Density matrix must be square and finite")
    if np.max(np.abs(rho-rho.conj().T)) > 1e-9 or abs(np.trace(rho)-1) > 1e-9:
        raise ValueError("Density matrix must be Hermitian with trace one")
    if np.linalg.eigvalsh(rho).min() < -1e-9:
        raise ValueError("Density matrix is not positive")
    return rho


def thermal_amplitude_damping(duration_s, total_rate_s_inv, excited_population=0):
    finite(duration_s, "duration_s", 0)
    finite(total_rate_s_inv, "total_rate_s_inv", 0)
    e = finite(excited_population, "excited_population", 0, 1)
    b = math.exp(-duration_s*total_rate_s_inv)
    s = math.sqrt(1-b)
    return [math.sqrt(1-e)*np.diag([1, math.sqrt(b)]).astype(complex),
            math.sqrt(1-e)*np.array([[0, s], [0, 0]], complex),
            math.sqrt(e)*np.diag([math.sqrt(b), 1]).astype(complex),
            math.sqrt(e)*np.array([[0, 0], [s, 0]], complex)]


def dephasing(coherence):
    """rho_01 -> coherence*rho_01; coherence is PURE dephasing, not total T2."""
    value = complex(coherence)
    mag = abs(value)
    if not np.isfinite([value.real, value.imag]).all() or mag > 1+1e-10:
        raise NumericalFailure("Coherence outside the CPTP pure-dephasing disk")
    mag = min(mag, 1.0)
    rotation = np.diag([1, np.exp(-1j*np.angle(value))])
    return [math.sqrt((1+mag)/2)*rotation, math.sqrt((1-mag)/2)*rotation @ Z]


def depolarizing(probability):
    """E(rho)=(1-p)rho+p*I/2, not a Pauli-error-probability convention."""
    p = finite(probability, "depolarizing_probability", 0, 1)
    return [math.sqrt(1-3*p/4)*I2, math.sqrt(p/4)*X,
            math.sqrt(p/4)*Y, math.sqrt(p/4)*Z]


@dataclass
class MemoryChannel:
    conditional_kraus: list
    success_probability: float
    metadata: dict

    def __post_init__(self):
        self.conditional_kraus = [np.asarray(k, complex) for k in self.conditional_kraus]
        if any(k.shape != (2, 2) for k in self.conditional_kraus):
            raise ValueError("Conditional channel must act on one qubit")
        finite(self.success_probability, "success_probability", 0, 1)
        check_cptp(self.conditional_kraus)

    def full_kraus(self):
        p = self.success_probability
        result = []
        for k in self.conditional_kraus:
            out = np.zeros((3, 2), complex)
            out[:2, :] = math.sqrt(p)*k
            result.append(out)
        result += [np.array([[0, 0], [0, 0], [math.sqrt(1-p), 0]], complex),
                   np.array([[0, 0], [0, 0], [0, math.sqrt(1-p)]], complex)]
        return result

    def metrics(self):
        entanglement = float(sum(abs(np.trace(k))**2 for k in self.conditional_kraus)/4)
        average = (2*entanglement+1)/3
        return {"conditional_average_fidelity": average if self.success_probability > 0 else None,
                "conditional_entanglement_fidelity": entanglement if self.success_probability > 0 else None,
                "retrieval_success_probability": self.success_probability,
                "unconditional_target_overlap": average*self.success_probability,
                "state_independent_heralding_assumed": True}

    def serialize(self):
        return {"schema": "westquant_memory_channel_v1", "basis_input": ["0", "1"],
                "basis_output": ["0", "1", "erasure"], "vectorization": "column",
                "kraus": [encode(k) for k in self.full_kraus()],
                "conditional_kraus": [encode(k) for k in self.conditional_kraus],
                "choi": encode(choi(self.full_kraus())), "metrics": self.metrics(),
                "cptp": check_cptp(self.full_kraus()), "metadata": self.metadata,
                "validated_for_hardware": False}

    @classmethod
    def from_serialized(cls, row):
        return cls([decode(k) for k in row["conditional_kraus"]],
                   row["metrics"]["retrieval_success_probability"], row["metadata"])
