#!/usr/bin/env python3
"""Run Maven with isolated test identity, recording actual exits and redacting passwords."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
env=json.loads((ROOT/'.local/d02-p1/test-env.json').read_text())
assert env['MYSQL_PORT']=='3373' and env['DB_NAME']=='northstar_phase01_test'
label=sys.argv[1];args=[str(ROOT/'apps/api/mvnw'),'-f',str(ROOT/'apps/api/pom.xml')]+sys.argv[2:]
p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True)
s=p.stdout+p.stderr
for k,v in env.items():
    if 'PASSWORD' in k and v:s=s.replace(v,'<REDACTED>')
out=ROOT/'qa/phase10d2-p1/evidence';(out/(label+'.log')).write_text(s)
with (out/'exit-codes.jsonl').open('a') as f:f.write(json.dumps({'name':label,'argv':args,'exit_code':p.returncode})+'\n')
print(label,'exit='+str(p.returncode));print('\n'.join(s.splitlines()[-12:]))
sys.exit(p.returncode)
