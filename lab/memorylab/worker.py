import sys
import time
from pathlib import Path
from .channels import encode
from .common import (BackendUnavailable, MissingData, NumericalFailure, UnsupportedPhysics,
                     read_json, write_json)
from .models import evaluate
from .network import MemoryDevice, link_benchmark


def compute(job, result_path):
    config = job["config"]
    started = time.monotonic()
    result = {"run_id": job["run_id"], "config_hash": job["config_hash"],
              "method": config["backend"], "model_id": config["model_id"],
              "parameters": config["parameters"], "seeds": config["seeds"],
              "environment": config["environment"], "source_sha256": config["source_sha256"],
              "status": "success", "metrics": [], "raw_path": str(Path(result_path).parent.resolve())}
    try:
        from .runner import source_fingerprint
        if source_fingerprint() != config["source_sha256"]:
            raise ValueError("Source files changed after enumeration; rerun the study with the new code")
        channels = evaluate(config["profile"], config["times_s"], config["backend"])
        raw = Path(result_path).parent/"channels.json"
        write_json(raw, {"samples": [c.serialize() for c in channels]})
        result["metrics"] = [{"storage_age_s": c.metadata["storage_age_s"], **c.metrics()} for c in channels]
        thresholds = config.get("gates", {})
        passed = [m["conditional_average_fidelity"] is not None and
                  m["conditional_average_fidelity"] >= thresholds.get("minimum_fidelity", 0)
                  and m["retrieval_success_probability"] >= thresholds.get("minimum_success", 0)
                  for m in result["metrics"]]
        prefix = []
        for age, ok in zip(config["times_s"], passed) if config["times_s"][0] == 0 else []:
            if not ok:
                break
            prefix.append(age)
        result["gates"] = {"all_grid_points_pass": all(passed),
                           "last_passing_prefix_grid_age_s": prefix[-1] if prefix else None,
                           "continuous_horizon_certified": False,
                           "right_censored": all(passed)}
        if config.get("network_workload"):
            device = MemoryDevice(channels, allow_hypothetical=True)
            result["network"] = link_benchmark(device, device, config["network_workload"],
                                                config["seeds"]["network"])
    except MissingData as e:
        result.update(status="missing_data", error=str(e))
    except UnsupportedPhysics as e:
        result.update(status="unsupported_physics", error=str(e))
    except BackendUnavailable as e:
        result.update(status="backend_unavailable", error=str(e))
    except NumericalFailure as e:
        result.update(status="numerical_failure", error=str(e))
    except (KeyError, TypeError, ValueError) as e:
        result.update(status="invalid_config", error=f"{type(e).__name__}: {e}")
    except Exception as e:
        result.update(status="runtime_error", error=f"{type(e).__name__}: {e}")
    result["runtime_s"] = time.monotonic()-started
    write_json(result_path, result)
    return result


if __name__ == "__main__":
    compute(read_json(sys.argv[1]), sys.argv[2])
