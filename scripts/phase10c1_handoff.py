#!/usr/bin/env python3
"""Package existing Phase 10C-1 evidence only; never start an app, database, or migration."""
import argparse
import array
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import wave
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'output/review'
STAGE = REVIEW / 'northstar-phase10c1-sanitized'
ZIP = REVIEW / 'northstar-phase10c1-sanitized-evidence.zip'
R4 = REVIEW / 'northstar-phase10c1-r4-sanitized'
EVIDENCE = ROOT / 'docs/handoff/evidence/phase10c1'
PROVENANCE = []
REFERENCES = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, data):
    path = STAGE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data)
    return name


def document(name, data):
    return write(name, json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def redact(text, identities=False):
    text = text.replace(str(ROOT), '<project-root>').replace(str(Path.home()), '<user-home>')
    text = text.replace('started by ' + Path.home().name, 'started by <user>')
    if identities:
        text = re.sub(r"(?m)^(SOURCE_UUID|SOURCE_CONTAINER)\s*=\s*(['\"]).*?\2", r"\1='<REDACTED_LOCAL_DENYLIST_ID>'", text)
    return text


def copy_exact(name):
    source = ROOT / name
    assert source.is_file() and not source.is_symlink(), name
    write(name, source.read_bytes())
    return name


def derived_json(name):
    source = ROOT / name
    raw = source.read_bytes()
    value = json.loads(redact(raw.decode()))
    document(name, value)
    PROVENANCE.append(dict(path=name, originalSha256=sha(raw), kind='path-redacted JSON'))
    return name


def source_snapshot():
    paths = set()
    for folder in ['apps/api/src', 'apps/web/src', 'apps/web/tests', 'scripts/tests']:
        paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob('*') if p.is_file() and p.suffix in ['.java', '.yml', '.sql', '.ts', '.tsx', '.css', '.svg', '.json', '.py'])
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'scripts').glob('phase10c1*') if p.suffix in ['.py', '.js'])
    paths.update(['README.md', 'package.json', 'package-lock.json', 'apps/api/pom.xml', 'apps/api/mvnw',
                  'apps/api/.mvn/wrapper/maven-wrapper.properties', 'apps/web/package.json',
                  'apps/web/next.config.ts', 'apps/web/tsconfig.json', 'apps/web/eslint.config.mjs',
                  'apps/web/postcss.config.mjs', 'docs/openapi.yaml', 'docs/DEPENDENCIES.md',
                  'scripts/data-transfer.py', 'scripts/full-learning-loop.js', 'scripts/player-timeline-browser-smoke.js',
                  'scripts/phase10b2.py', 'scripts/local.py',
                  'docs/handoff/evidence/phase10b1/isolated_rehearsal.py',
                  'docs/handoff/evidence/phase10b1/maintenance_backup.py',
                  'docs/handoff/evidence/phase10b1/runtime_media_preflight.py',
                  'docs/handoff/evidence/phase10b1/resume_watchdog.py'])
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'content/demo-01').rglob('*.json'))
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True)
    entries = []
    for name in sorted(paths):
        path = ROOT / name
        assert path.is_file(), 'Missing required source: ' + name
        after = path.read_bytes()
        before_result = subprocess.run(['git', 'show', head + ':' + name], cwd=ROOT, capture_output=True)
        before = before_result.stdout if before_result.returncode == 0 else None
        masked = name.startswith('docs/handoff/evidence/phase10b1/')
        shared_after = redact(after.decode(), identities=True).encode() if masked else after
        shared_before = redact(before.decode(), identities=True).encode() if masked and before is not None else before
        write(name, shared_after)
        before_path = None
        if before is not None:
            before_path = write('review/git-before/' + name, shared_before)
        patch_path = None
        if before != after:
            old = shared_before.decode().splitlines(keepends=True) if shared_before is not None else []
            patch = ''.join(difflib.unified_diff(old, shared_after.decode().splitlines(keepends=True),
                                               fromfile='a/' + name if before is not None else '/dev/null', tofile='b/' + name))
            patch_path = write('review/diffs/' + name + '.patch', patch)
        entries.append(dict(path=name, head=head, trackedAtHead=before is not None, changed=before != after,
                            beforeSha256=sha(before) if before is not None else None, beforeSharedSha256=sha(shared_before) if shared_before is not None else None, afterSha256=sha(after),
                            sharedSha256=sha(shared_after), beforeSnapshot=before_path, patch=patch_path,
                            redactedLocalGuardConstants=shared_after != after,
                            note='Machine-local denylist constants/path strings are masked; original hashes retained. Review-only guard dependency needs private local identity state to execute.' if shared_after != after else 'Exact source bytes'))
    document('review/source-manifest.json', entries)
    document('review/git.json', dict(head=head, status=status, snapshot='Uncommitted working tree; HEAD is the pre-10C-1 baseline, not the final runtime candidate'))
    return entries


def import_r4():
    rows = json.loads((R4 / 'manifest.json').read_text())['files']
    for row in rows:
        data = (R4 / row['path']).read_bytes()
        assert sha(data) == row['sha256'] and len(data) == row['bytes']
        write(row['path'], data)
    document('review/r4-origin.json', dict(sha256=sha((REVIEW / 'northstar-phase10c1-r4-sanitized-evidence.zip').read_bytes()),
                                        files=len(rows), copiedFrom='Frozen R4 whitelist; current reports and exact source snapshots supersede corresponding textual files'))


def execution_evidence():
    commands = [json.loads(line) for line in (EVIDENCE / 'execution-commands.jsonl').read_text().splitlines()]
    runs = []
    for row in commands:
        path = ROOT / row['log']
        data = path.read_bytes()
        assert sha(data) == row['sha256'], row['log']
        name = row['name']
        include = name.startswith(('java-', 'node-', 'python-', 'typecheck', 'lint', 'web-build', 'c01-fix-', 'browser-phase10c1-', 'browser-full-learning-loop.js'))
        if not include:
            continue
        text = data.decode(errors='replace')
        # Browser failure BODY dumps may contain existing learning inputs. Keep type/stack, withhold only the dump.
        text = re.sub(r' BODY .*', ' BODY <REDACTED_LEARNING_UI_DUMP>', text, flags=re.S)
        shared = 'Derived log; original SHA-256: ' + row['sha256'] + '\n' + redact(text)
        write(row['log'], shared)
        totals = re.findall(r'Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)', text)
        run = dict(name=name, at=row['at'], exitCode=row['exitCode'], argv=[redact(str(x)) for x in row['argv']],
                   cwd=redact(row['cwd']), log=row['log'], originalLogSha256=row['sha256'],
                   note='Historical actual run; not re-executed for handoff; nonzero exits preserved')
        if totals:
            run['lastJUnitSummary'] = dict(zip(['tests', 'failures', 'errors', 'skipped'], map(int, totals[-1])))
        run['isolatedDatabaseObservedInLog'] = 'northstar_phase01_test' in text and ('Flyway' in text or 'flyway' in text)
        runs.append(run)
        PROVENANCE.append(dict(path=row['log'], originalSha256=row['sha256'], kind='derived log; path and optional learning BODY redaction'))
    document('review/execution-catalog.json', runs)
    private_operations = []
    for journal in sorted((EVIDENCE / 'migrations').rglob('commands.jsonl')):
        for line in journal.read_text().splitlines():
            row = json.loads(line)
            if row.get('rawLog'):
                path = ROOT / row['rawLog']
                assert sha(path.read_bytes()) == row['rawLogSha256'], row['name']
            private_operations.append(dict(name=row['name'], at=row['started'], exitCode=row['returncode'],
                                           originalRawLogSha256=row.get('rawLogSha256'), stdinSha256=row.get('stdinSha256'),
                                           rawLogIncluded=False, reason='Private SQL/rows, local identity and connection details withheld; verify the hash locally'))
    document('review/database-command-catalog.json', private_operations)
    summaries = []
    for path in sorted((EVIDENCE / 'migrations').rglob('*.json')):
        if 'acceptance' in path.name or path.name == 'actual-backup-restore.json':
            summaries.append(derived_json(path.relative_to(ROOT).as_posix()))
    for name in ['audio-fixtures.json', 'audio-license-review.json', 'frozen-migrations.json', 'delivery-audit.json',
                 'candidate-inputs.json', 'phase10c1-browser-smoke.js.result.json', 'full-learning-loop.js.result.json', 'output-capture-probe.json']:
        derived_json((EVIDENCE / name).relative_to(ROOT).as_posix())
    document('review/retained-evidence-inventory.json', dict(originalCommandRecords=len(commands), sharedRuns=len(runs),
                                                          privateDatabaseOperations=len(private_operations), migrationSummaries=summaries))
    return runs, summaries


def database_snapshot_summary():
    base = ROOT / '.local/phase10c1/database/regression-final'
    names = ['r-healthy-1793349062660589000.json', 'r-corrupt-before-1793349074642839000.json',
             'r-corrupt-after-1793349085866855000.json', 'r-corrupt-after-1793349097296308000.json', 'r-restored-1793349108593546000.json']
    snapshots = [json.loads((base / name).read_text()) for name in names]
    assert snapshots[1] == snapshots[2] == snapshots[3] and snapshots[0] == snapshots[4]
    assert len(snapshots[0]) == 45
    tables = {}
    for table in snapshots[0]:
        states = [dict(rows=len(value[table]['rows']), sha256=sha(json.dumps(value[table], sort_keys=True).encode())) for value in snapshots]
        tables[table] = dict(states=states, rejectedRequestsLeaveTableExact=states[1] == states[2] == states[3], restoredExact=states[0] == states[4])
    document('review/database-static-snapshot-verification.json', dict(status='PASS (existing file comparison only)',
             databaseConnected=False, snapshots=[dict(localPath='.local/phase10c1/database/regression-final/' + name,
             sha256=sha((base / name).read_bytes()), included=False) for name in names], tables=tables,
             limitation='Hashes/counts cannot replace the withheld private row values for independent off-machine recomputation'))


def documents_and_images():
    for path in ['docs/IMPLEMENTATION_PLAN.md', 'docs/phase10/10C_1_IMPLEMENTATION_PLAN.md',
                 'docs/phase10/04_MIGRATION_PLAN.md', 'docs/phase10/05_AUDIO_ALIGNMENT_DESIGN.md',
                 'docs/phase10/06_CONTENT_IMPORT_PIPELINE.md', 'docs/phase10/07_API_AND_FRONTEND_IMPACT.md',
                 'docs/phase10/08_TEST_AND_ACCEPTANCE_PLAN.md',
                 'docs/progress/PHASE_10C_1.md', 'docs/progress/PHASE_10C_1_R.md', 'docs/progress/PHASE_10C_1_R_C01.md',
                 'docs/handoff/PHASE_10C_1_REVIEW.md']:
        copy_exact(path)
    images = []
    for name in ['full-track-1440.png', 'long-track-1440.png', 'player-failure.png']:
        path = 'output/playwright/phase10c1/' + name
        copy_exact(path)
        images.append(dict(path=path, reviewed='Original synthetic shared/long test content only; no personal writing/recordings/browser chrome',
                           historicalFailure=name == 'player-failure.png'))
    document('review/screenshots.json', dict(included=images, abScreenshot='NOT AVAILABLE: A/B is supported by existing E2E source/log assertions; no dedicated A/B screenshot/video was retained',
                                           demoScreenshots='Withheld to avoid sharing writing/input history; Demo checks and code/log evidence remain'))
    # Render only the existing self-authored noise calibration into playable short WAVs.
    controls = STAGE / 'docs/handoff/evidence/phase10c1-r/acoustic/mathematical-controls'
    converted = []
    for name in ['known-pcm-input.f32', 'known-pcm.f32', 'webcodecs-opus-input.f32', 'webcodecs-opus-decoded.f32']:
        source = controls / name
        data = array.array('f')
        data.frombytes(source.read_bytes())
        pcm = array.array('h', (max(-32768, min(32767, round(x * 32767))) for x in data))
        target = STAGE / 'review/audio' / (source.stem + '.wav')
        target.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(target), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(48000)
            audio.writeframes(pcm.tobytes())
        converted.append(dict(path=target.relative_to(STAGE).as_posix(), source=source.relative_to(STAGE).as_posix(), sourceSha256=sha(source.read_bytes()),
                              sampleRate=48000, frames=len(data), transformation='Existing mathematical-noise Float32 -> PCM16 WAV; format conversion only, no new capture'))
    document('review/audio/manifest.json', converted)


def entrypoints(runs, summaries, sources):
    def logs(prefix):
        return [run['log'] for run in runs if run['name'].startswith(prefix)]
    core = 'docs/handoff/evidence/phase10c1-r/acoustic/'
    cases = [
        ('C01-assets', '独立/共享、非零start、句间静音、单句/顺序/循环/A-B', 'Original-media E2E passed=true; assertions in actual source and retained run logs', ['scripts/phase10c1-browser-smoke.js', core + 'fixed-browser-regression.json'] + logs('browser-phase10c1-browser-smoke.js')),
        ('C01-rates-boundaries', '四速率×两音轨模式×首中末×10次真实输出', 'Reported PASS, 240/240; fixed digital path; original speech output remains local', [core + 'acceptance-final.json', core + 'measurements-final.csv', core + 'group-statistics.json', core + 'raw-manifest.json']),
        ('C01-switch-loop', '20次快速同/异文件切句、至少10轮循环', 'E2E checks retained; actual acoustic repeats separately catalogued', ['scripts/phase10c1-browser-smoke.js', core + 'fixed-browser-regression.json']),
        ('C01-resume', '刷新暂停恢复、句内偏移与整轨坐标、>10分钟音轨', '645000ms asset position and 5000ms segment offset; 660s signal, not spoken lecture', [core + 'fixed-browser-regression.json', 'output/playwright/phase10c1/long-track-1440.png']),
        ('C01-native', '真实Chrome hidden→pause→visible后保持暂停→手动play', 'Native single and sentence-loop PASS; synthetic/automated visibility is not substituted', [core + 'native/native-acceptance.json', 'scripts/phase10c1_r_native_analysis.py']),
        ('C01-human', '逐句检查截词、漏词、重复、串句', '15 original sentences PASS, user self-reported; no new human signature in this handoff', ['docs/handoff/evidence/phase10c1-r/continuation/manual-listening.json']),
        ('C01-failure', '原始失败及修复后记录', 'Actual 1x after cross-file load despite UI1.25x; pre-fix failures retained, all 240 fixed-candidate runs recollected', [core + 'speed-reset-failure.json', core + 'excluded-captures.json'] + logs('c01-fix-')),
        ('C04-migrations', '旧基线升级、空库V001、部分DDL失败、恢复后续学/重启', 'Existing isolated acceptance summaries; private SQL/rows withheld, actual operation exit codes retained', summaries + ['review/database-command-catalog.json', 'docs/handoff/evidence/phase10c1/frozen-migrations.json']),
        ('C04-media', '索引/CHECK正反例、200/206/416、503、路径越界、非法区间、文本降级', 'Real isolated AudioIntegrationTest and catalog tests; zero skips must be checked per actual run', ['apps/api/src/test/java/local/northstar/catalog/AudioIntegrationTest.java', 'apps/api/src/test/java/local/northstar/catalog/CatalogIntegrationTest.java'] + logs('java-audio')),
        ('C04-evidence', '坏媒体作答不新增receipt/attempt/evidence或非法改变状态', 'Two actual 503 responses; all45 tables exact; offline snapshot rehash only in this handoff', ['docs/handoff/evidence/phase10c1-r/bad-media-guard.json', 'review/database-static-snapshot-verification.json', 'scripts/phase10c1_reacceptance.py']),
        ('regression', 'Java单元/真实隔离DB、Node、类型/lint/build、Demo学习闭环', 'Actual exit codes include original failures; runs belong to their recorded candidates, not all rerun on final Web BUILD_ID', ['review/execution-catalog.json', 'docs/handoff/evidence/phase10c1/full-learning-loop.js.result.json', 'scripts/full-learning-loop.js'])]
    result = []
    for code, expected, actual, evidence in cases:
        assert all((STAGE / path).is_file() for path in evidence), code
        result.append(dict(id=code, expected=expected, actual=actual, evidence=evidence, newlyExecuted=False))
        REFERENCES.extend(dict(case=code, path=path) for path in evidence)
    document('review/test-cases.json', result)
    personal = json.loads((EVIDENCE / 'personal-final-readonly.json').read_text())
    latest = json.loads((STAGE / core / 'runtime-cleanup.json').read_text())
    deployment_reports = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'docs/progress').glob('*DEPLOYMENT*') if '10C' in p.name]
    document('review/deployment-scope.json', dict(phase10c1DeploymentReports=deployment_reports, phase10c1PersonalDeploymentAuthorized=False,
             phase10c1PersonalDatabaseDeployed=False, lastRecordedPersonalMigrationVersion=latest['personalApiGETMigrationVersion'],
             lastRecordedPersonalJarSha256=personal['jarSha256'], lastRecordedPersonalWebBuildId=personal['webBuildId'],
             healthNotQueriedAgainForHandoff=True, privateDatabaseNotConnectedForHandoff=True,
             previousStageDeploymentReports=[p.relative_to(ROOT).as_posix() for p in (ROOT / 'docs/progress').glob('*10B_3_DEPLOYMENT.md')],
             sourceEvidence=[core + 'runtime-cleanup.json', 'docs/handoff/evidence/phase10c1/delivery-audit.json']))
    document('review/reference-index.json', REFERENCES)
    document('review/provenance.json', PROVENANCE)
    write('REVIEW_START_HERE.md', '''# Phase 10C-1 independent-review package

Start with [the handoff report](docs/handoff/PHASE_10C_1_REVIEW.md) and [the actual phase report](docs/progress/PHASE_10C_1.md).

- [Source before/after SHA-256 and patches](review/source-manifest.json), [Git HEAD/status](review/git.json). Current exact code keeps repository-relative paths; tracked HEAD copies are under review/git-before and per-file diffs under review/diffs. Local denylist constants in old isolation helper dependencies are explicitly masked, with original and shared hashes distinguished.
- [Actual run exit codes/logs](review/execution-catalog.json), [case-to-evidence map](review/test-cases.json), [database operation exit codes](review/database-command-catalog.json).
- [240 acoustic measurements](docs/handoff/evidence/phase10c1-r/acoustic/acceptance-final.json), [CSV](docs/handoff/evidence/phase10c1-r/acoustic/measurements-final.csv), [per-group statistics](docs/handoff/evidence/phase10c1-r/acoustic/group-statistics.json).
- [Current deployment scope](review/deployment-scope.json), [private snapshot hash/count comparison](review/database-static-snapshot-verification.json), [available screenshots and gaps](review/screenshots.json), [playable mathematical controls](review/audio/manifest.json).

This task only packages and checks existing records. It does not rerun business tests or services, deploy, migrate, or authorize a personal-database upgrade. Reported C01/C04 PASS is the implementation record for the reviewer to assess.

Speech/marked speech, personal recordings, writing, private SQL/row snapshots, credentials and private browser screenshots are excluded. Pure mathematical-noise controls may be shared. Raw speech output can be rehashed/recomputed only on the original local workspace; hashes alone cannot reproduce waveforms or private rows off-machine. A/B has source/log checks but no retained dedicated screenshot or video. Historical report references to .local paths, old ZIPs and earlier phases are provenance references, not bundled runtime dependencies.

Verify from this extracted directory: `python3 scripts/phase10c1_handoff.py verify .`
''')


def verify_stage(folder, archive=None):
    folder = folder.resolve()
    subprocess.run([sys.executable, str(folder / 'docs/handoff/evidence/phase10c1-r/verify.py'), str(folder)] + ([str(archive)] if archive else []), check=True)
    for item in json.loads((folder / 'review/source-manifest.json').read_text()):
        assert sha((folder / item['path']).read_bytes()) == item['sharedSha256']
        if item['beforeSnapshot']:
            assert (folder / item['beforeSnapshot']).is_file()
            assert sha((folder / item['beforeSnapshot']).read_bytes()) == item['beforeSharedSha256']
        if item['patch']:
            assert (folder / item['patch']).is_file()
    for entry in json.loads((folder / 'review/reference-index.json').read_text()):
        assert (folder / entry['path']).is_file(), entry
    for run in json.loads((folder / 'review/execution-catalog.json').read_text()):
        text = (folder / run['log']).read_text()
        assert text.startswith('Derived log; original SHA-256: ' + run['originalLogSha256'])
    assert (folder / 'docs/progress/PHASE_10C_1.md').is_file()
    # Required local source imports must resolve without filling the archive with dependency/build trees.
    missing = []
    for path in list((folder / 'apps/web/src').rglob('*.ts*')) + list((folder / 'apps/web/tests').glob('*.ts')):
        for ref in re.findall(r"(?:from\s*|import\s*)['\"]([^'\"]+)['\"]", path.read_text()):
            if not ref.startswith(('.', '@/')):
                continue
            target = folder / 'apps/web/src' / ref[2:] if ref.startswith('@/') else path.parent / ref
            if not any(p.is_file() for p in [target, Path(str(target)+'.ts'), Path(str(target)+'.tsx'), Path(str(target)+'.json'), target/'index.ts', target/'index.tsx']):
                missing.append((path.relative_to(folder).as_posix(), ref))
    assert not missing, missing
    frozen = json.loads((folder / 'docs/handoff/evidence/phase10c1/frozen-migrations.json').read_text())
    assert len(frozen) == 29
    for row in frozen:
        assert sha((folder / row['path']).read_bytes()) == row['sha256']
    assert sum(Path(row['path']).name.startswith('V010') for row in frozen) == 6
    for readme in ['REVIEW_START_HERE.md', 'docs/handoff/PHASE_10C_1_REVIEW.md']:
        for ref in re.findall(r'\]\(([^)]+)\)', (folder / readme).read_text()):
            if re.match(r'^[a-z]+://', ref) or ref.startswith('#'):
                continue
            assert ((folder / readme).parent / ref).is_file(), (readme, ref)
    patterns = {
        'private-key': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'aws-key': rb'(?:AKIA|ASIA)[0-9A-Z]{16}', 'openai-key': rb'sk-(?:proj-)?[A-Za-z0-9_-]{20,}',
        'github-token': rb'gh[pousr]_[A-Za-z0-9]{30,}', 'slack-token': rb'xox[baprs]-[A-Za-z0-9-]{20,}',
        'credential-literal': rb'''(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['"]([A-Za-z0-9_./+=-]{20,})['"]'''}
    hits = []
    for path in folder.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(folder).as_posix()
        assert path.name not in ['.env', 'credentials.json'] and '.git/' not in relative
        assert path.suffix not in ['.mp3', '.webm', '.jpg']
        if path.suffix == '.sql':
            assert 'apps/api/src/main/resources/db/migration/' in relative
        if path.suffix == '.wav':
            assert relative.startswith('review/audio/')
        data = path.read_bytes()
        if str(Path.home()).encode() in data:
            hits.append((relative, 'local-home-path'))
        for label, pattern in patterns.items():
            if re.search(pattern, data):
                hits.append((relative, label))
    assert not hits, hits
    print('PASS: exact source snapshots/diffs, 29 migration hashes (6 new), local TS imports, case/log/report references, privacy whitelist and secret signatures')


def build(refresh=False):
    if STAGE.exists():
        assert refresh, 'Existing staging preserved; use --refresh only for this handoff-owned staging directory'
    STAGE.mkdir(parents=True, exist_ok=refresh)
    previous = dict(sha256=sha(ZIP.read_bytes()), bytes=ZIP.stat().st_size) if ZIP.exists() else None
    import_r4()
    sources = source_snapshot()
    runs, summaries = execution_evidence()
    database_snapshot_summary()
    documents_and_images()
    entrypoints(runs, summaries, sources)
    document('review/previous-artifact.json', dict(previous=previous, policy='Preserve the previous same-name ZIP by its original SHA before atomic replacement'))
    # Nested fixture manifests must also be covered; only the root package manifest excludes itself.
    paths = sorted(p for p in STAGE.rglob('*') if p.is_file() and p != STAGE / 'manifest.json')
    document('manifest.json', dict(files=[dict(path=p.relative_to(STAGE).as_posix(), bytes=p.stat().st_size, sha256=sha(p.read_bytes())) for p in paths]))
    verify_stage(STAGE)
    pending = REVIEW / 'northstar-phase10c1-sanitized-evidence.pending.zip'
    assert not pending.exists(), 'Keep unexpected pending artifacts for inspection'
    with zipfile.ZipFile(pending, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in STAGE.rglob('*') if p.is_file()):
            archive.write(path, path.relative_to(STAGE).as_posix())
    verify_stage(STAGE, pending)
    if previous:
        assert sha(ZIP.read_bytes()) == previous['sha256'], 'Target ZIP changed concurrently'
        backup = REVIEW / ('northstar-phase10c1-sanitized-evidence.pre-handoff-' + previous['sha256'][:12] + '.zip')
        if backup.exists():
            assert sha(backup.read_bytes()) == previous['sha256']
        else:
            shutil.copy2(ZIP, backup)
    pending.replace(ZIP)
    digest = sha(ZIP.read_bytes())
    (REVIEW / 'northstar-phase10c1-sanitized-evidence.zip.sha256').write_text(digest + '  ' + ZIP.name + '\n')
    print(json.dumps(dict(path=str(ZIP.relative_to(ROOT)), files=len(paths), zipMembers=len(paths)+1, bytes=ZIP.stat().st_size, sha256=digest, previousPreserved=previous is not None)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['build', 'verify'])
    parser.add_argument('folder', nargs='?', type=Path, default=STAGE)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    if args.action == 'build':
        build(args.refresh)
    else:
        verify_stage(args.folder)


if __name__ == '__main__':
    main()
