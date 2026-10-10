"""Vector figure from the retained Bradley measurements and calibrated parameters."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
results=ROOT/'evaluation/results/bradley2022-nv0'
summary=json.loads((results/'summary.json').read_text())
with (results/'model_vs_observables.csv').open(newline='') as f:rows=list(csv.DictReader(f))
plt.rcParams.update({'font.size':12,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})
fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
for ax,name,label in zip(axes,('equatorial_length','X'),('Transverse Bloch length',r'$\langle X\rangle$')):
    points=[r for r in rows if r['observable']==name]
    for partition,color in [('calibration','#2474a8'),('heldout','#d47424')]:
        p=[r for r in points if r['partition']==partition]
        ax.errorbar([1000*float(r['time_s']) for r in p],[float(r['observed']) for r in p],
                    yerr=[float(r['reported_error']) for r in p],fmt='o',color=color,label=partition)
    times=np.linspace(0,max(float(r['time_s']) for r in points),800)
    par=summary['parameters'];decay=np.exp(-(times/par['tau_s'])**par['stretch_exponent'])
    if name=='equatorial_length':model=par['signal_amplitude']*decay
    else:
        phase=2*np.pi*summary['fixed_rotating_frame_frequency_Hz']*times
        c,s=summary['ramsey_cos_sin_coefficients'];model=decay*(c*np.cos(phase)+s*np.sin(phase))
    ax.plot(1000*times,model,color='#222222',label='effective model')
    ax.set(xlabel='Free evolution (ms)',ylabel=label);ax.legend(fontsize=10)
fig.suptitle('Bradley 2022: retrospective split; source error bars')
out=ROOT/'figures/validation_extension';out.mkdir(exist_ok=True,parents=True)
fig.savefig(out/'bradley_observables.pdf',bbox_inches='tight')
fig.savefig(out/'bradley_observables.png',dpi=180,bbox_inches='tight')
plt.close(fig)
