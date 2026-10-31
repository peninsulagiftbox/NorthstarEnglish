#!/usr/bin/env python3
"""10C-1-R: reuse the pinned isolated candidate; never start a personal database target."""
import hashlib
import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import phase10c1_isolated as iso

r = iso.r
OUT = r.OUT / 'reacceptance'
OUT.mkdir(parents=True, exist_ok=True)
r.OUT = OUT


def request(base, path, value=None, method='POST', match=None):
    headers = {'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:3175',
               'X-Northstar-Request': 'local-workspace'}
    if match is not None:
        headers['If-Match'] = match
    req = urllib.request.Request(base + path, data=json.dumps(value).encode() if value is not None else None,
                                 headers=headers, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as error:
        response = error
    raw = response.read()
    return response.status, json.loads(raw) if raw else None


def guard(c, role, e, base):
    schema = 'northstar_phase01_test'
    original_sql = c.sql
    def sql(role, query, *args, **kwargs):
        return original_sql(role, 'USE ' + schema + ';' + query, *args, **kwargs)
    c.sql = sql
    try:
        sentence = 'c1-shared-v1-s1'
        context = dict(lessonId='c1-shared', versionId='c1-shared-v1', sentenceId=sentence)
        # Nonempty history and a paused exercise/draft catch destructive rollbacks as well as inserts.
        event = dict(context, eventId=str(uuid.uuid4()), action='pause', clientOccurredAt='2026-10-30T00:00:00Z')
        result = request(base, '/study/events', event)
        assert result[0] == 200, result
        status, draft = request(base, '/drafts/' + sentence + '?lessonId=c1-shared&versionId=c1-shared-v1', method='GET')
        assert status == 200
        assert request(base, '/drafts/' + sentence, dict(lessonId=context['lessonId'], versionId=context['versionId'], text='Retained isolated draft.'), method='PUT', match='"' + str(draft['rowVersion']) + '"')[0] == 200
        asset = json.loads(c.sql(role, "SELECT JSON_OBJECT('key',storage_key,'bytes',byte_size,'sha256',sha256) FROM audio_asset WHERE id='c1-shared-v1-a1'", readonly=True).stdout)
        root = Path(e['NORTHSTAR_CONTENT_ROOT']).resolve()
        file = (root / asset['key']).resolve()
        assert file.is_relative_to(root)
        original = file.read_bytes()
        assert hashlib.sha256(original).hexdigest() == asset['sha256'] and len(original) == asset['bytes']
        healthy = c.snapshot(role, 'r-healthy-' + str(time.time_ns()))
        rows = []
        try:
            bad = b'corrupt MPEG reacceptance fixture'
            file.write_bytes(bad)
            c.sql(role, "UPDATE audio_asset SET byte_size=%d,sha256='%s' WHERE id='c1-shared-v1-a1'" % (len(bad), hashlib.sha256(bad).hexdigest()))
            before = c.snapshot(role, 'r-corrupt-before-' + str(time.time_ns()))
            for repeat in range(2):
                # Same event ID retried: a rejected command must not leave an idempotency receipt.
                if repeat == 0:
                    value = dict(context, eventId=str(uuid.uuid4()), text='An original wrong answer.', audioPlayed=True,
                                 answerExposed=False, clientOccurredAt='2026-10-30T00:00:00Z')
                status, body = request(base, '/exercises/' + sentence + '-dictation/attempts', value)
                assert status == 503 and body['code'] == 'AUDIO_UNAVAILABLE', (status, body)
                after = c.snapshot(role, 'r-corrupt-after-' + str(time.time_ns()))
                assert before == after, 'Rejected attempt changed database rows or schema'
                rows.append(dict(repeat=repeat, status=status, code=body['code'], allTablesExact=True))
        finally:
            file.write_bytes(original)
            c.sql(role, "UPDATE audio_asset SET byte_size=%d,sha256='%s' WHERE id='c1-shared-v1-a1'" % (asset['bytes'], asset['sha256']))
        assert healthy == c.snapshot(role, 'r-restored-' + str(time.time_ns()))
        assert request(base, '/audio/c1-shared-v1-a1', method='HEAD')[0] == 200
        report = dict(status='PASS', database='isolated test schema; UUID/port/container/mount gates checked',
                      rejectedRequests=rows, allTablesCompared=len(before),
                      tables={name: dict(rowCount=len(data['rows']), sha256=hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()) for name, data in before.items()},
                      protected=['command_receipt', 'exercise_attempt', 'learning_evidence', 'study_event', 'study_stage', 'exercise_draft', 'review_item', 'review_source'],
                      pausedStateAndDraftSeeded=True, mediaAndMetadataRestored=True, allRowsRestoredToHealthySnapshot=True)
        (OUT / 'bad-media-guard.json').write_text(json.dumps(report, indent=2) + '\n')
        print('Bad-media guard PASS: two 503 responses; all %d tables exact; media restored.' % len(before), flush=True)
    finally:
        c.sql = original_sql


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-only', action='store_true')
    options = parser.parse_args()
    if options.native_only:
        OUT = OUT / ('continuation-' + str(time.time_ns()))
        OUT.mkdir()
        r.OUT = OUT
    stop = r.STATE / 'R_STOP'
    if options.native_only:
        stop = OUT / 'STOP'
        (r.STATE / 'R_ACTIVE_OUTPUT').write_text(str(OUT.relative_to(r.ROOT)))
    assert not stop.exists(), 'Archive the previous stop marker before starting another isolated run'
    c = iso.campaign()
    c.OUT = OUT / 'database'
    c.OUT.mkdir(exist_ok=True)
    role = 'regression-final'
    d = c.verify(role)
    state = c.call('r-state', [c.DOCKER, 'inspect', '--format', '{{.State.Running}}', d['containerId']]).stdout.decode().strip()
    assert state == 'false', 'Refuse to adopt a running database'
    assert c.available(d['port']) and c.available(8155) and c.available(3175)
    if options.native_only:
        assert c.available(3177)
    c.call('r-start-owned', [c.DOCKER, 'start', d['containerId']])
    children = []
    streams = []
    command = None
    proxy = None
    try:
        for _ in range(40):
            probe = c.call('r-ready', [c.DOCKER, 'exec', d['containerId'], 'sh', '-c', 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "SELECT @@server_uuid"'], expected=(0, 1), private=True)
            if probe.returncode == 0:
                assert probe.stdout.decode().strip() == d['uuid']
                break
            time.sleep(.5)
        else:
            raise RuntimeError('Isolated DB readiness timeout')
        e = iso.env(c, role, 'northstar_phase01_test')
        for name, args, cwd in [
            ('api', [str(c.JAVA), '-jar', str(c.PATCHED_JAR), '--server.port=8155', '--northstar.content-root=' + e['NORTHSTAR_CONTENT_ROOT'], '--northstar.recording-root=' + e['NORTHSTAR_RECORDING_ROOT']], r.COPY / 'apps/api'),
            ('web', ['node', str(r.ROOT / 'node_modules/next/dist/bin/next'), 'start', '--hostname', '127.0.0.1', '--port', '3177' if options.native_only else '3175'], r.COPY / 'apps/web')]:
            stream = (OUT / (name + '-' + str(time.time_ns()) + '.log')).open('xb')
            streams.append(stream)
            children.append(subprocess.Popen(args, cwd=cwd, env=e, stdout=stream, stderr=subprocess.STDOUT))
        if options.native_only:
            import phase10c1_r_native_probe
            proxy, _ = phase10c1_r_native_probe.start(OUT)
        for _ in range(120):
            assert all(p.poll() is None for p in children)
            try:
                with urllib.request.urlopen('http://127.0.0.1:3175/api/v1/health', timeout=2) as response:
                    assert response.headers['X-Northstar-Test-Database'] == 'true'
                    assert json.load(response)['migrationVersion'] == '010.06'
                    break
            except OSError:
                time.sleep(.25)
        else:
            raise RuntimeError('Candidate readiness timeout')
        if not options.native_only:
            guard(c, role, e, 'http://127.0.0.1:8155/api/v1')
        cli = next(p.parent / 'playwright-cli.js' for p in sorted((Path.home() / '.npm/_npx').glob('*/node_modules/@playwright/cli/package.json')) if json.loads(p.read_text()).get('version') == '0.1.22')
        command = ['node', str(cli), '--session=northstar-phase10c1-r']
        r.record('browser-open', command + ['open', 'http://127.0.0.1:3175/lesson/c1-shared?version=c1-shared-v1&tab=text', '--headed'], env=e, cwd=r.ROOT)
        (OUT / 'session.json').write_text(json.dumps(dict(cli=str(cli), pids=[p.pid for p in children], stopFile=str(stop.relative_to(r.ROOT)), jarSha256=hashlib.sha256(c.PATCHED_JAR.read_bytes()).hexdigest(), webBuildId=(r.COPY / 'apps/web/.next/BUILD_ID').read_text().strip())) + '\n')
        print('READY: isolated candidate; output=' + str(OUT.relative_to(r.ROOT)) + '; stop=' + str(stop.relative_to(r.ROOT)), flush=True)
        deadline = time.monotonic() + 1800
        while time.monotonic() < deadline and not stop.exists():
            assert all(p.poll() is None for p in children)
            time.sleep(1)
    finally:
        if command:
            r.record('browser-close', command + ['close'], env=e, cwd=r.ROOT, expected=(0, 1))
        for p in children:
            if p.poll() is None:
                p.terminate()
        for p in children:
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=10)
        for stream in streams:
            stream.close()
        if proxy:
            proxy.shutdown()
            proxy.server_close()
        c.stop(role)
        (OUT / 'cleanup.json').write_text(json.dumps(dict(childrenStopped=all(p.poll() is not None for p in children), databaseStopped=True, volumePreserved=True)) + '\n')


if __name__ == '__main__':
    main()
