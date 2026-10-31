#!/usr/bin/env python3
"""Record pinned browser commands and retain exact result without printing binary audio."""
import json
from pathlib import Path
import sys
import time
import subprocess
import hashlib

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.local/phase10c1/c01-probe'
active=ROOT/(ROOT/'.local/phase10c1/R_ACTIVE_OUTPUT').read_text().strip()
session=json.loads((active/'session.json').read_text())
code=Path(sys.argv[1]).read_text() if sys.argv[1].endswith('.js') else sys.argv[1]
if len(sys.argv)>2:
    code=code.replace('windowGroup',json.dumps(json.loads(sys.argv[2])))
cmd=['/opt/homebrew/opt/node@22/bin/node',session['cli'],'--session=northstar-phase10c1-r','run-code',code]
stamp=str(time.time_ns())
result=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=240)
raw=result.stdout+result.stderr
(OUT/(stamp+'.log')).write_bytes(raw)
with (OUT/'commands.jsonl').open('a') as file:
    file.write(json.dumps(dict(atNs=stamp,exitCode=result.returncode,code=code,log=stamp+'.log',sha256=hashlib.sha256(raw).hexdigest()))+'\n')
if result.returncode or b'### Error' in raw:
    print(raw.decode(errors='replace')[-4000:]);raise SystemExit(1)
if b'### Result\n' in raw:
    print(raw.decode().split('### Result\n',1)[1].split('\n###',1)[0][:3000])
else:
    print(raw.decode()[-3000:])
