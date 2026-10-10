"""Audited Bradley NV0 observable comparison; deliberately separate from caseflow.

Measured Bloch lengths and X are not normalized complex pure-dephasing data.
The calibrated effective map must never acquire a physical-validation/export flag.
"""
import io
import zipfile
import numpy as np
from scipy.optimize import least_squares
from .common import read, write, source_path, audit_identity, new_output, csv_rows


def envelope(t, amplitude, tau, beta):
    return amplitude * np.exp(-(np.asarray(t) / tau) ** beta)


def effective_kraus(t, tau, beta, frequency):
    """CPTP model only: U_z followed by dephasing. Signal amplitude is SPAM."""
    if not np.isfinite([t, tau, beta, frequency]).all() or t < 0 or tau <= 0 or beta <= 0:
        raise ValueError('Invalid effective-channel parameters')
    e = float(envelope(t, 1, tau, beta))
    u = np.diag(np.exp(-1j * np.pi * frequency * t * np.array([1, -1])))
    return [np.sqrt((1 + e) / 2) * u, np.sqrt((1 - e) / 2) * u @ np.diag([1, -1])]


def load_case(config, base):
    if config['schema'] != 'bradley2022_nv0_observable_case_v1':
        raise ValueError('Unsupported observable case')
    if config['conditions'] != config['model']['experimental_conditions']:
        raise ValueError('Experimental conditions mismatch')
    if config['network_export_allowed'] or config['review']['population_relaxation_separated']:
        raise ValueError('This dataset cannot support complete-channel export or isolated pure dephasing')
    paths = [source_path(config[k], base) for k in ('source_data', 'archive', 'notebook')]
    with zipfile.ZipFile(paths[1]) as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read('Shared Data.zip'))) as inner:
            if inner.read('Shared Data/data_3b.json') != paths[0].read_bytes():
                raise ValueError('Extracted observations do not match original archive')
        if outer.read('DataAnalysis_RobustMemory.ipynb') != paths[2].read_bytes():
            raise ValueError('Analysis notebook does not match original archive')
    data = read(paths[0])
    if len(data) != 6:
        raise ValueError('Expected six source arrays')
    blocks = []
    for start in (0, 3):
        t, y, error = (np.asarray(v, dtype=float) for v in data[start:start + 3])
        if any(v.ndim != 1 for v in (t, y, error)) or not (len(t) == len(y) == len(error)):
            raise ValueError('Invalid observable dimensions')
        if not all(np.isfinite(v).all() for v in (t, y, error)) or np.any(error <= 0):
            raise ValueError('Nonfinite observations or invalid error scale')
        order = np.argsort(t); t, y, error = t[order] * .001, y[order], error[order]
        if np.any(t < 0) or np.any(np.diff(t) <= 0):
            raise ValueError('Invalid experimental time grid')
        blocks.append((t, y, error))
    return blocks, paths


def split_mask(times, cutoff):
    mask = times <= cutoff + 1e-12
    if mask.sum() < 4 or (~mask).sum() < 1:
        raise ValueError('Insufficient calibration or heldout points')
    return mask


def fit_envelope(block, mask, settings):
    t, y, error = block
    fit = least_squares(lambda p: (envelope(t[mask], *p) - y[mask]) / error[mask],
                        settings['initial'], bounds=(settings['lower'], settings['upper']),
                        ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=5000)
    if not fit.success or not np.isfinite(fit.x).all():
        raise ValueError('Envelope calibration failed')
    return fit.x, int(fit.nfev)


def fit_ramsey(block, mask, parameters, frequency):
    t, y, error = block
    e = envelope(t, 1, parameters[1], parameters[2])
    design = e[:, None] * np.column_stack((np.cos(2*np.pi*frequency*t), np.sin(2*np.pi*frequency*t)))
    coefficients, _, rank, _ = np.linalg.lstsq(design[mask] / error[mask, None], y[mask] / error[mask], rcond=None)
    if rank != 2:
        raise ValueError('Ramsey calibration has insufficient rank')
    return design @ coefficients, coefficients


def comparison(block, mask, prediction, name, threshold):
    t, y, error = block
    z = (prediction - y) / error
    rows = [{'observable': name, 'time_s': float(a), 'observed': float(b),
             'reported_error': float(c), 'prediction': float(d), 'residual_over_error': float(e),
             'partition': 'calibration' if f else 'heldout'}
            for a, b, c, d, e, f in zip(t, y, error, prediction, z, mask)]
    maximum = float(np.max(np.abs(z[~mask])))
    return rows, {'calibration_points': int(mask.sum()), 'heldout_points': int((~mask).sum()),
                  'max_heldout_residual_over_error': maximum, 'gate_passed': maximum <= threshold}


def run(config, out, base):
    blocks, paths = load_case(config, base)
    masks = [split_mask(b[0], config['split'][key]) for b, key in zip(blocks,
             ('envelope_calibration_max_s', 'ramsey_calibration_max_s'))]
    counts = config['split']['expected_counts']
    for name, mask in zip(('envelope', 'ramsey'), masks):
        if (int(mask.sum()), int((~mask).sum())) != (counts[name+'_calibration'], counts[name+'_heldout']):
            raise ValueError('Unexpected calibration/heldout counts')
    parameters, nfev = fit_envelope(blocks[0], masks[0], config['fit'])
    frequency = config['model']['nmr_center_Hz'] - config['model']['rf_reference_Hz']
    prediction_x, coefficients = fit_ramsey(blocks[1], masks[1], parameters, frequency)
    predictions = [envelope(blocks[0][0], *parameters), prediction_x]
    threshold = config['gate']['threshold']
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError('Invalid diagnostic threshold')
    rows, metrics = [], {}
    for name, block, mask, predicted in zip(('equatorial_length', 'X'), blocks, masks, predictions):
        r, m = comparison(block, mask, predicted, name, threshold); rows.extend(r); metrics[name] = m
    sensitivity = []
    for delta in config['frequency_sensitivity_offsets_Hz']:
        px, _ = fit_ramsey(blocks[1], masks[1], parameters, frequency + delta)
        _, metric = comparison(blocks[1], masks[1], px, 'X', threshold)
        sensitivity.append({'frequency_Hz': float(frequency + delta), **metric})
    result = {'status': 'completed_observable_comparison', 'experimental_case_completed': True,
              'heldout_observable_gate_passed': all(m['gate_passed'] for m in metrics.values()),
              'physical_validation_passed': False, 'microscopic_model_validated': False,
              'network_exported': False, 'hardware_experiments': 0,
              'measured_points': len(rows), 'heldout_points': sum(m['heldout_points'] for m in metrics.values()),
              'primary_comparisons': 2, 'frequency_sensitivity_comparisons': len(sensitivity),
              'parameters': dict(zip(config['fit']['parameters'], map(float, parameters))),
              'envelope_optimizer_nfev': nfev, 'fixed_rotating_frame_frequency_Hz': float(frequency),
              'ramsey_cos_sin_coefficients': coefficients.tolist(), 'metrics': metrics,
              'frequency_sensitivity': sensitivity, 'gate': config['gate'],
              'limitations': ['Retrospective split after data inspection; not preregistered',
                             'Envelope parameters and signal amplitude/phase calibrated, not fixed microscopic prediction',
                             'Scalar Bloch length and X only; complex pure dephasing and population relaxation not identified',
                             'No source covariance, raw-shot likelihood, or calibration uncertainty propagation',
                             'No independent scientific review or new hardware experiment',
                             'No optical write/read channel or network export'],
              'provenance': audit_identity(config, paths)}
    out = new_output(out)
    csv_rows(out / 'model_vs_observables.csv', rows)
    write(out / 'summary.json', result)
    return result
