"""Paired native SeQUeNCe / QuNetSim protocol executions with external logical trace."""
import copy
import hashlib
import importlib.metadata
import math
import time
import zipfile
from pathlib import Path
import numpy as np
from memorylab.channels import MemoryChannel, I2, apply, encode
from memorylab.models import evaluate
from memorylab.protocol import readout_instrument
from memorylab.qunetsim_adapter import QuNetSimSession
from memorylab.sequence_adapter import apply_to_manager,seconds_to_ps
from memorylab.common import digest
from .protocol_validation import independent_instrument
from . import reference
from .common import new_output,write,read,source_path,audit_identity,csv_rows

BELL=np.array([1,0,0,1],complex)/math.sqrt(2)
INITIAL=np.outer(BELL,BELL.conj())


def stream_seed(master,seed,stream):
    value=f'{master}|{seed}|{stream}'.encode()
    return int.from_bytes(hashlib.sha256(value).digest()[:8],'little')


def external_trace(config,seed):
    manifest={name:stream_seed(config['master_seed'],seed,name) for name in ['herald','left_readout','right_readout']}
    return np.column_stack([np.random.default_rng(s).random(config['attempts']) for s in manifest.values()]),manifest


def model_case(config,base,noise,age):
    profile=read(source_path(config['profile'],base))
    profile['storage_model']='markov'
    profile['noise_budget']=[n for n in profile['noise_budget'] if n!='specified_nuclear_spin_bath']
    profile['rates']={key:{'kind':'constant','rate_s_inv':value,'valid_temperature_K':[1,300]}
                      for key,value in config['rates_s_inv'].items()}
    profile['equilibrium_excited_population']=.2;profile['detuning_Hz']=config['detuning_Hz']
    profile['io'].update(config['io'])
    detector=dict(config['detector'],base_rate_s_inv=noise)
    signal=evaluate(profile,[age])[0];accepted=readout_instrument(signal,detector)
    ref=independent_instrument(profile,detector,age)
    sigma=np.asarray(accepted.metadata['background_state'],complex)
    reset=[math.sqrt(sigma[i,i].real)*np.outer(I2[:,i],I2[:,j]) for i in range(2) for j in range(2)]
    noise_channel=MemoryChannel(reset,1,dict(signal.metadata))
    signal_super=reference.superoperator(profile,age)[0]
    reset_super=np.outer(sigma.reshape(-1,order='F'),np.array([1,0,0,1]))
    superops={'signal':signal_super,'noise':reset_super}
    channels={'signal':signal,'noise':noise_channel}
    expected={}
    for left in superops:
        for right in superops:
            # Independently apply each single-site superoperator to tensor matrix units.
            rho=np.zeros((4,4),complex)
            for a,b,c,d in np.ndindex(2,2,2,2):
                ea=np.zeros((2,2));eb=np.zeros((2,2));ea[a,b]=1;eb[c,d]=1
                rho+=INITIAL[2*a+c,2*b+d]*np.kron(reference.action(superops[left],ea),reference.action(superops[right],eb))
            expected[left[0]+right[0]]=rho
    p=accepted.success_probability
    weights={'s':signal.success_probability/p,'n':accepted.metadata['noise_click_probability']/p} if p else {'s':0,'n':0}
    mean=sum(weights[k[0]]*weights[k[1]]*rho for k,rho in expected.items())
    return signal,accepted,channels,superops,expected,float(np.real(BELL.conj()@mean@BELL)) if p else None


def branch(value,signal,accepted):
    if value<signal.success_probability:return 'signal'
    if value<accepted.success_probability:return 'noise'
    return 'loss'


def outcomes(trace,prob,signal,accepted):
    return [(bool(u[0]<prob),branch(u[1],signal,accepted),branch(u[2],signal,accepted)) for u in trace]


def summarize(arm,records,counts,rho_sum,max_error,elapsed,case,manifest,trace_sha,expected_fidelity):
    retrieved=sum(counts.values());observed=rho_sum/retrieved if retrieved else None
    return {'simulator':arm,'status':'success','case':case,'seed_manifest':manifest,'trace_sha256':trace_sha,
            'attempts':len(records),'heralded':sum(r['heralded'] for r in records),'retrieved_pairs':retrieved,
            'branch_pair_counts':counts,'density_sum':encode(rho_sum),
            'observed_conditional_Bell_fidelity':float(np.real(BELL.conj()@observed@BELL)) if retrieved else None,
            'expected_conditional_Bell_fidelity':expected_fidelity,
            'quality_qualified_pairs':retrieved if expected_fidelity is not None and expected_fidelity>=case['minimum_Bell_fidelity'] else 0,
            'max_density_error_against_matrix_unit_reference':max_error if retrieved else None,
            'logical_trace_sha256':digest(records),'runtime_s':elapsed}


def run_sequence(events,case,signal,accepted,channels,expected,manifest,trace_sha,fidelity):
    from sequence.kernel.timeline import Timeline
    from sequence.kernel.event import Event
    from sequence.kernel.process import Process
    start=time.perf_counter();interval=seconds_to_ps(case['attempt_interval_s'])
    delay=seconds_to_ps(signal.metadata['total_write_store_read_s']+accepted.metadata['readout_detector']['window_s'])
    if delay>=interval:raise ValueError('Single-slot protocol requires complete cycle < attempt interval')
    timeline=Timeline(stop_time=len(events)*interval+delay+1,formalism='density_matrix')
    manager=timeline.quantum_manager;keys=[manager.new(),manager.new()]
    class Protocol:
        def __init__(self):self.records=[];self.counts={k:0 for k in expected};self.rho_sum=np.zeros((4,4),complex);self.error=0.
        def attempt(self,index):
            h,left,right=events[index]
            self.records.append({'attempt':index,'heralded':h,'left':left,'right':right,
                                 'attempt_ps':timeline.now(),'readout_ps':timeline.now()+delay if h else None})
            if h:
                manager.set(keys,INITIAL)
                timeline.schedule(Event(timeline.now()+delay,Process(self,'retrieve',[index])))
        def retrieve(self,index):
            _,left,right=events[index]
            if left!='loss' and right!='loss':
                apply_to_manager(manager,keys[0],channels[left]);rho=apply_to_manager(manager,keys[1],channels[right])
                key=left[0]+right[0];self.counts[key]+=1;self.rho_sum+=rho
                self.error=max(self.error,float(np.max(abs(rho-expected[key]))))
            manager.set(keys,np.eye(4)/4)
    protocol=Protocol()
    for i in range(len(events)):timeline.schedule(Event(i*interval,Process(protocol,'attempt',[i])))
    timeline.init();timeline.run()
    result=summarize('SeQUeNCe',protocol.records,protocol.counts,protocol.rho_sum,protocol.error,time.perf_counter()-start,
                     case,manifest,trace_sha,fidelity)
    result['native_events_executed']=timeline.run_counter
    return result


def run_qunetsim(session,events,case,signal,accepted,superops,expected,manifest,trace_sha,fidelity):
    start=time.perf_counter();interval=seconds_to_ps(case['attempt_interval_s'])
    delay=seconds_to_ps(signal.metadata['total_write_store_read_s']+accepted.metadata['readout_detector']['window_s'])
    if delay>=interval:raise ValueError('Single-slot protocol requires complete cycle < attempt interval')
    counts={k:0 for k in expected};rho_sum=np.zeros((4,4),complex);error=0.;records=[]
    transfers=session.backend.transfers
    for i,(h,left,right) in enumerate(events):
        records.append({'attempt':i,'heralded':h,'left':left,'right':right,
                        'attempt_ps':i*interval,'readout_ps':i*interval+delay if h else None})
        if not h:continue
        a,b=session.load_bell()
        if left!='loss' and right!='loss':
            session.backend.apply_superoperator(a,superops[left]);session.backend.apply_superoperator(b,superops[right])
            rho=session.backend.joint_state([a,b]);key=left[0]+right[0];counts[key]+=1;rho_sum+=rho
            error=max(error,float(np.max(abs(rho-expected[key]))))
        a.release();b.release()
        if session.backend.groups:raise ValueError('Consumed/erased qubits left stale joint states')
    result=summarize('QuNetSim',records,counts,rho_sum,error,time.perf_counter()-start,case,manifest,trace_sha,fidelity)
    result['native_quantum_packet_transfers']=session.backend.transfers-transfers
    if result['native_quantum_packet_transfers']!=result['heralded']:
        raise ValueError('QuNetSim did not execute every heralded packet transfer')
    return result


def run(config,out,base,stage_prerequisites):
    if any(r.get('status')!='pass' for r in stage_prerequisites):
        raise ValueError('Protocol and convergence numerical gates must pass before cross-simulator expansion')
    if config.get('prerequisite_pilot_required') and len(stage_prerequisites)<3:
        raise ValueError('Larger study requires a passed cross-simulator pilot')
    for field in ('seeds','background_rates_s_inv','storage_ages_s','herald_probabilities'):
        values=config[field]
        if not values or len(values)!=len(set(values)) or not np.isfinite(values).all():
            raise ValueError('Nonempty unique finite study levels required: '+field)
    n=config['attempts']
    if isinstance(n,bool) or not isinstance(n,int) or not 1<=n<=100000:
        raise ValueError('Bounded integer attempt budget required')
    if any(a<0 for a in config['storage_ages_s']) or any(p<0 or p>1 for p in config['herald_probabilities']):
        raise ValueError('Invalid age or herald probability')
    out=new_output(out);(out/'runs').mkdir();(out/'traces').mkdir()
    session=QuNetSimSession();records=[];pairs=[];failures=[]
    try:
        for seed in config['seeds']:
            trace,manifest=external_trace(config,seed)
            trace_sha=hashlib.sha256(trace.astype('<f8').tobytes()).hexdigest()
            np.save(out/'traces'/f'seed_{seed}.npy',trace,allow_pickle=False)
            for noise,age,prob in __import__('itertools').product(config['background_rates_s_inv'],config['storage_ages_s'],config['herald_probabilities']):
                case={'noise_rate_s_inv':noise,'storage_age_s':age,'link_herald_probability':prob,
                      'attempt_interval_s':config['attempt_interval_s'],'minimum_Bell_fidelity':config['minimum_Bell_fidelity'],'seed':seed}
                signal,accepted,channels,superops,expected,fidelity=model_case(config,base,noise,age)
                events=outcomes(trace,prob,signal,accepted)
                case_id=digest(case)[:16];arm_results=[]
                for name,fn in [('sequence',lambda:run_sequence(events,case,signal,accepted,channels,expected,manifest,trace_sha,fidelity)),
                                ('qunetsim',lambda:run_qunetsim(session,events,case,signal,accepted,superops,expected,manifest,trace_sha,fidelity))]:
                    try:r=fn()
                    except (ValueError,TimeoutError,RuntimeError) as e:
                        r={'simulator':name,'case':case,'status':'runtime_error','error':str(e)};failures.append(r)
                    write(out/'runs'/f'{case_id}_{name}.json',r);records.append(r);arm_results.append(r)
                a,b=arm_results
                if a['status']=='success' and b['status']=='success':
                    density_error=float(np.max(abs(np.asarray(a['density_sum']['real'])+1j*np.asarray(a['density_sum']['imag'])-
                                                np.asarray(b['density_sum']['real'])-1j*np.asarray(b['density_sum']['imag']))))/max(1,a['retrieved_pairs'])
                    same=all(a[k]==b[k] for k in ['heralded','retrieved_pairs','branch_pair_counts','quality_qualified_pairs','logical_trace_sha256'])
                    local=max(a['max_density_error_against_matrix_unit_reference'] or 0,b['max_density_error_against_matrix_unit_reference'] or 0)
                    passed=same and max(local,density_error)<=config['density_tolerance']
                    pairs.append({'case_id':case_id,**case,'counts_and_trace_identical':same,'mean_density_error':density_error,
                                  'local_max_density_error':local,'retrieved_pairs':a['retrieved_pairs'],
                                  'expected_success_per_attempt':prob*accepted.success_probability**2,
                                  'expected_Bell_fidelity':fidelity,'quality_qualified_pairs':a['quality_qualified_pairs'],
                                  'qualified_rate_per_s':a['quality_qualified_pairs']/(config['attempts']*config['attempt_interval_s']),
                                  'sequence_runtime_s':a['runtime_s'],'qunetsim_runtime_s':b['runtime_s'],
                                  'gate':'pass' if passed else 'fail'})
                else:pairs.append({'case_id':case_id,**case,'gate':'inconclusive'})
            print(f'Cross-simulator seed {seed} complete; {len(records)} arm runs retained',flush=True)
    finally:session.close()
    planned=2*len(config['seeds'])*len(config['background_rates_s_inv'])*len(config['storage_ages_s'])*len(config['herald_probabilities'])
    summary={'status':'pass' if len(records)==planned and not failures and all(p['gate']=='pass' for p in pairs) else 'fail',
             'planned_arm_runs':planned,'attempted_arm_runs':len(records),'successful_arm_runs':sum(r['status']=='success' for r in records),
             'failed_arm_runs':len(failures),'paired_comparisons':len(pairs),
             'attempts_per_arm_run':config['attempts'],'total_attempts_all_arms':len(records)*config['attempts'],
             'maximum_mean_density_error':max((p.get('mean_density_error',0) for p in pairs),default=0),
             'all_counts_and_logical_traces_identical':all(p.get('counts_and_trace_identical',False) for p in pairs),
             'total_retrieved_pairs_all_arms':sum(r.get('retrieved_pairs',0) for r in records),
             'native_SeQUeNCe_events':sum(r.get('native_events_executed',0) for r in records),
             'native_QuNetSim_quantum_packet_transfers':sum(r.get('native_quantum_packet_transfers',0) for r in records),
             'simulator_versions':{n:importlib.metadata.version(n) for n in ['sequence','qunetsim','qutip']},
             'hardware_validated':False,'evidence_kind':'hypothetical','network_timing_equivalence_claimed':False,
             'scope':'single-slot two-node transport and memory instruments; native protocol stacks, shared external logical clock',
             'limitations':['QuNetSim uses a custom QuTiP density backend, not its stock EQSN backend',
                            'Native QuNetSim wall-clock scheduling is not a physical clock',
                            'No routing, swapping, contention, finite fiber propagation, or detector double clicks',
                            'Goodput uses the model ensemble fidelity gate, not hidden per-trial signal labels'],
             'prerequisite_configuration_hashes':[r['provenance']['configuration_sha256'] for r in stage_prerequisites],
             'provenance':audit_identity(config,[source_path(config['profile'],base)])}
    fields=list(dict.fromkeys(key for row in pairs for key in row))
    csv_rows(out/'paired_comparison.csv',[{k:r.get(k) for k in fields} for r in pairs])
    write(out/'failures.json',failures)
    with zipfile.ZipFile(out/'raw_runs_and_traces.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for directory in ('runs','traces'):
            for path in sorted((out/directory).iterdir()):archive.write(path,path.relative_to(out))
    summary['raw_archive_sha256']=hashlib.sha256((out/'raw_runs_and_traces.zip').read_bytes()).hexdigest()
    write(out/'summary.json',summary)
    return summary
