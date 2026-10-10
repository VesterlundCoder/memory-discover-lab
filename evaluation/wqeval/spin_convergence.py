"""Bounded, explicitly synthetic convergence studies before bath expansion."""
import copy
import itertools
import math
import time
import numpy as np
from scipy.linalg import expm
from memorylab.spin import bath_hamiltonians, exact_coherence
from memorylab.backends import pycce_coherence
from memorylab.common import digest
from .common import new_output, write, csv_rows, audit_identity


def synthetic_bath(count):
    nuclei = []
    # Nested, noncommuting weak-tail control; this is not a diamond lattice or a material sample.
    gyro = 6.72828532  # PyCCE 13C, rad/ms/G; retained convention, not a fitted parameter.
    field = .0002
    for i in range(count):
        radius = 3.5*1.7**i
        angle = .8*i
        position = [radius*math.cos(angle), radius*math.sin(angle), .3*radius]
        scale = (3.5/radius)**3
        tensor = np.zeros((3,3));tensor[2] = np.array([1600, 300, 2400])*scale
        nuclei.append({'isotope_id':'C-13', 'spin_I':.5, 'frame':'lab', 'position_angstrom':position,
                       'zeeman_vector_Hz':[0,0,-gyro*field*1e7/(2*np.pi)], 'hyperfine_Hz':tensor.tolist()})
    # Supply every pair, including zeros; PyCCE otherwise fills absent pairs from dipoles.
    pairs = []
    for i,j in itertools.combinations(range(count),2):
        strength = 120*.25**(i+j-1)
        pairs.append({'sites':[i,j], 'coupling_Hz':(strength*np.diag([1,1,-2])).tolist()})
    return {'central_m':[-.5,.5], 'bath_initialization':'maximally_mixed', 'max_dimension':256,
            'nuclei':nuclei, 'pairs':pairs,
            'center':{'spin_S':.5,'alpha_index':0,'beta_index':1,'position_angstrom':[0,0,0],
                      'gyro_rad_s_T':-176085970500,'zfs_Hz':np.zeros((3,3)).tolist()},
            'magnetic_field_T':[0,0,field], 'r_bath_angstrom':max(np.linalg.norm(n['position_angstrom']) for n in nuclei)+1,
            'r_dipole_angstrom':2*max(np.linalg.norm(n['position_angstrom']) for n in nuclei)+1,
            'order':min(count,4), 'nbstates':0, 'method':'cce', 'require_explicit_zeeman_match':True}


def spectral_coherence(bath, times, pulses=0):
    h, h0, h1 = bath_hamiltonians(bath)
    eig = [np.linalg.eigh(a) for a in (h0,h1)]
    if bath.get('bath_initialization') != 'maximally_mixed':
        raise ValueError('Spectral reference in this study requires maximally mixed bath')
    d = len(h)
    if pulses == 0:
        a, va = eig[0];b, vb = eig[1]
        weights = abs(va.conj().T@vb)**2/d
        return np.array([np.sum(weights*np.exp(-2j*np.pi*(a[:,None]-b)*t)) for t in times])
    def u(which, duration):
        e,v = eig[which];return (v*np.exp(-2j*np.pi*e*duration))@v.conj().T
    result = []
    for t in times:
        cuts = [0]+[t*(j+.5)/pulses for j in range(pulses)]+[t]
        ua,ub = np.eye(d,dtype=complex),np.eye(d,dtype=complex)
        for segment,(left,right) in enumerate(zip(cuts[:-1],cuts[1:])):
            ua = u(segment%2,right-left)@ua
            ub = u(1-segment%2,right-left)@ub
        result.append(np.trace(ua@ub.conj().T)/d)
    return np.array(result)


def split_operator_coherence(bath,times,pulses,substeps):
    h,h0,h1 = bath_hamiltonians(bath);d = len(h)
    result = []
    for t in times:
        cuts = [0]+[t*(j+.5)/pulses for j in range(pulses)]+[t] if pulses else [0,t]
        ua,ub = np.eye(d,dtype=complex),np.eye(d,dtype=complex)
        for segment,(left,right) in enumerate(zip(cuts[:-1],cuts[1:])):
            dt = (right-left)/substeps
            half = expm(-1j*np.pi*h*dt)
            props = [np.linalg.matrix_power(half@expm(-2j*np.pi*(a-h)*dt)@half,substeps) for a in (h0,h1)]
            ua = props[segment%2]@ua;ub = props[1-segment%2]@ub
        result.append(np.trace(ua@ub.conj().T)/d)
    return np.array(result)


def run(config,out):
    out = new_output(out);rows=[];curves=[];calls=0
    times = np.linspace(0,config['max_age_s'],config['time_points'])
    t_start=time.perf_counter()
    for pulses in config['pulses']:
        bath=synthetic_bath(config['small_exact_spins'])
        exact=exact_coherence(bath,times,4.2,pulses);calls+=1
        spectral=spectral_coherence(bath,times,pulses);calls+=1
        err=float(max(abs(exact-spectral)))
        rows.append({'axis':'independent_solver','pulses':pulses,'level':'expm_vs_spectral','max_complex_error':err,
                     'tolerance':config['solver_tolerance'],'gate':'pass' if err<=config['solver_tolerance'] else 'fail'})
        for steps in config['control_substeps']:
            approx=split_operator_coherence(bath,times,pulses,steps);calls+=1
            error=float(max(abs(approx-exact)))
            rows.append({'axis':'control_resolution','pulses':pulses,'level':str(steps),'max_complex_error':error,
                         'tolerance':config['control_tolerance'],'gate':'pass' if error<=config['control_tolerance'] else 'fail'})
        for order in config['cluster_orders']:
            b=copy.deepcopy(bath);b['order']=order
            cce=pycce_coherence(b,times,pulses,0);calls+=1
            error=float(max(abs(cce-exact)))
            rows.append({'axis':'cluster_order','pulses':pulses,'level':str(order),'max_complex_error':error,
                         'tolerance':config['cluster_tolerance'],'gate':'pass' if error<=config['cluster_tolerance'] else 'fail'})
            curves.append({'kind':'PyCCE','pulses':pulses,'spins':len(b['nuclei']),'order':order,
                           'times_s':times.tolist(),'real':cce.real.tolist(),'imag':cce.imag.tolist()})
        for cutoff in config['pair_cutoffs_angstrom']:
            b=copy.deepcopy(bath);b['order']=max(config['cluster_orders']);b['r_dipole_angstrom']=cutoff
            cce=pycce_coherence(b,times,pulses,0);calls+=1
            error=float(max(abs(cce-exact)))
            rows.append({'axis':'pair_cutoff','pulses':pulses,'level':str(cutoff),'max_complex_error':error,
                         'tolerance':config['cluster_tolerance'],'gate':'pass' if error<=config['cluster_tolerance'] else 'fail'})
        previous=None
        for count in config['bath_sizes']:
            b=synthetic_bath(count);c=spectral_coherence(b,times,pulses);calls+=1
            error=float(max(abs(c-previous))) if previous is not None else None
            rows.append({'axis':'bath_size','pulses':pulses,'level':str(count),'max_complex_error':error,
                         'tolerance':config['bath_tolerance'],'gate':'inconclusive' if error is None else
                         ('pass' if error<=config['bath_tolerance'] else 'fail')})
            curves.append({'kind':'spectral','pulses':pulses,'spins':count,'times_s':times.tolist(),
                           'real':c.real.tolist(),'imag':c.imag.tolist()});previous=c
        previous_metric=None
        for size in config['time_grid_sizes']:
            ts=np.linspace(0,config['max_age_s'],size)
            c=spectral_coherence(bath,ts,pulses);calls+=1
            metric=float(np.trapezoid(abs(c),ts)/config['max_age_s'])
            error=abs(metric-previous_metric) if previous_metric is not None else None
            rows.append({'axis':'time_grid','pulses':pulses,'level':str(size),'max_complex_error':error,
                         'tolerance':config['grid_tolerance'],'gate':'inconclusive' if error is None else
                         ('pass' if error<=config['grid_tolerance'] else 'fail')});previous_metric=metric
    axes={}
    for axis in ('independent_solver','control_resolution','cluster_order','pair_cutoff','bath_size','time_grid'):
        subset=[r for r in rows if r['axis']==axis]
        final=[next(r for r in reversed(subset) if r['pulses']==p) for p in config['pulses']]
        axes[axis]={'status':'pass' if all(r['gate']=='pass' for r in final) else 'fail','final_rows':final}
    summary={'status':'pass' if all(a['status']=='pass' for a in axes.values()) else 'fail',
             'coherence_solver_calls':calls, 'diagnostic_rows':len(rows),'axes':axes,
             'runtime_s':time.perf_counter()-t_start,'evidence_kind':'hypothetical',
             'material_prediction_authorized':False,'independent_physical_model_review':False,
             'scope':'nested noncommuting finite-bath software controls, maximally mixed initialization',
             'limitations':['Not a material lattice or measured hyperfine/bath ensemble',
                            'Time-grid gate tests mean |L| integration, not all revival extrema or a measured T2',
                            'Maximum exact bath size 8 spins; convergence domain is the supplied time window',
                            'Control pulses are ideal; pulse-shape/error convergence is not established'],
             'small_bath_sha256':digest(synthetic_bath(config['small_exact_spins'])),
             'provenance':audit_identity(config)}
    csv_rows(out/'convergence.csv',rows);write(out/'curves.json',curves);write(out/'summary.json',summary)
    return summary
