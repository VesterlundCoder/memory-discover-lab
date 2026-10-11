"""Bundled example profiles for quickstart and testing.

These small example JSON profiles are packaged with the wheel so that
`pip install westquant-memory-lab` provides working examples without
requiring a checkout of the source repository.

Usage:
    import os
    from memorylab import examples
    profile_path = os.path.join(
        os.path.dirname(examples.__file__),
        "atomic_ensemble_profile.json"
    )
"""
import os

EXAMPLES_DIR = os.path.dirname(__file__)

AVAILABLE_EXAMPLES = [
    "atomic_ensemble_profile.json",
    "defect_spin_profile.json",
    "rare_earth_solid_profile.json",
    "molecular_spin_profile.json",
    "network_workload.json",
    "pipeline.json",
]

def example_path(name):
    """Return the full path to a bundled example file."""
    p = os.path.join(EXAMPLES_DIR, name)
    if not os.path.exists(p):
        raise FileNotFoundError(f"Example not found: {name}. Available: {AVAILABLE_EXAMPLES}")
    return p
