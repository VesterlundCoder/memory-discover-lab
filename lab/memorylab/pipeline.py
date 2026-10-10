"""One data -> catalog -> candidate -> electronics -> memory -> network workflow."""
from pathlib import Path
from .catalog import Catalog, expand_candidates
from .calibration import bind_observations
from .datasets import synchronize
from .backends import electronic
from .common import digest, read_json, write_json
from .runner import run
from .network import export


def pipeline(config, output, skip_fetch=False):
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    catalog = Catalog(root/"catalog.sqlite")
    results = {"config_hash": digest(config), "output": str(root), "steps": {}}
    try:
        if config.get("datasets") and not skip_fetch:
            result = synchronize(config["datasets"], root/"data", catalog)
            results["steps"]["datasets"] = result
            if not result["all_success"]:
                results["status"] = "dataset_failure"
                write_json(root/"pipeline_result.json", results)
                return results
        candidates = expand_candidates(config["candidates"]) if config.get("candidates") else []
        for row in candidates:
            catalog.put("candidates", row)
        write_json(root/"generated_candidates.json", {"candidates": candidates})
        results["steps"]["candidates"] = {"generated": len(candidates)}
        if config.get("electronic"):
            electronic_config = config["electronic"]
            budget = electronic_config["max_candidates"]
            selected = candidates[:budget]
            calculations = []
            # Expensive steps are bounded independently of the memory parameter grid.
            for candidate in selected:
                result = electronic(candidate, electronic_config["recipe"], root/"electronic_cache")
                calculations.append({"candidate_id": candidate["id"], "result": result})
            write_json(root/"electronic_results.json", calculations)
            results["steps"]["electronic"] = {"calculated": len(calculations),
                                             "remaining_uncomputed": len(candidates)-len(calculations)}
        if config.get("study"):
            study = read_json(config["study"]) if isinstance(config["study"], str) else config["study"]
            for model in study["models"]:
                if model.get("bindings"):
                    model["profile"] = bind_observations(model["profile"], model["bindings"], catalog)
            results["steps"]["study"] = run(study, root/"runs")
            if not results["steps"]["study"]["all_success"]:
                results["status"] = "simulation_failure"
                write_json(root/"pipeline_result.json", results)
                return results
            exported = []
            for run_id in read_json(root/"runs"/"manifest.json")["job_ids"]:
                path = root/"runs"/run_id/"channels.json"
                target = root/"network"/(path.parent.name+".json")
                result = export(read_json(path)["samples"], target,
                                allow_hypothetical=config.get("allow_hypothetical_network", False))
                exported.append(result)
            results["steps"]["network_exports"] = exported
        results["steps"]["catalog"] = catalog.summary()
        results["status"] = "success"
        write_json(root/"pipeline_result.json", results)
        return results
    finally:
        catalog.close()
