"""Step 4: bounded native runner scaling, resume consistency and failure probes."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
from memorylab.runner import enumerate_jobs,execute_job,run as native_run
from memorylab.common import digest
from .common import LAB,ROOT,read,write,new_output,audit_identity,csv_rows

def study_for(config,workers):
    return {'study_id':'system_performance_control_v1','stage':'software_smoke',
        'models':[{'id':'markov','task':'memory','profile':read(LAB/'examples/atomic_ensemble_profile.json')},
                  {'id':'finite_bath','task':'memory','profile':read(LAB/'examples/molecular_spin_profile.json')}],
        'times_s':config['times_s'],'replicates':config['replicates'],'master_seed':config['seed'],
        'backends':['analytic'],'grid':{'detuning_Hz':config['detunings_Hz']},
        'resources':{'max_workers':workers,'max_runs':config['max_runs'],'timeout_s':config['job_timeout_s']}}

def scientific_digest(directory):
    records=[]
    for p in sorted(Path(directory).glob('*/result.json')):
        r=read(p)
        # Runtime/log paths deliberately excluded; physics and seeds are covered
        # by the configuration hash and serialized channel bytes.
        raw=p.parent/'channels.json'
        records.append({'run_id':r['run_id'],'status':r['status'],'config_hash':r['config_hash'],
                        'channels':read(raw) if raw.exists() else None})
    return digest(records)

def run(config,output):
    out=new_output(output)
    if config['timing_repeats'] < 1 or not config['workers'] or any(w<1 or w>8 for w in config['workers']):
        raise ValueError('Positive repeats and workers in 1..8 required')
    env=dict(os.environ)
    for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[k]='1'
    env['PYTHONPATH']=str(ROOT/'evaluation')+os.pathsep+str(LAB)+os.pathsep+env.get('PYTHONPATH','')
    rows=[];records=[]
    for repeat in range(config['timing_repeats']):
        order=np.random.default_rng(config['seed']+repeat).permutation(config['workers']).tolist()
        for position,workers in enumerate(order):
            study=study_for(config,workers)
            tag=f'w{workers}_r{repeat}'
            sp=out/(tag+'_study.json');rp=out/(tag+'_measurement.json');jobs=out/tag
            write(sp,study)
            with (out/(tag+'_driver.log')).open('w') as log:
                subprocess.run([sys.executable,'-m','wqeval.perf_child',str(sp.resolve()),str(jobs.resolve()),str(rp.resolve())],
                    env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=config['driver_timeout_s'])
            r=read(rp);r['scientific_digest']=scientific_digest(jobs);records.append(r)
            rows.append({'workers':workers,'repeat':repeat,'order_position':position,'jobs':r['cold']['enumerated_run_count'],
                'cold_s':r['cold_s'],'resume_s':r['warm_s'],'cold_jobs_per_s':r['cold']['enumerated_run_count']/r['cold_s'],
                'resumed_runs':r['warm']['resumed_runs'],'parent_peak_rss_bytes':r['parent_peak_rss_bytes'],
                'largest_child_peak_rss_bytes':r['largest_terminated_child_peak_rss_bytes'],'scientific_digest':r['scientific_digest']})
    csv_rows(out/'performance.csv',rows)
    # Real native failures, not a separate imitation runner.
    study=study_for(config,1)
    bad=copy.deepcopy(study);bad['models']=bad['models'][:1]
    del bad['models'][0]['profile']['temperatures_K']['write']
    failed=execute_job(enumerate_jobs(bad)[0],out/'robustness_missing_parameter')
    timeout_job=copy.deepcopy(enumerate_jobs(study)[0]);timeout_job['timeout_s']=1e-6
    timed=execute_job(timeout_job,out/'robustness_timeout')
    partial_root=out/'robustness_partial_checkpoint'
    first=execute_job(enumerate_jobs(study)[0],partial_root)
    restored=native_run(study,partial_root)
    same=len({r['scientific_digest'] for r in records})==1
    passing=all(r['cold']['all_success'] and r['warm']['resumed_runs']==r['cold']['enumerated_run_count'] for r in records)
    robustness={'missing_parameter_status':failed['status'],'timeout_status':timed['status'],
                'partial_checkpoint_precompleted_status':first['status'],'restored_summary':restored,
                'scope':'Resume after one normally completed checkpoint; no forced crash, power-loss or filesystem corruption experiment'}
    passing &= failed['status']=='missing_data' and timed['status']=='timeout' and restored['all_success'] and restored['resumed_runs']==1
    result={'step':4,'status':'pass' if passing and same else 'benchmark_gate_failed',
        'worker_invariant_scientific_results':same,'robustness':robustness,
        'measurements':records,'identity':audit_identity(config),'native_threads_per_worker':1,
        'timing_scope':'Subprocess startup, native channel computation and artifact IO; resume is terminal-result checkpoint reuse',
        'memory_scope':'Parent peak and largest terminated child peak separately; no total concurrent peak estimate',
        'hardware_validation':False,'external_environment_validation':False}
    write(out/'summary.json',result)
    return result
