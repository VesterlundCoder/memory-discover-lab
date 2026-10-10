"""Generate scientific figures solely from the retained extension result tables."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def rows(path):
    with path.open(newline='') as stream:return list(csv.DictReader(stream))


def save(fig,out,name):
    fig.savefig(out/(name+'.png'),dpi=180,bbox_inches='tight')
    fig.savefig(out/(name+'.pdf'),bbox_inches='tight')
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=Path('evaluation/results/validation_extension/selected'))
    parser.add_argument('--out',type=Path,default=Path('evaluation/results/validation_extension/figures'))
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    records=rows(args.results/'protocol/protocol_metrics.csv')
    fig,axes=plt.subplots(1,3,figsize=(12,3.5),layout='constrained')
    for case,label in [('thermal_background','Termiskt brus'),('noise_dominated','Brusdominerat')]:
        data=[r for r in records if r['case_id']==case];x=[float(r['storage_age_s'])*1000 for r in data]
        for ax,key in zip(axes,['conditional_detected_average_fidelity','signal_efficiency','noise_click_probability']):
            ax.plot(x,[float(r[key]) for r in data],marker='o',label=label)
    for ax,title in zip(axes,['Betingad medelfidelity','Signalens effektivitet','Sannolikhet för brusklick']):
        ax.set(xlabel='Lagringstid (ms)',title=title,xscale='symlog');ax.grid(alpha=.2)
    axes[0].set_ylim(.45,1);axes[0].legend(fontsize=9)
    fig.suptitle('Gemensam protokollmodell — syntetiska kontroller')
    save(fig,args.out,'protocol_joint')
    records=rows(args.results/'convergence/convergence.csv')
    fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
    names={'independent_solver':'Oberoende lösare','control_resolution':'Strang-delsteg','cluster_order':'CCE-klusterordning',
           'pair_cutoff':'Parkopplingsgräns (Å)','bath_size':'Antal badspinn','time_grid':'Tidsgrid: medelvärde av |L|'}
    for ax,(axis,title) in zip(axes.flat,names.items()):
        selected=[r for r in records if r['axis']==axis]
        for pulses in [0,1,4]:
            data=[r for r in selected if int(r['pulses'])==pulses and r['max_complex_error']]
            x=[1 if axis=='independent_solver' else float(r['level']) for r in data]
            ax.plot(x,[max(float(r['max_complex_error']),1e-17) for r in data],'o-',label=f'{pulses} pulser')
        ax.axhline(float(selected[0]['tolerance']),color='black',ls='--',lw=1,label='Gränsvärde')
        ax.set(title=title,yscale='log',ylabel='Avvikelse');ax.grid(alpha=.2)
        if axis=='independent_solver':ax.set_xticks([1],['expm / spektral'])
    axes.flat[0].legend(fontsize=8)
    fig.suptitle('Konvergens: syntetiska spinnbad, 0–0,4 ms; lägre nivåers fel kvarstår')
    save(fig,args.out,'spin_convergence')
    records=rows(args.results/'larger/paired_comparison.csv')
    fig,axes=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
    for rate,label,color in [(0,'Grundbrus 0/s','C0'),(5000,'Grundbrus 5 000/s','C1')]:
        data=[r for r in records if float(r['noise_rate_s_inv'])==rate and float(r['link_herald_probability'])==.75]
        ages=sorted(set(float(r['storage_age_s']) for r in data));fidelity=[];goodput=[]
        for age in ages:
            group=[r for r in data if float(r['storage_age_s'])==age]
            f=float(group[0]['expected_Bell_fidelity']);fidelity.append(f)
            goodput.append(float(group[0]['expected_success_per_attempt'])/.04 if f>=.8 else 0.)
            axes[1].scatter([1000*age]*len(group),[float(r['qualified_rate_per_s']) for r in group],s=16,color=color,alpha=.45)
        axes[0].plot(np.array(ages)*1000,fidelity,'o-',label=label,color=color)
        axes[1].plot(np.array(ages)*1000,goodput,'o-',label=label,color=color)
    axes[0].axhline(.8,color='black',ls='--',label='Kvalitetsgräns 0,8')
    axes[0].set(title='Modellens Bell-fidelity',ylabel='Betingad överlapp med Bell-tillstånd',ylim=(.2,1))
    axes[1].set(title='Godkända par per sekund',ylabel='Par/s')
    for ax in axes:ax.set_xlabel('Lagringstid (ms)');ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Två noder, heraldsannolikhet 0,75 — linjer: modell; punkter: åtta seeds')
    save(fig,args.out,'crosssim_larger')


if __name__=='__main__':main()
