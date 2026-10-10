"""Validate retained study evidence and generate manuscript numbers, tables and claim map.

Does not rerun or overwrite scientific results. Historical source hashes stay historical.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tables'
RESULTS=ROOT/'evaluation/results/validation_extension/selected'


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sci(value):
    a,b=f'{value:.3e}'.split('e')
    return r'\ensuremath{'+a+r'\times10^{'+str(int(b))+'}}'
def integer(value):return f'{value:,}'.replace(',',r'\,')
def tex(name,content):(OUT/name).write_text(content+'\n')


def main():
    OUT.mkdir(exist_ok=True)
    brpath=ROOT/'evaluation/results/bradley2022-nv0/summary.json';br=read(brpath)
    assert br['experimental_case_completed'] and not br['physical_validation_passed']
    assert not br['microscopic_model_validated'] and not br['network_exported']
    assert br['measured_points']==24 and br['heldout_points']==10
    env,x=br['metrics']['equatorial_length'],br['metrics']['X']
    assert env['gate_passed'] and not x['gate_passed']
    assert br['gate']['threshold']==3 and all(not v['gate_passed'] for v in br['frequency_sensitivity'])
    provpath=ROOT/'data/experimental/bradley2022/provenance.json';prov=read(provpath)
    for filename,expected in prov['files'].items():assert sha(provpath.parent/filename)==expected
    data=ROOT/'data/experimental/bradley2022/data_3b.json'
    assert sha(data)==br['provenance']['configuration']['source_data']['sha256']
    with zipfile.ZipFile(provpath.parent/'research_data.zip') as archive:
        assert archive.testzip() is None
    stages={name:read(RESULTS/name/'summary.json') for name in ['protocol','convergence','pilot','larger']}
    p,c,pilot,large=[stages[n] for n in ['protocol','convergence','pilot','larger']]
    assert all(s['status']=='pass' for s in stages.values())
    root=read(RESULTS/'summary.json');assert root['executed_stages']==list(stages)
    assert not root['joint_experimental_validation_passed'] and not root['material_prediction_authorized']
    assert not root['network_timing_equivalence_claimed'] and root['hardware_experiments']==0
    assert p['channel_age_points']==56 and p['state_probe_comparisons']==336 and p['maximum_numerical_error']<p['tolerance']
    audit=read(RESULTS/'protocol/experimental_audit.json')
    assert not audit['joint_experimental_validation_passed'] and audit['measured_time_points']==9
    assert all(v['qubit_fidelity'] is None for v in audit['observations'])
    assert c['coherence_solver_calls']==69 and c['diagnostic_rows']==66 and not c['material_prediction_authorized']
    assert len(c['axes'])==6 and all(v['status']=='pass' for v in c['axes'].values())
    for name,s in [('pilot',pilot),('larger',large)]:
        assert s['successful_arm_runs']==s['planned_arm_runs']==s['attempted_arm_runs']
        assert s['failed_arm_runs']==0 and s['all_counts_and_logical_traces_identical']
        assert s['maximum_mean_density_error']<1e-10
        assert s['total_attempts_all_arms']==s['attempts_per_arm_run']*s['attempted_arm_runs']
        archive=RESULTS/name/'raw_runs_and_traces.zip';assert sha(archive)==s['raw_archive_sha256']
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert sum(n.endswith('.json') for n in z.namelist())==s['attempted_arm_runs']
        with (RESULTS/name/'paired_comparison.csv').open(newline='') as f:rows=list(csv.DictReader(f))
        assert len(rows)==s['paired_comparisons'] and all(r['gate']=='pass' for r in rows)
        assert all(r['counts_and_trace_identical']=='True' for r in rows)
    manifest=read(ROOT/'evidence/validation_extension/manifest.json')
    for filename,digest in manifest['delivered_result_file_sha256'].items():assert sha(ROOT/filename)==digest
    replay=read(ROOT/'evidence/validation_extension/offline-replay-verification.json')
    assert replay['status']=='pass' and replay['source_and_configuration_fingerprints_equal']
    assert replay['compared']=={'json_records':359,'random_trace_arrays':11}
    suites=manifest['test_suites'];passed=sum(s['pass'] for s in suites.values());skipped=sum(s['skip'] for s in suites.values())
    for name in ['lab','evaluation']:
        log=(ROOT/f'evidence/validation_extension/{name}-tests.log').read_text()
        assert re.search(r'Ran '+str(suites[name]['run'])+r' tests',log) and re.search(r'^OK(?: \(skipped=\d+\))?$',log,re.M)
    assert passed==107 and skipped==2
    # Current plotting/manuscript scripts are outside the archived lab/evaluation fingerprints.
    import sys
    sys.path[:0]=[str(ROOT/'evaluation'),str(ROOT/'lab')]
    from wqeval.common import audit_identity
    identity=audit_identity({})
    for s in stages.values():
        for key in ['lab_source_sha256','evaluation_source_sha256']:assert s['provenance'][key]==identity[key]
    numbers={'BPoints':integer(br['measured_points']),'BHeldout':integer(br['heldout_points']),
             'BEnvelopeError':f"{env['max_heldout_residual_over_error']:.3f}",'BXError':f"{x['max_heldout_residual_over_error']:.3f}",
             'BTauMs':f"{br['parameters']['tau_s']*1000:.3f}",'BBeta':f"{br['parameters']['stretch_exponent']:.5f}",
             'BAmplitude':f"{br['parameters']['signal_amplitude']:.5f}",'BCos':f"{br['ramsey_cos_sin_coefficients'][0]:.5f}",
             'BSin':f"{br['ramsey_cos_sin_coefficients'][1]:.5f}",'BFrequency':f"{br['fixed_rotating_frame_frequency_Hz']:.1f}",
             'ProtoPoints':integer(p['channel_age_points']),'ProtoProbes':integer(p['state_probe_comparisons']),
             'ProtoError':sci(p['maximum_numerical_error']),'ConvCalls':integer(c['coherence_solver_calls']),
             'ConvRows':integer(c['diagnostic_rows']),'LargerRuns':integer(large['attempted_arm_runs']),
             'LargerAttempts':integer(large['total_attempts_all_arms']),'LargerPairs':integer(large['paired_comparisons']),
             'LargerError':sci(large['maximum_mean_density_error']),'NativeEvents':integer(large['native_SeQUeNCe_events']),
             'NativeTransfers':integer(large['native_QuNetSim_quantum_packet_transfers']),
             'ReplayRecords':integer(replay['compared']['json_records']),'ReplayArrays':integer(replay['compared']['random_trace_arrays']),
             'LatestPass':str(passed),'LatestSkip':str(skipped),'LatestTests':str(passed+skipped)}
    tex('validation_extension_numbers.tex','% Generated from retained evidence; run scripts/document_article_update.py\n'+
        '\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in numbers.items()))
    names={'independent_solver':('Matrix exponential / spectral','4-spin reference'),
           'control_resolution':('Strang substeps','128 substeps'),
           'cluster_order':('CCE order','Order 4; 4 spins'),
           'pair_cutoff':('Pair cutoff','40 angstrom; 4 spins'),
           'bath_size':('Bath size','6 to 8 spins'),
           'time_grid':('Mean $|L|$ integration','129 to 257 points')}
    rows=[]
    for axis,(label,level) in names.items():
        v=c['axes'][axis]['final_rows'];error=max(r['max_complex_error'] for r in v)
        assert all(r['gate']=='pass' and r['max_complex_error']<=r['tolerance'] for r in v)
        rows.append(label+' & '+level+' & '+sci(error)+' & '+sci(v[0]['tolerance'])+r'\\')
    tex('validation_convergence.tex',r'\begin{table}[tbp]\centering\small'+ '\n'+
        r'\begin{tabular}{p{.29\linewidth}p{.25\linewidth}rr}\toprule Control & Final comparison & Maximum error & Tolerance\\\midrule'+'\n'+
        '\n'.join(rows)+'\n'+r'\bottomrule\end{tabular}'+ '\n'+
        r'\caption{Final convergence diagnostics over 0--0.4 ms, taking the maximum over 0, 1 and 4 ideal pulses. Solver, CCE and cutoff errors use the exact four-spin reference; bath-size and time-grid errors compare adjacent nested levels. The time-grid metric is mean absolute coherence, not every revival extremum or an inferred lifetime.}\label{tab:validationconvergence}\end{table}')
    rows=[]
    for label,s in [('Pilot',pilot),('Larger',large)]:
        cfg=s['provenance']['configuration']
        rows.append(label+' & '+str(len(cfg['seeds']))+' & '+integer(s['paired_comparisons'])+' & '+integer(s['attempted_arm_runs'])+' & '+str(s['attempts_per_arm_run'])+' & '+integer(s['total_attempts_all_arms'])+r'\\')
    tex('validation_crosssim.tex',r'\begin{table}[tbp]\centering\small'+ '\n'+
        r'\begin{tabular}{lrrrrr}\toprule Study & Seeds & Pairs of runs & Arm runs & Trials/run & Trials, both arms\\\midrule'+'\n'+
        '\n'.join(rows)+'\n'+r'\bottomrule\end{tabular}'+ '\n'+
        r'\caption{Actual native simulator work counts. Each parameter/seed combination is executed once per simulator. Paired shared traces test implementation agreement; seeds are the independent Monte Carlo clusters. Pilot and larger stages are separate processes and use different seeds.}\label{tab:validationcrosssim}\end{table}')
    sources=[brpath,provpath,RESULTS/'summary.json',*[RESULTS/n/'summary.json' for n in stages],
             ROOT/'evidence/validation_extension/manifest.json',ROOT/'evidence/validation_extension/offline-replay-verification.json']
    claims=[{'id':'UP1','claim':'Distinct-family Bradley observable comparison, with retained X failure','source':str(brpath.relative_to(ROOT)),
             'value':br['metrics'],'scope':'Calibrated effective model; physical_validation_passed=false; no optical export'},
            {'id':'UP2','claim':'Joint effective protocol numerical verification','source':str((RESULTS/'protocol/summary.json').relative_to(ROOT)),
             'value':{'points':56,'probes':336,'maximum_error':p['maximum_numerical_error']},'scope':'Hypothetical controls; matched experimental fidelity missing'},
            {'id':'UP3','claim':'Bounded synthetic spin convergence','source':str((RESULTS/'convergence/summary.json').relative_to(ROOT)),
             'value':{'calls':69,'rows':66,'axes':6},'scope':'At most eight spins, ideal pulses, 0--0.4 ms; no material authorization'},
            {'id':'UP4','claim':'Paired SeQUeNCe/QuNetSim larger study','source':str((RESULTS/'larger/summary.json').relative_to(ROOT)),
             'value':{'arm_runs':256,'attempts':131072,'paired_comparisons':128,'maximum_mean_density_error':large['maximum_mean_density_error']},
             'scope':'Custom QuTiP backend; shared logical clock; no physical timing equivalence'},
            {'id':'UP5','claim':'Offline replay and latest test environment','source':'evidence/validation_extension/manifest.json',
             'value':{'replay_json':359,'replay_rng':11,'tests_passed':passed,'tests_skipped':skipped},
             'scope':'Author-operated same-machine checks; not independent scientific review'}]
    target=ROOT/'evidence/article_update_claim_map.json'
    target.write_text(json.dumps({'schema':'westquant_article_update_claim_map_v1','status':'pass','retrospective':True,
        'hardware_experiments':0,'claims':claims,'inputs':{str(p.relative_to(ROOT)):sha(p) for p in sources},
        'current_lab_source_sha256':identity['lab_source_sha256'],'current_evaluation_source_sha256':identity['evaluation_source_sha256'],
        'source_execution_git_base':manifest['execution_git_base'],'extension_sources_were_uncommitted_during_execution':True,
        'independent_scientific_review_completed':False},indent=2)+'\n')
    print('Verified five updated claim groups; generated numeric macros, two tables and evidence/article_update_claim_map.json')


if __name__=='__main__':main()
