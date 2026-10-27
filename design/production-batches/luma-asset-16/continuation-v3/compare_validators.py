"""Read-only cross-PR behavior comparison. Pass downloaded validator file paths."""
import argparse
import hashlib
import importlib.util
import json
import os
import tempfile
import tracemalloc
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def main():
    parser=argparse.ArgumentParser();parser.add_argument('files',nargs='+',type=Path);args=parser.parse_args()
    modules=[load('comparison_'+str(n),p) for n,p in enumerate(args.files)]
    fixtures=[(ROOT/f'design/production-batches/monsters/batch07/M{i:03}/base-v2.png').read_bytes() for i in range(61,66)]
    fixtures.extend([b'bad PNG',fixtures[0][:-4]])
    mismatches=[];cases=0
    with tempfile.TemporaryDirectory(prefix='luma-144-compare-') as temp:
        path=Path(temp)/'mutable.png'
        for index,data in enumerate(fixtures):
            path.write_bytes(data)
            for alpha in (False,True):
                for bound,digest in ((False,False),(True,False),(False,True),(True,True)):
                    actual=[]
                    for module in modules:
                        bounds=[] if bound else None;hashes=[] if digest else None
                        errors=module.png_errors(path,alpha,bounds,hashes)
                        actual.append((errors,bounds,hashes))
                    cases+=1
                    if any(x!=actual[0] for x in actual[1:]):mismatches.append([index,alpha,bound,digest])
        path.write_bytes(fixtures[0]);stamp=path.stat().st_mtime_ns
        mutation=[]
        for module in modules:module.png_errors(path,True,[],[])
        corrupt=bytearray(fixtures[0]);corrupt[-1]^=1;path.write_bytes(corrupt);os.utime(path,ns=(stamp,stamp))
        for module in modules:mutation.append('PNG CRC mismatch' in module.png_errors(path,True,[],[]))
        path.unlink();deletion=[bool(m.png_errors(path)) for m in modules]
        memory=[]
        for module in modules:
            # Fresh allocations from bounded fixture set; not a maximum memory claim.
            tracemalloc.start()
            for i,data in enumerate(fixtures[:5]):
                path.write_bytes(data)
                for alpha in (False,True):module.png_errors(path,alpha,[],[])
            current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            memory.append({'currentBytes':current,'peakBytes':peak,'scope':'warm-cache five BASE files, not worst-case memory'})
    result={'files':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'measuredMemory':m} for p,m in zip(args.files,memory)],'sameResultCases':cases,'mismatches':mismatches,'samePathSameMtimeCorruptionDetected':mutation,'deletionDetected':deletion,'status':'PASS' if not mismatches and all(mutation) and all(deletion) else 'FAIL','comparisonScope':'Errors, bounds, normalized visible Pixel Hash under 8 option combinations; no approval or shared code writes'}
    print(json.dumps(result,indent=2))
    return int(result['status']!='PASS')

if __name__=='__main__':raise SystemExit(main())
