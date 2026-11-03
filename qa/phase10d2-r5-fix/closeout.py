import hashlib
import json
import sys
import tempfile
import zipfile
import subprocess
from pathlib import Path

from run import git_inputs, q

BINARY_SUFFIXES = {'.mp3', '.wav', '.ogg', '.opus', '.m4a', '.webm', '.mov', '.png', '.jpg', '.jpeg', '.zip', '.jar'}
PLAYWRIGHT_DIR = 'output/playwright/phase10d2-r5-fix'


def preserve():
    manifest_path = q.OUT / 'qa-final-candidate-manifest.sha256'
    frozen = {line.split('  ', 1)[1]: line.split('  ', 1)[0] for line in manifest_path.read_text().splitlines()}
    binding = {}
    for name, checksum in frozen.items():
        binding[name] = dict(frozen=checksum, current=q.sha(q.ROOT / name), testedCopy=q.sha(q.SOURCE / name))
        assert len(set(binding[name].values())) == 1, name
    delivery = [p for p in git_inputs() if not p.startswith('qa/phase10d2-r5-fix/evidence/')]
    (q.OUT / 'delivery-manifest.sha256').write_text(''.join(q.sha(q.ROOT / p) + '  ' + p + '\n' for p in sorted(delivery)))
    evidence_files = {p.name: q.sha(p) for p in sorted(q.OUT.iterdir()) if p.is_file()}
    assert (q.ROOT / 'docs/progress/PHASE_10D_2_R5_FIX.md').is_file(), 'progress report missing'
    q.save('delivery-identity.json', dict(
        deliveryManifestSha256=q.sha(q.OUT / 'delivery-manifest.sha256'), deliveryCount=len(delivery),
        deliveryScope='all uncommitted and untracked files at closeout, excluding the local evidence directory',
        excludedLocalPaths=['qa/phase10d2-r5-fix/evidence/', 'output/', '.local/'],
        evidenceFileCount=len(evidence_files),
        frozenInputsUnchangedDuringRun=len(binding),
        webBuildId=(q.SOURCE / 'apps/web/.next/BUILD_ID').read_text().strip(),
        runtimeJarSha256=q.JAR_SHA,
        r5FailureEvidence=str((q.ROOT / 'qa/phase10d-final-r5/evidence').relative_to(q.ROOT)),
    ))
    q.sql('SELECT version,description,checksum,success FROM flyway_schema_history ORDER BY installed_rank', label='final-flyway-history')
    q.sql('SELECT COUNT(*) FROM concept_review_card; SELECT COUNT(*) FROM concept_review_source; '
          'SELECT COUNT(*) FROM concept_review_result; SELECT COUNT(*) FROM command_receipt', label='final-counts')
    q.run('final-db-logical-dump', [q.DOCKER, 'exec', q.identity()['containerId'], 'sh', '-c',
                                    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --no-tablespaces --set-gtid-purged=OFF ' + q.SCHEMA])
    dump = q.PRIVATE / 'final-db-logical-dump.log'
    (q.OUT / 'final-db-logical-dump.log').rename(dump)
    q.save('private-dump-identity.json', dict(path=str(dump), sha256=q.sha(dump), includedInEvidence=False, restoreTest=False))
    q.run('qa-ports-after-stop', ['/usr/sbin/lsof', '-nP', f'-iTCP:{q.API_PORT}', f'-iTCP:{q.WEB_PORT}', '-sTCP:LISTEN'], check=False)
    q.run('retained-qa-container', [q.DOCKER, 'inspect', '--format',
                                    '{"id":{{json .Id}},"running":{{json .State.Running}},"mounts":{{json .Mounts}}}',
                                    q.identity()['containerId']])
    print('PRESERVED', len(delivery), q.sha(q.OUT / 'delivery-manifest.sha256'), flush=True)


def package():
    files = {}
    for line in (q.OUT / 'qa-final-candidate-manifest.sha256').read_text().splitlines():
        checksum, name = line.split('  ', 1)
        path = q.ROOT / name
        assert q.sha(path) == checksum, name
        if path.suffix.lower() not in BINARY_SUFFIXES:
            files['source/' + name] = path
    for path in q.OUT.iterdir():
        if path.is_file() and path.suffix in ('.log', '.json', '.jsonl', '.sha256'):
            assert 'dump' not in path.name or path.name == 'private-dump-identity.json'
            files['evidence/' + path.name] = path
    for path in sorted((q.ROOT / PLAYWRIGHT_DIR).glob('*')):
        if path.is_file():
            files['playwright/' + path.name] = path
    for archive_name, path in {
        'docs/PHASE_10D_2_R5_FIX.md': q.ROOT / 'docs/progress/PHASE_10D_2_R5_FIX.md',
        'docs/PHASE_10D_QA_R5.md': q.ROOT / 'docs/progress/PHASE_10D_QA_R5.md',
        'docs/10D_D02_QA_R5_FINAL.md': q.ROOT / 'docs/qa/phase10d/10D_D02_QA_R5_FINAL.md',
    }.items():
        files[archive_name] = path
    status = subprocess.check_output(['git', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=q.ROOT, text=True)
    all_paths = sorted({line[3:] for line in status.splitlines() if (q.ROOT / line[3:]).is_file()})
    complete_manifest = q.ROOT / 'output/review/northstar-phase10d2-r5-fix-all-worktree.sha256'
    complete_manifest.write_text(''.join(q.sha(q.ROOT / name) + '  ' + name + '\n' for name in all_paths))
    files['freeze/all-worktree.sha256'] = complete_manifest
    for name in ('queue-recheck-result.json', 'browser-result.json'):
        path = q.ROOT / 'qa/phase10d-final-r5/evidence' / name
        if path.is_file():
            files['r5-original-failure/' + name] = path
    for name in ('queue-header.png', 'concept-queue-only.png', 'concept-queue-only.txt'):
        path = q.ROOT / 'output/playwright/phase10d-final-r5' / name
        if path.is_file(): files['r5-original-failure/' + name] = path
    secrets = list(q.credentials().values())
    sums = {}
    bundle = q.ROOT / 'output/review/northstar-phase10d2-r5-fix-sanitized-evidence.zip'
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            assert not any(part in ('.env', 'credentials.json', 'learning.json') for part in Path(name).parts)
            data = path.read_bytes()
            assert not any(secret.encode() in data for secret in secrets), name
            if path.suffix == '.zip':
                with zipfile.ZipFile(path) as trace:
                    assert all(not any(secret.encode() in trace.read(member) for secret in secrets) for member in trace.namelist())
            archive.writestr(name, data)
            sums[name] = hashlib.sha256(data).hexdigest()
        archive.writestr('SHA256SUMS.json', json.dumps(sums, indent=2, sort_keys=True) + '\n')
        archive.writestr('verify.py', """import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent
files=json.loads((root/'SHA256SUMS.json').read_text())
bad=[name for name,checksum in files.items() if not (root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=checksum]
if bad:raise SystemExit('FAIL '+str(bad))
print('PASS',len(files),'allowlisted files')
""")
    Path(str(bundle) + '.sha256').write_text(q.sha(bundle) + '  ' + bundle.name + '\n')
    with tempfile.TemporaryDirectory(prefix='northstar-r5fix-verify-') as directory:
        with zipfile.ZipFile(bundle) as archive:
            archive.extractall(directory)
        subprocess.run([sys.executable, Path(directory) / 'verify.py'], check=True)
    assert all(q.sha(q.ROOT / name) == checksum for checksum, name in (line.split('  ', 1) for line in complete_manifest.read_text().splitlines()))
    print('BUNDLE', len(files), q.sha(bundle), flush=True)


if __name__ == '__main__':
    {'preserve': preserve, 'package': package}[sys.argv[1]]()
