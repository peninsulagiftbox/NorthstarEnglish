#!/usr/bin/env python3
"""Offline evidence audit. No DB, application startup or process control."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = ROOT / 'docs/handoff/evidence/phase10b1'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    records = []

    def command(argv):
        result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
        records.append(dict(argv=argv, exitCode=result.returncode,
                            stdout=result.stdout, stderr=result.stderr))
        assert result.returncode == 0, argv
        return result.stdout

    head = command(['git', 'rev-parse', 'HEAD']).strip()
    command(['git', 'status', '--short', '--untracked-files=all'])
    command(['git', 'diff', '--check'])
    frozen = read(BASE / 'candidate/candidate-manifest.json')
    candidates = []
    for item in frozen['files']:
        candidate = ROOT / item['path']
        actual = ROOT / 'apps/api/src/main/resources/db/migration' / candidate.name
        assert candidate.stat().st_size == item['bytes']
        assert sha(candidate) == sha(actual) == item['sha256']
        candidates.append(dict(name=candidate.name, bytes=item['bytes'],
                               sha256=item['sha256'], applicationCopyMatches=True))
    old = []
    for path in sorted((ROOT / 'apps/api/src/main/resources/db/migration').glob('V00[1-8]*.sql')):
        result = subprocess.run(['git', 'show', f'HEAD:{path.relative_to(ROOT)}'],
                                cwd=ROOT, capture_output=True)
        records.append(dict(argv=['git', 'show', f'HEAD:{path.relative_to(ROOT)}'],
                            exitCode=result.returncode, outputSha256=hashlib.sha256(result.stdout).hexdigest()))
        assert result.returncode == 0 and result.stdout == path.read_bytes()
        old.append(dict(name=path.name, sha256=sha(path), matchesHead=True))
    assert len(old) == 8
    campaign = BASE / 'isolated-20261027t154428'
    audit = read(campaign / 'final-audit.json')
    stages = {}
    for role in audit['stages']:
        path = campaign / f'{role}-result.json'
        assert read(path)['status'] == 'PASS'
        stages[role] = dict(status='PASS', sha256=sha(path))
    assert len(stages) == 12
    logs = []
    for item in audit['publicFlywayLogs']:
        path = ROOT / item['exported']
        assert sha(path) == item['exportedSha256']
        logs.append(dict(path=item['exported'], sha256=sha(path), historicalExitCode=item['exitCode']))
    failure = read(campaign / 'controller-finalization-failure.json')
    assert failure['actualProcessExitCode'] == audit['controllerExitCode'] == 1
    writer = read(BASE / 'controller-writer-regression.json')
    assert writer['exitCode'] == 0 and not writer['fullRehearsalRerun']
    result = dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(), head=head,
                  scope='Offline artifact reconciliation; not an independent sign-off or DB rerun',
                  candidates=candidates, historicalMigrations=old, historicalStages=stages,
                  publicFlywayLogs=logs, controllerFailure=failure,
                  independentReview=read(BASE / 'STATUS.json')['independentReview'],
                  priorWaiver=read(ROOT / 'docs/handoff/evidence/personal-migration-20261027/authorization.json'),
                  databaseCommands=0, businessCodeChangedByThisAudit=False,
                  phase10b2FunctionalAcceptance='NOT VERIFIED', exitCode=0)
    (OUT / 'offline-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'audit-commands.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print('Offline audit PASS: 4 candidate copies, 8 historical migrations, 12 saved stage results, 10 public log hashes. Phase10B2 NOT VERIFIED.')


if __name__ == '__main__':
    main()
