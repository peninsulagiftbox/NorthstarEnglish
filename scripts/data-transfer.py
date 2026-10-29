#!/usr/bin/env python3
"""Private logical backups and create-only isolated restores. Never overwrite a schema."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import urllib.parse
import local


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_snapshot(path):
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('JSON 超过 32 MiB')
    envelope = json.loads(path.read_text())
    if set(envelope) != {'format', 'sha256', 'payloadJson'} or envelope['format'] != 'northstar.snapshot.v1':
        raise ValueError('不支持的数据格式')
    if digest(envelope['payloadJson'].encode()) != envelope['sha256']:
        raise ValueError('校验和不匹配')
    payload = json.loads(envelope['payloadJson'])
    if payload['project'] != local.IDENTITY or payload['owner'] != 'local' or payload['schemaVersion'] not in {'008', '009.04', '009.05', '009.14', '009.15'}:
        raise ValueError('版本或归属不匹配')
    return envelope, payload


def literal(value):
    if value is None:
        return 'NULL'
    if not isinstance(value, str):
        raise ValueError('只接受快照字符串或空值')
    return "CONVERT(X'" + value.encode().hex() + "' USING utf8mb4)"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup', 'restore'])
    parser.add_argument('path', type=Path, help='backup: new folder; restore: learning.json')
    parser.add_argument('--web-port', type=int, help='paired Web origin port for read-only import preview')
    parser.add_argument('--api', default='http://127.0.0.1:8085')
    parser.add_argument('--recording-root', type=Path, default=Path.home() / 'Library/Application Support/NorthstarEnglish/recordings', help='private media parent, same as API recording-root')
    parser.add_argument('--target', help='new schema: northstar_restore_YYYYMMDDhhmmss')
    parser.add_argument('--confirm-new-isolated', action='store_true')
    parser.add_argument('--separate-mysql', action='store_true', help='restore only: verified dedicated recovery MySQL instance')
    parser.add_argument('--phase09r', action='store_true', help='use ONLY identity-checked Phase09-R source and restore containers')
    parser.add_argument('--phase10b3', action='store_true', help='use ONLY the UUID-checked Phase10B3 isolated test source; never the personal container')
    args = parser.parse_args()
    if args.phase10b3 and (args.phase09r or args.separate_mysql):
        raise ValueError('Phase10B3隔离模式不能和其他目标模式组合')
    if args.action == 'backup' and args.separate_mysql:
        raise ValueError('--separate-mysql 仅用于恢复目标，不更改备份来源')
    url = urllib.parse.urlparse(args.api)
    if url.scheme != 'http' or url.hostname not in ('localhost', '127.0.0.1') or url.path not in ('', '/') or url.username or url.query or url.fragment:
        raise ValueError('仅支持本地回环 API')
    env = local.environment()
    source_container = 'northstar-english-mysql-01'
    if args.phase10b3:
        import phase10b3_isolated as isolated
        campaign = isolated.campaign()
        role = (isolated.r.STATE / 'ACTIVE_TEST_ROLE').read_text().strip()
        state = campaign.verify(role)
        env = isolated.env(campaign, role, 'northstar_phase01_test')
        if args.api != 'http://127.0.0.1:' + env['API_PORT'] or not args.recording_root.resolve().is_relative_to(campaign.PRIVATE / role / 'recordings'):
            raise ValueError('Phase10B3 API和媒体目录必须属于已核验的隔离目标')
        campaign.sql(role, 'SELECT project_key FROM project_identity', readonly=True)
        source_container = state['containerId']
    elif args.phase09r:
        import phase09r
        env = phase09r.verify('source')
        if args.api != env['NORTHSTAR_BASE_URL'].replace(':'+env['WEB_PORT'], ':'+env['API_PORT']):
            raise ValueError('Phase09-R requires its exact isolated source API')
        source_container = phase09r.CONTAINERS['source']
        if args.separate_mysql:
            raise ValueError('Phase09-R selects its own dedicated target; do not combine modes')
        if not args.recording_root.resolve().is_relative_to(phase09r.STATE):
            raise ValueError('Phase09-R media must remain under its private test directory')
    else:
        local.verify_container(env)
    def api(path, body=None):
        request = urllib.request.Request(args.api.rstrip('/') + '/api/v1' + path, data=None if body is None else json.dumps(body).encode(), headers={'Origin': 'http://127.0.0.1:' + str(args.web_port or env['WEB_PORT']), 'X-Northstar-Request': 'local-workspace', 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    def sql(query, schema=None, container=None):
        container = container or source_container
        command = ['docker', 'exec', '-i', container, 'sh', '-c', 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot --default-character-set=utf8mb4 -N --batch --raw' + (' ' + schema if schema else '')]
        result = subprocess.run(command, input=query, text=True, capture_output=True, env=env)
        if result.returncode:
            raise RuntimeError('隔离数据库操作失败；没有覆盖现库，失败目标保留供排查。未输出私人数据。')
        return result.stdout
    def write(path, data):
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as f:
            f.write(data)
    if args.action == 'backup':
        args.path.mkdir(mode=0o700, parents=True, exist_ok=False)
        envelope = api('/data/export')
        write(args.path / 'learning.json', json.dumps(envelope, ensure_ascii=False).encode())
        _, payload = load_snapshot(args.path / 'learning.json')
        media = args.path / 'media'
        media.mkdir(mode=0o700)
        table = payload['tables']['personal_recording']
        manifest = []
        for values in table['rows']:
            row = dict(zip(table['columns'], values))
            item = {key: row[key] for key in ('id', 'lesson_id', 'version_id', 'sentence_id', 'sha256', 'byte_size', 'status')}
            item['included'] = False
            if row['status'] == 'ready':
                if not re.fullmatch(r'[0-9a-f-]{36}', row['id']):
                    raise ValueError('无效录音 ID')
                with urllib.request.urlopen(args.api + '/api/v1/recordings/' + row['id'] + '/audio', timeout=60) as response:
                    data = response.read(8388609)
                if digest(data) != row['sha256'] or len(data) != int(row['byte_size']):
                    raise ValueError('录音与事务快照不一致，请重新备份到新目录')
                write(media / (row['id'] + '.audio'), data)
                item['included'] = True
            manifest.append(item)
        write(args.path / 'media-manifest.json', json.dumps({'snapshotSha256': envelope['sha256'], 'recordings': manifest}, ensure_ascii=False).encode())
        write(args.path / 'COMPLETE', envelope['sha256'].encode())
        print('PASS: JSON + 媒体清单 + 可用录音已校验；不含浏览器未同步缓冲。目录：' + str(args.path))
        return
    envelope, payload = load_snapshot(args.path)
    destination = source_container if args.phase10b3 else 'northstar-english-mysql-01'
    if args.phase09r:
        phase09r.verify('restore')
        destination = phase09r.CONTAINERS['restore']
    if args.separate_mysql:
        import recovery_mysql
        recovery_mysql.verify(env)
        destination = recovery_mysql.CONTAINER
    def target_sql(query, schema=None):
        return sql(query, schema, destination)
    preview = api('/data/import-preview', envelope)
    if not preview['valid'] or preview['sha256'] != envelope['sha256']:
        raise ValueError('服务器预检失败')
    if not args.target or not re.fullmatch(r'northstar_restore_[0-9]{14}', args.target) or not args.confirm_new_isolated:
        raise ValueError('已预检；恢复需 --target northstar_restore_YYYYMMDDhhmmss --confirm-new-isolated。只创建新库，不覆盖。')
    media_target = args.recording_root / args.target
    if media_target.exists() or media_target.is_symlink():
        raise ValueError('目标媒体目录已存在，拒绝覆盖')
    # Refuse an existing target, including a previous restore, before creating files or SQL.
    if target_sql('SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name=' + literal(args.target)).strip() != '0':
        raise ValueError('目标已存在，拒绝覆盖或重复合并；请使用新目标。')
    health_request = urllib.request.Request(args.api + '/api/v1/health')
    with urllib.request.urlopen(health_request, timeout=8) as response:
        source = 'northstar_phase01_test' if response.headers.get('X-Northstar-Test-Database') == 'true' else 'northstar_english'
    if sql('SELECT project_key FROM project_identity', source).strip() != local.IDENTITY:
        raise ValueError('源库身份不匹配')
    # Preflight media before any writes; JSON-only restores must explicitly remain unavailable.
    recordings = payload['tables']['personal_recording']
    copies = []
    for values in recordings['rows']:
        row = dict(zip(recordings['columns'], values))
        if row['status'] == 'ready':
            if not re.fullmatch(r'[0-9a-f-]{36}', row['id']):
                raise ValueError('无效录音 ID')
            path = args.path.parent / 'media' / (row['id'] + '.audio')
            if path.is_symlink() or not path.is_file() or path.stat().st_size != int(row['byte_size']) or digest(path.read_bytes()) != row['sha256']:
                raise ValueError('可用录音缺失或校验失败；请使用完整备份目录恢复。未创建目标。')
            copies.append(path)
    dump = subprocess.run(['docker', 'exec', source_container, 'sh', '-c', 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --no-data --skip-add-drop-table --no-tablespaces --set-gtid-purged=OFF ' + source], capture_output=True, env=env)
    if dump.returncode:
        raise RuntimeError('无法读取当前版本表结构')
    # Get dependencies from verified source metadata; never execute SQL supplied by a JSON file.
    dependencies = {}
    for line in sql("SELECT table_name,referenced_table_name FROM information_schema.key_column_usage WHERE table_schema='" + source + "' AND referenced_table_name IS NOT NULL").splitlines():
        table, parent = line.split('\t')
        if table != parent and not (table == 'lesson' and parent == 'lesson_version'):
            dependencies.setdefault(table, set()).add(parent)
    pending = set(payload['tables'])
    order = []
    while pending:
        ready = sorted(t for t in pending if not (dependencies.get(t, set()) & pending))
        if not ready:
            raise ValueError('无法安全排序外键依赖')
        order.extend(ready)
        pending.difference_update(ready)
    for table, data in payload['tables'].items():
        if not re.fullmatch(r'[a-z_]+', table) or not all(re.fullmatch(r'[a-z][a-z0-9_]*', c) for c in data['columns']):
            raise ValueError('无效表结构')
    target = args.target
    # CREATE DATABASE deliberately has no IF NOT EXISTS, so a race cannot reuse another schema.
    target_sql('CREATE DATABASE `' + target + '` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;')
    target_sql(dump.stdout.decode(), target)
    commands = ['SET NAMES utf8mb4;', 'SET FOREIGN_KEY_CHECKS=1;', 'START TRANSACTION;']
    lesson_links = []
    for table in order:
        data = payload['tables'][table]
        if not re.fullmatch(r'[a-z_]+', table) or not all(re.fullmatch(r'[a-z][a-z0-9_]*', c) for c in data['columns']):
            raise ValueError('无效表结构')
        generated = {'target_uniqueness_key'} if table == 'version_sentence_map' else set()
        restored_columns = [c for c in data['columns'] if c not in generated]
        rows = data['rows']
        if table == 'writing_revision':
            rows = sorted(rows, key=lambda r: (r[data['columns'].index('task_id')], int(r[data['columns'].index('version_no')])))
        for original in rows:
            values = list(original)
            if table == 'lesson':
                index = data['columns'].index('current_version_id')
                lesson_links.append((values[data['columns'].index('id')], values[index]))
                values[index] = None
            commands.append('INSERT INTO `' + table + '` (' + ','.join('`' + c + '`' for c in restored_columns) + ') VALUES (' + ','.join(literal(v) for c, v in zip(data['columns'], values) if c not in generated) + ');')
    for lesson, version in lesson_links:
        commands.append('UPDATE lesson SET current_version_id=' + literal(version) + ' WHERE id=' + literal(lesson) + ';')
    commands.append('COMMIT;')
    target_sql('\n'.join(commands), target)
    counts_sql = ' UNION ALL '.join("SELECT '" + table + "',COUNT(*) FROM `" + table + "`" for table in payload['tables'])
    counts = dict(line.split('\t') for line in target_sql(counts_sql, target).splitlines())
    for table, data in payload['tables'].items():
        if int(counts[table]) != len(data['rows']):
            raise ValueError('恢复行数核对失败；保留隔离目标')
    root = args.recording_root / target
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    for path in copies:
        write(root / path.name, path.read_bytes())
    grants = [f"GRANT SELECT ON `{target}`.* TO 'northstar_app'@'%'; GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON `{target}`.* TO 'northstar_migrator'@'%';"]
    # Keep immutable history read-only. Runtime writes use the same table policy as the main instance.
    for table in ('study_resume','user_setting','command_receipt','study_stage','exercise_draft','review_item','vocabulary_favorite','reading_progress','writing_draft','personal_recording','practice_progress','quiz_progress'):
        grants.append(f"GRANT INSERT,UPDATE ON `{target}`.`{table}` TO 'northstar_app'@'%';")
    for table in ('exercise_attempt','learning_evidence','study_event','review_source','reading_answer','writing_revision','recording_observation','quiz_run','quiz_answer','review_result'):
        grants.append(f"GRANT INSERT ON `{target}`.`{table}` TO 'northstar_app'@'%';")
    target_sql('\n'.join(grants))
    print('PASS: 逐表行数与媒体哈希通过，恢复到全新隔离库 ' + target + '；没有修改当前库。')
    print('启动此恢复副本需项目级 DB_NAME=' + target + ' NORTHSTAR_ALLOW_RESTORE_DB=true，并选择空闲 API/Web 端口；不要改主 .env。')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not echo DB driver responses, raw texts or connection credentials.
        print('FAIL: ' + (str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__), file=sys.stderr)
        sys.exit(1)
