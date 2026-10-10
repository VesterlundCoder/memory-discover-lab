"""Exact finite nuclear bath in the central-spin pure-dephasing approximation.

H is in Hz and propagators contain 2*pi. This includes the specified bath only,
not transverse central-spin relaxation, phonons or an optical interface.
"""
import math
import numpy as np
from scipy.linalg import expm
from scipy.constants import h, k
from .common import finite, UnsupportedPhysics


def operators(spin):
    spin = finite(spin, "nuclear spin", 0)
    if not float(2*spin).is_integer():
        raise ValueError("Spin must be integer or half-integer")
    m = np.arange(spin, -spin-1, -1)
    dimension = len(m)
    plus = np.zeros((dimension, dimension), complex)
    for j in range(1, dimension):
        plus[j-1, j] = math.sqrt(spin*(spin+1)-m[j]*(m[j]+1))
    minus = plus.conj().T
    return [(plus+minus)/2, (plus-minus)/(2j), np.diag(m).astype(complex)]


def embed(operator, index, dimensions):
    result = np.ones((1, 1), complex)
    for i, size in enumerate(dimensions):
        result = np.kron(result, operator if i == index else np.eye(size))
    return result


def bath_hamiltonians(spec):
    bath = spec["nuclei"]
    dimensions = [int(2*finite(n["spin_I"], "spin_I", 0)+1) for n in bath]
    size = math.prod(dimensions)
    if size > spec.get("max_dimension", 256):
        raise UnsupportedPhysics("Exact bath dimension exceeds configured bound; use a converged CCE")
    H = np.zeros((size, size), complex)
    coupling = np.zeros_like(H)
    ops = []
    for i, nucleus in enumerate(bath):
        if not nucleus.get("isotope_id") or nucleus.get("frame") != "lab":
            raise ValueError("Each nucleus needs isotope_id and explicit lab tensor frame")
        local = operators(nucleus["spin_I"])
        oi = [embed(op, i, dimensions) for op in local]
        ops.append(oi)
        frequencies = np.asarray(nucleus["zeeman_vector_Hz"], float)
        tensor = np.asarray(nucleus["hyperfine_Hz"], float)
        if tensor.shape != (3, 3) or frequencies.shape != (3,) or not np.isfinite(tensor).all() or not np.isfinite(frequencies).all():
            raise ValueError("Invalid hyperfine tensor or bath Zeeman vector")
        # Quantization axis is central S_z; central S_x/S_y terms are omitted by this model.
        H += sum(frequencies[a]*oi[a] for a in range(3))
        coupling += sum(tensor[2, a]*oi[a] for a in range(3))
        Q = np.asarray(nucleus.get("quadrupole_Hz", np.zeros((3, 3))), float)
        if Q.shape != (3, 3) or not np.isfinite(Q).all() or not np.allclose(Q, Q.T):
            raise ValueError("Quadrupole tensor must be finite, real and symmetric")
        H += sum(Q[a, b]*oi[a]@oi[b] for a in range(3) for b in range(3))
    for pair in spec.get("pairs", []):
        i, j = pair["sites"]
        if i == j or min(i, j) < 0 or max(i, j) >= len(bath):
            raise ValueError("Invalid bath pair")
        J = np.asarray(pair["coupling_Hz"], float)
        if J.shape != (3, 3) or not np.isfinite(J).all():
            raise ValueError("Invalid spin-spin tensor")
        H += sum(J[a, b]*ops[i][a]@ops[j][b] for a in range(3) for b in range(3))
    if not np.allclose(H, H.conj().T):
        raise ValueError("Non-Hermitian spin Hamiltonian")
    m0, m1 = spec["central_m"]
    finite(m0, "central_m[0]")
    finite(m1, "central_m[1]")
    if m0 == m1:
        raise ValueError("Logical central-spin projections must differ")
    return H, H+m0*coupling, H+m1*coupling


def exact_coherence(spec, times_s, temperature_K, pulses=0):
    temperature = finite(temperature_K, "temperature_K", 0)
    H, H0, H1 = bath_hamiltonians(spec)
    eigenvalues, vectors = np.linalg.eigh(H)
    if temperature == 0:
        weights = np.isclose(eigenvalues, eigenvalues.min(), atol=1e-10, rtol=0).astype(float)
    else:
        weights = np.exp(-h*(eigenvalues-eigenvalues.min())/(k*temperature))
    weights /= weights.sum()
    rho_bath = (vectors*weights) @ vectors.conj().T
    if not isinstance(pulses, int) or isinstance(pulses, bool) or pulses < 0:
        raise ValueError("pulses is the integer number of ideal CPMG pi pulses")
    result = []
    for time_s in times_s:
        finite(time_s, "time_s", 0)
        cuts = [0] + [time_s*(j+0.5)/pulses for j in range(pulses)] + [time_s] if pulses else [0, time_s]
        U0 = np.eye(len(H), dtype=complex)
        U1 = U0.copy()
        for segment, (left, right) in enumerate(zip(cuts[:-1], cuts[1:])):
            a, b = (H0, H1) if segment % 2 == 0 else (H1, H0)
            U0 = expm(-2j*math.pi*a*(right-left)) @ U0
            U1 = expm(-2j*math.pi*b*(right-left)) @ U1
        result.append(complex(np.trace(U0 @ rho_bath @ U1.conj().T)))
    return np.asarray(result)
