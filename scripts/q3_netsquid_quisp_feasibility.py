"""Q3: NetSquid and QuISP adapter feasibility analysis.

This script documents the feasibility of adding NetSquid and QuISP adapters
to WestQuant. It does not run any simulations; it analyzes the API, licence,
and formalism compatibility.

Usage:
    python scripts/q3_netsquid_quisp_feasibility.py
"""
import json
from pathlib import Path


def main():
    print("=== Q3: NetSquid and QuISP adapter feasibility ===")
    print()

    analysis = {
        "study": "q3_netsquid_quisp_feasibility",
        "description": "Feasibility analysis for NetSquid and QuISP adapters",

        "netsquid": {
            "name": "NetSquid",
            "version": "1.0+ (latest)",
            "licence": "Free for academic/non-commercial use; requires forum registration. "
                       "Not on public PyPI; installed from https://pypi.netsquid.org with credentials. "
                       "Adapter code that imports NetSquid can be distributed, but users need their own "
                       "NetSquid account to install it.",
            "api": {
                "event_engine": "PyDynAA (Cython-accelerated discrete-event engine)",
                "state_formalism": "Supports both stabilizer and density-matrix formalisms",
                "memory_component": "QuantumMemory component with built-in noise models",
                "channel_application": "Custom models can be attached to components",
            },
            "compatibility": {
                "density_matrix": "YES — NetSquid supports density-matrix formalism, "
                                  "compatible with WestQuant's Kraus operators",
                "erasure_channel": "YES — NetSquid can model loss/erasure as a separate outcome",
                "event_timing": "YES — PyDynAA provides the same event-driven timing as SeQUeNCe",
                "noise_double_counting": "MUST DISABLE — NetSquid's built-in memory noise models "
                                         "must be disabled to avoid double-counting with WestQuant's channel",
            },
            "adapter_requirements": [
                "Create a NetSquid QuantumMemory component that holds the density matrix passively",
                "Attach a custom model that applies the WestQuant channel at retrieval time",
                "Disable all built-in noise models (T1, T2, dephasing)",
                "Use PyDynAA's event scheduler for timing",
                "Feed the same pre-generated random trace as SeQUeNCe and QuNetSim",
            ],
            "feasibility": "HIGH — NetSquid's density-matrix formalism and component architecture "
                           "are directly compatible with WestQuant's channel model. The main work is "
                           "creating a custom memory component and disabling built-in noise.",
            "blockers": [
                "NetSquid is not on public PyPI — users need a forum account",
                "Licence may restrict commercial use",
                "Cannot be tested in CI without credentials",
            ],
            "estimated_effort": "2-3 days for a minimal adapter; 1 week for full benchmark integration",
        },

        "quisp": {
            "name": "QuISP",
            "version": "latest (GitHub sfc-aqua/quisp)",
            "licence": "Open source (MIT-style)",
            "api": {
                "event_engine": "OMNeT++ (C++ discrete-event framework)",
                "state_formalism": "Primarily error-basis (stabilizer-like); density-matrix mode exists "
                                   "but is limited to ~56 qubits",
                "memory_component": "QNIC (Quantum Network Interface Card) with per-qubit memory",
                "channel_application": "Error models attached to channels and components",
            },
            "compatibility": {
                "density_matrix": "PARTIAL — QuISP can output density matrices but primarily operates "
                                  "in the error basis. The WestQuant channel's Kraus operators would "
                                  "need to be translated to QuISP's error model.",
                "erasure_channel": "PARTIAL — QuISP supports non-Pauli errors including loss, but the "
                                   "erasure channel's 3-outcome measurement may not map cleanly to "
                                   "QuISP's error tracking.",
                "event_timing": "YES — OMNeT++ provides event-driven timing",
                "noise_double_counting": "MUST DISABLE — QuISP's built-in error models must be "
                                         "disabled or set to zero",
            },
            "adapter_requirements": [
                "Build QuISP from source with OMNeT++ and Eigen",
                "Create a custom QuISP module that applies the WestQuant channel",
                "Translate Kraus operators to QuISP's error-basis representation",
                "Or: use QuISP's density-matrix mode (limited to small systems)",
                "Disable all built-in error models",
            ],
            "feasibility": "MEDIUM — QuISP's error-basis formalism is not directly compatible with "
                           "WestQuant's density-matrix channel. A density-matrix mode exists but is "
                           "limited. The adapter would need either a formalism translation layer or "
                           "a restriction to density-matrix mode.",
            "blockers": [
                "QuISP requires OMNeT++ (C++ framework) — heavy dependency",
                "Error-basis formalism may not support general CPTP maps",
                "Installation is complex (OMNeT++ + Eigen + QuISP build)",
                "Python API is limited — QuISP is primarily C++",
            ],
            "estimated_effort": "1-2 weeks for a minimal adapter; 3-4 weeks for full benchmark integration",
        },

        "recommendation": {
            "priority": "NetSquid first, QuISP second",
            "rationale": "NetSquid's density-matrix formalism is directly compatible with WestQuant's "
                        "channel model. QuISP's error-basis formalism requires a translation layer that "
                        "may not preserve the channel's full physics. NetSquid also has a Python API, "
                        "while QuISP is primarily C++.",
            "next_steps": [
                "1. Register for a NetSquid forum account",
                "2. Install NetSquid in a test environment",
                "3. Prototype a minimal adapter that creates a passive memory and applies a channel",
                "4. Run the existing benchmark config with the NetSquid adapter",
                "5. Compare results against SeQUeNCe and QuNetSim",
                "6. For QuISP: evaluate whether the density-matrix mode supports the erasure channel",
                "7. If yes, prototype a QuISP adapter; if no, defer QuISP to a future release",
            ],
        },

        "pyproject_extras": {
            "netsquid": {
                "description": "NetSquid adapter (requires NetSquid forum account)",
                "dependencies": ["netsquid>=1.0"],
                "install_command": "pip install --extra-index-url https://pypi.netsquid.org 'westquant-memory-lab[netsquid]'",
                "note": "Users must have a NetSquid forum account to install NetSquid itself",
            },
            "quisp": {
                "description": "QuISP adapter (requires OMNeT++ and Eigen)",
                "dependencies": [],
                "install_command": "Not available via pip — build from source",
                "note": "QuISP requires OMNeT++ and Eigen; not pip-installable",
            },
        },
    }

    output_path = Path("results/q3_netsquid_quisp_feasibility.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(analysis, f, indent=2)
    print(f"Analysis saved to {output_path}")

    print()
    print("=== NetSquid ===")
    print(f"  Feasibility: {analysis['netsquid']['feasibility']}")
    print(f"  Effort: {analysis['netsquid']['estimated_effort']}")
    print(f"  Blockers: {len(analysis['netsquid']['blockers'])}")
    for b in analysis['netsquid']['blockers']:
        print(f"    - {b}")

    print()
    print("=== QuISP ===")
    print(f"  Feasibility: {analysis['quisp']['feasibility']}")
    print(f"  Effort: {analysis['quisp']['estimated_effort']}")
    print(f"  Blockers: {len(analysis['quisp']['blockers'])}")
    for b in analysis['quisp']['blockers']:
        print(f"    - {b}")

    print()
    print("=== Recommendation ===")
    print(f"  Priority: {analysis['recommendation']['priority']}")
    print(f"  Rationale: {analysis['recommendation']['rationale']}")


if __name__ == "__main__":
    main()
