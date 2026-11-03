#!/usr/bin/env python3
"""Record actual child status, without shell pipelines masking a failing exit."""
import datetime,json,subprocess,sys
from pathlib import Path
out=Path(__file__).resolve().parents[1]/'logs'
name=sys.argv[1]
with (out/(name+'.log')).open('w') as f:r=subprocess.run(sys.argv[2:],stdout=f,stderr=subprocess.STDOUT)
with (out/'exit-codes.jsonl').open('a') as f:f.write(json.dumps({'name':name,'argv':sys.argv[2:],'exit_code':r.returncode,'time':datetime.datetime.now(datetime.timezone.utc).isoformat()})+'\n')
print(name,'exit_code='+str(r.returncode),flush=True)
sys.exit(r.returncode)
