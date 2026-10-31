#!/usr/bin/env python3
"""Create a fresh R4 review package from the explicit R3 whitelist plus C01 evidence/sources."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'output/review'
BASE=REVIEW/'northstar-phase10c1-r3-sanitized'
TARGET=REVIEW/'northstar-phase10c1-r4-sanitized'
ZIP=REVIEW/'northstar-phase10c1-r4-sanitized-evidence.zip'
assert not TARGET.exists() and not ZIP.exists(),'Preserve existing published review packages'
paths={row['path'] for row in json.loads((BASE/'manifest.json').read_text())['files']}
paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'docs/handoff/evidence/phase10c1-r/acoustic').rglob('*') if p.is_file())
paths.update(p.relative_to(ROOT).as_posix() for p in ROOT.glob('scripts/phase10c1_c01_*.py'))
paths.update(p.relative_to(ROOT).as_posix() for p in ROOT.glob('scripts/phase10c1-c01-*.js'))
paths.update(['README.md','apps/web/src/lib/media/AudioController.ts','apps/web/tests/media.test.ts',
              'docs/progress/PHASE_10C_1_R_C01.md'])
rows=[]
for name in sorted(paths):
    path=ROOT/name
    assert path.resolve().is_relative_to(ROOT) and path.is_file() and not path.is_symlink()
    assert path.suffix not in ['.mp3','.wav','.webm','.zip']
    if path.suffix=='.f32':assert '/mathematical-controls/' in name
    target=TARGET/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,target)
    data=path.read_bytes()
    rows.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(TARGET/'manifest.json').write_text(json.dumps(dict(files=rows),indent=2)+'\n')
with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(TARGET.rglob('*')):
        if path.is_file():archive.write(path,path.relative_to(TARGET).as_posix())
print(json.dumps(dict(files=len(rows),zipMembers=len(rows)+1,zipBytes=ZIP.stat().st_size,
                      sha256=hashlib.sha256(ZIP.read_bytes()).hexdigest())))
