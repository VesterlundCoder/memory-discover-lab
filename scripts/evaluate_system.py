"""Run the four separately scoped system-paper evaluations."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'evaluation'),str(ROOT/'lab')]
from wqeval.common import read

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('step',choices=['step1','step2','step3','step4','fetch'])
    ap.add_argument('--config',type=Path)
    ap.add_argument('--out',type=Path)
    ap.add_argument('--allow-hypothetical',action='store_true')
    ap.add_argument('--offline',action='store_true',help='For step1/fetch: use verified bundled/local bytes; never download')
    args=ap.parse_args()
    if args.step == 'fetch':
        from wqeval.datasets import ensure_teller
        _,cache=ensure_teller(offline=args.offline); print(cache); return 0
    if args.out is None: ap.error('--out must identify a fresh result directory')
    defaults={'step1':'comparison.json','step2':'second_family_pending.json','step3':'ablation.json','step4':'performance.json'}
    path=args.config or ROOT/'evaluation/config'/defaults[args.step]
    config=read(path)
    if args.step == 'step1':
        from wqeval.comparison import run
        summary=run(config,args.out,offline=args.offline)
    elif args.step == 'step2':
        from wqeval.caseflow import run
        summary=run(config,args.out,path.parent,args.allow_hypothetical)
    elif args.step == 'step3':
        from wqeval.ablation import run
        summary=run(config,args.out)
    else:
        from wqeval.performance import run
        summary=run(config,args.out)
    print(json.dumps(summary,indent=2,allow_nan=False))
    return 0 if summary['status'] in ('pass','model_curve_gate_pass') else 2

if __name__ == '__main__': sys.exit(main())
