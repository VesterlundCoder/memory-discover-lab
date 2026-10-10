"""Execute all four pathways, including the explicit synthetic/physical step-2 split."""
import argparse,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'evaluation'),str(ROOT/'lab')]
from wqeval.common import write,read
from wqeval.verification import compare
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--out',type=Path,required=True)
ap.add_argument('--reference-root',type=Path,help='Directory containing step1/ through step4/ for comparison')
args=ap.parse_args();out=args.out.resolve()
if out.exists() and any(out.iterdir()):ap.error('Choose a fresh output directory')
out.mkdir(parents=True,exist_ok=True);results={}
for name,extras in [('step1',['--offline']),('step2',['--config',str(ROOT/'evaluation/data/software_control/case.json'),'--allow-hypothetical']),('step3',[]),('step4',[])]:
    command=[sys.executable,str(ROOT/'scripts/evaluate_system.py'),name,'--out',str(out/name),*extras]
    print('Running:',name,flush=True)
    with (out/(name+'.log')).open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    results[name]=read(out/name/'summary.json')['status']
    if args.reference_root:write(out/(name+'-comparison.json'),compare(args.reference_root/name,out/name,require_same_source=True))
with (out/'step2-physical-pending.log').open('w') as log:
    result=subprocess.run([sys.executable,str(ROOT/'scripts/evaluate_system.py'),'step2','--out',str(out/'step2-physical-pending')],stdout=log,stderr=subprocess.STDOUT)
pending=read(out/'step2-physical-pending/summary.json')
if result.returncode!=2 or pending['status']!='blocked_missing_reviewed_data' or pending['physical_validation_passed']:raise ValueError('Pending case was incorrectly promoted')
write(out/'summary.json',{'status':'pass','steps':results,'step2_physical_status':pending['status'],
    'step2_physical_validated':False,'scope':'Software pathway reproduction; no independent experiment or new material validation'})
print('All software pathways completed; second experimental family remains pending:',out)
