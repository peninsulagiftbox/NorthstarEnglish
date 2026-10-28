#!/usr/bin/env python3
"""Package public evidence only. Private SQL/rows/credentials/media remain under .local."""
import datetime
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    report=ROOT/'docs/progress/PHASE_10_PERSONAL_MIGRATION.md'
    files=sorted([p for p in BASE.rglob('*') if p.is_file()]+[report])
    assert not any(p.is_symlink() or '.local' in p.relative_to(ROOT).parts or '__pycache__' in p.parts for p in files)
    # Check actual known credentials without emitting their values.
    secrets=[]
    for line in (ROOT/'.env').read_text().splitlines():
        key,sep,value=line.partition('=')
        if sep and key.endswith('PASSWORD') and value:secrets.append(value.encode())
    for path in (ROOT/'.local/personal-migration').glob('*/isolated/*/credentials.json'):
        secrets.extend(v.encode() for v in json.loads(path.read_text()).values())
    for path in files:assert not any(value in path.read_bytes() for value in secrets),'Secret detected in package input: '+str(path.relative_to(ROOT))
    stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%H%M%S')
    destination=BASE.parent/('personal-migration-review-20261028-'+stamp+'.zip')
    assert not destination.exists()
    manifest=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
    with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as archive:
        for path in files:archive.write(path,str(path.relative_to(ROOT)))
        archive.writestr('REVIEW_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for row in manifest:
            content=archive.read(row['path']);assert len(content)==row['bytes'] and hashlib.sha256(content).hexdigest()==row['sha256']
    receipt={'zip':str(destination.relative_to(ROOT)),'bytes':destination.stat().st_size,'sha256':sha(destination),'files':len(manifest),'crcAndEveryEntryHash':'PASS','credentialScan':'PASS','privateRowsSqlMediaIncluded':False}
    with destination.with_suffix('.receipt.json').open('x') as stream:json.dump(receipt,stream,ensure_ascii=False,indent=2)
    print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
