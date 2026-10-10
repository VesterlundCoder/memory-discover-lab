"""Scope and identity checks before a spin model is labelled a material prediction."""
from .common import digest, MissingData, finite


def profile_identity(profile):
    return digest({k:v for k,v in profile.items() if k != 'convergence_certificate'})


def require_material_convergence(profile, times_s=None):
    if profile['storage_model'] not in ('exact_spin_bath', 'pycce'):
        raise MissingData('This material-prediction gate requires a spin Hamiltonian')
    record = profile.get('convergence_certificate', {})
    if record.get('status') != 'pass' or record.get('profile_sha256') != profile_identity(profile):
        raise MissingData('Missing, failed or mismatched convergence certificate')
    if not all(record.get(k) is True for k in ('bath_size_converged', 'cluster_order_converged', 'pair_cutoff_converged',
                                              'control_resolution_converged', 'time_grid_converged')):
        raise MissingData('All four convergence axes must be demonstrated')
    tol = finite(record['tolerance'], 'convergence tolerance', 1e-15)
    if finite(record['maximum_error'], 'convergence error', 0) > tol:
        raise MissingData('Convergence error exceeds declared tolerance')
    if record.get('independent_physical_model_review') is not True or profile['evidence_kind'] == 'hypothetical':
        raise MissingData('Numerical software controls cannot authorize material predictions')
    if times_s is not None:
        lo, hi = record['validated_storage_age_s']
        if min(times_s) < lo or max(times_s) > hi:
            raise MissingData('Requested times exceed converged domain')
