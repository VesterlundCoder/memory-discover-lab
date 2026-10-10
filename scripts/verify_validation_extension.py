"""Compare complete scientific records, including every archived native run and RNG trace."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np

EXCLUDED={'provenance','runtime_s','raw_archive_sha256'}


def scientific(value):
    if isinstance(value,dict):return {k:scientific(v) for k,v in value.items() if k not in EXCLUDED}
    if isinstance(value,list):return [scientific(v) for v in value]
    return value


def compare(a,b,path='root',tol=1e-10):
    if isinstance(a,dict):
        if not isinstance(b,dict) or a.keys()!=b.keys():raise ValueError('Key mismatch: '+path)
        for key in a:compare(a[key],b[key],path+'.'+key,tol)
    elif isinstance(a,list):
        if not isinstance(b,list) or len(a)!=len(b):raise ValueError('Length mismatch: '+path)
        for i,(x,y) in enumerate(zip(a,b)):compare(x,y,f'{path}[{i}]',tol)
    elif isinstance(a,float):
        if not isinstance(b,(int,float)) or not np.isfinite([a,b]).all() or not np.isclose(a,b,atol=tol,rtol=tol):
            raise ValueError('Numeric mismatch: '+path)
    elif a!=b:raise ValueError('Value mismatch: '+path)


def verify(reference,actual):
    counts={'json_records':0,'random_trace_arrays':0}
    for stage in ['protocol','convergence','pilot','larger']:
        a=json.loads((reference/stage/'summary.json').read_text());b=json.loads((actual/stage/'summary.json').read_text())
        compare(scientific(a),scientific(b),stage+'.summary');counts['json_records']+=1
        for key in ['configuration_sha256','evaluation_source_sha256','lab_source_sha256']:
            if a['provenance'][key]!=b['provenance'][key]:raise ValueError('Provenance mismatch: '+stage+' '+key)
        if stage in ['pilot','larger']:
            archives=[]
            for root,summary in [(reference,a),(actual,b)]:
                p=root/stage/'raw_runs_and_traces.zip'
                if hashlib.sha256(p.read_bytes()).hexdigest()!=summary['raw_archive_sha256']:raise ValueError('Archive integrity failure: '+str(p))
                archives.append(zipfile.ZipFile(p))
            with archives[0] as za,archives[1] as zb:
                if sorted(za.namelist())!=sorted(zb.namelist()):raise ValueError('Archive entries mismatch')
                for name in za.namelist():
                    if name.endswith('.json'):
                        compare(scientific(json.loads(za.read(name))),scientific(json.loads(zb.read(name))),stage+'.'+name)
                        counts['json_records']+=1
                    else:
                        np.testing.assert_array_equal(np.load(io.BytesIO(za.read(name)),allow_pickle=False),np.load(io.BytesIO(zb.read(name)),allow_pickle=False))
                        counts['random_trace_arrays']+=1
        else:
            for filename in (['channels.json','experimental_audit.json'] if stage=='protocol' else ['curves.json']):
                compare(scientific(json.loads((reference/stage/filename).read_text())),scientific(json.loads((actual/stage/filename).read_text())),stage+'.'+filename)
                counts['json_records']+=1
    return {'status':'pass','compared':counts,'absolute_and_relative_tolerance':1e-10,
            'source_and_configuration_fingerprints_equal':True,
            'scope':'same-machine replay; runtime, timestamp/platform provenance and archive container bytes excluded from scientific equality'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--actual',type=Path,required=True)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args();result=verify(args.reference,args.actual)
    output=json.dumps(result,indent=2)+'\n'
    if args.out:args.out.write_text(output)
    print(output)


if __name__=='__main__':main()
