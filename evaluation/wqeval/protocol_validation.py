"""Joint instrument verification against independent matrix-unit construction."""
import copy
import math
from pathlib import Path
import numpy as np
from memorylab.models import evaluate
from memorylab.protocol import readout_instrument, metrics
from memorylab.channels import choi, apply, check_cptp
from . import reference
from .common import audit_identity, source_path, write, new_output, csv_rows, read


def independent_instrument(profile, detector, age):
    superop, eta = reference.superoperator(profile, age)
    rate = detector['base_rate_s_inv']+detector['age_rate_s_inv_per_s']*age
    noise = (1-eta)*(1-math.exp(-rate*detector['window_s']))
    sigma = np.diag([1-detector['background_excited_population'], detector['background_excited_population']])
    trace = np.array([1, 0, 0, 1])
    success_super = eta*superop + noise*np.outer(sigma.reshape(-1, order='F'), trace)
    p = eta+noise
    j = np.zeros((6, 6), complex)
    for a in range(2):
        for b in range(2):
            unit = np.zeros((2, 2)); unit[a, b] = 1
            out = np.zeros((3, 3), complex)
            out[:2, :2] = reference.action(success_super, unit)
            out[2, 2] = (1-p)*np.trace(unit)
            j += np.kron(unit, out)
    f = reference.average_fidelity(success_super)/p if p else None
    return {'choi': j, 'accepted_superoperator': success_super, 'eta': eta, 'noise': noise,
            'acceptance': p, 'conditional_fidelity': f}


def audit_experiments(root):
    manifest = read(root/'data/experimental/manifest.json')
    rec = next(r for r in manifest['groups']['pr2026'] if r['path'].endswith('fig3.npz'))
    path = source_path({'path': rec['path'], 'sha256': rec['sha256']}, root/'data/experimental')
    with np.load(path, allow_pickle=False) as d:
        rows = [{'source_time_us': float(t), 'signal_efficiency_percent': float(e),
                 'signal_efficiency_error_percent': float(se), 'noise_percent_per_herald': float(n),
                 'noise_error_percent_per_herald': float(sn), 'signal_idler_g2': float(g),
                 'g2_error': float(sg), 'qubit_fidelity': None}
                for t, e, se, n, sn, g, sg in zip(d['st'], d['eff'], d['eff_err'], d['nf'], d['nf_err'], d['g2'], d['g2_err'])]
    return {'status': 'inconclusive_missing_matched_fidelity_and_clock_review',
            'joint_experimental_validation_passed': False, 'hardware_experiments': 0,
            'measured_time_points': len(rows), 'measured_scalar_values': 3*len(rows),
            'source_sha256': rec['sha256'], 'doi': '10.5281/zenodo.21532904', 'observations': rows,
            'gaps': ['g2 is signal-idler correlation, not qubit fidelity',
                     '0.9 us source/article total-time offset is unresolved',
                     'noise per herald is not automatically a per-vacuum false-click probability',
                     'Teller fixed optical point cannot identify time dependence',
                     'Bradley NV0 Bloch/X curves have no optical efficiency/noise series'],
            'required_data': ['Matched qubit state/tomography counts and background-only counts at each storage time',
                              'Input photon regime, trial denominators, detector window and herald semantics',
                              'Common clock and identical write/read, field, temperature and pulse conditions',
                              'Calibration/heldout split and error/covariance definition'],
            'scope': 'source audit only; no fidelity inferred from correlation or imported from another experiment'}


def run(config, out, base):
    out = new_output(out)
    profile_path = source_path(config['profile'], base)
    template = read(profile_path)
    rows, serialized = [], []
    maximum = 0.0
    for case in config['cases']:
        profile = copy.deepcopy(template)
        profile['storage_model'] = 'markov'
        profile['noise_budget'] = [n for n in profile['noise_budget'] if n != 'specified_nuclear_spin_bath']
        profile['rates'].update({key: {'kind':'constant','rate_s_inv':value,'valid_temperature_K':[1,300]}
                                for key, value in case['rates_s_inv'].items()})
        profile['io'].update(case['io'])
        profile['equilibrium_excited_population'] = case['equilibrium_population']
        profile['detuning_Hz'] = case['detuning_Hz']
        detector = dict(config['detector'], **case['detector'])
        for signal in evaluate(profile, config['times_s']):
            channel = readout_instrument(signal, detector)
            ref = independent_instrument(profile, detector, signal.metadata['storage_age_s'])
            j_error = float(np.max(np.abs(choi(channel.full_kraus())-ref['choi'])))
            state_error = 0.0
            for rho in reference.state_probes():
                predicted = apply(channel.full_kraus(), rho)
                expected = np.zeros((3,3),complex)
                expected[:2,:2] = reference.action(ref['accepted_superoperator'], rho)
                expected[2,2] = 1-ref['acceptance']
                state_error = max(state_error, float(np.max(abs(predicted-expected))))
            m = metrics(signal, channel)
            f_error = abs(m['conditional_detected_average_fidelity']-ref['conditional_fidelity']) if ref['acceptance'] else 0.0
            probability_error = max(abs(m['signal_efficiency']-ref['eta']),
                                    abs(m['noise_click_probability']-ref['noise']),
                                    abs(m['acceptance_probability']-ref['acceptance']))
            check = check_cptp(channel.full_kraus())
            error = max(j_error, state_error, f_error, probability_error)
            maximum = max(maximum, error)
            rows.append({'case_id':case['id'], **m, 'choi_max_error':j_error, 'six_state_max_error':state_error,
                         'fidelity_error':f_error, 'probability_max_error':probability_error,
                         'tp_error':check['tp_max_error'], 'choi_min_eigenvalue':check['choi_min_eigenvalue'],
                         'numerical_gate':'pass' if error <= config['tolerance'] else 'fail'})
            serialized.append({'case_id':case['id'], 'signal':signal.serialize(), 'detected':channel.serialize()})
    audit = audit_experiments(Path(__file__).resolve().parents[2])
    summary = {'status':'pass' if maximum <= config['tolerance'] else 'fail', 'channel_age_points':len(rows),
               'state_probe_comparisons':6*len(rows), 'maximum_numerical_error':maximum,
               'tolerance':config['tolerance'], 'joint_experimental_validation_passed':False,
               'scope':'hypothetical complete effective instruments; independent Liouvillian numerical verification',
               'experimental_audit_status':audit['status'], 'provenance':audit_identity(config,[profile_path])}
    csv_rows(out/'protocol_metrics.csv', rows)
    write(out/'channels.json', serialized)
    write(out/'experimental_audit.json', audit)
    write(out/'summary.json', summary)
    return summary
