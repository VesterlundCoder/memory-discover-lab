"""Command line entry point, wqml / python -m memorylab."""
import argparse
import importlib.metadata
import json
import shutil
import sys
from pathlib import Path
from .common import environment, optional_import, read_json, write_json
from .catalog import Catalog, expand_candidates
from .datasets import synchronize
from .models import evaluate
from .runner import run


def doctor():
    capabilities = {}
    for name in ("numpy", "scipy", "qutip", "pyscf", "pycce", "ase", "maxwellbloch", "pynmrstar", "openpyxl"):
        try:
            optional_import(name)
            capabilities[name] = {"import_ok": True, "version": importlib.metadata.version(name)}
        except Exception as e:
            capabilities[name] = {"import_ok": False, "error": f"{type(e).__name__}: {e}"}
    capabilities["orca"] = {"binary": shutil.which("orca")}
    capabilities["quantum_espresso"] = {"binary": shutil.which("pw.x")}
    return {"environment": environment(), "capabilities": capabilities,
            "import_checks_only": True,
            "integration_test_command": "python -m unittest discover -s tests -v"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    commands = ap.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    p = commands.add_parser("datasets")
    p.add_argument("plan"); p.add_argument("--root", default="data")
    p.add_argument("--catalog", default="data/catalog.sqlite"); p.add_argument("--refresh", action="store_true")
    p = commands.add_parser("catalog")
    p.add_argument("path"); p.add_argument("--table", choices=["artifacts", "candidates", "observations"])
    p.add_argument("--out")
    p = commands.add_parser("generate")
    p.add_argument("plan"); p.add_argument("--out", default="data/generated_candidates.json")
    p = commands.add_parser("run")
    p.add_argument("study"); p.add_argument("--out", default="runs/study"); p.add_argument("--dry-run", action="store_true")
    p = commands.add_parser("simulate")
    p.add_argument("profile"); p.add_argument("--times", default="0,0.001,0.01,0.1,1")
    p.add_argument("--backend", choices=["analytic", "qutip"], default="analytic")
    p.add_argument("--out", default="runs/channel_samples.json")
    p = commands.add_parser("export")
    p.add_argument("samples"); p.add_argument("--out", default="runs/network_device.json")
    p.add_argument("--allow-hypothetical", action="store_true")
    p = commands.add_parser("network")
    p.add_argument("left"); p.add_argument("right"); p.add_argument("workload")
    p.add_argument("--seed", type=int, default=20261010)
    p.add_argument("--allow-hypothetical", action="store_true"); p.add_argument("--out", default="runs/network.json")
    p = commands.add_parser("electronic")
    p.add_argument("candidate"); p.add_argument("recipe"); p.add_argument("--cache", default="cache/electronic")
    p.add_argument("--out", default="runs/electronic.json")
    p = commands.add_parser("external")
    p.add_argument("kind", choices=["orca", "qe"]); p.add_argument("candidate"); p.add_argument("recipe")
    p.add_argument("--directory", default="runs/external"); p.add_argument("--execute", action="store_true")
    p = commands.add_parser("couplings")
    p.add_argument("kind", choices=["orca", "qe"]); p.add_argument("output_file")
    p.add_argument("--options"); p.add_argument("--out", default="data/couplings.json")
    p = commands.add_parser("propagate")
    p.add_argument("config"); p.add_argument("--out", default="runs/propagation")
    p = commands.add_parser("extract-xlsx")
    p.add_argument("workbook"); p.add_argument("sheets", nargs="+"); p.add_argument("--out", default="data/sheets")
    p = commands.add_parser("fit")
    p.add_argument("curve"); p.add_argument("--out", default="runs/fit.json")
    p = commands.add_parser("baseline")
    p.add_argument("profile"); p.add_argument("reference"); p.add_argument("--out", default="runs/baseline.json")
    p = commands.add_parser("pipeline")
    p.add_argument("config"); p.add_argument("--out", default="runs/lab"); p.add_argument("--skip-fetch", action="store_true")
    p = commands.add_parser("reproduce")
    p.add_argument("config"); p.add_argument("--out", default="baselines/teller2025")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--reviewed-bundle", help="Replay licensed numerical data; unbundled paper bytes are not reverified")
    p = commands.add_parser("sequence")
    p.add_argument("left"); p.add_argument("right"); p.add_argument("workload")
    p.add_argument("--seed", type=int, default=20261010); p.add_argument("--out", default="runs/sequence.json")
    args = ap.parse_args()
    try:
        if args.command == "doctor":
            result = doctor()
        elif args.command == "datasets":
            catalog = Catalog(args.catalog)
            try:
                result = synchronize(read_json(args.plan), args.root, catalog, args.refresh)
            finally:
                catalog.close()
        elif args.command == "catalog":
            catalog = Catalog(args.path)
            try:
                result = catalog.rows(args.table) if args.table else catalog.summary()
            finally:
                catalog.close()
            if args.out:
                write_json(args.out, result)
        elif args.command == "generate":
            result = {"candidates": expand_candidates(read_json(args.plan))}
            write_json(args.out, result)
            result = {"candidate_count": len(result["candidates"]), "output": args.out}
        elif args.command == "run":
            result = run(read_json(args.study), args.out, args.dry_run)
        elif args.command == "simulate":
            samples = evaluate(read_json(args.profile), [float(x) for x in args.times.split(",")], args.backend)
            write_json(args.out, {"samples": [c.serialize() for c in samples]})
            result = {"samples": len(samples), "output": args.out}
        elif args.command == "export":
            from .network import export
            result = export(read_json(args.samples)["samples"], args.out, args.allow_hypothetical)
        elif args.command == "network":
            from .network import load_device, link_benchmark
            result = link_benchmark(load_device(args.left, args.allow_hypothetical),
                                    load_device(args.right, args.allow_hypothetical),
                                    read_json(args.workload), args.seed)
            write_json(args.out, result)
        elif args.command == "electronic":
            from .backends import electronic
            result = electronic(read_json(args.candidate), read_json(args.recipe), args.cache)
            write_json(args.out, result)
        elif args.command == "external":
            from .backends import prepare_external, execute_external
            result = prepare_external(args.kind, read_json(args.candidate), read_json(args.recipe), args.directory)
            if args.execute:
                result = execute_external(result)
                write_json(Path(args.directory)/"result.json", result)
        elif args.command == "couplings":
            from .backends import import_couplings
            result = import_couplings(args.kind, args.output_file, read_json(args.options) if args.options else None)
            write_json(args.out, result)
        elif args.command == "propagate":
            from .backends import maxwell_bloch
            result = maxwell_bloch(read_json(args.config), args.out)
        elif args.command == "extract-xlsx":
            from .importers import extract_workbook
            result = extract_workbook(args.workbook, args.out, args.sheets)
        elif args.command == "fit":
            from .calibration import fit_exponential
            curve = read_json(args.curve)
            result = fit_exponential(curve["times_s"], curve["pure_coherence_amplitude"],
                                     curve["standard_errors"], curve["conditions"], curve["provenance"])
            write_json(args.out, result)
        elif args.command == "baseline":
            from .calibration import compare_baseline
            result = compare_baseline(read_json(args.profile), read_json(args.reference))
            write_json(args.out, result)
        elif args.command == "reproduce":
            from .baseline_workflow import run_baseline
            result = run_baseline(read_json(args.config), args.out, args.offline, args.reviewed_bundle)
        elif args.command == "sequence":
            from .sequence_adapter import run_link
            from .network import load_device
            result = run_link(load_device(args.left), load_device(args.right), read_json(args.workload), args.seed)
            write_json(args.out, result)
        else:
            from .pipeline import pipeline
            result = pipeline(read_json(args.config), args.out, args.skip_fetch)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        if isinstance(result, dict) and (result.get("all_success") is False or
                                        result.get("status") in {"fail", "model_mismatch", "dataset_failure", "simulation_failure"}):
            sys.exit(2)
    except (ValueError, RuntimeError, KeyError, OSError, ImportError) as e:
        ap.exit(2, f"{type(e).__name__}: {e}\n")


if __name__ == "__main__":
    main()
