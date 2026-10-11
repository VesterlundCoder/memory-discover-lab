"""Protocol-explicit inference of a decay scale; never infer T2 from one point.

The likelihood is Gaussian with supplied standard errors or binomial with raw
phase-resolved counts. Confidence intervals are parametric bootstrap intervals,
conditional on that likelihood and the supplied decay model.
"""
import math
import numpy as np
from scipy.optimize import least_squares
from scipy.stats import chi2
from .common import digest


def validate_curve(curve):
    for key in ("times_s", "quantity", "conditions", "provenance", "time_definition",
                "decay_factor", "target_definition", "mapping_review"):
        if key not in curve:
            raise ValueError("Curve lacks " + key)
    t = np.asarray(curve["times_s"], float)
    if t.ndim != 1 or len(t) < 6 or len(np.unique(t)) < 6 or not np.isfinite(t).all() or (t < 0).any():
        raise ValueError("At least six distinct finite nonnegative storage times required")
    if not curve["provenance"] or not curve["time_definition"]:
        raise ValueError("Provenance and time definition required")
    factor = float(curve["decay_factor"])
    if not np.isfinite(factor) or factor <= 0:
        raise ValueError("Positive reviewed amplitude/intensity decay factor required")
    kind = curve.get("likelihood", "gaussian")
    if kind == "gaussian":
        y, sigma = np.asarray(curve["values"], float), np.asarray(curve["standard_errors"], float)
        if y.shape != t.shape or sigma.shape != t.shape or not np.isfinite(y).all() or not np.isfinite(sigma).all() or (sigma <= 0).any():
            raise ValueError("One finite value and positive standard error per observation required")
        return t, y, sigma
    if kind == "binomial":
        k, n, phases = [np.asarray(curve[x], float) for x in ("counts_plus", "trials", "phases_rad")]
        if any(a.shape != t.shape or not np.isfinite(a).all() for a in (k, n, phases)):
            raise ValueError("Counts/trials/phases must match times")
        if (n <= 0).any() or (k < 0).any() or (k > n).any() or (k != np.floor(k)).any() or (n != np.floor(n)).any():
            raise ValueError("Binomial data require integer counts, 0 <= k <= n")
        return t, k, n
    raise ValueError("Unsupported likelihood")


def envelope(t, parameters, factor, stretched):
    amplitude, log_tau, background = parameters[:3]
    beta = parameters[3] if stretched else 1.0
    return background + amplitude*np.exp(-factor*(t/math.exp(log_tau))**beta)


def _fit(curve, stretched=False, selected=None, values=None):
    t, y, scale = validate_curve(curve)
    sel = np.ones(len(t), bool) if selected is None else np.asarray(selected, bool)
    y = y if values is None else np.asarray(values, float)
    positive = t[t > 0]
    lo, hi = math.log(positive.min()/100), math.log(max(t.max(), positive.min())*100)
    factor = curve["decay_factor"]
    binomial = curve.get("likelihood") == "binomial"
    # Phase is a measured analysis setting. Phase drift is not fitted away as decay.
    phases = np.asarray(curve.get("phases_rad", np.zeros(len(t))), float)
    if binomial:
        lower, upper = [0, lo, -0.05], [0.94, hi, 0.05]
    else:
        lower, upper = [0, lo, -np.inf], [np.inf, hi, np.inf]
    if stretched:
        lower += [0.25]; upper += [4.0]
    def prediction(p):
        if binomial:
            c = p[0]*np.exp(-factor*(t/math.exp(p[1]))**(p[3] if stretched else 1.0))
            return (1+p[2]+c*np.cos(phases))/2
        return envelope(t, p, factor, stretched)
    def residual(p):
        pred = prediction(p)
        if binomial:
            pred = np.clip(pred, 1e-12, 1-1e-12)
            # Signed square root binomial deviance: least-squares equals ML.
            from scipy.special import xlogy
            mu = scale*pred
            dev = 2*(xlogy(y, y/mu)+xlogy(scale-y, (scale-y)/(scale-mu)))
            return (np.sign(y-mu)*np.sqrt(np.maximum(0, dev)))[sel]
        return ((y-pred)/scale)[sel]
    best = None
    for multiplier in (0.3, 1.0, 3.0):
        a = 0.7 if binomial else max(float(np.ptp(y[sel])), float(np.mean(scale[sel])))
        b = 0.0 if binomial else float(np.min(y[sel]))
        guess = [a, np.clip(math.log(max(t.max(), positive.min())*multiplier), lo+1e-6, hi-1e-6), b]
        if stretched:
            guess += [1.5]
        fit = least_squares(residual, guess, bounds=(lower, upper), max_nfev=3000, x_scale="jac")
        if best is None or fit.cost < best.cost:
            best = fit
    return best, prediction(best.x), (lo, hi)


def fit_curve(curve, model="exponential", bootstrap=200, seed=20261010):
    if model not in {"exponential", "stretched"}:
        raise ValueError("Model must be exponential or stretched")
    if not isinstance(bootstrap, int) or isinstance(bootstrap, bool) or not 0 <= bootstrap <= 10000:
        raise ValueError("bootstrap must be an integer between 0 and 10000")
    t, y, scale = validate_curve(curve)
    stretched = model == "stretched"
    fit, pred, bounds = _fit(curve, stretched)
    n_params = len(fit.x); dof = len(t)-n_params
    goodness = float(2*fit.cost)
    pvalue = float(chi2.sf(goodness, dof)) if dof > 0 else None
    # Predetermined interleaved time holdout; amplitude and background remain free.
    _, time_groups = np.unique(t, return_inverse=True)
    hold = time_groups % 4 == 3
    holdout = None
    if (~hold).sum() >= n_params+3 and hold.sum() >= 2:
        _, hp, _ = _fit(curve, stretched, ~hold)
        if curve.get("likelihood") == "binomial":
            hres = (y-scale*hp)/np.sqrt(np.maximum(scale*hp*(1-hp), 1e-12))
        else:
            hres = (y-hp)/scale
        holdout = float(np.sqrt(np.mean(hres[hold]**2)))
    tau, beta = math.exp(fit.x[1]), float(fit.x[3] if stretched else 1)
    is_bound = fit.x[1] < bounds[0]+0.02 or fit.x[1] > bounds[1]-0.02
    bracketed = float(t.min()) <= tau <= float(t.max())
    mapping = curve["mapping_review"]
    reviewed = mapping.get("status") == "reviewed" and bool(mapping.get("source"))
    issues = []
    if not fit.success: issues.append("optimizer_failure")
    if is_bound: issues.append("fit_boundary")
    if not bracketed: issues.append("e_minus_one_time_outside_observed_range")
    if pvalue is not None and pvalue < 0.01: issues.append("decay_model_rejected")
    if holdout is not None and holdout > 3: issues.append("heldout_time_mismatch")
    if not reviewed: issues.append("mapping_not_reviewed")
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(bootstrap):
        yy = (rng.binomial(scale.astype(int), np.clip(pred, 0, 1)) if curve.get("likelihood") == "binomial"
              else rng.normal(pred, scale))
        try:
            ff, _, _ = _fit(curve, stretched, values=yy)
            if ff.success and bounds[0]+0.02 < ff.x[1] < bounds[1]-0.02:
                draws.append(math.exp(ff.x[1]))
        except (ValueError, FloatingPointError):
            pass
    interval = np.quantile(draws, [0.025, 0.975]).tolist() if len(draws) >= 30 else None
    if bootstrap and len(draws) < max(30, 0.8*bootstrap): issues.append("bootstrap_unstable")
    if interval and interval[1]/interval[0] > 10: issues.append("weak_identifiability")
    if any(i in issues for i in ("decay_model_rejected", "heldout_time_mismatch")):
        status = "model_mismatch"
    elif issues:
        status = "inconclusive"
    else:
        status = "pass"
    return {"schema": "westquant_t2_fit_v1", "curve_hash": digest(curve), "status": status,
            "issues": issues, "target_definition": curve["target_definition"], "model": model,
            "apparent_decay_scale_s": tau,
            "identified_T2_s": tau if status == "pass" and curve["target_definition"].startswith("T2") else None,
            "beta": beta, "amplitude": float(fit.x[0]), "background": float(fit.x[2]),
            "decay_factor": curve["decay_factor"], "conditional_bootstrap_95_interval_s": interval,
            "bootstrap_requested": bootstrap, "bootstrap_success": len(draws), "seed": seed,
            "goodness_statistic": goodness, "degrees_of_freedom": dof, "goodness_p_approx": pvalue,
            "heldout_standardized_rmse": holdout, "times_s": t.tolist(), "fitted_values": pred.tolist(),
            "conditions": curve["conditions"], "provenance": curve["provenance"],
            "limitations": ["Gaussian errors/binomial trials and independence are model assumptions",
                            "Parametric bootstrap does not include shared systematics or model uncertainty",
                            "No T1, retrieval fidelity, or full quantum channel inferred from an envelope"]}


def operational_horizon(times_s, fidelity_lower, efficiency_lower, f_min, eta_min):
    t, f, e = [np.asarray(a, float) for a in (times_s, fidelity_lower, efficiency_lower)]
    if not len(t) or t.shape != f.shape or t.shape != e.shape or not all(np.isfinite(a).all() for a in (t, f, e)):
        raise ValueError("Finite matching arrays required")
    if np.any(np.diff(t) <= 0) or t[0] < 0 or not 0 <= f_min <= 1 or not 0 <= eta_min <= 1:
        raise ValueError("Increasing times and thresholds in [0,1] required")
    first_failure = next((i for i in range(len(t)) if f[i] < f_min or e[i] < eta_min), len(t))
    return {"last_contiguously_qualified_sample_s": float(t[first_failure-1]) if first_failure else None,
            "first_failed_sample_s": float(t[first_failure]) if first_failure < len(t) else None,
            "between_samples_validated": False}
