"""Run protocol -> convergence -> native cross-simulator pilot -> larger study."""
import argparse
from pathlib import Path
import sys
import subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'evaluation'),str(ROOT/'lab')]
from wqeval.common import read,write,audit_identity
from wqeval.protocol_validation import run as protocol
from wqeval.spin_convergence import run as convergence
from wqeval.crosssim import run as crosssim


def counts():
    base=ROOT/'evaluation/config/validation_extension'
    p,c=read(base/'protocol.json'),read(base/'convergence.json')
    def native(name):
        x=read(base/(name+'.json'))
        paired=len(x['background_rates_s_inv'])*len(x['storage_ages_s'])*len(x['herald_probabilities'])*len(x['seeds'])
        return {'paired_cases':paired,'arm_runs':2*paired,'attempts_per_arm_run':x['attempts'],'attempts_all_arms':2*paired*x['attempts']}
    return {'protocol_channel_age_points':len(p['cases'])*len(p['times_s']),
            'protocol_state_probes':6*len(p['cases'])*len(p['times_s']),
            'convergence_solver_calls':len(c['pulses'])*(2+len(c['control_substeps'])+len(c['cluster_orders'])+
                len(c['pair_cutoffs_angstrom'])+len(c['bath_sizes'])+len(c['time_grid_sizes'])),
            'pilot':native('crosssim_pilot'),'larger':native('crosssim_larger')}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--stage',choices=['all','protocol','convergence','pilot','larger'],default='all')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--count',action='store_true')
    parser.add_argument('--worker-stage',choices=['pilot','larger'],help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.count:
        import json
        print(json.dumps(counts(),indent=2));return 0
    if args.out is None:parser.error('--out is required unless --count is supplied')
    args.out.mkdir(parents=True,exist_ok=True)
    base=ROOT/'evaluation/config/validation_extension'
    configs={'protocol':'protocol','convergence':'convergence','pilot':'crosssim_pilot','larger':'crosssim_larger'}
    if args.worker_stage:
        name=args.worker_stage
        config=read(base/(configs[name]+'.json'))
        required=['protocol','convergence']+(['pilot'] if name=='larger' else [])
        result=crosssim(config,args.out/name,base,[read(args.out/x/'summary.json') for x in required])
        return 0 if result['status']=='pass' else 2
    results={}
    for name in configs:
        destination=args.out/name;config=read(base/(configs[name]+'.json'))
        required=name in ['protocol','convergence'] and args.stage in ['all','pilot','larger']
        required=required or (name=='pilot' and args.stage in ['all','larger'])
        required=required or args.stage in ['all',name]
        if not required:continue
        if (destination/'summary.json').exists() and args.resume:
            result=read(destination/'summary.json');identity=audit_identity(config)
            for key in ['configuration_sha256','evaluation_source_sha256','lab_source_sha256']:
                if result['provenance'][key]!=identity[key]:raise ValueError('Stale checkpoint: '+name+' '+key)
            print('Verified checkpoint:',name,flush=True)
        else:
            prerequisites=list(results.values())
            if any(r['status']!='pass' for r in prerequisites):
                write(args.out/'blocked.json',{'status':'blocked_prerequisite_gate','stage':name,'prerequisite_status':{k:v['status'] for k,v in results.items()}})
                return 2
            print('Running:',name,flush=True)
            if name=='protocol':result=protocol(config,destination,base)
            elif name=='convergence':result=convergence(config,destination)
            else:
                # QuNetSim is a singleton with native worker threads. Never restart
                # its network in the same interpreter after a completed stage.
                worker=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--out',str(args.out),
                                       '--worker-stage',name],timeout=900)
                if worker.returncode not in (0,2) or not (destination/'summary.json').exists():
                    raise RuntimeError('Native simulator worker failed: '+name)
                result=read(destination/'summary.json')
        results[name]=result
    summary={'status':'numerical_validation_passed_experimental_inconclusive' if all(r['status']=='pass' for r in results.values()) else 'numerical_gate_failed',
             'executed_stages':list(results),'stage_status':{k:r['status'] for k,r in results.items()},
             'planned_counts':counts(),'joint_experimental_validation_passed':False,'material_prediction_authorized':False,
             'network_timing_equivalence_claimed':False,'hardware_experiments':0}
    write(args.out/'summary.json',summary)
    print(summary['status'])
    return 0 if all(r['status']=='pass' for r in results.values()) else 2


if __name__=='__main__':raise SystemExit(main())
