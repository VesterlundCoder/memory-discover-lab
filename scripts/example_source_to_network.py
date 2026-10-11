"""Use the profile produced by the licensed Teller source replay; no extrapolation."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lab'))
from memorylab.common import read_json,write_json
from memorylab.models import evaluate
from memorylab.network import export,load_device
from memorylab.sequence_adapter import run_link

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    profile=read_json(args.baseline/'measured_point_profile.json')
    channels=evaluate(profile,[18e-6],backend='qutip')
    export(channels,args.out/'device.json')
    device=load_device(args.out/'device.json')
    workload={'attempts':400000,'link_herald_probability':1.0,
              'attempt_interval_s':0.001,'storage_age_s':18e-6,
              'minimum_Bell_fidelity':0.8}
    result=run_link(device,device,workload,simulation_seed=20261014)
    write_json(args.out/'sequence.json',result)
    print('Source-constrained point exported and executed:',args.out)

if __name__=='__main__':main()
