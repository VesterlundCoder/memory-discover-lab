"""Step 3: deliberately unsafe local bypasses; no production guards changed."""
import copy
import math
import tempfile
from pathlib import Path
import numpy as np
from memorylab.models import evaluate
from memorylab.channels import apply
from memorylab.network import MemoryDevice, UnsupportedOperation
from memorylab.common import MissingData, UnsupportedPhysics
from memorylab.t2assessment import calculate
from memorylab.units import convert
from .common import LAB, read, write, source_path, hash_file, new_output, audit_identity, csv_rows

def run(config, output):
    out=new_output(output)
    rows=[]
    rejected=(ValueError, MissingData, UnsupportedPhysics, UnsupportedOperation)
    def probe(name, good, bad, bypass, impact, unit, native=True):
        good() # Positive control must work, otherwise rejecting everything could look useful.
        try:
            bad(); blocked=False; reason='accepted'
        except rejected as e:
            blocked=True; reason=type(e).__name__+': '+str(e)
        bypass()
        rows.append({'fault':name,'protected_blocked':blocked,'protected_reason':reason,
                     'positive_control_passed':True,'unsafe_bypass_accepted':True,
                     'impact':float(impact()),'impact_unit':unit,
                     'guard_location':'existing_lab' if native else 'new_evaluation_source_contract'})
    point=read(LAB/'baselines/teller2025/measured_point_profile.json')
    age=point['point']['end_to_end_age_s']
    wrong_age=10*age
    bypass=copy.deepcopy(point); bypass['point']['end_to_end_age_s']=wrong_age
    probe('measured_point_age_extrapolation',lambda:evaluate(point,[age]),lambda:evaluate(point,[wrong_age]),
          lambda:evaluate(bypass,[wrong_age]),lambda:wrong_age/age,'unsupported_age_factor')
    bypass=copy.deepcopy(point)
    wrong=copy.deepcopy(point)
    for stage in wrong['temperatures_K']: wrong['temperatures_K'][stage]=4
    bypass=copy.deepcopy(wrong); bypass['point']['temperature_K']=4
    probe('measured_point_temperature_extrapolation',lambda:evaluate(point,[age]),lambda:evaluate(wrong,[age]),
          lambda:evaluate(bypass,[age]),lambda:1,'unsupported_temperature_delta_K')
    rate={'method':'markov','evidence_kind':'hypothetical','provenance':[{'software_control':True}],
          'conditions':{'temperature_K':4.2},'rate_definition':'population_and_independent_pure_dephasing',
          'population_rate_s_inv':10,'pure_dephasing_rate_s_inv':20}
    bad=copy.deepcopy(rate);bad['rate_definition']='total_T2_reused_as_pure_dephasing';bad['pure_dephasing_rate_s_inv']=25
    unsafe=copy.deepcopy(bad);unsafe['rate_definition']=rate['rate_definition']
    probe('total_T2_double_counting',lambda:calculate(rate),lambda:calculate(bad),lambda:calculate(unsafe),
          lambda:100*abs(calculate(unsafe)['T2_s']/calculate(rate)['T2_s']-1),'T2_relative_error_percent')
    spin=read(LAB/'examples/molecular_spin_profile.json')
    bad=copy.deepcopy(spin);bad['additional_dephasing_independent_of_markov']=False
    unsafe=copy.deepcopy(bad);unsafe['additional_dephasing_independent_of_markov']=True
    probe('unreviewed_noise_independence',lambda:evaluate(spin,[0,.001]),lambda:evaluate(bad,[0,.001]),
          lambda:evaluate(unsafe,[0,.001]),lambda:1,'unsupported_independence_declarations')
    channels=evaluate(spin,[0,.001])
    probe('hypothetical_network_promotion',lambda:MemoryDevice(channels,True),lambda:MemoryDevice(channels),
          lambda:MemoryDevice(channels,True),lambda:len(channels),'synthetic_age_samples_promoted')
    rho=np.array([[.5,.5],[.5,.5]],complex)
    markov=read(LAB/'examples/atomic_ensemble_profile.json')
    markov['rates']['pure_dephasing']={'kind':'constant','rate_s_inv':1000,'valid_temperature_K':[1,300]}
    one=evaluate(markov,[.001])[0]; device=MemoryDevice([one],True)
    once=apply(one.conditional_kraus,rho)
    twice=apply(one.conditional_kraus,once)
    probe('absolute_age_as_increment',lambda:device.channel_at(.001),lambda:device.apply_increment(rho,.001),
          lambda:apply(one.conditional_kraus,once),lambda:np.max(abs(twice-once)),'density_matrix_max_error')
    with tempfile.TemporaryDirectory() as directory:
        p=Path(directory)/'source.json';p.write_text('{"T2_s":0.001}')
        item={'path':p.name,'sha256':hash_file(p)}
        original=p.read_bytes()
        def good():
            p.write_bytes(original);source_path(item,directory)
        def bad():
            p.write_text('{"T2_s":1.0}');source_path(item,directory)
        probe('source_bytes_modified',good,bad,lambda:read(p),lambda:1000,'forged_T2_factor',False)
    correct_age=convert(1,'ms','s')
    good=evaluate(markov,[correct_age])[0]
    wrong=evaluate(markov,[1])[0]
    unit_impact=float(np.max(abs(apply(good.conditional_kraus,rho)-apply(wrong.conditional_kraus,rho))))
    csv_rows(out/'faults.csv',rows)
    result={'step':3,'status':'pass' if all(r['protected_blocked'] and r['positive_control_passed'] for r in rows) else 'fault_gate_failed',
        'invalid_contract_cases':len(rows),'blocked_cases':sum(r['protected_blocked'] for r in rows),
        'positive_controls_passed':len(rows),'unsafe_bypasses_accepted':len(rows),
        'unit_conversion_control':{'input_value':1,'input_unit':'ms','converted_s':correct_age,
                                   'conversion_omitted_age_s':1,'density_matrix_max_error':unit_impact},
        'identity':audit_identity(config),
        'interpretation':'Constructed fault coverage only; not real-world researcher error incidence or a comparison with other workflow engines',
        'production_guards_modified':False}
    write(out/'summary.json',result)
    return result
