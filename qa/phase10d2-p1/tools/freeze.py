#!/usr/bin/env python3
"""Freeze actual compilation inputs, including untracked files; never use git diff as inventory."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
files=set()
for folder in ['apps/api/src/main','apps/api/src/test','apps/web/src','apps/web/tests','apps/api/.mvn','scripts','qa/phase10d2-p1/tools']:
    for p in (ROOT/folder).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':files.add(p)
for name in ['package.json','package-lock.json','apps/api/pom.xml','apps/api/mvnw','apps/api/mvnw.cmd','apps/web/package.json','apps/web/tsconfig.json','apps/web/next.config.ts','apps/web/next-env.d.ts','apps/web/eslint.config.mjs','apps/web/postcss.config.mjs','docs/openapi.yaml','docs/phase10/10D_2_IMPLEMENTATION_PLAN.md']:
    p=ROOT/name
    if p.is_file():files.add(p)
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
out=ROOT/'qa/phase10d2-p1/evidence'
text=json.dumps(manifest,indent=2,sort_keys=True)+'\n';(out/'candidate-inputs.json').write_text(text)
(out/'candidate-inputs.sha256').write_text(hashlib.sha256(text.encode()).hexdigest()+'  candidate-inputs.json\n')
print(len(manifest),'inputs',hashlib.sha256(text.encode()).hexdigest())
