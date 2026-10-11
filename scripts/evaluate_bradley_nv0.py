"""Offline reproduction of the second measured observable case (not strict caseflow)."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'evaluation'), str(ROOT/'lab')]
from wqeval.common import read
from wqeval.experimental_observables import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'evaluation/data/bradley2022_nv0/case.json')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--plot', action='store_true')
    args = parser.parse_args()
    result = run(read(args.config), args.out, args.config.parent)
    if args.plot:
        import csv
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        from wqeval.experimental_observables import envelope
        rows = list(csv.DictReader((args.out/'model_vs_observables.csv').open()))
        fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout='constrained')
        for ax, name, label in zip(axes, ('equatorial_length', 'X'), ('Transverse Bloch length', '<X>')):
            points = [r for r in rows if r['observable'] == name]
            for partition, color in [('calibration', '#2474a8'), ('heldout', '#d47424')]:
                p = [r for r in points if r['partition'] == partition]
                ax.errorbar([1000*float(r['time_s']) for r in p], [float(r['observed']) for r in p],
                            yerr=[float(r['reported_error']) for r in p], fmt='o', color=color, label=partition)
            times = np.linspace(0, max(float(r['time_s']) for r in points), 800)
            p = result['parameters']
            decay = envelope(times, 1, p['tau_s'], p['stretch_exponent'])
            if name == 'equatorial_length':
                model = p['signal_amplitude'] * decay
            else:
                phase = 2*np.pi*result['fixed_rotating_frame_frequency_Hz']*times
                c, s = result['ramsey_cos_sin_coefficients']
                model = decay * (c*np.cos(phase) + s*np.sin(phase))
            ax.plot(1000*times, model, color='#222222', label='effective model')
            ax.set(xlabel='Free evolution (ms)', ylabel=label)
            ax.legend(fontsize=8)
        fig.suptitle('Bradley et al. 2022, Fig. 3b: retrospective split; reported error bars')
        fig.savefig(args.out/'observables.png', dpi=180)
        plt.close(fig)
    print(result['status'])
    print('Heldout observable gate:', result['heldout_observable_gate_passed'])
    print('Physical validation:', result['physical_validation_passed'])
    return 0 if result['heldout_observable_gate_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
