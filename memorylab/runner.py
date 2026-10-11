"""Enumerated studies with process timeouts, immutable config IDs and checkpoint/resume."""
import copy
import hashlib
import itertools
import json
import os
import signal
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .common import canonical, digest, environment, now, read_json, seed, write_json
from . import __version__


def source_fingerprint():
    sha = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        sha.update(path.name.encode())
        sha.update(path.read_bytes())
    return sha.hexdigest()


def assign(profile, dotted_key, value):
    keys = dotted_key.split(".")
    target = profile
    for key in keys[:-1]:
        if key not in target or not isinstance(target[key], dict):
            raise ValueError("Unknown grid path " + dotted_key)
        target = target[key]
    if keys[-1] not in target:
        raise ValueError("Unknown grid field " + dotted_key)
    target[keys[-1]] = value


def enumerate_jobs(study):
    for key in ("study_id", "stage", "models", "times_s", "replicates", "master_seed", "resources"):
        if key not in study:
            raise ValueError("Study lacks " + key)
    reps = study["replicates"]
    if not isinstance(reps, int) or isinstance(reps, bool) or reps < 1:
        raise ValueError("replicates must be a positive integer")
    if not isinstance(study["models"], list) or not study["models"]:
        raise ValueError("Study requires at least one model")
    if study["stage"] not in {"software_smoke", "baseline", "exploration", "discovery"}:
        raise ValueError("Unknown research stage")
    if study["stage"] == "discovery":
        gate = study.get("baseline_reproduction")
        if not gate or gate.get("status") != "pass" or not gate.get("report_sha256"):
            raise ValueError("Discovery stage requires a baseline reproduction report and checksum")
        if hashlib.sha256(Path(gate["report_path"]).read_bytes()).hexdigest() != gate["report_sha256"]:
            raise ValueError("Baseline reproduction report hash mismatch")
        if read_json(gate["report_path"]).get("status") != "pass":
            raise ValueError("Baseline reproduction report did not pass")
    grid = study.get("grid", {})
    if any(not isinstance(v, list) or not v for v in grid.values()):
        raise ValueError("Every grid dimension needs a nonempty value list")
    for name in ("timeout_s", "max_workers", "max_runs"):
        if name not in study["resources"] or study["resources"][name] <= 0:
            raise ValueError("Missing/invalid resource bound " + name)
    env = environment()
    source = source_fingerprint()
    jobs = []
    for model in study["models"]:
        if model["task"] != "memory":
            raise ValueError("Study runner currently supports memory tasks; electronics are cached separately")
        for values in itertools.product(*grid.values()) if grid else [()]:
            profile = copy.deepcopy(model["profile"])
            parameters = dict(zip(grid, values))
            for key, value in parameters.items():
                assign(profile, key, value)
            for replicate in range(reps):
                physical_id = digest({"profile": profile, "times_s": study["times_s"],
                                      "model_id": model["id"], "parameters": parameters})
                streams = {name: seed(study["master_seed"], [study["study_id"], physical_id], name, replicate)
                           for name in ("bath", "parameter_uncertainty", "network")}
                profile["simulation_seed"] = streams["bath"]
                for backend in study.get("backends", ["analytic"]):
                    config = {"study_id": study["study_id"], "stage": study["stage"],
                              "model_id": model["id"], "profile": profile,
                              "parameters": parameters, "times_s": study["times_s"],
                              "replicate": replicate, "backend": backend, "seeds": streams,
                              "gates": study.get("gates", {}), "network_workload": study.get("network_workload"),
                              "software_version": __version__, "source_sha256": source,
                              "environment": env}
                    config_hash = digest(config)
                    jobs.append({"run_id": config_hash[:24], "config_hash": config_hash,
                                 "config": config, "timeout_s": study["resources"]["timeout_s"]})
                    if len(jobs) > study["resources"]["max_runs"]:
                        raise ValueError("Enumerated study exceeds max_runs")
    if len({j["run_id"] for j in jobs}) != len(jobs):
        raise ValueError("Duplicate configurations; remove duplicate grid values/model IDs")
    return jobs


def execute_job(job, root):
    directory = Path(root)/job["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    result_path = directory/"result.json"
    if result_path.exists():
        previous = read_json(result_path)
        if previous.get("config_hash") != job["config_hash"]:
            raise ValueError("Checkpoint identity mismatch")
        # All terminal statuses are immutable checkpoints. Retry under a new configuration.
        return {**previous, "resumed_from_checkpoint": True}
    write_json(directory/"job.json", job)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)+os.pathsep+env.get("PYTHONPATH", "")
    started = time.monotonic()
    with (directory/"worker.log").open("w") as log:
        process = subprocess.Popen([sys.executable, "-m", "memorylab.worker",
                                    str((directory/"job.json").resolve()),
                                    str(result_path.resolve())],
                                   stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            code = process.wait(timeout=job["timeout_s"])
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait()
            code = None
        except BaseException:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait()
            raise
    if not result_path.exists():
        result = {"run_id": job["run_id"], "config_hash": job["config_hash"],
                  "method": job["config"]["backend"], "parameters": job["config"]["parameters"],
                  "seeds": job["config"]["seeds"], "environment": job["config"]["environment"],
                  "status": "timeout" if code is None else "runtime_error",
                  "error": "Worker exceeded timeout" if code is None else f"Worker exited {code}; see worker.log",
                  "metrics": [], "runtime_s": time.monotonic()-started,
                  "raw_path": str(directory.resolve())}
        write_json(result_path, result)
    return read_json(result_path)


def run(study, output, dry_run=False):
    jobs = enumerate_jobs(study)
    if dry_run:
        return {"study_id": study["study_id"], "enumerated_run_count": len(jobs),
                "model_count": len(study["models"]), "backends": study.get("backends", ["analytic"]),
                "replicates": study["replicates"], "run_ids": [j["run_id"] for j in jobs]}
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    write_json(root/"study.json", study)
    write_json(root/"manifest.json", {"at": now(), "enumerated_run_count": len(jobs),
                                     "job_ids": [j["run_id"] for j in jobs]})
    workers = min(int(study["resources"]["max_workers"]), 8)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda job: execute_job(job, root), jobs))
    counts = dict(Counter(row["status"] for row in results))
    summary = {"study_id": study["study_id"], "enumerated_run_count": len(jobs),
               "completed_runs": len(results), "statuses": counts,
               "all_success": all(row["status"] == "success" for row in results),
               "resumed_runs": sum(bool(row.get("resumed_from_checkpoint")) for row in results),
               "gate_pass_runs": sum(row.get("gates", {}).get("all_grid_points_pass", False) for row in results),
               "hardware_validated": False, "output": str(root)}
    write_json(root/"summary.json", summary)
    return summary
