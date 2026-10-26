#!/usr/bin/env python3
"""Read-only verification of both delivered archives and local report links."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

ROOT=Path(__file__).resolve().parents[3]
HANDOFF=ROOT/'docs/handoff'
required=['PHASE_01_09_SUMMARY.md','PHASE_09_ACCEPTANCE_REPORT.md','TEST_EVIDENCE.md',
          'ARCHITECTURE_SNAPSHOT.md','API_AND_DATABASE_SNAPSHOT.md','KNOWN_ISSUES.md','GIT_CHANGE_SUMMARY.md','README.md']
assert all((HANDOFF/name).is_file() for name in required)
for report in HANDOFF.glob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)',report.read_text()):
        if not target.startswith(('https:','http:','#')):
            assert (report.parent/target.split('#')[0]).exists(),(report.name,target)
for name,prefix,manifest in [
    ('northstar-source.zip','northstar-source','source-package-files.json'),
    ('northstar-handoff.zip','northstar-handoff','handoff-package-files.json')]:
    rows=json.loads((HANDOFF/'evidence'/manifest).read_text())
    with zipfile.ZipFile(ROOT/name) as archive:
        assert archive.testzip() is None
        for row in rows:
            data=archive.read(prefix+'/'+row['path'])
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],row['path']
        if prefix=='northstar-handoff':
            for file in HANDOFF.rglob('*'):
                if file.is_file() and '__pycache__' not in file.parts and file.suffix != '.pyc':
                    assert archive.read(prefix+'/'+file.relative_to(HANDOFF).as_posix())==file.read_bytes(),file.name
        else:
            assert set(archive.namelist()) == {prefix+'/'+r['path'] for r in rows}, 'Unexpected/missing ZIP entries'
            snapshot=json.loads((HANDOFF/'evidence/source-snapshot.json').read_text())
            internal=json.loads(archive.read(prefix+'/SOURCE_FILES.json'))
            assert {r['path'] for r in internal['files']} == {r['path'] for r in rows}-{'SOURCE_FILES.json'}
            for folder in ('apps/api/src/main/java','apps/api/src/test/java'):
                expected={p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*.java')}
                packed={r['path'] for r in rows if r['path'].startswith(folder+'/') and r['path'].endswith('.java')}
                assert expected and expected == packed == set(snapshot['javaInventory'][folder]['paths']), folder
                for path in expected:
                    row=next(r for r in snapshot['files'] if r['path']==path)
                    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==row['workspaceSha256'], path
            for row in internal['files']:
                assert hashlib.sha256(archive.read(prefix+'/'+row['path'])).hexdigest()==row['sha256']
for row in (ROOT/'northstar-packages.sha256').read_text().splitlines():
    checksum,name=row.split('  ',1)
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==checksum,name
print(json.dumps({'exitCode':0,'requiredReports':8,'localMarkdownLinks':'PASS',
    'zipCRC':'PASS','allManifestHashes':'PASS','handoffMatchesLocalDirectory':'PASS',
    'archiveChecksums':'PASS','note':'Packaging verification only; not project acceptance.'}))
