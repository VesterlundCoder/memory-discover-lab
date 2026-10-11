"""WestQuant Memory Discovery Lab — Discovery Screening v1.

Evidence-tiered triage of every candidate and combination available from the
project's existing data sources, to shortlist possible future quantum-memory
candidates. Produces bounded physical estimates, evidence levels, missing-data
checklists and network-requirement maps.

This package does NOT modify or bypass production guards. New code calls them.
"""
from .inventory import run_inventory


def dispatch_screen(phase, config_path, output_dir):
    """Dispatch a screening phase by name.

    phases: inventory | tier1 | pilot | calibrate | tier2 | tier2b |
            tier3 | tier4 | tier5 | rank | report
    """
    from ..common import read_json
    config = read_json(config_path) if config_path else {}

    if phase == "inventory":
        return run_inventory(config, output_dir)
    elif phase == "tier1":
        from .tier1 import run_tier1
        return run_tier1(config, output_dir)
    elif phase == "pilot":
        from .tier2_cce import run_pilot
        return run_pilot(config, output_dir)
    elif phase == "calibrate":
        from .calibration import run_calibration
        return run_calibration(config, output_dir)
    elif phase == "tier2":
        from .tier2_cce import run_tier2_production
        return run_tier2_production(config, output_dir)
    elif phase == "tier3":
        from .tier3 import run_tier3
        return run_tier3(config, output_dir)
    elif phase == "tier4":
        from .tier4 import run_tier4
        return run_tier4(config, output_dir)
    elif phase == "tier5":
        from .tier5_network import run_tier5
        return run_tier5(config, output_dir)
    elif phase == "rank":
        from .rank import run_rank
        return run_rank(config, output_dir)
    elif phase == "report":
        from .report import run_report
        return run_report(config, output_dir)
    else:
        raise ValueError(f"Unknown screening phase: {phase}")
