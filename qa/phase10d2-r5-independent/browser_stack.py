from pathlib import Path
import json
import subprocess
import time
import urllib.request
import uuid
import shutil

from pagination_api import run_checks, set_due
from run import q


def wait_health(process):
    for _ in range(100):
        assert process.poll() is None, 'web process exited; private log retained'
        try:
            with urllib.request.urlopen(q.WEB + '/api/v1/health', timeout=2) as response:
                if json.load(response).get('migrationVersion') == '012.11':
                    return
        except OSError:
            pass
        time.sleep(0.3)
    raise RuntimeError('QA web readiness timeout')


def stage(name):
    q.run('browser-' + str(name), [q.NODE + '/node', q.TOOLS / 'matrix.cjs'], env=dict(q.env(), CARD_COUNT=str(name)), timeout=420)


def attempt(path, body, label):
    status, response = q.request(path, body)
    assert status == 200, (label, status, response)


def dictation(sentence):
    attempt('/exercises/' + sentence + '-dictation/attempts', dict(
        eventId=str(uuid.uuid4()), lessonId='qa-r5fix-queue', versionId='qa-r5fix-queue-v1',
        sentenceId=sentence, text='wrong answer', audioPlayed=True, answerExposed=False,
        clientOccurredAt='2026-11-03T10:00:00Z'), sentence)


def baseline():
    old = q.PRIVATE / 'r5-baseline'
    old.mkdir(exist_ok=True)
    shutil.copytree(q.ROOT / '.local/qa-final-r5/source/apps/web/.next', old / '.next', dirs_exist_ok=True)
    shutil.copy2(q.ROOT / '.local/qa-final-r5/source/apps/web/package.json', old / 'package.json')
    (old / 'node_modules').symlink_to(q.ROOT / 'node_modules', target_is_directory=True)
    runtime = json.loads((q.OUT / 'browser-runtime.json').read_text())
    baseline_env = dict(q.env(), API_PORT='8192', WEB_PORT='3199')
    old_api = subprocess.Popen([str(q.JAVA), '-jar', str(q.JAR)], env=baseline_env, cwd=q.SOURCE,
                               stdout=(q.PRIVATE / 'baseline-api.log').open('wb'), stderr=subprocess.STDOUT)
    old_web = subprocess.Popen([q.NODE + '/node', str(q.ROOT / 'node_modules/next/dist/bin/next'), 'start', '--hostname', '127.0.0.1', '--port', '3199'],
                               env=baseline_env, cwd=old, stdout=(q.PRIVATE / 'baseline-web.log').open('wb'), stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            assert old_api.poll() is None and old_web.poll() is None
            try:
                with urllib.request.urlopen('http://127.0.0.1:3199/api/v1/health', timeout=2) as response:
                    if json.load(response).get('migrationVersion') == '012.11': break
            except OSError: pass
            time.sleep(.3)
        else: raise RuntimeError('baseline startup failed')
        q.save('browser-runtime.json', dict(runtime, web='http://127.0.0.1:3199'))
        q.run('baseline-21', [q.NODE + '/node', q.TOOLS / 'matrix.cjs'], env=dict(q.env(), CARD_COUNT='21', BASELINE='1'), timeout=180)
    finally:
        q.save('browser-runtime.json', runtime)
        q.stop(old_web); q.stop(old_api)


def main():
    api = q.start_api()
    web = None
    try:
        existing = int(q.sql('SELECT COUNT(*) FROM concept_review_card'))
        assert existing in (0, 100), 'resume only at the explicit 100-card checkpoint'
        web = subprocess.Popen([q.NODE + '/node', str(q.ROOT / 'node_modules/next/dist/bin/next'), 'start',
                                '--hostname', '127.0.0.1', '--port', str(q.WEB_PORT)],
                               cwd=q.SOURCE / 'apps/web', env=q.env(),
                               stdout=(q.PRIVATE / 'web.log').open('wb'), stderr=subprocess.STDOUT)
        wait_health(web)
        q.save('browser-runtime.json', dict(root=str(Path(__file__).resolve().parents[2]), api=q.API, web=q.WEB,
                                            buildId=(q.SOURCE / 'apps/web/.next/BUILD_ID').read_text().strip(),
                                            jarSha256=q.JAR_SHA, database=q.identity()))
        if existing == 0: stage(0)
        if existing == 100:
            q.sql('UPDATE concept_review_card SET due_at=UTC_TIMESTAMP(3)', label='resume-100-due')
            stage(100)
        for index in range(existing + 1, 101):
            dictation('qa-r5fix-queue-v1-s' + str(index))
            if index in (1, 20, 21, 22, 100):
                assert q.sql('SELECT COUNT(*) FROM concept_review_card') == str(index)
                # The old baseline remains archived; this run tests only the new candidate.
                stage(index)
        assert q.sql('SELECT COUNT(*) FROM concept_review_card') == '100'
        rating = json.loads((q.OUT / 'matrix-100.json').read_text())['rating']
        assert q.sql("SELECT COUNT(*) FROM concept_review_result WHERE event_id='" + rating['eventId'] + "'") == '1'
        assert q.sql("SELECT row_version FROM concept_review_card WHERE id='" + rating['cardId'] + "'") == str(rating['rowVersion'])
        before_results = q.sql('SELECT COUNT(*) FROM concept_review_result')
        code, body = q.request('/concept-reviews/' + rating['cardId'] + '/results', dict(eventId=str(uuid.uuid4()), rowVersion=rating['rowVersion'] - 1,
                             rating='good', answerRevealed=True, clientOccurredAt='2026-11-03T10:00:00Z'))
        assert code == 409, (code, body)
        assert q.sql('SELECT COUNT(*) FROM concept_review_result') == before_results
        assert q.sql("SELECT COUNT(*) FROM exercise_attempt WHERE lesson_id='qa-r5fix-queue'") == '100'
        q.save('rating-cas-check.json', dict(replayedEvent=rating['eventId'], rowsForEvent=1, rowVersion=rating['rowVersion'], staleVersionStatus=code, unchangedResults=True, realAttempts=100))
        for index in range(83):
            lesson, version, exercise, option = ('cr-b', 'cr-b-v1', 'cr-read-2', 'cr2-a') if index == 1 else ('cr-a', 'cr-a-v1', 'cr-read-1', 'cr1-a')
            attempt('/reading/' + exercise + '/attempts', dict(eventId=str(uuid.uuid4()), lessonId=lesson,
                                                              versionId=version, optionId=option,
                                                              clientOccurredAt='2026-11-03T10:00:00Z'), 'reading-' + str(index))
        assert q.sql('SELECT COUNT(*) FROM concept_review_source') == '183'
        q.sql("UPDATE lesson SET availability='withdrawn' WHERE id='cr-a'", label='withdraw-qa-course-a')
        runtime = json.loads((q.OUT / 'browser-runtime.json').read_text())
        runtime['bankCardId'] = q.sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin'")
        q.save('browser-runtime.json', runtime)
        stage(101)
        run_checks()
        readonly = ('concept_review_source', 'concept_review_result', 'command_receipt')
        before = {table: q.sql(f'SELECT * FROM `{table}` ORDER BY 1', label='duecheck-before-' + table) for table in readonly}
        for count in (0, 1, 20, 21, 22, 100):
            set_due(count)
            q.run('browser-due-' + str(count), [q.NODE + '/node', q.TOOLS / 'due_check.cjs'],
                  env=dict(q.env(), DUE_COUNT=str(count)), timeout=240)
        q.save('duecheck-read-only-comparison.json',
               {table: before[table] == q.sql(f'SELECT * FROM `{table}` ORDER BY 1', label='duecheck-after-' + table) for table in readonly})
    finally:
        for table in ('concept_review_card', 'concept_review_source', 'concept_review_result', 'command_receipt',
                      'exercise_attempt', 'attempt_knowledge', 'review_item', 'review_source', 'review_result',
                      'learning_evidence', 'quiz_run', 'flyway_schema_history'):
            q.sql('SELECT * FROM `' + table + '` ORDER BY 1', label='final-state-' + table)
        if web:
            q.stop(web)
        q.stop(api)
        q.save('stop-state.json', dict(apiPid=api.pid, apiExit=api.returncode,
                                       webPid=None if web is None else web.pid, webExit=None if web is None else web.returncode))


if __name__ == '__main__':
    main()
