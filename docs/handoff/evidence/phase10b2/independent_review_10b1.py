#!/usr/bin/env python3
"""Independent offline review: reads historical files; never connects to a DB."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = ROOT / 'docs/handoff/evidence/phase10b1'
RUN = BASE / 'isolated-20261027t154428'
PRIVATE = ROOT / '.local/phase10b1-isolated/20261027t154428'
BACKUP = ROOT / '.local/phase10b1-backups/20261027T154428'
SOURCE_UUID = '104d5d9d-cd3f-11f1-8da4-920f115cf5cb'
SOURCE_CONTAINER = 'bbf8c3f55c023dd7e16377417e31b54c742cb3ecf109fd57f22c152babc58fd0'


def read(p):
    return json.loads(p.read_text())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def objects(table):
    return [dict(zip(table['columns'], [None if v is None else bytes.fromhex(v).decode() for v in row])) for row in table['rows']]


def keyed(table, columns=None):
    cols = table['columns'] if columns is None else columns
    return {tuple(row[table['columns'].index(c)] for c in table['primaryKey']):
            tuple(row[table['columns'].index(c)] for c in cols) for row in table['rows']}


def unchanged(old, new, extended=False):
    assert set(new) == set(old) | ({'paragraph'} if extended else set())
    for name, table in old.items():
        actual = new[name]
        assert set(table['columns']) <= set(actual['columns'])
        expected_rows = keyed(table)
        actual_rows = keyed(actual, table['columns'])
        if extended and name == 'flyway_schema_history':
            actual_rows = {k: v for k, v in actual_rows.items() if k in expected_rows}
        assert actual_rows == expected_rows, name + ': original cells changed'
        if not extended:
            assert table['createSql'] == actual['createSql'], name + ': schema changed'
        elif name != 'sentence':
            assert table['createSql'] == actual['createSql'], name + ': unapproved schema change'
        else:
            # Only approved column/index/FK lines may be new, including pre-NOT-NULL snapshots.
            old_lines = {l.strip().rstrip(',') for l in table['createSql'].splitlines()}
            new_lines = {l.strip().rstrip(',') for l in actual['createSql'].splitlines()
                         if not re.match(r'\s*`paragraph_id`\s', l)
                         and '`ix_sentence_paragraph_version`' not in l
                         and '`fk_sentence_paragraph_version`' not in l}
            assert old_lines == new_lines, 'sentence original constraints changed'


def inventory(folder):
    assert folder.is_dir() and not any(p.is_symlink() for p in [folder, *folder.parents])
    result = []
    for p in sorted(folder.rglob('*')):
        assert not p.is_symlink()
        if p.is_file():
            result.append(dict(path=str(p.relative_to(folder)), bytes=p.stat().st_size, sha256=digest(p)))
    return result


def main():
    checks = {}
    manifest = read(BASE / 'candidate/candidate-manifest.json')
    for item in manifest['files']:
        path = ROOT / item['path']
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256']
        assert (ROOT / 'apps/api/src/main/resources/db/migration' / path.name).read_bytes() == path.read_bytes()
    checks['frozenCandidateFiles'] = 4
    for item in read(BACKUP / 'SHA256SUMS.json'):
        path = BACKUP / item['path']
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256']
    assert (BACKUP / 'COMPLETE').is_file()
    assert not re.search(r'FOREIGN_KEY_CHECKS|DISABLE KEYS|DROP\s+(DATABASE|TABLE)|REPAIR|CLEAN',
                         (BACKUP / 'restore.sql').read_text(), re.I)
    checks['backupFiles'] = len(read(BACKUP / 'SHA256SUMS.json'))
    source = read(BACKUP / 'source-snapshot.json')
    assert len(source) == 37
    assert [h['version'] for h in objects(source['flyway_schema_history']) if h['type'] == 'SQL'] == [f'{n:03}' for n in range(1, 9)]
    checks['sourceHistoricalSchema'] = 'V008 / 37 tables'
    old_migrations = sorted((ROOT / 'apps/api/src/main/resources/db/migration').glob('V00[1-8]*.sql'))
    for path in old_migrations:
        p = subprocess.run(['git', 'show', 'HEAD:' + str(path.relative_to(ROOT))], cwd=ROOT, capture_output=True)
        assert p.returncode == 0 and p.stdout == path.read_bytes()
    checks['historicalMigrationsMatchHead'] = len(old_migrations)
    raw = read(RUN / 'commands.json')
    log_count = 0
    for item in raw:
        assert SOURCE_CONTAINER not in item.get('argv', [])
        if item.get('rawLog'):
            assert digest(ROOT / item['rawLog']) == item['rawLogSha256']
            log_count += 1
    checks.update(commandRecords=len(raw), rawLogHashes=log_count)
    summary_count = 0
    for path in RUN.glob('*-summary.json'):
        item = read(path)
        if 'privateSnapshot' in item:
            assert digest(ROOT / item['privateSnapshot']) == item['sha256']
            summary_count += 1
    checks['snapshotSummaryHashes'] = summary_count
    final = read(RUN / 'final-audit.json')
    roles = list(final['stages'])
    runtime = read(BASE / 'isolated-final-runtime-check.json')
    assert runtime['all12TargetsStopped'] and len(runtime['targets']) == 12
    assert len({t['uuid'] for t in runtime['targets']}) == 12
    assert all(t['uuid'] != SOURCE_UUID and t['status'] == 'exited' for t in runtime['targets'])
    media = read(BACKUP / 'media-manifest.json')
    for role in roles:
        assert read(RUN / (role + '-result.json'))['status'] == 'PASS'
        state = read(PRIVATE / role / 'state.json')
        assert state['uuid'] != SOURCE_UUID and state['containerId'] != SOURCE_CONTAINER
        assert inventory(PRIVATE / role / 'content') == media['content']
        if role != 'empty':
            assert inventory(PRIVATE / role / 'recordings/northstar_english') == media['recordings']
    checks['isolatedRolesAndMedia'] = len(roles)
    for tag in ['v008-restored', 'old-app-read']:
        unchanged(source, read(PRIVATE / 'upgrade' / (tag + '.json')))
    for ver in manifest['versions']:
        unchanged(source, read(PRIVATE / 'upgrade' / ('after-' + ver + '.json')), True)
    upgrade = read(PRIVATE / 'upgrade/candidate-baseline.json')
    empty = read(PRIVATE / 'empty/candidate-baseline.json')
    unchanged(read(PRIVATE / 'empty/v008-seeded.json'), empty, True)
    assert {t: d['createSql'] for t, d in upgrade.items()} == {t: d['createSql'] for t, d in empty.items()}
    for role, before in [('upgrade', upgrade), ('empty', empty)]:
        assert len(objects(before['paragraph'])) == 2
        paragraphs = {p['id']: p['version_id'] for p in objects(before['paragraph'])}
        sentences = objects(before['sentence'])
        assert len(sentences) == 20
        assert all(paragraphs[s['paragraph_id']] == s['lesson_version_id'] for s in sentences)
        for n in [1, 2]:
            unchanged(before, read(PRIVATE / role / f'candidate-start-{n}.json'))
        histories = objects(before['flyway_schema_history'])
        sql = [h for h in histories if h['type'] == 'SQL']
        assert len(sql) == 12 and all(h['success'] == '1' for h in sql)
        assert sum(h['type'] == 'BASELINE' for h in histories) == (role == 'upgrade')
        for h in sql:
            p = BASE / 'candidate' / h['script'] if h['version'].startswith('009') else ROOT / 'apps/api/src/main/resources/db/migration' / h['script']
            crc = 0
            for line in p.read_text(encoding='utf-8-sig').splitlines():
                crc = zlib.crc32(line.encode(), crc)
            assert int(h['checksum']) == (crc if crc < 2**31 else crc - 2**32)
        negative = read(RUN / (role + '-constraints.json'))
        assert [negative[k] for k in ['crossVersionFkError', 'checkError', 'uniqueError']] == [1452, 3819, 1062]
    checks['upgradeAndEmptyPaths'] = 'PASS, including old cells, history CRC, media, repeat startup, FK/CHECK/UQ negatives'
    for fault in ['fault-ddl-01', 'fault-ddl-02', 'fault-ddl-04', 'fault-history', 'fault-dml']:
        before = read(PRIVATE / fault / 'before-fault.json')
        after = read(PRIVATE / fault / 'after-fault.json')
        unchanged(source, before)
        for table, data in source.items():
            assert keyed(data) == keyed(after[table], data['columns'])
        assert after['flyway_schema_history']['rows'] == source['flyway_schema_history']['rows']
        if fault in ['fault-ddl-01', 'fault-history']:
            assert 'paragraph_id' not in after['sentence']['columns']
        if fault in ['fault-ddl-02', 'fault-dml']:
            assert not after['paragraph']['rows']
            assert all(s['paragraph_id'] is None for s in objects(after['sentence']))
        if fault == 'fault-ddl-04':
            assert after['sentence']['createSql'] == upgrade['sentence']['createSql']
        role = fault.replace('fault-', 'recover-')
        for tag in ['restored-v008', 'old-read']:
            unchanged(source, read(PRIVATE / role / (tag + '.json')))
        continued = read(PRIVATE / role / 'after-continuation.json')
        receipt = read(RUN / (role + '-continuation.json'))
        assert receipt['idempotentReplay'] and receipt['exactlyOneNewRevision'] and receipt['parentPreserved']
        event_hex = receipt['eventId'].encode().hex().upper()
        for name, old_table in source.items():
            new_table = continued[name]
            assert new_table['createSql'] == old_table['createSql']
            a, b = keyed(old_table), keyed(new_table)
            if name in ['writing_revision', 'learning_evidence', 'command_receipt']:
                assert len(b) == len(a) + 1 and all(b[k] == v for k, v in a.items())
                inserted = dict(zip(new_table['columns'], next(v for k, v in b.items() if k not in a)))
                assert inserted['event_id'] == event_hex
            elif name in ['writing_draft', 'practice_progress']:
                # Exactly one approved writing task projection may change; no unrelated row changes.
                changed = [k for k in set(a) | set(b) if a.get(k) != b.get(k)]
                assert len(changed) <= 1
                task = next(t for t in objects(source['writing_task']) if t['version_id'] == 'demo-01-v2')
                allowed = (task['id'].encode().hex().upper(),) + (() if name == 'writing_draft' else ('writing'.encode().hex().upper(),))
                assert all(k == allowed for k in changed)
            else:
                assert a == b, name + ': unrelated continuation delta'
        unchanged(continued, read(PRIVATE / role / 'after-restart.json'))
    checks['faultAndNewTargetRecoveryPaths'] = 5
    for item in final['publicFlywayLogs']:
        assert digest(ROOT / item['exported']) == item['exportedSha256'] == item['originalSha256']
        assert (ROOT / item['exported']).read_bytes() == (ROOT / item['originalPrivateLog']).read_bytes()
    failure_log = next(r for r in raw if r['name'] == 'fault-history-flyway-009.01')
    assert failure_log['returncode'] == 1 and 'INSERT command denied' in (ROOT / failure_log['rawLog']).read_text()
    failure = read(RUN / 'controller-finalization-failure.json')
    assert failure['actualProcessExitCode'] == 1 and 'FileExistsError' in failure['exception']
    assert read(RUN / 'result.json')['status'] == 'BLOCKED'
    assert read(BASE / 'controller-writer-regression.json')['exitCode'] == 0
    candidate_jar = ROOT / '.local/phase10b1-tools/northstar-isolated-candidate.jar'
    assert digest(candidate_jar) == read(RUN / 'artifacts.json')['isolatedCandidateJarSha256']
    with zipfile.ZipFile(candidate_jar) as z:
        for item in manifest['files']:
            p = ROOT / item['path']
            assert z.read('BOOT-INF/classes/db/migration/' + p.name) == p.read_bytes()
    checks['controllerExitPreserved'] = 1
    checks['publicFlywayLogHashes'] = len(final['publicFlywayLogs'])
    checks['isolatedCandidateJarHash'] = digest(candidate_jar)
    result = dict(at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
                  reviewer='/root/phase10b1_review', reviewerType='Independent review agent, not human signature',
                  verdict='PASS_WITH_CONTROLLER_NOTE', B01='PASS', B03='PASS',
                  acceptedFor='Phase10B2 isolated code development and testing only', checks=checks,
                  excluded=['Personal DB migration or service replacement', 'Changed/new migration automatic approval',
                            'Modern latest-schema empty bootstrap (must be retested in 10B2)', 'Human/third-party signature',
                            'Browser microphone/real-device/audio listening acceptance', 'Content publication/licensing'],
                  historicalSourceVersion='008', currentSourceVersion='009.04 per later migration evidence and parent health check',
                  databaseCommands=0, processControlCommands=0, exitCode=0,
                  controllerExitCode=1, independentReviewComplete=True)
    (OUT / 'INDEPENDENT_10B1_SIGNOFF.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
