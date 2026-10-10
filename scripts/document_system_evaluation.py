"""Generate paper tables and an auditable claim map from executed steps 1–4."""
import csv,json,hashlib,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'evaluation/results'
OUT=ROOT/'evaluation/paper';OUT.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads((ROOT/p).read_text())
def rows(p):
 with (ROOT/p).open(newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def write(p,x):(ROOT/p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def tex(name,body):(OUT/name).write_text(body+'\n')
def num(x):return f'{x:.6g}'
def sci(x):
 if x==0:return '$0$'
 a,b=f'{x:.3e}'.split('e');return '$'+a+r'\times10^{'+str(int(b))+'}$'
paths={'step1':'evaluation/results/step1-executed/summary.json',
       'step2':'evaluation/results/step2-confirmation/summary.json',
       'step3':'evaluation/results/step3-confirmation/summary.json',
       'step4':'evaluation/results/step4-executed/summary.json'}
s={k:read(p) for k,p in paths.items()};a,b,c,d=[s[k] for k in paths]
assert a['status']=='pass' and a['channel_age_points']==73 and a['processed_fidelity_values']==90
assert max(a[k] for k in ['max_full_choi_error','max_state_error','max_fidelity_error','max_acceptance_error','max_processed_value_error'])<=a['tolerance']
assert b['software_control_only'] and not b['physical_validation_passed'] and b['points']==41
assert c['status']=='pass' and c['blocked_cases']==7 and c['positive_controls_passed']==7
assert d['status']=='pass' and d['worker_invariant_scientific_results']
assert len({v['identity']['evaluation_source_sha256'] for v in s.values()})==1
perf=rows('evaluation/results/step4-executed/performance.csv')
assert len(perf)==9 and sum(int(r['jobs']) for r in perf)==108 and sum(int(r['resumed_runs']) for r in perf)==108
assert len({r['scientific_digest'] for r in perf})==1
faults=rows('evaluation/results/step3-confirmation/faults.csv')
assert len(faults)==7 and all(r['protected_blocked']=='True' and r['positive_control_passed']=='True' for r in faults)
pending=read('evaluation/results/step2-physical-pending/summary.json')
assert not pending['physical_validation_passed'] and not pending['network_exported']
ci=read('evidence/core_ci_verification.json')
assert sha('evidence/core_ci_job.log')==ci['log_sha256']
assert ci['conclusion']=='success' and ci['core_tests']==7
assert ci['step1_max_full_choi_error']<=a['tolerance']
head=r'\begin{table}[htbp]\centering\small\begin{tabular}{p{.62\linewidth}r}\toprule Quantity & Result\\\midrule'+'\n'
body=[('Profiles / channel-age points','13 / 73'),('Processed fidelity values','90'),('Maximum full Choi discrepancy',sci(a['max_full_choi_error'])),('Maximum six-state output discrepancy',sci(a['max_state_error'])),('Maximum conditional average-fidelity discrepancy',sci(a['max_fidelity_error'])),('Maximum acceptance / processed-value discrepancy','$0$ / $0$'),('Declared numerical gate',sci(a['tolerance']))]
tex('comparison.tex',head+'\n'.join(k+' & '+v+r'\\' for k,v in body)+r'\bottomrule\end{tabular}\caption{Step 1: matched numerical and processed-data comparison. Twelve profiles are supplied software controls; one profile is an experiment-constrained point.}\label{tab:systemcomparison}\end{table}')
head=r'\begin{table}[htbp]\centering\small\begin{tabular}{r r r r}\toprule Workers & Cold median [min,max] (s) & Resume median (s) & Median jobs/s\\\midrule'+'\n'
p_rows=[]
for w in [1,2,4]:
 r=[x for x in perf if int(x['workers'])==w];cold=[float(x['cold_s']) for x in r];warm=[float(x['resume_s']) for x in r]
 p_rows.append(f"{w} & {statistics.median(cold):.4f} [{min(cold):.4f}, {max(cold):.4f}] & {statistics.median(warm):.5f} & {statistics.median([float(x['cold_jobs_per_s']) for x in r]):.3f}"+r'\\')
tex('performance.tex',head+'\n'.join(p_rows)+r'\bottomrule\end{tabular}\caption{Step 4: three local cold studies and three checkpoint-reuse passes per worker count, with 12 jobs per study. Bounds are observed minima/maxima, not confidence intervals.}\label{tab:systemperformance}\end{table}')
labels={'measured_point_age_extrapolation':'Operating-point age extrapolation','measured_point_temperature_extrapolation':'Operating-point temperature extrapolation','total_T2_double_counting':'Total coherence rate reused as pure dephasing','unreviewed_noise_independence':'Unreviewed noise independence','hypothetical_network_promotion':'Hypothetical channel without opt-in','absolute_age_as_increment':'Absolute-age map applied incrementally','source_bytes_modified':'Modified source bytes'}
impacts={'measured_point_age_extrapolation':r'$10\times$ unsupported age','measured_point_temperature_extrapolation':'1 K unsupported shift','total_T2_double_counting':r'16.667\% conditional $T_2$ error','unreviewed_noise_independence':'One unsupported declaration','hypothetical_network_promotion':'Two hypothetical age samples','absolute_age_as_increment':'0.097247 maximum element error','source_bytes_modified':r'$1000\times$ forged source value'}
tex('faults.tex',r'{\small\begin{longtable}{p{.37\linewidth}p{.16\linewidth}p{.38\linewidth}}\toprule Constructed fault & Guarded result & Accepted unsafe-bypass consequence\\\midrule\endhead'+'\n'+'\n'.join(labels[r['fault']]+' & Blocked & '+impacts[r['fault']]+r'\\' for r in faults)+r'\bottomrule\caption{Step 3: all seven valid positive controls pass; all invalid cases are rejected. Consequences have distinct units and are not aggregated into an accuracy score.}\label{tab:systemfaults}\end{longtable}}')
claims=[{'id':'SE1','claim':'Matched reference agreement','source':paths['step1'],'value':a['max_full_choi_error'],'scope':'Specified equations and processed-data consistency'},
 {'id':'SE2','claim':'Second-family software control','source':paths['step2'],'value':b['max_normalized_error'],'scope':'Synthetic curve and hypothetical write/read; no physical validation'},
 {'id':'SE2P','claim':'Second physical-family case remains blocked','source':'evaluation/results/step2-physical-pending/summary.json','value':pending['status'],'scope':'Missing reviewed experimental inputs'},
 {'id':'SE3','claim':'Constructed fault coverage','source':paths['step3'],'value':c['blocked_cases'],'scope':'Seven selected faults, not empirical error incidence'},
 {'id':'SE4','claim':'Local performance and checkpoint consistency','source':paths['step4'],'value':108,'scope':'Nine bounded cold studies, one Linux environment; no large-scale claim'},
 {'id':'SECI','claim':'Core fresh-checkout tests and automatic retrieval passed','source':'evidence/core_ci_verification.json','value':read('evidence/core_ci_verification.json')['conclusion'],'scope':'Seven core tests and step 1; not colleague-led physical review'}]
manifest={'schema':'westquant_system_paper_evaluation_v1','retrospective':True,'hardware_experiments':0,'ML_training_runs':0,
 'release_commit_for_core_ci':'de52b32f0c34a05cf4f6a0c01bca6ee087e6cb67','claims':claims,
 'runs':{k:{'status':v['status'],'at_utc':v['identity']['at_utc'],'configuration_sha256':v['identity']['configuration_sha256'],
 'evaluation_source_sha256':v['identity']['evaluation_source_sha256'],'lab_source_sha256':v['identity']['lab_source_sha256'],'source':paths[k],'sha256':sha(paths[k])} for k,v in s.items()},
 'performance_cold_jobs':108,'performance_checkpoint_reuses':108,
 'validation_limitations':['Second experimental physical-family baseline remains pending','One synthetic second-family case and seven selected fault cases','Local small-model benchmark with three repeats per worker count','Human independent reproduction and scientific review remain pending']}
write('evidence/system_evaluation_claim_map.json',manifest)
print('Validated executed evidence and generated three LaTeX tables and claim map')
