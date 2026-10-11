"""Compare scientific results; retain source fingerprints as separate provenance."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'evaluation'),str(ROOT/'lab')]
from wqeval.verification import compare
from wqeval.common import write
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--reference',type=Path,required=True);ap.add_argument('--actual',type=Path,required=True)
ap.add_argument('--require-same-source',action='store_true');ap.add_argument('--out',type=Path)
args=ap.parse_args()
try:
    result=compare(args.reference,args.actual,args.require_same_source)
    if args.out:write(args.out,result)
    print(json.dumps(result,indent=2))
except (ValueError,OSError,KeyError) as e:ap.exit(2,'Reproduction comparison failed: '+str(e)+'\n')
