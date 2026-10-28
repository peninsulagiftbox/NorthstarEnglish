#!/usr/bin/env python3
"""Local artifact checks only; no SQL, network or service operations."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
REPORT = ROOT / 'docs/progress/PHASE_10B_1.md'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    results = []
    commands = []
    baseline = json.loads((OUT / 'baseline.json').read_text())
    for item in baseline['trackedSourceHashes']:
        assert digest(ROOT / item['path']) == item['sha256'], item['path']
    results.append('190 tracked source/config/content files unchanged from preflight')
    for item in baseline['migrations']:
        assert item['matchesHead'] and item['gitShowReturncode'] == 0
        assert digest(ROOT / item['path']) == item['sha256']
    assert len(baseline['migrations']) == 8
    results.append('V001-V008 unchanged; no candidate DDL added')
    assert len(list((ROOT / 'apps/api/src/main/resources/db/migration').glob('*.sql'))) == 8
    for path in OUT.glob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
    for path in OUT.glob('*.json'):
        json.loads(path.read_text())
    results.append('Python AST and evidence JSON parse')
    for path in [REPORT, *OUT.glob('*.md'), *OUT.glob('*.py')]:
        assert all(line == line.rstrip() for line in path.read_text().splitlines()), str(path)
    for line in (ROOT / '.env').read_text().splitlines():
        key, sep, value = line.partition('=')
        if sep and 'PASSWORD' in key and len(value) >= 16:
            for path in [REPORT, *OUT.iterdir()]:
                if path.is_file():
                    assert value.encode() not in path.read_bytes(), 'Configured secret found'
    results.append('No configured DB password present in report/evidence; whitespace valid')
    for argv in [['git', 'diff', '--check'], ['git', 'status', '--short', '--untracked-files=all']]:
        p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        commands.append(dict(argv=argv, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr))
        assert p.returncode == 0
        if argv[1] == 'status':
            for line in p.stdout.splitlines():
                assert line.startswith('?? docs/handoff/evidence/phase10b1/') or line == '?? docs/progress/PHASE_10B_1.md'
    results.append('Git diff check and change scope limited to this report/evidence')
    acceptance = dict(B01='BLOCKED', B03='BLOCKED', evidence={
        k: 'BLOCKED' for k in ['source_identity_flyway', 'consistent_sql_media_backup',
        'v008_upgrade', 'v001_empty_init', 'failure_recovery', 'old_column_media_comparison']},
        historical_migration_bytes='PASS', database_privileges='NOT VERIFIED',
        source_database_audit='NOT VERIFIED', sourceWritesByThisRun=False,
        databaseConnected=False, servicesStartedOrStopped=False)
    (OUT / 'acceptance.json').write_text(json.dumps(acceptance, indent=2) + '\n')
    validation = dict(at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        command='PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/phase10b1/verify_evidence.py',
        result='PASS', checks=results, commands=commands,
        application_tests='NOT RUN', database_tests='BLOCKED')
    (OUT / 'validation.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n')
    manifest = [dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size, sha256=digest(p))
                for p in sorted([REPORT, *OUT.iterdir()])
                if p.is_file() and p.name != 'SHA256SUMS.json']
    (OUT / 'SHA256SUMS.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(result='PASS', checks=len(results), manifestFiles=len(manifest))))


if __name__ == '__main__':
    main()
