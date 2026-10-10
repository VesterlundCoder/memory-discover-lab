"""Replay licensed paper inputs offline; --online reacquires the wider sources.

Write fresh outputs to a separate tree. Historical article evidence is preserved.
Offline replay excludes the unlicensed molecular collection and unbundled paper
bytes; reviewed transcriptions and primary-reference tables are retained inputs.
"""
from pathlib import Path
import argparse, importlib.util, json, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lab'))
from memorylab.common import write_json, environment
from memorylab.bundled import verified_group

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--online',action='store_true',help='Reacquire original wider sources (requires external servers)')
    ap.add_argument('--out',type=Path,default=ROOT/'reproductions/latest')
    args=ap.parse_args();out=args.out.resolve()
    missing=[p for p in ['qutip','sequence','matplotlib'] if importlib.util.find_spec(p) is None]
    if missing:ap.error('Paper replay needs '+', '.join(missing)+". Install: python -m pip install -c lab/constraints-tested.txt -r requirements-paper.txt -e './lab[all]'")
    if out.exists() and any(out.iterdir()):ap.error('Choose a fresh --out directory; historical results are never overwritten')
    if not args.online:
        for group in ['teller2025','pr2026']:verified_group(ROOT/'data/experimental',group)
    (out/'evidence').mkdir(parents=True,exist_ok=True)
    lab=out/'lab';lab.mkdir(exist_ok=True)
    bundle=[] if args.online else ['--offline','--reviewed-bundle',str(ROOT/'data/experimental')]
    tasks=[([sys.executable,'-m','memorylab','reproduce',str(ROOT/'lab/examples/teller2025_baseline.json'),'--out',str(lab/'baselines/teller2025'),*bundle],'paper_teller_reproduction.log'),
        ([sys.executable,'-m','memorylab.t2lab','run','--sequence','--root',str(lab/'t2_data'),'--out',str(lab/'t2_runs/deterministic'),*bundle],'paper_t2_reproduction.log'),
        ([sys.executable,'-m','unittest','discover','-s',str(ROOT/'lab/tests'),'-v'],'paper_test_results.log')]
    for command,name in tasks:
        print('Running:', ' '.join(command),flush=True)
        with (out/'evidence'/name).open('w') as log:
            subprocess.run(command,cwd=ROOT/'lab',stdout=log,stderr=subprocess.STDOUT,check=True)
    copies={'baselines/teller2025/summary.json':'teller_summary.json','baselines/teller2025/spatial_holdout.json':'teller_holdout.json',
        'baselines/teller2025/readout_window_noise_fit.json':'teller_window_fits.json','t2_runs/deterministic/summary.json':'deterministic_summary.json',
        't2_runs/deterministic/experimental_decay/summary.json':'pr2026_curve_summary.json','t2_runs/deterministic/hypothetical_sequence.json':'hypothetical_sequence.json'}
    for source,target in copies.items():shutil.copyfile(lab/source,out/'evidence'/target)
    subprocess.run([sys.executable,str(ROOT/'scripts/make_figures.py'),'--inputs',str(out),'--out',str(out/'figures')],check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/make_tables.py'),'--inputs',str(out),'--out',str(out/'tables')],check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/verify_results.py'),'--inputs',str(out),*(['--numerical-replay'] if not args.online else [])],check=True)
    write_json(out/'scope.json',{'status':'pass','mode':'source_acquisition' if args.online else 'licensed_numerical_replay',
        'environment':environment(),'molecular_collection_reacquired':args.online,'unbundled_paper_bytes_reverified':args.online,
        'independent_scientific_review':False,'hardware_validation':False})
    print('Replay complete:',out)
    return 0
if __name__=='__main__':sys.exit(main())
