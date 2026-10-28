#!/usr/bin/env python3
"""Phase10B2 command recorder and isolated build copy. Never starts personal services."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import local

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.local/phase10b2'
COPY = STATE / 'source'
OUT = ROOT / 'docs/handoff/evidence/phase10b2'


def environment():
    env = local.environment()
    # Runtime paths are reused, credentials/ports are replaced by the isolated runner before DB work.
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def record(name, argv, env=None, cwd=COPY, expected=(0,), timeout=600):
    OUT.mkdir(parents=True, exist_ok=True)
    token = str(__import__('time').time_ns())
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    p = subprocess.run(argv, cwd=cwd, env=env or environment(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    raw = p.stdout.decode(errors='replace')
    for key, value in (env or environment()).items():
        if 'PASSWORD' in key and value: raw = raw.replace(value, '<REDACTED>')
    log = OUT / (name + '-' + token + '.log'); log.write_text(raw)
    row = dict(name=name, argv=[str(x) for x in argv], cwd=str(cwd), at=stamp, exitCode=p.returncode,
               gitSha=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
               log=str(log.relative_to(ROOT)), sha256=hashlib.sha256(log.read_bytes()).hexdigest())
    with (OUT/'execution-commands.jsonl').open('a') as f: f.write(json.dumps(row)+'\n')
    print(json.dumps(dict(name=name, exitCode=p.returncode, log=log.name)), flush=True)
    if p.returncode not in expected: raise RuntimeError('Failed command: '+name+'; see retained log')
    return p


def sync():
    COPY.mkdir(parents=True, exist_ok=True)
    for name in ['apps/api','apps/web','content','scripts','infra']:
        shutil.copytree(ROOT/name, COPY/name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('target','.next','node_modules','__pycache__'))
    for name in ['package.json','package-lock.json']:
        shutil.copyfile(ROOT/name, COPY/name)
    for name in ['node_modules','apps/web/node_modules']:
        target = COPY/name
        if (ROOT/name).exists() and not target.exists(): target.symlink_to(ROOT/name, target_is_directory=True)
    print('Isolated build copy synchronized', flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['sync']: sync()
    elif len(sys.argv) >= 4 and sys.argv[1] == 'run': record(sys.argv[2], sys.argv[3:])
    else: raise SystemExit('Usage: phase10b2.py sync | run NAME COMMAND...')
