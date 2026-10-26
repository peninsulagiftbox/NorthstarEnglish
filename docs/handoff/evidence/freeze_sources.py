#!/usr/bin/env python3
"""Freeze allowlisted source files; excludes personal/runtime data and media."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
stage = Path(tempfile.mkdtemp(prefix='northstar-source-audit-', dir='/private/tmp'))
allowed_suffix = {'.java','.md','.json','.ts','.tsx','.js','.mjs','.css','.sql','.yml','.yaml','.py','.sh','.xml','.properties','.svg','.txt','.cmd'}
allowed_root = {'.env.example','.gitignore','.gitattributes','.node-version','AGENTS.md','README.md','package.json','package-lock.json'}
paths = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).split(b'\0')
records, excluded = [], []
for item in sorted(set(paths)):
    if not item: continue
    name=item.decode(); p=ROOT/name
    if name.startswith('docs/handoff/'): continue  # attached after documents are finalized
    reason = None
    if p.is_symlink() or not p.is_file(): reason='not a regular source file'
    elif any(part in {'.git','.local','node_modules','.next','target','__pycache__','recordings','backups','.codex','.agents','output'} for part in p.relative_to(ROOT).parts): reason='private/runtime/generated directory'
    elif name.startswith(('docs/evidence/','docs/progress/')): reason='original historical reports/evidence may contain personal activity; curated audit evidence supplied instead'
    elif p.name.startswith('.env') and name!='.env.example': reason='private environment'
    elif name not in allowed_root and p.suffix not in allowed_suffix and p.name!='mvnw': reason='non-source/binary/media'
    elif name.split('/')[0] not in {'apps','scripts','infra','content','docs','references','Northstar_English_Codex'} and name not in allowed_root: reason='unneeded original root material'
    if reason:
        excluded.append({'path':name,'reason':reason}); continue
    raw=p.read_bytes()
    try: text=raw.decode('utf-8')
    except UnicodeDecodeError:
        excluded.append({'path':name,'reason':'non-UTF8/binary'}); continue
    redacted=text.replace(str(ROOT),'<PROJECT_ROOT>').replace(str(Path.home()),'<HOME>')
    # Preserve hashes/bytes of frozen content and source unless a machine path needs removal.
    data=redacted.encode()
    dest=stage/name; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
    if p.stat().st_mode & 0o111: dest.chmod(0o755)
    records.append({'path':name,'workspaceSha256':hashlib.sha256(raw).hexdigest(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'machinePathRedacted':raw!=data})
java_inventory = {}
by_path = {row['path']: row for row in records}
for folder in ('apps/api/src/main/java', 'apps/api/src/test/java'):
    expected = {p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*.java')}
    actual = {name for name in by_path if name.startswith(folder+'/') and name.endswith('.java')}
    assert expected and expected == actual, 'Java source inventory mismatch: '+folder
    for name in expected:
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == by_path[name]['workspaceSha256']
    java_inventory[folder] = {'count': len(expected), 'paths': sorted(expected)}
stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
(HERE/'source-snapshot.json').write_text(json.dumps({'frozenAt':stamp,'gitHead':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'javaInventory':java_inventory,'files':records,'excluded':excluded},ensure_ascii=False,indent=2)+'\n')
(HERE/'git-status-snapshot.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT).decode())
baseline=json.loads((HERE/'baseline-files.json').read_text()); by_path={r['path']:r for r in records}
changes=[]
for row in baseline:
    current=ROOT/row['path']
    value=hashlib.sha256(current.read_bytes()).hexdigest() if current.is_file() else None
    if value!=row['sha256']: changes.append({'path':row['path'],'before':row['sha256'],'observed':value})
(HERE/'source-integrity.json').write_text(json.dumps({'observedAt':stamp,'auditWrites':'docs/handoff plus output archives; no business source edits by audit','worktreeDriftDetected':bool(changes),'changedBaselineFiles':changes,'warning':'Concurrent external edits observed; package is a frozen working-tree snapshot, not a wholly retested release.'},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'stage':str(stage),'files':len(records),'frozenAt':stamp}))
