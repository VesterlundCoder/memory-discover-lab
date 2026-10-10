"""One-command open-data -> audited baseline -> QuTiP -> SeQUeNCe workflow."""
import hashlib
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from .common import read_json, write_json, digest, environment, MissingData
from .datasets import Client
from .catalog import Catalog
from .importers import put_observation, provenance
from .experimental import parse_indexed_infidelity, interval_sigma, spatial_holdout, window_noise_fit
from .models import evaluate
from .channels import choi, apply, encode, validate_state
from .network import export, MemoryDevice
from .sequence_adapter import run_link


def run_baseline(config, output, offline=False, reviewed_bundle=None):
    actual_counts = {"measured_operating_point_backend_runs": 2,
                     "network_replicates": len(config["network_seeds"]),
                     "network_attempts_total": len(config["network_seeds"])*config["network_workload"]["attempts"],
                     "window_model_fits": 3}
    if config["run_counts"] != actual_counts or len(set(config["network_seeds"])) != len(config["network_seeds"]):
        raise ValueError("Declared run counts do not match actual unique-seed workload")
    out = Path(output)
    cache = out/"cache"
    client = Client(cache, max_bytes=10_000_000, timeout_s=40, retries=1)
    # Published repository version is fixed; checksums in reviewed lock are mandatory.
    lock = config["source_lock"]
    if set(lock["files"]) != set(config["download_files"]):
        raise MissingData("Reviewed data lock must cover every requested file")
    if reviewed_bundle is not None:
        from .bundled import reviewed_baseline_inputs
        artifacts, metadata_record = reviewed_baseline_inputs(config, cache, reviewed_bundle)
    else:
        artifacts, metadata_record = _retrieve_inputs(config, client, offline)
    write_json(out/"fetch_manifest.json", {"metadata": metadata_record, "artifacts": artifacts,
                "all_checksums_verified": reviewed_bundle is None,
                "numerical_data_checksums_verified": True,
                "input_mode": "bundled_numerical_replay" if reviewed_bundle else "source_acquisition",
                "unbundled_paper_bytes_verified": reviewed_bundle is None, "offline": offline})
    return _compute_baseline(config, out, cache, artifacts, metadata_record, actual_counts, reviewed_bundle)


def _retrieve_inputs(config, client, offline):
    cache = client.root
    lock = config['source_lock']
    metadata_url = f"https://zenodo.org/api/records/{lock['record_id']}"
    if offline:
        metadata, metadata_record = _cached_json(client, metadata_url, "teller2025_metadata")
    else:
        metadata, metadata_record = client.json(metadata_url, "teller2025_metadata")
    if metadata["metadata"]["license"]["id"] != "cc-by-4.0":
        raise MissingData("Data license changed; source review required")
    listed = {f["key"]: f for f in metadata["files"]}
    artifacts = {}

    def fetch(name):
        file = listed[name]
        if file["checksum"] != lock["files"][name]["archive_checksum"]:
            raise MissingData("Archive MD5 differs from reviewed lock: "+name)
        kwargs = dict(url=file["links"]["self"], source_id="teller2025",
                      revision="14929997:v1", license_info=metadata["metadata"]["license"],
                      expected_checksum=file["checksum"], filename=name)
        record = _cached_fetch(client, kwargs) if offline else client.fetch(**kwargs)
        data = (cache/record["relative_path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != lock["files"][name]["sha256"]:
            raise MissingData("Data SHA256 differs from reviewed lock: "+name)
        return name, record

    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, artifact in pool.map(fetch, config["download_files"]):
            artifacts[name] = artifact
    # Papers are retained as source artifacts too; offline never contacts servers.
    for source in config["paper_sources"]:
        kwargs = dict(url=source["url"], source_id=source["id"], filename=source["filename"],
                      license_info="CC-BY-4.0", expected_checksum="sha256:"+source["sha256"])
        record = _cached_fetch(client, kwargs) if offline else client.fetch(**kwargs)
        if hashlib.sha256((cache/record["relative_path"]).read_bytes()).hexdigest() != source["sha256"]:
            raise MissingData("Paper differs from reviewed source")
        artifacts[source["filename"]] = record
    return artifacts, metadata_record


def _compute_baseline(config, out, cache, artifacts, metadata_record, actual_counts, reviewed_bundle):
    write_json(out/"data_quality.json", {"reviewed_mapping_notes": config["source_mapping_notes"],
        "excluded_from_physical_inference": [{"file": "3a.csv",
        "reason": "Unclear abscissa unit: metadata says seconds; numeric extent is 0.070..1183.278 with no header",
        "action": "not bundled or used in numerical replay" if reviewed_bundle else "retained with checksum, not used to estimate storage lifetime or pulse shape"}],
        "review_status": "computational source audit; external domain-expert signoff pending"})

    def path(name):
        return cache/artifacts[name]["relative_path"]

    def load(name):
        return np.loadtxt(path(name), delimiter=";", comments="#")

    path_states = parse_indexed_infidelity(path("4.csv"), 5, ["X", "-X", "Y", "-Y", "0", "1"], "basis,cell")
    time_states = parse_indexed_infidelity(path("8a.csv"), 10, ["X", "-X", "Y", "-Y", "E", "L"], "basis,cell", cell_index_base=1)
    windows = load("5_xaxis.csv")
    window_f, window_lo, window_hi = [load(n) for n in (
        "5_yaxis2_F.csv", "5_yaxis2_Fmin.csv", "5_yaxis2_Fmax.csv")]
    window_sigma = interval_sigma(window_f, window_lo, window_hi)
    f, lo, hi = [load(n) for n in ("8b_F.csv", "8b_Fmin.csv", "8b_Fmaxn.csv")]
    tsigma = interval_sigma(f, lo, hi)
    index270 = int(np.argmin(abs(windows-270)))
    if abs(windows[index270]-270) > 1e-8:
        raise MissingData("No exact 270 ns read-out window")
    reconstruction_error = float(np.max(abs(path_states.mean(axis=0)[[0, 2, 4]]-window_f[:, index270])))
    time_error = float(np.max(abs(time_states.mean(axis=0)-f)))
    rho_x = validate_state(np.loadtxt(path("3b.csv"), delimiter=",", dtype=complex))
    ket_x = np.array([1, 1], complex)/math.sqrt(2)
    rho_x_fidelity = float(np.real(ket_x.conj() @ rho_x @ ket_x))
    rho_x_error = abs(rho_x_fidelity-path_states[0, 2])
    if rho_x_error > 1e-9:
        raise MissingData("Released density matrix and Figure 4 X-state disagree")
    if reconstruction_error > 1e-12 or time_error > 1e-12:
        raise MissingData("State-averaged fidelities disagree with supplied figures")

    # Numerically reproduce paper summary using raw, un-subtracted fidelities.
    path_mean, time_mean = float(path_states.mean()), float(time_states.mean())
    reproduction = {"schema": "westquant_experimental_reanalysis_v1",
        "status": "pass", "baseline_id": config["id"],
        "paper_doi": config["paper_doi"], "raw_state_fidelities": 90,
        "path_six_state_average": path_mean, "paper_path_average": .95,
        "time_bin_six_state_average": time_mean, "paper_time_bin_average": .91,
        "published_rounded_summary_agreement": abs(path_mean-.95) <= .02 and abs(time_mean-.91) <= .02,
        "path_figure_consistency_max_error": reconstruction_error,
        "time_bin_figure_consistency_max_error": time_error,
        "released_density_matrix_X_fidelity": rho_x_fidelity,
        "density_matrix_figure4_consistency_error": rho_x_error,
        "scope": "reanalyze released processed experimental data; not a new hardware experiment",
        "unique_channel_identified": False, "T2_identified": False,
        "provenance": provenance(artifacts["4.csv"])+provenance(artifacts["8a.csv"])}
    if not reproduction["published_rounded_summary_agreement"]:
        reproduction["status"] = "fail"
    write_json(out/"experimental_reanalysis.json", reproduction)
    holdout = spatial_holdout(f, lo, hi)
    write_json(out/"spatial_holdout.json", holdout)
    noise_fit = window_noise_fit(windows, window_f, window_lo, window_hi)
    write_json(out/"readout_window_noise_fit.json", noise_fit)

    # Rebuild the generated catalog atomically: software review changes must
    # not silently double-count the same measured datum on a rerun.
    staging_catalog = out/"catalog.rebuild.sqlite"
    staging_catalog.unlink(missing_ok=True)
    catalog = Catalog(staging_catalog)
    try:
        with catalog.transaction():
            catalog.put("artifacts", metadata_record)
            for artifact in artifacts.values():
                catalog.put("artifacts", artifact)
            candidate = {"id": "teller2025_pr_yso", "family": "rare_earth_solid",
                         "name": "Pr3+:Y2SiO5 memory array", "ionic_charge_e": 3,
                         "specimen_charge_e": 0, "nuclear_isotope": None,
                         "isotope_note": "No isotope assay in reviewed experiment",
                         "host": "Y2SiO5", "geometry_angstrom": None,
                         "status": "measured_optical_memory_at_fixed_conditions",
                         "network_channel_validated": False,
                         "provenance": provenance(artifacts["paper.pdf"])}
            catalog.put("candidates", candidate)
            for label, states, filename, detection in (
                    ("path", path_states, "4.csv", 270e-9),
                    ("time_bin", time_states, "8a.csv", 295e-9)):
                labels = ["X", "-X", "Y", "-Y", "0", "1"] if label == "path" else ["X", "-X", "Y", "-Y", "E", "L"]
                for basis in range(6):
                    for cell in range(states.shape[1]):
                        conditions = {"temperature_K": 3, "encoding": label,
                            "state": labels[basis], "cell_or_pair_index": cell+1,
                            "detection_window_s": detection, "background_subtracted": False}
                        put_observation(catalog, artifacts[filename], candidate["id"],
                            "conditional_state_fidelity", float(states[basis, cell]), "1",
                            f"{filename}: indexed basis {basis}, cell/pair {cell}", conditions,
                            "experimental", {"uncertainty": None, "uncertainty_note": "Not released per state in this CSV"})
            for cell in range(10):
                put_observation(catalog, artifacts["8b_F.csv"], candidate["id"],
                    "conditional_average_fidelity", float(f[cell]), "1", f"8b: cell {cell+1}",
                    {"temperature_K": 3, "encoding": "time_bin", "cell": cell+1,
                     "spin_storage_s": 11e-6, "detection_window_s": 295e-9}, "experimental",
                    {"uncertainty": {"standard_error": float(tsigma[cell]),
                     "kind": "MC distribution std", "low": float(lo[cell]), "high": float(hi[cell])},
                     "uncertainty_provenance": provenance(artifacts["8b_Fmin.csv"])+provenance(artifacts["8b_Fmaxn.csv"])})
            for i, pair in enumerate(([1, 2], [5, 6], [9, 10])):
                for j, window in enumerate(windows):
                    put_observation(catalog, artifacts["5_yaxis2_F.csv"], candidate["id"],
                        "conditional_average_fidelity", float(window_f[i, j]), "1",
                        f"Figure 5 CSV row {i}, column {j}",
                        {"temperature_K": 3, "encoding": "path", "pair": pair,
                         "end_to_end_storage_s": 18e-6, "spin_storage_s": 8e-6,
                         "detection_window_s": float(window*1e-9)}, "experimental",
                        {"uncertainty": {"standard_error": float(window_sigma[i, j]),
                         "kind": "MC distribution std; correlated across windows"},
                         "uncertainty_provenance": provenance(artifacts["5_yaxis2_Fmin.csv"])+provenance(artifacts["5_yaxis2_Fmax.csv"])})
            for component in config["reviewed_point"]["classical_efficiency_components"]:
                put_observation(catalog, artifacts["supplement.pdf"], candidate["id"],
                    "classical_efficiency_"+component["name"], component["value"], "1",
                    "Supplement Table I, pair 5,6", {"temperature_K": 3, "encoding": "path", "pair": [5, 6]},
                    "experimental", {"uncertainty": {"standard_error": component["standard_error"]},
                                     "extraction": "explicit reviewed transcription from published table"})
            put_observation(catalog, artifacts["paper.pdf"], candidate["id"],
                "accepted_photon_fraction", .42, "1", "Main text section III, Figure 3a discussion",
                {"encoding": "path", "pair": [5, 6], "detection_window_s": 270e-9}, "experimental",
                {"uncertainty": None, "extraction": "published rounded 42 percent; uncertainty not supplied"})
        summary_catalog = catalog.summary()
        write_json(out/"observations.json", {"observations": catalog.rows("observations")})
    finally:
        catalog.close()
    staging_catalog.replace(out/"catalog.sqlite")

    # Pair 5,6 at the exact 270 ns window. No rates/T1/T2 are invented.
    review = config["reviewed_point"]
    eta_components = review["classical_efficiency_components"]
    eta = math.prod(e["value"] for e in eta_components)*review["photon_window_fraction"]
    relative_var = sum((e["standard_error"]/e["value"])**2 for e in eta_components)
    profile = {"id": "teller2025_path_pair_5_6_270ns", "family": "rare_earth_solid",
        "storage_model": "measured_operating_point", "evidence_kind": "fit_to_experiment",
        "temperatures_K": {"write": 3, "storage": 3, "read": 3},
        "temperature_note": "Single reported cryostat setpoint; no independent stage thermometry",
        "provenance": provenance(artifacts["5_yaxis2_F.csv"])+provenance(artifacts["5_yaxis2_Fmin.csv"])+provenance(artifacts["5_yaxis2_Fmax.csv"])+provenance(artifacts["paper.pdf"])+provenance(artifacts["supplement.pdf"]),
        "control": {"optical_control_pulses": 2, "radiofrequency_decoupling": False},
        "io": {"protocol": "AFC_spin_wave_path_qubit", "logical_encoding": "path",
               "read_duration_s": 0, "write_duration_s": 0,
               "duration_note": "Whole 18 us point includes optical read; no extra latency supplied",
               "wavelength_nm": 606, "filter_bandwidth_Hz": 2e6,
               "memory_bandwidth_Hz": None, "modes": 2},
        "point": {"temperature_K": 3, "end_to_end_age_s": 18e-6,
            "spin_storage_s": 8e-6, "afc_rephasing_s": 10e-6,
            "detection_window_s": 270e-9,
            "conditional_average_fidelity": float(window_f[1, index270]),
            "fidelity_standard_error": float(window_sigma[1, index270]),
            "signal_retrieval_probability": eta,
            "retrieval_standard_error_conditional_on_window_fraction": eta*math.sqrt(relative_var),
            "photon_window_fraction": review["photon_window_fraction"],
            "window_fraction_uncertainty": None,
            "retrieval_uncertainty_assumptions": "Independent component errors; temporal-acceptance uncertainty and covariance absent",
            "loss_scope": "AFC x two-way optical transfer x demultiplexing AOD x temporal acceptance; excludes fiber coupling, filters, detector and analysis success",
            "loss_is_direct_single_photon_measurement": False,
            "efficiency_components": eta_components}}
    write_json(out/"measured_point_profile.json", profile)
    channels = [evaluate(profile, [18e-6], backend)[0] for backend in ("analytic", "qutip")]
    difference = float(np.max(abs(choi(channels[0].full_kraus())-choi(channels[1].full_kraus()))))
    if difference > 1e-10:
        raise ValueError("QuTiP channel differs from analytic channel")
    write_json(out/"channel_samples.json", {"samples": [channels[0].serialize()]})
    write_json(out/"qutip_channel_samples.json", {"samples": [channels[1].serialize()]})
    export([channels[0]], out/"network_device.json")
    qt = __import__("qutip")
    pure = np.array([1, 0, 0, 1], complex)/math.sqrt(2)
    rho = np.outer(pure, pure.conj())
    joint = [np.kron(a, b) for a in channels[1].conditional_kraus for b in channels[1].conditional_kraus]
    output_state = sum(qt.Qobj(k)*qt.Qobj(rho)*qt.Qobj(k).dag() for k in joint).full()
    bell_fidelity = float(np.real(pure.conj() @ output_state @ pure))
    write_json(out/"qutip_two_node.json", {"conditional_Bell_fidelity": bell_fidelity,
                "density_matrix": encode(output_state), "qutip_version": qt.__version__,
                "fidelity_convention": "squared Uhlmann / pure-state overlap"})
    network_results = []
    device = MemoryDevice([channels[0]])
    for s in config["network_seeds"]:
        result = run_link(device, device, config["network_workload"], s)
        network_results.append(result)
        write_json(out/"sequence_runs"/f"seed_{s}.json", result)
    trials = sum(r["attempts"] for r in network_results)
    success = sum(r["retrieved_pairs"] for r in network_results)
    from .network import wilson
    network_ci = wilson(success, trials)
    expected = network_results[0]["expected_success_probability"]
    gates = {"schema": "westquant_baseline_gate_v2", "status": "blocked_for_discovery",
             "single_point_data_reanalysis": reproduction["status"],
             "spatial_holdout_conditional_fidelity": holdout["status"],
             "simulator_consistency": "pass", "T2_identified": False,
             "time_resolved_fidelity_and_efficiency_validated": False,
             "independent_raw_count_reconstruction": False,
             "full_network_optical_loss_and_false_herald_model_validated": False,
             "missing": ["storage-time sweep with conditional fidelity AND retrieval efficiency",
                         "raw counts/trial numbers and covariance", "single-photon loss and noise instrument",
                         "temperature sweep or independent thermometry"],
             "allowed": ["reproduce published fidelity summaries", "finite-point qubit-channel simulations",
                         "clearly scoped ideal-heralding network workload"],
             "prohibited_claims": ["inferred T2", "temperature extrapolation", "better-than-SOTA material ranking"]}
    write_json(out/"discovery_gate.json", gates)
    from .runner import source_fingerprint
    summary = {"schema": "westquant_open_baseline_pipeline_v1", "status": "completed_with_scientific_limits",
        "baseline": config["id"], "configuration_sha256": digest(config), "environment": environment(),
        "source_sha256": source_fingerprint(), "verified_run_counts": actual_counts,
        "catalog": summary_catalog, "source_artifacts": len(artifacts)+1,
        "source_data_checksums_verified": True, "experimental_reanalysis": reproduction,
        "input_mode": "bundled_numerical_replay" if reviewed_bundle else "source_acquisition",
        "unbundled_paper_bytes_verified": reviewed_bundle is None,
        "spatial_holdout": {k: v for k, v in holdout.items() if k != "comparisons"},
        "readout_window_fits": [{k: v for k, v in r.items() if k != "predictions"} for r in noise_fit["fits"]],
        "negative_control_model": noise_fit["negative_control_model"],
        "operating_point": profile["point"], "analytic_qutip_max_choi_error": difference,
        "simulated_conditional_Bell_fidelity": bell_fidelity,
        "sequence_runs": len(network_results), "network_attempts": trials,
        "network_retrieved_pairs": success, "network_retrieved_fraction_95CI": network_ci,
        "network_expected_success_probability": expected,
        "network_expected_probability_in_95CI": network_ci[0] <= expected <= network_ci[1],
        "network_max_density_error": max((r["max_density_error_against_analytic"] or 0) for r in network_results),
        "discovery_gate": gates, "hardware_validated": False}
    write_json(out/"summary.json", summary)
    return summary


def _cached_fetch(client, kwargs):
    key = digest([kwargs["source_id"], kwargs["url"], kwargs.get("revision"), kwargs.get("filename")])
    manifest = client.root/"manifests"/(key+".json")
    if not manifest.exists():
        raise MissingData("Offline artifact missing: "+kwargs["url"])
    record = read_json(manifest)
    path = client.root/record["relative_path"]
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
        raise MissingData("Offline cache missing/corrupt")
    return record


def _cached_json(client, url, source_id):
    record = _cached_fetch(client, {"url": url, "source_id": source_id})
    return read_json(client.root/record["relative_path"]), record
