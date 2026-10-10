"""Complete effective write/store/read instrument with explicit readout false positives.

A true retrieved signal wins over background; background can register only if
signal retrieval failed. This exclusive first-click model excludes double clicks.
Signal noise already represented by the input channel must not include this source.
"""
import math
import numpy as np
from .channels import MemoryChannel, I2, validate_state
from .common import finite, UnsupportedPhysics


def readout_instrument(signal, detector):
    if detector.get('event_model') != 'exclusive_signal_then_background':
        raise UnsupportedPhysics('Declare exclusive first-click detection semantics')
    if not detector.get('independent_of_signal_noise') or not detector.get('noise_source_id'):
        raise UnsupportedPhysics('Independent named readout noise source required')
    if detector['noise_source_id'] in signal.metadata.get('noise_budget', []):
        raise UnsupportedPhysics('Readout noise would be counted twice')
    window = finite(detector['window_s'], 'detection window_s', 0)
    age = signal.metadata['storage_age_s']
    rate = finite(detector['base_rate_s_inv'], 'background rate', 0)
    rate += finite(detector['age_rate_s_inv_per_s'], 'age-dependent background rate', 0)*age
    false_given_loss = -math.expm1(-rate*window)
    eta = signal.success_probability
    noise = (1-eta)*false_given_loss
    acceptance = eta+noise
    excited = finite(detector['background_excited_population'], 'background population', 0, 1)
    state = np.diag([1-excited, excited]).astype(complex)
    validate_state(state)
    reset = [math.sqrt(state[i, i].real)*np.outer(I2[:, i], I2[:, j]) for i in range(2) for j in range(2)]
    if acceptance > 0:
        accepted = [math.sqrt(eta/acceptance)*k for k in signal.conditional_kraus]
        accepted += [math.sqrt(noise/acceptance)*k for k in reset]
    else:
        accepted = [I2]
    metadata = dict(signal.metadata)
    metadata.update({'protocol_instrument': 'exclusive_signal_then_background_v1',
                     'signal_retrieval_probability': eta, 'noise_click_probability': noise,
                     'false_click_probability_given_signal_loss': false_given_loss,
                     'readout_detector': detector, 'background_state': state.real.tolist(),
                     'hardware_validated': False})
    return MemoryChannel(accepted, acceptance, metadata)


def metrics(signal, accepted):
    sm, am = signal.metrics(), accepted.metrics()
    eta, noise = signal.success_probability, accepted.metadata['noise_click_probability']
    p = accepted.success_probability
    return {'storage_age_s': signal.metadata['storage_age_s'],
            'total_write_store_read_s': signal.metadata['total_write_store_read_s'],
            'signal_efficiency': eta, 'noise_click_probability': noise, 'acceptance_probability': p,
            'noise_fraction_among_accepted': noise/p if p else None,
            'signal_to_noise_ratio': eta/noise if noise else None,
            'conditional_signal_average_fidelity': sm['conditional_average_fidelity'],
            'conditional_detected_average_fidelity': am['conditional_average_fidelity'],
            'conditional_detected_entanglement_fidelity': am['conditional_entanglement_fidelity'],
            'unconditional_target_overlap': am['unconditional_target_overlap'],
            'erasure_probability': 1-p,
            'fidelity_definition': 'pure-state overlap averaged over six Pauli eigenstates; unsquared-root convention'}
