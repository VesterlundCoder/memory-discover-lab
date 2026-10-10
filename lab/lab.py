#!/usr/bin/env python3
"""Offline inventory and analytically validated qubit-channel starter lab.
No electronic-structure or material T2 prediction is implemented here.
"""
import argparse
import csv
import hashlib
import json
import math
import platform
from pathlib import Path

VERSION = "0.2.0"
SYMBOLS = "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split()
CHARGES = [-1, 0, 1, 2, 3]
FIELDS = ["T1_s", "T2_s", "eta_write", "eta_read", "retention_s"]

def stable_seed(master, experiment, stream, replicate):
    payload = json.dumps([master, experiment, stream, replicate], separators=(",", ":"))
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")

def validate_profile(p):
    if p.get("model") != "markov_amplitude_damping_plus_dephasing":
        raise ValueError("Only the named Markov channel is implemented; do not fit arbitrary echo data into it.")
    for name in FIELDS:
        x = p.get(name)
        if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x):
            raise ValueError(f"Missing or nonfinite parameter: {name}")
        if name.startswith("eta_"):
            if not 0 <= x <= 1:
                raise ValueError(f"{name} must be in [0,1]")
        elif x <= 0:
            raise ValueError(f"{name} must be positive")
    if p["T2_s"] > 2 * p["T1_s"]:
        raise ValueError("T2 > 2*T1 is invalid for this specific Markov channel")
    if p.get("evidence") not in ["hypothetical", "literature", "computed", "measured"]:
        raise ValueError("evidence must be declared")
    if not isinstance(p.get("conditions"), dict) or not p["conditions"]:
        raise ValueError("Operating conditions must be explicit")
    if not p.get("provenance"):
        raise ValueError("provenance is required, including for hypothetical profiles")

def evolve_bloch(r, t, T1, T2):
    """Ground-state amplitude damping plus pure dephasing, no Hamiltonian rotation.
    z=+1 is ground; T2 includes relaxation's contribution. Units: seconds.
    """
    if t < 0 or not math.isfinite(t):
        raise ValueError("time must be finite and nonnegative")
    if T1 <= 0 or T2 <= 0 or T2 > 2*T1:
        raise ValueError("Invalid Markov relaxation parameters")
    x, y, z = r
    if any(not math.isfinite(v) for v in r) or x*x+y*y+z*z > 1+1e-12:
        raise ValueError("Bloch vector must describe a physical state")
    a, b = math.exp(-t/T2), math.exp(-t/T1)
    return (a*x, a*y, b*z+1-b)

def metrics(p, t):
    validate_profile(p)
    evolve_bloch((0, 0, 1), t, p["T1_s"], p["T2_s"])
    a, b = math.exp(-t/p["T2_s"]), math.exp(-t/p["T1_s"])
    # Erasure is independent and state-independent, NOT T1 population relaxation.
    success = p["eta_write"]*p["eta_read"]*math.exp(-t/p["retention_s"])
    favg = (3+2*a+b)/6
    fe = (1+2*a+b)/4
    return {"t_s": t, "conditional_storage_average_fidelity": favg,
            "conditional_storage_entanglement_fidelity": fe,
            "retrieval_success_probability": success,
            "success_weighted_average_overlap": success*favg}

def photodetachment_overlap_fidelity(environment_overlap):
    """Illustrative ideal mapping, two electron/environment records with real overlap.
    This is NOT an atomic photodetachment calculation or a proof of feasibility.
    """
    if not math.isfinite(environment_overlap) or not -1 <= environment_overlap <= 1:
        raise ValueError("Real environment overlap must be in [-1,1]")
    return (2+environment_overlap)/3

def usable_horizon(samples, min_fidelity, min_success):
    """Conservative first-prefix horizon from measured FULL-channel samples.
    No interpolation/extrapolation or inference from a spin T2. The caller must
    ensure all samples share thermal schedule, noise protocol and activity.
    Missing metrics produce inconclusive, never an invented value.
    """
    if not 0 <= min_fidelity <= 1 or not 0 <= min_success <= 1:
        raise ValueError("Thresholds must be probabilities")
    if not samples:
        return {"status": "inconclusive", "reason": "no full-channel samples"}
    rows = sorted(samples, key=lambda r: r["t_s"])
    times = [r["t_s"] for r in rows]
    if any(not isinstance(t,(int,float)) or not math.isfinite(t) or t < 0 for t in times) or len(set(times)) != len(times):
        raise ValueError("Times must be unique, finite and nonnegative")
    if times[0] != 0:
        return {"status": "inconclusive", "reason": "no t=0 baseline; cannot certify a prefix"}
    last = None
    for r in rows:
        f, p = r.get("full_channel_fidelity"), r.get("retrieval_success_probability")
        if f is None or p is None:
            return {"status":"inconclusive", "last_passing_grid_time_s":last,
                    "reason":"missing complete fidelity or success probability"}
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in [f,p]):
            raise ValueError("Invalid sample probabilities")
        if f < min_fidelity or p < min_success:
            return {"status":"threshold_failed_at_grid_point", "last_passing_grid_time_s":last,
                    "first_failing_grid_time_s":r["t_s"],
                    "continuous_horizon_certified":False}
        last = r["t_s"]
    return {"status":"right_censored_on_grid", "last_passing_grid_time_s":last,
            "continuous_horizon_certified":False}

def evidence_audit(path):
    """Audit evidence completeness, not truthfulness or scientific quality."""
    catalog = json.loads(Path(path).read_text())
    reports=[]
    for record in catalog["records"]:
        missing=[]
        conditions=record.get("conditions",{})
        for stage in ["write_temperature_K","storage_temperature_K","read_temperature_K"]:
            if conditions.get(stage) is None: missing.append(stage)
        for field in ["photon_input","readout_mode","network_activity"]:
            if conditions.get(field) is None: missing.append(field)
        if not record.get("source",{}).get("url"): missing.append("source_url")
        for m in record.get("measurements",[]):
            for field in ["quantity","value","unit","evidence_kind","source_location"]:
                if m.get(field) is None: missing.append("measurement_"+field)
        quantities={m["quantity"] for m in record.get("measurements",[])}
        full=bool(quantities & {"full_channel_fidelity","memory_output_qubit_fidelity"})
        reports.append({"id":record["id"], "missing_metadata":sorted(set(missing)),
                        "has_photonic_fidelity":full,
                        "has_measured_operating_point":full and "retrieval_efficiency" in quantities,
                        "ready_for_network_channel":False,
                        "reason":"Independent operating points do not determine a complete time-dependent quantum channel"})
    return {"records":reports,"note":"Metadata audit only; human source review and model validation remain necessary"}

def dump(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+"\n")

def init_inventory(out):
    rows = []
    for Z, symbol in enumerate(SYMBOLS, 1):
        for q in CHARGES:
            rows.append({"id": f"{symbol}_q{q:+d}", "Z": Z, "symbol": symbol,
                         "charge_e": q, "isotope": None, "host": None,
                         "electronic_state": None, "status": "unassessed",
                         "bound_state_exists": None, "optical_interface": None,
                         "T1_s": None, "T2_s": None, "provenance": []})
    dump(out, {"version": VERSION, "scope": "inventory only, not viable species",
               "count": len(rows), "candidates": rows})
    return {"inventory_rows": len(rows), "elements": len(SYMBOLS), "out": out}

def screen(path):
    db = json.loads(Path(path).read_text())
    totals = {"rejected": 0, "needs_data": 0, "needs_channel_validation": 0}
    rows = []
    for c in db["candidates"]:
        if c.get("bound_state_exists") is False or c.get("optical_interface") is False:
            status = "rejected"
        elif any(c.get(k) is None for k in ["isotope", "host", "electronic_state", "bound_state_exists", "optical_interface", "T1_s", "T2_s"]) or not c.get("provenance"):
            status = "needs_data"
        else:
            status = "needs_channel_validation"
        totals[status] += 1
        rows.append({"id": c["id"], "status": status})
    return {"counts": totals, "ranked": False, "results": rows}

def demo(out):
    p = {"id": "SYNTHETIC_NOT_A_MATERIAL", "model": "markov_amplitude_damping_plus_dephasing",
         "T1_s": 100, "T2_s": 10, "retention_s": 200,
         "eta_write": 0.8, "eta_read": 0.7, "evidence": "hypothetical",
         "conditions": {"temperature_K": "unspecified; synthetic demo", "control": "none"},
         "provenance": ["Chosen for software demonstration, no material association"]}
    dump(out, p)
    return p

def simulate(path, out):
    p = json.loads(Path(path).read_text())
    times = [0, .001, .01, .1, 1, 10, 100, 1000]
    results = [metrics(p, t) for t in times]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with Path(out).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    dump(str(out)+".manifest.json", {"version": VERSION, "python": platform.python_version(),
         "config_sha256": digest, "evidence": p["evidence"], "solver": "analytic",
         "limitations": ["No write/read process noise modeled beyond independent erasure",
                         "Storage fidelities exclude conversion, gates and detectors",
                         "Independent Markov noise only; not an atomistic prediction"]})
    return {"evaluations": len(results), "out": out, "evidence": p["evidence"]}

def export_profile(path, out, allow_hypothetical):
    p = json.loads(Path(path).read_text())
    validate_profile(p)
    if p["evidence"] == "hypothetical" and not allow_hypothetical:
        raise ValueError("Hypothetical export requires --allow-hypothetical")
    result = {"schema": "westquant_memory_channel_v0.2", "profile": p,
              "mapping": {"bloch_A_diagonal": ["exp(-age_s/T2_s)", "exp(-age_s/T2_s)", "exp(-age_s/T1_s)"],
                          "bloch_translation": [0, 0, "1-exp(-age_s/T1_s)"],
                          "erasure_success": "eta_write*eta_read*exp(-age_s/retention_s)"},
              "adapter_status": "generic JSON contract; SeQUeNCe/NetSquid adapters NOT implemented",
              "operational_comparison_ready": False,
              "operational_limitations": ["No measured full write-store-read channel",
                  "Stage temperatures and thermal transition costs not validated",
                  "No activity-dependent memory noise or on-demand interface validation"],
              "validated_for_hardware": False}
    dump(out, result)
    return {"out": out, "adapter_status": result["adapter_status"]}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init"); p.add_argument("--out", default="results/inventory.json")
    p = sub.add_parser("screen"); p.add_argument("inventory"); p.add_argument("--out", default="results/screen.json")
    p = sub.add_parser("demo-profile"); p.add_argument("--out", default="results/demo_profile.json")
    p = sub.add_parser("simulate"); p.add_argument("profile"); p.add_argument("--out", default="results/channel.csv")
    p = sub.add_parser("export"); p.add_argument("profile"); p.add_argument("--out", default="results/network_profile.json"); p.add_argument("--allow-hypothetical", action="store_true")
    p = sub.add_parser("audit-evidence"); p.add_argument("catalog", nargs="?", default="evidence_catalog.json"); p.add_argument("--out", default="results/evidence_audit.json")
    args = ap.parse_args()
    try:
        if args.command == "init": result = init_inventory(args.out)
        elif args.command == "screen":
            result = screen(args.inventory); dump(args.out, result)
        elif args.command == "demo-profile": result = demo(args.out)
        elif args.command == "simulate": result = simulate(args.profile, args.out)
        elif args.command == "audit-evidence":
            result = evidence_audit(args.catalog); dump(args.out,result)
        else: result = export_profile(args.profile, args.out, args.allow_hypothetical)
    except (ValueError, OSError, KeyError) as exc:
        ap.exit(2, f"error: {exc}\n")
    print(json.dumps(result if args.command != "screen" else result["counts"], ensure_ascii=False))

if __name__ == "__main__":
    main()
