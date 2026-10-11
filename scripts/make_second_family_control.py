"""Create an explicitly synthetic one-spin control from a closed-form solution."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.constants import h,k
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'evaluation/data/software_control';out.mkdir(parents=True,exist_ok=True)
p=json.loads((ROOT/'lab/examples/molecular_spin_profile.json').read_text())
p['control']={'cpmg_pulses':0}
(out/'model.json').write_text(json.dumps(p,indent=2)+'\n')
A=p['spin_bath']['nuclei'][0]['hyperfine_Hz'][2][2]
z=p['spin_bath']['nuclei'][0]['zeeman_vector_Hz'][2]
T=p['temperatures_K']['storage']
times=np.linspace(0,.001,41)
# Bath eigenvalues +/-z/2; central m0-m1=1. Closed-form FID.
polarization=-np.tanh(h*z/(2*k*T))
L=np.cos(np.pi*A*times)-1j*polarization*np.sin(np.pi*A*times)
with (out/'curve.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['time_s','real','imag','sem_complex'])
    for t,l in zip(times,L):w.writerow([t,l.real,l.imag,.01])
def source(name):return {'path':name,'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()}
config={'observable':'complex_pure_dephasing_coherence','includes_population_relaxation':False,
    'evidence_kind':'hypothetical','curve':source('curve.csv'),'model':source('model.json'),
    'review':{'reviewer':'software_control_generator','source_location':'scripts/make_second_family_control.py',
              'normalization':'L(0)=1','observable_mapping':'closed-form pure-dephasing FID; no experimental observations'},
    'conditions':{'temperature_K':T,'control':p['control'],'field_and_frame':'specified nuclear Zeeman vector in lab frame',
                  'composition_and_isotopes':'one explicitly hypothetical C-13 spin'},
    'gate':{'kind':'max_complex_residual_over_sem','threshold':3},
    'optical_interface_review':{'reviewer':'software_control_generator','source_location':'chosen example profile',
                                'evidence_kind':'hypothetical'},
    'network_workload':{'attempts':10000,'link_herald_probability':.1,'attempt_interval_s':.001,
                        'storage_age_s':float(times[20]),'minimum_Bell_fidelity':.8},'seed':20261010}
(out/'case.json').write_text(json.dumps(config,indent=2)+'\n')
print(out/'case.json')
