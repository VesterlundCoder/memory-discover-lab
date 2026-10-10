"""Rebuild all example configs. Every memory parameter below is a SOFTWARE scenario."""
import copy
from pathlib import Path
from memorylab.catalog import SYMBOLS
from memorylab.common import write_json

ROOT = Path(__file__).resolve().parent


def profile(family="trapped_atom_ion"):
    return {
        "name": "SYNTHETIC_SOFTWARE_SCENARIO_NOT_A_MEASURED_MATERIAL",
        "family": family, "storage_model": "markov", "evidence_kind": "hypothetical",
        "provenance": [{"kind": "chosen_software_test_parameters", "not_a_material_prediction": True}],
        "temperatures_K": {"write": 4.2, "storage": 4.2, "read": 4.2},
        "rates": {
            "population": {"kind": "constant", "rate_s_inv": 0.05, "valid_temperature_K": [1, 300]},
            "pure_dephasing": {"kind": "phenomenological_temperature", "base_s_inv": 0.01,
                "direct_s_inv_K_inv": 0.001, "reference_K": 10, "raman_at_reference_s_inv": 0.001,
                "raman_exponent": 3, "valid_temperature_K": [1, 300]},
            "erasure": {"kind": "constant", "rate_s_inv": 0.01, "valid_temperature_K": [1, 300]}},
        "io": {"eta_write": 0.8, "eta_read": 0.7, "write_depolarizing_p": 0.01,
               "read_depolarizing_p": 0.02, "write_duration_s": 0.0001,
               "read_duration_s": 0.0002, "thermal_transition_s": 0,
               "logical_encoding": "abstract_qubit", "protocol": "supplied_effective_write_read_channel",
               "bandwidth_Hz": None, "wavelength_nm": None, "modes": 1},
        "noise_budget": ["phenomenological_relaxation", "independent_markov_dephasing",
                        "write_depolarization", "read_depolarization", "independent_erasure"],
        "network_activity": {"attempt_rate_Hz": 0, "coherence_loss_per_attempt": 0},
        "control": {}, "detuning_Hz": 0, "equilibrium_excited_population": 0}


def spin_bath():
    return {"central_m": [0.5, -0.5], "max_dimension": 64,
            "nuclei": [{"isotope_id": "C-13", "spin_I": 0.5, "frame": "lab",
                "position_angstrom": [3, 0, 0], "zeeman_vector_Hz": [0, 0, 214163.9829],
                "hyperfine_Hz": [[0, 0, 0], [0, 0, 0], [0, 0, 4000]]}]}


def build():
    families = ["atomic_ensemble", "trapped_atom_ion", "rare_earth_solid",
                "defect_spin", "molecular_spin", "negative_ion"]
    models = []
    for family in families:
        p = profile(family)
        if family in ("defect_spin", "molecular_spin"):
            p.update(storage_model="exact_spin_bath", spin_bath=spin_bath(),
                     additional_dephasing_independent_of_markov=True, control={"cpmg_pulses": 1})
            p["noise_budget"].append("specified_nuclear_spin_bath")
        if family == "negative_ion":
            p.update(candidate={"charge_e": -1}, optical_process="photodetachment",
                     electron_record_overlap=[0.9, 0])
            p["noise_budget"].append("electron_record_distinguishability")
        write_json(ROOT/(family+"_profile.json"), p)
        models.append({"id": family+"_synthetic", "task": "memory", "profile": p})
    study = {"study_id": "six_family_software_smoke_v1", "stage": "software_smoke",
        "hypotheses": ["analytical and numerical channel representations agree",
                       "write-store-read metrics remain CPTP across the temperature grid"],
        "models": models, "grid": {"temperatures_K.storage": [4.2, 10, 80]},
        "backends": ["analytic"], "replicates": 2, "master_seed": 20261010,
        "times_s": [0, 0.0001, 0.001, 0.01, 0.1, 1, 10],
        "resources": {"timeout_s": 90, "max_workers": 2, "max_runs": 100},
        "gates": {"minimum_fidelity": 0.8, "minimum_success": 0.1},
        "network_workload": {"attempts": 2000, "link_herald_probability": 0.2,
            "attempt_interval_s": 0.001, "storage_age_s": 0.01, "minimum_Bell_fidelity": 0.7}}
    write_json(ROOT/"study.json", study)
    cross = copy.deepcopy(study)
    cross.update(study_id="analytic_qutip_conformance_v1", backends=["analytic", "qutip"], replicates=1)
    write_json(ROOT/"cross_backend_study.json", cross)
    p = profile("defect_spin")
    bath = spin_bath()
    bath.update(center={"spin_S": 0.5, "alpha_index": 0, "beta_index": 1,
                       "position_angstrom": [0, 0, 0], "gyro_rad_s_T": -176085970500,
                       "zfs_Hz": [[0, 0, 0], [0, 0, 0], [0, 0, 0]]},
                magnetic_field_T=[0, 0, 0.02], r_bath_angstrom=6,
                r_dipole_angstrom=5, order=1, nbstates=0, method="cce")
    p.update(storage_model="pycce", spin_bath=bath,
             additional_dephasing_independent_of_markov=True, control={"cpmg_pulses": 1})
    p["noise_budget"].append("specified_nuclear_spin_bath")
    write_json(ROOT/"pycce_profile.json", p)
    plan = {"family": "molecular_spin",
        "templates": [{"name": "H2_geometry_template_not_memory", "composition": {"H": 2},
                       "geometry_angstrom": [["H", [0, 0, 0]], ["H", [0, 0, 0.74]]],
                       "periodic": False, "provenance": [{"kind": "software_geometry_template"}]}],
        "charges_e": [-1, 0, 1], "spin_2S": [0, 1, 2], "hosts": [None],
        "isotope_choices_by_site": {"0": ["H-1", "H-2"], "1": ["H-1", "H-2"]},
        "max_candidates": 100}
    write_json(ROOT/"new_combinations.json", plan)
    all_elements = {"family": "trapped_atom_ion",
        "templates": [{"name": symbol, "composition": {symbol: 1},
                       "geometry_angstrom": [[symbol, [0, 0, 0]]], "periodic": False,
                       "provenance": [{"kind": "unassessed_periodic_table_inventory"}]} for symbol in SYMBOLS],
        "charges_e": [-1, 0, 1, 2, 3], "spin_2S": [0, 1, 2, 3],
        "hosts": [None], "max_candidates": 5000}
    write_json(ROOT/"all_elements.json", all_elements)
    data = {"download": {"max_bytes": 50_000_000, "timeout_s": 25, "retries": 2},
        "max_total_bytes": 150_000_000,
        "sources": [
            {"id": "molecular_qubit_dataset", "kind": "github",
             "repository": "MTD-group/Molecular_Qubit_Dataset", "ref": "main",
             "include": ["Relaxation_time_data_08_02_24.csv"], "max_files": 1,
             "importer": "molecular_csv", "license": "not_verified"},
            {"id": "cr_host_matrix_2022", "kind": "zenodo", "record_id": 6828667,
             "include": ["fig_3b_1.txt", "fig_3d_1.txt"], "max_files": 2},
            {"id": "ciaaw_isotopes", "kind": "http", "revision": "live_table_retrieval",
             "urls": ["https://www.ciaaw.org/isotopic-abundances.htm"],
             "max_files": 1, "importer": "ciaaw_abundances"}
        ]}
    write_json(ROOT/"data_plan.json", data)
    extended = copy.deepcopy(data)
    extended["sources"] += [
        {"id": "nist_isotope_masses", "kind": "http", "max_files": 1,
         "urls": ["https://physics.nist.gov/cgi-bin/Compositions/stand_alone.pl?ele=all&ascii=ascii2&isotype=all"],
         "importer": "nist_isotopes"},
        {"id": "dryad_molecular_optical", "kind": "dryad",
         "doi": "10.5061/dryad.v6wwpzh55", "include": ["Data.zip"], "max_files": 1},
        {"id": "bmrb_metabolite", "kind": "bmrb", "entries": ["bmse000001"],
         "max_files": 1, "importer": "bmrb_star"},
        {"id": "pubchem_molecules", "kind": "pubchem", "cids": [241, 702],
         "geometry_3d": True, "max_files": 4},
        {"id": "cryogenic_materials", "kind": "github", "repository": "CMB-S4/Cryogenic_Material_Properties",
         "ref": "main", "include": ["thermal_conductivity/**/*.csv"], "max_files": 2000}]
    write_json(ROOT/"data_plan_extended.json", extended)
    pipeline = {"datasets": data, "candidates": plan, "study": study,
                "allow_hypothetical_network": True}
    write_json(ROOT/"pipeline.json", pipeline)
    pipeline["electronic"] = {"max_candidates": 2, "recipe": {"basis": "sto-3g", "method": "HF",
                            "threads": 1, "memory_MB": 1024, "max_cycle": 100, "conv_tol": 1e-9}}
    write_json(ROOT/"pipeline_full.json", pipeline)
    write_json(ROOT/"h2_candidate.json", {"name": "H2_conformance_geometry", "family": "molecular_spin",
        "charge_e": 0, "spin_2S": 0, "periodic": False,
        "geometry_angstrom": [["H", [0, 0, 0]], ["H", [0, 0, 0.74]]],
        "isotopes_by_site": {"0": "H-1", "1": "H-1"}})
    write_json(ROOT/"pyscf_recipe.json", {"basis": "sto-3g", "method": "HF", "threads": 1,
                                        "memory_MB": 1024, "conv_tol": 1e-10, "excited_states": 1})
    write_json(ROOT/"orca_recipe.json", {"keywords": "PBE def2-SVP TightSCF", "binary": None,
                                         "timeout_s": 600, "blocks": "%pal nprocs 1 end"})
    write_json(ROOT/"lambda_eit.json", {
        "atom": {"num_states": 3, "initial_state": [1, 0, 0],
            "decays": [{"channels": [[0, 2], [1, 2]], "rate": 0.1}],
            "fields": [
                {"coupled_levels": [[0, 2]], "rabi_freq": 0.01,
                 "rabi_freq_t_func": "gaussian", "rabi_freq_t_args": {"centre": 0, "fwhm": 0.3, "ampl": 1}},
                {"coupled_levels": [[1, 2]], "rabi_freq": 2.0,
                 "rabi_freq_t_func": "square", "rabi_freq_t_args": {"on": -1, "off": 1, "ampl": 1}}]},
        "t_min": -0.5, "t_max": 0.5, "t_steps": 40, "z_min": 0, "z_max": 1,
        "z_steps": 4, "interaction_strengths": [0.1, 0.1], "opts": {"atol": 1e-9, "rtol": 1e-7}})
    write_json(ROOT/"network_workload.json", study["network_workload"])


if __name__ == "__main__":
    build()
