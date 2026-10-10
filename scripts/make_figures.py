"""Regenerate manuscript figures from archived evidence, not typed plot values."""
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lab'))
from memorylab.experimental import parse_indexed_infidelity
from memorylab.channels import depolarizing, apply, I2, Z
def load(p): return json.loads(p.read_text())
def save(fig,name):
    fig.savefig(ROOT/'figures'/f'{name}.pdf',bbox_inches='tight')
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=180,bbox_inches='tight')
    plt.close(fig)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'pdf.fonttype':42,'font.family':'DejaVu Sans'})

# One compact diagram of the implemented data/model boundary.
fig,ax=plt.subplots(figsize=(9.2,4.2));ax.set_xlim(0,10);ax.set_ylim(0,4.9);ax.axis('off')
boxes={
 'source':(.2,3.6,2.7,.85,'Pinned source artifacts\nbytes, revision, checksum'),
 'catalog':(3.6,3.6,2.7,.85,'Typed catalog + review\nunits, conditions, evidence'),
 'gaps':(7,3.6,2.7,.85,'Unresolved observations\nretained; no physical inference'),
 'table':(.2,1.75,2.7,.95,'Reviewed table lookup\nprotocol-specific references'),
 'physics':(3.6,1.75,2.7,.95,'Specified physical model\nMarkov / spin bath / propagation'),
 'channel':(7,1.75,2.7,.95,'Write-store-read instrument\nKraus + erasure, domain checks'),
 'out':(3.6,.15,6.1,.85,'Archived observables and optional SeQUeNCe event workload\nsource and model hashes, age semantics, limits')}
for key,(x,y,w,h,txt) in boxes.items():
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.035',edgecolor='#2d536f',facecolor='#eff4f8' if key!='gaps' else '#faf0e4'))
 ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=9)
for a,b in [((2.9,4),(3.55,4)),((6.3,4),(6.95,4)),((4.45,3.6),(1.55,2.75)),((4.95,3.6),(4.95,2.75)),((6.35,2.2),(6.95,2.2)),((1.55,1.75),(4.1,1.05)),((4.95,1.75),(4.95,1.05)),((8.35,1.75),(8.35,1.05))]:
 ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,color='#2d536f',lw=1.2))
save(fig,'architecture')

# Experimental processed state fidelities, preserving the distinct encodings.
cache=ROOT/'lab/baselines/teller2025/cache/raw'
path=next(cache.rglob('4.csv'));time=next(cache.rglob('8a.csv'))
pathvals=parse_indexed_infidelity(path,5,['X','-X','Y','-Y','0','1'],'basis,cell')
timevals=parse_indexed_infidelity(time,10,['X','-X','Y','-Y','E','L'],'basis,cell',1)
hold=load(ROOT/'evidence/teller_holdout.json')
fig,axes=plt.subplots(1,2,figsize=(9.2,3.4),layout='constrained')
for ax,vals,labels,title in [(axes[0],pathvals,['1,2','3,4','5,6','7,8','9,10'],'(a) Path encoding'),
                           (axes[1],timevals,[str(i) for i in range(1,11)],'(b) Time-bin encoding')]:
 x=np.arange(vals.shape[1])
 for i,row in enumerate(vals):ax.scatter(x+(i-2.5)*.065,row,s=11,alpha=.65,color='#648ca8')
 ax.plot(x,vals.mean(axis=0),'o-',color='#183b57',markersize=4,label='Six-state mean')
 ax.set(xticks=x,xticklabels=labels,ylim=(.73,1.015),xlabel='Memory pair' if vals.shape[1]==5 else 'Memory cell',title=title)
 ax.grid(axis='y',alpha=.15)
axes[0].set_ylabel('Conditional target-state fidelity')
axes[1].axhline(hold['fitted_average_fidelity'],ls='--',color='#b56b30',label='Odd-cell calibration')
held=hold['comparisons'];axes[1].errorbar([r['cell']-1 for r in held],[r['observed'] for r in held],yerr=[r['experimental_sigma'] for r in held],fmt='none',ecolor='#b56b30',capsize=2)
axes[1].legend(fontsize=8,loc='lower left');save(fig,'teller_fidelities')

# Four distinct storage-efficiency curves: fit is a diagnostic, not spin T2.
fig,axes=plt.subplots(2,2,figsize=(9.2,6),layout='constrained')
for ax,seq in zip(axes.flat,['none','XX','XY4','XY16']):
 c=load(ROOT/f'lab/t2_data/processed/curves/pr2026_{seq}.json')
 e=load(ROOT/f'lab/t2_runs/deterministic/experimental_decay/pr2026_{seq}_exponential.json')
 s=load(ROOT/f'lab/t2_runs/deterministic/experimental_decay/pr2026_{seq}_stretched.json')
 t=np.array(c['times_s'])*1000
 ax.errorbar(t,np.array(c['values'])*100,yerr=np.array(c['standard_errors'])*100,fmt='.',ms=3,color='#183b57',alpha=.7,label='Released data')
 ax.plot(t,np.array(e['fitted_values'])*100,lw=1.2,color='#b56b30',label='Exponential')
 ax.plot(t,np.array(s['fitted_values'])*100,lw=1.2,ls='--',color='#377f72',label='Stretched')
 ax.set(title='No RF' if seq=='none' else seq,xlabel='Reported total delay (ms)',ylabel='Storage efficiency (%)')
 ax.grid(alpha=.15)
axes[0,0].legend(fontsize=8);save(fig,'pr_decay_diagnostics')

fig,axes=plt.subplots(1,2,figsize=(9.2,3.3),layout='constrained')
for n,label in [(0,'Free induction'),(1,'Ideal Hahn pulse')]:
 r=load(ROOT/f'lab/t2_runs/deterministic/spin_bath_{n}pulse.json')
 axes[0].plot(np.array(r['times_s'])*1000,r['envelope'],lw=1.7,label=label)
axes[0].axhline(np.exp(-1),color='gray',ls='--',lw=1,label='1/e')
axes[0].set(xlabel='Storage time (ms)',ylabel='Coherence magnitude',title='(a) Hypothetical spin-bath control',ylim=(-.02,1.08));axes[0].legend(fontsize=8)
curve=load(ROOT/'lab/t2_runs/deterministic/synthetic_control/curve.json')
fit=load(ROOT/'lab/t2_runs/deterministic/synthetic_control/fit.json')
t=np.array(curve['times_s']);phase=np.array(curve['phases_rad']);k=np.array(curve['counts_plus']);N=np.array(curve['trials']);m=phase==0
axes[1].errorbar(t[m]*1000,k[m]/N[m],yerr=np.sqrt((k[m]/N[m])*(1-k[m]/N[m])/N[m]),fmt='.',color='#183b57',label='Synthetic phase-0 counts')
axes[1].plot(t[m]*1000,np.array(fit['fitted_values'])[m],color='#b56b30',label='Count-likelihood fit')
axes[1].set(xlabel='Storage time (ms)',ylabel='Projection probability',title='(b) Known 1 ms count generator');axes[1].legend(fontsize=8)
for ax in axes:ax.grid(alpha=.15)
save(fig,'deterministic_controls')

# Independent seeds quantify MC variation under a fixed, hypothetical loss model.
from memorylab.network import wilson
summary=load(ROOT/'evidence/teller_summary.json')
data=[load(p) for p in sorted((ROOT/'lab/baselines/teller2025/sequence_runs').glob('*.json'))]
fig,ax=plt.subplots(figsize=(7.4,3.2),layout='constrained')
for i,r in enumerate(data):
 v=r['retrieved_pairs']/r['attempts'];lo,hi=wilson(r['retrieved_pairs'],r['attempts'])
 ax.errorbar(i,v*1e4,yerr=np.array([[v-lo],[hi-v]])*1e4,fmt='o',color='#183b57',capsize=4)
v=summary['network_retrieved_pairs']/summary['network_attempts'];lo,hi=summary['network_retrieved_fraction_95CI']
ax.errorbar(4,v*1e4,yerr=np.array([[v-lo],[hi-v]])*1e4,fmt='s',color='#b56b30',capsize=4)
ax.axhline(summary['network_expected_success_probability']*1e4,ls='--',color='#377f72',label='Analytic fixed-loss expectation')
ax.set(xticks=range(5),xticklabels=['Seed 10','Seed 11','Seed 12','Seed 13','Pooled'],ylabel=r'Retrieved pairs / attempt ($10^{-4}$)',ylim=(0,6.5))
ax.legend(fontsize=9);ax.grid(axis='y',alpha=.15);save(fig,'network_control')

# Supplemental example: a mean alone does not identify the channel.
f=summary['operating_point']['conditional_average_fidelity'];p=2*(1-f);q=3*p/4
dep=depolarizing(p);phase=[np.sqrt(1-q)*I2,np.sqrt(q)*Z]
bell=np.array([1,0,0,1],complex)/np.sqrt(2);rho=np.outer(bell,bell.conj())
def bellf(kraus):return float(np.real(bell.conj()@apply([np.kron(a,b) for a in kraus for b in kraus],rho)@bell))
result={'scope':'Constructive mean-fidelity nonidentifiability example; not two fits to all experimental states',
 'mean_fidelity':f,'depolarizing_p':p,'phase_flip_q':q,'Bell_fidelity_depolarizing':bellf(dep),
 'Bell_fidelity_phase_flip':bellf(phase),'mean_fidelity_phase_flip':1-2*q/3,
 'difference':bellf(phase)-bellf(dep)}
assert abs(result['mean_fidelity_phase_flip']-f)<1e-13
(ROOT/'evidence/mean_fidelity_nonidentifiability.json').write_text(json.dumps(result,indent=2)+'\n')
print('Five figures and constructive channel example regenerated')
