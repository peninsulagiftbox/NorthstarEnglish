#!/usr/bin/env python3
"""Read-only audit checks; no app startup, DB tests, imports or learning writes."""
from pathlib import Path
import datetime
import json
import os
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import local

def clean(value):
    value = value.replace(str(ROOT), '<PROJECT_ROOT>').replace(str(Path.home()), '<HOME>')
    # Only redact actual secret values, never emit the environment itself.
    for key, secret in CONFIG.items():
        if any(word in key.upper() for word in ('PASSWORD', 'TOKEN', 'SECRET', 'API_KEY')) and len(secret) >= 8:
            value = value.replace(secret, '<REDACTED>')
    return re.sub(r'(?:sk-proj-|ghp_|github_pat_)[A-Za-z0-9_-]+', '<REDACTED>', value)

CONFIG = local.read_env(ROOT / '.env') if (ROOT / '.env').exists() else {}
env = local.environment() if CONFIG else dict(os.environ)
env['PYTHONDONTWRITEBYTECODE'] = '1'
checks = [
    ('versions', ['python3', '-c', 'import subprocess,sys; print(sys.version); [subprocess.run(x,check=True) for x in [["node","--version"],["npm","--version"],["java","-version"]]]']),
    ('python-unit', ['python3', '-m', 'unittest', 'discover', '-s', 'scripts/tests', '-v']),
    ('web-unit', ['npm', 'test']),
    ('web-typecheck', ['npm', 'run', 'typecheck']),
    ('web-lint', ['npm', 'run', 'lint']),
    ('content-v1', ['python3', 'scripts/validate-content.py', 'content/demo-01/v1']),
    ('content-v2', ['python3', 'scripts/validate-content.py', 'content/demo-01/v2']),
    ('web-build', ['npm', 'run', 'build']),
    ('java-unit', ['./mvnw', '-o', '-Dtest=TokenAlignerTest,SimpleSchedulerTest,ContentPackageTest,DatabaseGuardTest,HealthControllerTest', 'test']),
    ('java-pure', ['./mvnw', '-o', '-Dtest=TokenAlignerTest,SimpleSchedulerTest,ContentPackageTest', 'test']),
    ('java-compile', ['./mvnw', '-o', '-DskipTests', 'package']),
    ('diff-check', ['git', 'diff', '--check']),
]
if len(sys.argv) > 1:
    checks = [c for c in checks if c[0] in sys.argv[1:]]
records = json.loads((HERE / 'commands.json').read_text()) if (HERE / 'commands.json').exists() else []
for name, args in checks:
    started = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    before = time.monotonic()
    try:
        result = subprocess.run(args, cwd=ROOT / 'apps/api' if name.startswith('java-') else ROOT,
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=240)
        code, output = result.returncode, result.stdout
    except subprocess.TimeoutExpired as exc:
        code, output = 124, (exc.stdout or b'').decode(errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        output += '\nAUDIT TIMEOUT: 240 seconds; not a passing check.\n'
    except OSError as exc:
        code, output = 127, str(exc)
    record = dict(id=name, command=args, cwd='apps/api' if name.startswith('java-') else '.', startedAt=started,
        exitCode=code, seconds=round(time.monotonic()-before, 3), log=name+'.log')
    (HERE / (name+'.log')).write_text(clean(json.dumps(record, ensure_ascii=False)+'\n\n'+output))
    records.append(record)
    (HERE / 'commands.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
    print(f'{name}: exit={code}', flush=True)
