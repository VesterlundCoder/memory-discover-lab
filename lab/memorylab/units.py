"""Internal units: seconds, Hz, tesla, kelvin, angstrom; tensors retain a frame."""
import math
from .common import finite

SCALES = {
    "s": ("time", 1), "ms": ("time", 1e-3), "us": ("time", 1e-6),
    "µs": ("time", 1e-6), "ns": ("time", 1e-9),
    "Hz": ("frequency", 1), "kHz": ("frequency", 1e3),
    "MHz": ("frequency", 1e6), "GHz": ("frequency", 1e9),
    "rad/s": ("frequency", 1 / (2 * math.pi)),
    "T": ("field", 1), "mT": ("field", 1e-3), "G": ("field", 1e-4),
    "angstrom": ("length", 1), "nm": ("length", 10),
    "K": ("temperature", 1), "1": ("dimensionless", 1),
    "u": ("mass", 1), "eV": ("energy", 1), "hartree": ("energy", 27.211386245981),
}


def convert(value, source, target):
    if source not in SCALES or target not in SCALES:
        raise ValueError("Unsupported unit; do not infer units from a column name")
    a, b = SCALES[source], SCALES[target]
    if a[0] != b[0]:
        raise ValueError("Dimensionally inconsistent conversion")
    return finite(value, "value") * a[1] / b[1]


def isotope_id(symbol, mass, state="ground"):
    if not isinstance(mass, int) or isinstance(mass, bool) or mass < 1:
        raise ValueError("Isotope mass number must be a positive integer")
    if state != "ground":
        return f"{symbol}-{mass}:{state}"
    return f"{symbol}-{mass}"
