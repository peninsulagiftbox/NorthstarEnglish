#!/usr/bin/env python3
"""Package allowlisted synthetic evidence and frozen source inputs; keep credentials private."""
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];EV=ROOT/'qa/phase10d2-p1/evidence';PRIVATE=ROOT/'.local/d02-p1'
inputs=json.loads((EV/'candidate-inputs.json').read_text())
secrets=[]
for base in [PRIVATE/'database',ROOT/'.local/d02-risk-closure/database']:
    for p in base.glob('*/credentials.json'):secrets.extend(json.loads(p.read_text()).values())
qa=Path('/Users/wangshiqi/.codex/worktrees/worktree-10d-d02-qa/NorthstarEnglish')
secrets.extend(json.loads((qa/'.local/qa-r3/credentials.json').read_text()).values())
files={}
for name,h in inputs.items():
    p=ROOT/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,'input drift '+name
    files['source/'+name]=p.read_bytes()
for p in EV.rglob('*'):
    if p.is_file() and 'database' not in p.relative_to(EV).parts:files['evidence/'+str(p.relative_to(EV))]=p.read_bytes()
for p in (EV/'database').glob('*identity.json'):files['evidence/database/'+p.name]=p.read_bytes()
for name in ['PHASE_10D_2_P1.md']:
    files[name]=(ROOT/'docs/progress'/name).read_bytes()
files['10D_D02_QA_FINAL_ACCEPTANCE.md']=(ROOT/'docs/qa/phase10d/10D_D02_QA_FINAL_ACCEPTANCE.md').read_bytes()
# Place the candidate manifests beside the packaged source verifier.
for name in ['candidate-inputs.json','candidate-inputs.sha256']:
    files['source/qa/phase10d2-p1/evidence/'+name]=(EV/name).read_bytes()
files['verify.py']=b'''import hashlib,json,pathlib
base=pathlib.Path(__file__).resolve().parent
m=json.loads((base/'SHA256SUMS.json').read_text())
actual={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*') if p.is_file() and p.name!='SHA256SUMS.json'}
assert m==actual,'missing, extra or changed package files'
print('PASS',len(actual),'files')
'''
for name,data in files.items():
    assert not any(isinstance(v,str) and v and v.encode() in data for v in secrets),'secret in '+name
files['SHA256SUMS.json']=(json.dumps({n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())},indent=2)+'\n').encode()
archive=ROOT/'output/review/northstar-phase10d2-p1-sanitized-evidence.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in sorted(files.items()):z.writestr('d02-p1/'+name,data)
sha=hashlib.sha256(archive.read_bytes()).hexdigest();archive.with_suffix('.zip.sha256').write_text(sha+'  '+archive.name+'\n')
jar=ROOT/'output/review/northstar-phase10d2-p1-candidate.jar';shutil.copyfile(PRIVATE/'candidate.jar',jar)
jar.with_suffix('.jar.sha256').write_text(hashlib.sha256(jar.read_bytes()).hexdigest()+'  '+jar.name+'\n')
print('PACKAGE',len(files),'files',sha)
