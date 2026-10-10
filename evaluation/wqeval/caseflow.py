"""Step 2: audited fixed-model versus complex pure-dephasing observations.

No fitting of a decay time from a paper's headline, no default optical interface.
"""
import csv
import numpy as np
from memorylab.models import evaluate, extra_coherence, validate
from memorylab.network import export, MemoryDevice, link_benchmark
from memorylab.t2assessment import first_crossing
from .common import read, write, source_path, audit_identity, new_output, csv_rows

def run(config, output, base, allow_hypothetical=False):
    out = new_output(output)
    if config.get('status') == 'awaiting_reviewed_data':
        result = {'step': 2, 'status': 'blocked_missing_reviewed_data',
                  'required': config['required'], 'reference': config['reference'],
                  'physical_validation_passed': False, 'network_exported': False,
                  'identity': audit_identity(config)}
        write(out / 'summary.json', result)
        return result
    if config['observable'] != 'complex_pure_dephasing_coherence' or config['includes_population_relaxation'] is not False:
        raise ValueError('Separate complex pure-dephasing observable required; total echo decay cannot be relabeled')
    evidence = config['evidence_kind']
    if evidence not in ('measured', 'hypothetical'):
        raise ValueError('Measured or explicitly hypothetical case required')
    review = config['review']
    if not all(review.get(k) for k in ('reviewer', 'source_location', 'normalization', 'observable_mapping')):
        raise ValueError('Incomplete curve review')
    curvepath = source_path(config['curve'], base)
    profilepath = source_path(config['model'], base)
    profile = read(profilepath)
    model_review = config.get('model_review')
    if evidence == 'measured':
        if not model_review or not all(model_review.get(k) for k in ('reviewer', 'source_location', 'parameter_scope')):
            raise ValueError('Measured validation needs audited model parameter provenance')
        if profile['evidence_kind'] in ('hypothetical', 'unknown'):
            raise ValueError('A hypothetical model cannot count as a physically validated baseline')
        if profile.get('experimental_conditions') != config['conditions']:
            raise ValueError('Reviewed full experimental conditions must match the model exactly')
    if profile['family'] == 'rare_earth_solid':
        raise ValueError('Step 2 must exercise another family')
    if profile['storage_model'] not in ('exact_spin_bath', 'pycce'):
        raise ValueError('A fixed independently supplied spin Hamiltonian is required')
    conditions = config['conditions']
    if profile['temperatures_K']['storage'] != conditions['temperature_K'] or profile.get('control', {}) != conditions['control']:
        raise ValueError('Model and measurement temperature/pulse conditions differ')
    if not conditions.get('field_and_frame') or not conditions.get('composition_and_isotopes'):
        raise ValueError('Field/frame and isotope/composition review required')
    with curvepath.open(newline='') as f:
        rows = list(csv.DictReader(f))
    times = np.array([float(r['time_s']) for r in rows])
    observed = np.array([complex(float(r['real']), float(r['imag'])) for r in rows])
    sem = np.array([float(r['sem_complex']) for r in rows])
    if len(times) < 3 or not np.isfinite(times).all() or times[0] != 0 or np.any(np.diff(times) <= 0):
        raise ValueError('Increasing curve grid including zero required')
    if not np.isfinite(observed).all() or not np.isfinite(sem).all() or np.any(sem <= 0) or abs(observed[0]-1) > 1e-9 or np.any(abs(observed) > 1+1e-9):
        raise ValueError('Finite normalized physical coherence and positive complex SEM required')
    predicted = extra_coherence(profile, times.tolist())
    residual = abs(predicted-observed)
    normalized = residual/sem
    csv_rows(out/'model_vs_curve.csv', [{'time_s':float(t),'observed_real':float(o.real),'observed_imag':float(o.imag),
        'predicted_real':float(p.real),'predicted_imag':float(p.imag),'sem_complex':float(s),'normalized_error':float(e)}
        for t,o,p,s,e in zip(times,observed,predicted,sem,normalized)])
    if config['gate']['kind'] != 'max_complex_residual_over_sem':
        raise ValueError('Unsupported validation gate')
    threshold = float(config['gate']['threshold'])
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError('Positive finite gate required')
    passed = bool(np.max(normalized) <= threshold)
    result = {'step':2, 'status':'model_curve_gate_pass' if passed else 'model_curve_gate_fail',
        'gate': config['gate'], 'max_normalized_error':float(max(normalized)), 'points':len(times),
        'physical_validation_passed': passed and evidence == 'measured',
        'software_control_only': evidence == 'hypothetical', 'evidence_kind':evidence,
        'fitted_parameters':0, 'coherence_descriptor':first_crossing(times,abs(predicted)),
        'network_exported':False, 'identity':audit_identity(config,[curvepath,profilepath]),
        'limitations':['Fixed-model consistency gate is not a confidence interval or proof of uniqueness',
                       'Coherence validation does not establish a quantum write/read interface']}
    optical = config.get('optical_interface_review')
    if not passed:
        result['network_status'] = 'blocked_model_curve_mismatch'
    elif optical is None:
        result['network_status'] = 'blocked_missing_optical_interface_review'
    else:
        if not all(optical.get(k) for k in ('reviewer','source_location','evidence_kind')):
            raise ValueError('Incomplete optical interface review')
        hypothetical = evidence == 'hypothetical' or optical['evidence_kind'] == 'hypothetical'
        if optical['evidence_kind'] not in ('measured', 'hypothetical'):
            raise ValueError('Unsupported optical evidence')
        if hypothetical and not allow_hypothetical:
            result['network_status'] = 'blocked_hypothetical_interface_requires_opt_in'
        else:
            profile['evidence_kind'] = 'hypothetical' if hypothetical else 'fit_to_experiment'
            profile['provenance'] += [{'curve_review':review,'interface_review':optical,'curve_sha256':config['curve']['sha256']}]
            validate(profile)
            channels = evaluate(profile,times.tolist())
            export(channels,out/'memory_device.json',allow_hypothetical)
            device = MemoryDevice(channels,allow_hypothetical)
            workload = config['network_workload']
            result['network_result'] = link_benchmark(device,device,workload,config['seed'])
            result['network_exported'] = True
            result['network_status'] = 'hypothetical_channel_benchmark' if hypothetical else 'experiment_constrained_channel_benchmark'
    write(out/'summary.json',result)
    return result
