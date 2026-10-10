"""Compare explicit scientific fields while reporting execution provenance separately."""
import csv, math
from pathlib import Path
from .common import read, write, hash_file
from memorylab.common import canonical

def numeric_compare(a,b,path='',atol=1e-10,rtol=1e-10):
    if isinstance(a,bool) or isinstance(b,bool):
        if type(a) is not type(b) or a!=b:raise ValueError('Boolean mismatch: '+path)
    elif isinstance(a,(int,float)) and isinstance(b,(int,float)):
        if not math.isfinite(a) or not math.isfinite(b):raise ValueError('Nonfinite value: '+path)
        if isinstance(a,int) and isinstance(b,int):equal=a==b
        else:equal=math.isclose(a,b,abs_tol=atol,rel_tol=rtol)
        if not equal:raise ValueError(f'Numeric mismatch: {path}: {a} != {b}')
    elif type(a) is not type(b):raise ValueError('Type mismatch: '+path)
    elif isinstance(a,dict):
        if set(a)!=set(b):raise ValueError('Field mismatch: '+path)
        for k in sorted(a):numeric_compare(a[k],b[k],path+'/'+k,atol,rtol)
    elif isinstance(a,list):
        if len(a)!=len(b):raise ValueError('Length mismatch: '+path)
        for i,(x,y) in enumerate(zip(a,b)):numeric_compare(x,y,path+'/'+str(i),atol,rtol)
    elif a!=b:raise ValueError('Value mismatch: '+path)

def portable_results(directory):
    """Full channel/config payload without execution-derived IDs or environments."""
    records=[]
    for p in Path(directory).glob('*/result.json'):
        r=read(p);job=read(p.parent/'job.json');config=job['config']
        physical={k:v for k,v in config.items() if k not in ['software_version','source_sha256','environment']}
        raw=p.parent/'channels.json'
        records.append({'configuration':physical,'status':r['status'],
                        'channels':read(raw) if raw.exists() else None})
    if not records:raise ValueError('No scientific jobs to compare')
    return sorted(records,key=lambda r:canonical(r['configuration']))

def _csv(path):
    with Path(path).open(newline='') as f:raw=list(csv.DictReader(f))
    def value(x):
        if x in ['True','False']:return x=='True'
        try:return float(x)
        except ValueError:return x
    return [{k:value(v) for k,v in row.items()} for row in raw]

def projection(directory):
    directory=Path(directory);s=read(directory/'summary.json');step=s['step']
    identity=s['identity']
    p={'configuration':identity['configuration'],'input_hashes':sorted(x['sha256'] for x in identity['inputs'])}
    if step in [1,2,3]:
        p['summary']={k:v for k,v in s.items() if k not in ['identity','median_construction_s']}
        names={1:['channel_comparison.csv','data_comparison.csv'],2:['model_vs_curve.csv'],3:['faults.csv']}[step]
        for name in names:
            rows=_csv(directory/name)
            if step==3:
                rows=[{k:v for k,v in row.items() if k!='protected_reason'} for row in rows]
            p[name]=rows
        if step==1:p['cases']=read(directory/'cases.json')
        if step==2 and s['network_exported']:p['channel_payload']=read(directory/'memory_device.json')
    elif step==4:
        def status(x):return {k:v for k,v in x.items() if k!='output'}
        p['summary']={k:v for k,v in s.items() if k not in ['identity','measurements','robustness']}
        p['robustness']={**s['robustness'],'restored_summary':status(s['robustness']['restored_summary'])}
        # Full portable payload is mandatory: a legacy source-dependent digest
        # alone is insufficient to compare computations across source versions.
        p['scientific_results']=read(directory/'scientific_results.json')
        rows=_csv(directory/'performance.csv')
        p['studies']=sorted([{k:r[k] for k in ['workers','repeat','order_position','jobs','resumed_runs']} for r in rows],key=lambda r:(r['repeat'],r['workers']))
        p['statuses']=[{'cold':status(x['cold']),'warm':status(x['warm'])} for x in s['measurements']]
    else:raise ValueError('Unsupported evaluation step')
    return p

def compare(reference,actual,require_same_source=False,atol=1e-10,rtol=1e-10):
    if not 0<=atol<=1e-8 or not 0<=rtol<=1e-8:raise ValueError('Tolerance must be in 0..1e-8')
    a=read(Path(reference)/'summary.json');b=read(Path(actual)/'summary.json')
    code={k:{'reference':a['identity'][k],'actual':b['identity'][k],
             'matches':a['identity'][k]==b['identity'][k]} for k in ['evaluation_source_sha256','lab_source_sha256']}
    if require_same_source and not all(x['matches'] for x in code.values()):raise ValueError('Source fingerprint mismatch')
    if a['status'] not in ['pass','model_curve_gate_pass'] or b['status'] not in ['pass','model_curve_gate_pass']:
        raise ValueError('A blocked or failed evaluation cannot pass reproduction')
    numeric_compare(projection(reference),projection(actual),atol=atol,rtol=rtol)
    return {'status':'pass','step':a['step'],'absolute_tolerance':atol,'relative_tolerance':rtol,
            'source_fingerprints':code,'same_source_required':require_same_source,
            'reference_summary_sha256':hash_file(Path(reference)/'summary.json'),
            'actual_summary_sha256':hash_file(Path(actual)/'summary.json'),
            'excluded_from_numeric_equality':['UTC timestamps','input/output/temp path strings','environment versions (reported separately)',
                'timing/order-arm measurements','RSS/CPU measurements','source-dependent run IDs and scientific digests (portable payload compared)',
                'exception diagnostic path text'],
            'scope':'Scientific/configuration equality at specified tolerances, not equal performance or independent physical validation'}
