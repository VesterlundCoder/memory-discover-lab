"""One clean tagged source, one runtime, all existing studies and a full confirmation.

No acquisition or new parameter designs. Outputs must be outside the checkout.
External network access is denied in every worker after dependency installation.
"""
import argparse,hashlib,importlib.metadata,json,os,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'evaluation'),str(ROOT/'lab')]
from memorylab.common import environment,write_json
from wqeval.common import audit_identity
from wqeval.verification import compare as compare_system
from verify_validation_extension import verify as compare_extension

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def run(command,log,env,expected=0):
    print('Running:',log.name,flush=True)
    with log.open('w') as f:
        result=subprocess.run([sys.executable,*command],cwd=ROOT,env=env,
                              stdout=f,stderr=subprocess.STDOUT)
    if result.returncode!=expected:
        raise RuntimeError(f'{log}: exit {result.returncode}, expected {expected}')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag',default='v0.7.0')
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();out=args.out.resolve()
    if out.is_relative_to(ROOT):p.error('Write outputs outside the clean checkout')
    if out.exists():p.error('Output must be a fresh directory')
    if git('status','--porcelain'):p.error('Source checkout is not clean')
    commit=git('rev-parse','HEAD')
    if git('rev-parse',args.tag+'^{commit}')!=commit:p.error('HEAD is not the declared release tag')
    out.mkdir(parents=True)
    lock=ROOT/'requirements-release-v070.txt'
    pins={line.split('==')[0].lower().replace('_','-'):line.split('==')[1]
          for line in lock.read_text().splitlines() if '==' in line and not line.startswith('#')}
    actual={d.metadata['Name'].lower().replace('_','-'):d.version for d in importlib.metadata.distributions()}
    missing={k:(v,actual.get(k)) for k,v in pins.items() if actual.get(k)!=v}
    if missing:raise RuntimeError('Runtime differs from release lock: '+str(missing))
    env=dict(os.environ,WQ_BLOCK_EXTERNAL_NETWORK='1',PYTHONHASHSEED='0',
             OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',
             PYTHONPATH=os.pathsep.join([str(ROOT/'scripts/network_guard'),str(ROOT/'lab'),str(ROOT/'evaluation')]))
    # Execute the combined discovered suite once and report one total.
    run(['-c',"import unittest,sys; from pathlib import Path; r=Path.cwd(); s=unittest.TestSuite(); "
         "[s.addTests(unittest.TestLoader().discover(str(r/x),top_level_dir=str(r/x))) for x in ['lab/tests','evaluation/tests']]; "
         "z=unittest.TextTestRunner(verbosity=2).run(s); sys.exit(not z.wasSuccessful())"],out/'tests.log',env)
    import re
    testtext=(out/'tests.log').read_text()
    tested=int(re.search(r'Ran (\d+) tests',testtext)[1])
    skipped=re.search(r'OK \(skipped=(\d+)\)',testtext)
    tests={'run':tested,'passed':tested-(int(skipped[1]) if skipped else 0),
           'skipped':int(skipped[1]) if skipped else 0}
    for name in ['canonical','confirmation']:
        dest=out/name;dest.mkdir()
        run(['scripts/reproduce.py','--skip-tests','--out',str(dest/'paper')],dest/'paper.log',env)
        run(['scripts/reproduce_system.py','--out',str(dest/'system')],dest/'system.log',env)
        run(['scripts/evaluate_bradley_nv0.py','--out',str(dest/'bradley')],dest/'bradley.log',env,2)
        run(['scripts/run_validation_extension.py','--out',str(dest/'extension')],dest/'extension.log',env)
        run(['scripts/example_source_to_network.py','--baseline',str(dest/'paper/lab/baselines/teller2025'),
             '--out',str(dest/'example')],dest/'example.log',env)
    a,b=out/'canonical',out/'confirmation'
    checks={name:compare_system(a/'system'/name,b/'system'/name) for name in ['step1','step2','step3','step4']}
    extension=compare_extension(a/'extension',b/'extension')
    # Compare the measured-case payload and effective example, including negative results.
    from verify_validation_extension import compare,scientific
    for name in ['bradley/summary.json','example/sequence.json']:
        compare(scientific(json.loads((a/name).read_text())),scientific(json.loads((b/name).read_text())),name)
    if git('status','--porcelain') or git('rev-parse','HEAD')!=commit:raise RuntimeError('Source changed during replay')
    files={str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest()
           for f in sorted(out.rglob('*')) if f.is_file() and 'cache' not in f.parts and f.suffix not in ['.sqlite']}
    write_json(out/'manifest.json',{'schema':'westquant_unified_release_v1','status':'pass',
        'software_tag':args.tag,'software_commit':commit,'clean_source_before_and_after':True,
        'identity':audit_identity({}),'environment':environment(),'tests':tests,
        'runtime_lock_sha256':hashlib.sha256(lock.read_bytes()).hexdigest(),
        'external_network_denied':True,'scientific_replay_tolerance':1e-10,
        'system_confirmation':checks,'extension_confirmation':extension,
        'bradley_negative_result_preserved':True,'example_confirmation_passed':True,
        'result_file_sha256':files,'new_experimental_designs':0,'hardware_experiments':0})
    print('Unified release replay passed:',out,tests,flush=True)

if __name__=='__main__':main()
