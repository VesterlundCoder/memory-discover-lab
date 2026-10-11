"""Explicit observation binding, raw-curve fits and operating-point baseline comparisons."""
import copy
import math
import numpy as np
from scipy.optimize import least_squares
from .common import MissingData, finite, digest, read_json
from .runner import assign
from .models import evaluate


def bind_observations(profile, bindings, catalog):
    result = copy.deepcopy(profile)
    observations = catalog.rows("observations")
    for binding in bindings:
        if not binding.get("model_justification"):
            raise MissingData("Observation binding requires a reviewed model justification")
        matches = [o for o in observations if
                   (o["id"] == binding["observation_id"] if "observation_id" in binding else
                    o["subject_id"] == binding["subject_id"] and o["quantity"] == binding["quantity"])
                   and all(o["conditions"].get(k) == v for k, v in binding.get("conditions", {}).items())]
        if len(matches) != 1:
            raise MissingData(f"Binding needs one unambiguous observation, got {len(matches)}")
        row = matches[0]
        if row["unit"] != binding["required_unit"] or row["quantity"] != binding["quantity"]:
            raise MissingData("Observation quantity or verified unit does not match binding")
        value = finite(row["value"], "bound observation", 0)
        transformation = binding.get("transform", "identity")
        if transformation == "inverse":
            if value <= 0:
                raise ValueError("Cannot invert nonpositive lifetime")
            value = 1/value
        elif transformation != "identity":
            raise ValueError("Unsupported binding transformation")
        assign(result, binding["target"], value)
        result["provenance"].append({"observation_id": row["id"],
                                    "binding": binding, "observation_provenance": row["provenance"]})
    return result


def fit_exponential(times_s, amplitudes, uncertainties, conditions, provenance):
    """Fit normalized PURE coherence with fixed L(0)=1; never infer an optical memory interface."""
    t, y, sigma = [np.asarray(v, float) for v in (times_s, amplitudes, uncertainties)]
    if any(v.ndim != 1 for v in (t, y, sigma)) or t.shape != y.shape or y.shape != sigma.shape or len(t) < 5:
        raise ValueError("Fit needs at least five equally sized one-dimensional arrays")
    if not np.isfinite(np.r_[t, y, sigma]).all() or np.any(sigma <= 0) or t[0] != 0 or np.any(np.diff(t) <= 0):
        raise ValueError("Fit needs finite positive uncertainty and increasing times starting at zero")
    if not conditions or not provenance:
        raise MissingData("Curve fit requires conditions and raw-data provenance")
    if np.any(np.diff(y) > 5*np.sqrt(sigma[1:]**2+sigma[:-1]**2)):
        raise ValueError("Resolved coherence revival; a single Markov exponential is inappropriate")
    scale = t[-1]
    if scale <= 0:
        raise ValueError("Time range must be positive")
    fit = least_squares(lambda a: (np.exp(-a[0]*t/scale)-y)/sigma, [1.0], bounds=(0, np.inf))
    gamma = float(fit.x[0]/scale)
    if not fit.success or not math.isfinite(gamma):
        raise ValueError("Fit failed")
    chi2 = float(np.sum(fit.fun**2))
    dof = len(t)-1
    information = float((fit.jac.T @ fit.jac)[0, 0])
    se = math.sqrt(1/information)/scale if information > 0 else None
    return {"schema": "westquant_curve_fit_v1", "quantity": "pure_dephasing_rate",
            "rate_s_inv": gamma, "standard_error_s_inv": se, "chi2": chi2,
            "degrees_of_freedom": dof, "reduced_chi2": chi2/dof,
            "status": "pass" if chi2/dof <= 2 else "model_mismatch",
            "conditions": conditions, "provenance": provenance, "evidence_kind": "fit_to_experiment",
            "raw_curve_sha256": digest([times_s, amplitudes, uncertainties]),
            "does_not_validate_photonic_write_read": True,
            "uncertainty_assumptions": "independent Gaussian stated errors; no rescaling of residual variance"}


def compare_baseline(profile, baseline):
    """Compare only matching measured full-channel operating points with supplied uncertainty."""
    if baseline.get("evidence_kind") not in ("experimental", "curated_experimental"):
        raise MissingData("Baseline comparison requires experimental reference data")
    if not baseline.get("provenance") or baseline.get("temperatures_K") != profile["temperatures_K"]:
        raise MissingData("Baseline provenance/temperatures absent or mismatched")
    if baseline.get("protocol") != profile["io"]["protocol"] or baseline.get("control", {}) != profile.get("control", {}):
        raise MissingData("Baseline optical protocol or spin control does not match")
    points = baseline["points"]
    grid = sorted(set(p["storage_age_s"] for p in points))
    computed = dict(zip(grid, evaluate(profile, grid)))
    comparisons = []
    for p in points:
        if p["quantity"] not in {"conditional_average_fidelity", "retrieval_success_probability",
                                 "conditional_entanglement_fidelity"}:
            raise MissingData("A spin T2 cannot validate a complete network-memory channel")
        val = finite(p["value"], "reference probability", 0, 1)
        se = finite(p["standard_error"], "reference standard_error", 1e-15)
        predicted = computed[p["storage_age_s"]].metrics()[p["quantity"]]
        z = abs(predicted-val)/se
        comparisons.append({**p, "prediction": predicted, "absolute_z": z,
                            "pass": z <= baseline.get("maximum_absolute_z", 3)})
    if not comparisons:
        raise MissingData("No comparable full-channel baseline measurements")
    return {"schema": "westquant_baseline_reproduction_v1",
            "baseline_id": baseline["id"], "status": "pass" if all(p["pass"] for p in comparisons) else "fail",
            "comparisons": comparisons, "provenance": baseline["provenance"],
            "profile_hash": digest(profile), "reference_hash": digest(baseline),
            "scope": "agreement at supplied operating points only; not a unique channel reconstruction",
            "hardware_validated": False}
