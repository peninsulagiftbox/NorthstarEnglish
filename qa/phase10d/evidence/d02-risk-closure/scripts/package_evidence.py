#!/usr/bin/env python3
"""Allowlisted, credential-scanned evidence package; exclude private dumps and old learning rows."""
import hashlib,json,re,shutil,zipfile
from pathlib import Path
import qa_runtime as q
stage=q.PRIVATE/'sanitized-package';stage.mkdir(exist_ok=True)
secrets=[]
for p in (q.PRIVATE/'database').glob('*/credentials.json'):secrets.extend(json.loads(p.read_text()).values())
secrets.extend(json.loads((q.QA/'.local/qa-r3/credentials.json').read_text()).values())
def scrub(s):
    for value in secrets:
        if isinstance(value,str) and value:s=s.replace(value,'<REDACTED>')
    return s
files=list((q.OUT/'scripts').glob('*.py'))+list((q.OUT/'scripts').glob('*.js'))+list((q.OUT/'logs').glob('*'))
files+=list((q.OUT/'migrations/migrations').glob('*acceptance.json'))+list((q.OUT/'migrations/migrations').glob('*identity.json'))+list((q.OUT/'migrations/migrations').glob('*summary.json'))
for p in files:
    if not p.is_file():continue
    dest=stage/p.relative_to(q.OUT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(scrub(p.read_text()))
for name in ['10D_D02_QA_FINAL_ACCEPTANCE.md','10D_D02_QA_RISK_CLOSURE.md']:
    (stage/name).write_text((q.ROOT/'docs/qa/phase10d'/name).read_text())
(stage/'R3-original-final-acceptance.md').write_text((q.OUT/'R3-original-final-acceptance.md').read_text())
# Keep actual statuses and raw-log hashes for ALL commands, without exporting old-backup row bodies.
records=[]
for line in (q.OUT/'migrations/migrations/commands.jsonl').read_text().splitlines():
    r=json.loads(line);records.append({k:r[k] for k in ['name','argv','started','returncode','rawLogSha256','stdinSha256'] if k in r})
    if 'flyway' in r['name'] or (not r.get('privateOutput') and "Injected after committed" in r.get('stdinSql','')):
        source=q.ROOT/r['rawLog'];dest=stage/'migration-raw'/source.name;dest.parent.mkdir(exist_ok=True);dest.write_text(scrub(source.read_text()))
(stage/'migration-command-status.json').write_text(json.dumps(records,indent=2))
api=scrub((q.PRIVATE/'runtime-api.log').read_text());(stage/'runtime-api.log').write_text(api)
for name in ['candidate-sha256.txt','candidate-filelist-sha256.txt']:
    shutil.copyfile(q.ROOT/'qa/phase10d2/evidence'/name,stage/name)
md=q.ROOT/'apps/api/src/main/resources/db/migration';dest=stage/'migrations-source';dest.mkdir(exist_ok=True)
for p in md.glob('V012*.sql'):shutil.copyfile(p,dest/p.name)
inputs=[q.QA/'package.json',q.QA/'package-lock.json',q.QA/'apps/web/package.json',q.QA/'apps/web/next.config.ts',q.QA/'apps/web/tsconfig.json']+sorted((q.QA/'apps/web/src').rglob('*'))
(stage/'frontend-build-inputs.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(q.QA))+'\n' for p in inputs if p.is_file()))
(stage/'verify.py').write_text('''import hashlib,json,pathlib,sys
base=pathlib.Path(__file__).resolve().parent
manifest=json.loads((base/'SHA256SUMS.json').read_text())
actual={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*') if p.is_file() and p.name!='SHA256SUMS.json'}
assert actual==manifest,'missing, extra or changed files'
print('PASS',len(actual),'files')
''')
manifest={str(p.relative_to(stage)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(stage.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.json'}
(stage/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2,sort_keys=True))
for p in stage.rglob('*'):
    if p.is_file():assert not any(isinstance(v,str) and v and v in p.read_text() for v in secrets),'credential in '+str(p)
archive=q.ROOT/'output/review/northstar-phase10d2-risk-closure-evidence.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(stage.rglob('*')):
        if p.is_file():z.write(p,'d02-risk-closure/'+str(p.relative_to(stage)))
sha=hashlib.sha256(archive.read_bytes()).hexdigest();archive.with_suffix('.zip.sha256').write_text(sha+'  '+archive.name+'\n')
print('PACKAGE',len(manifest),'files',sha)
