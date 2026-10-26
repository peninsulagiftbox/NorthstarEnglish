#!/usr/bin/env python3
"""Phase09-R acceptance tools. Only two new, identity-checked MySQL instances may be written."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import local

ROOT = local.ROOT
STATE = ROOT / '.local/phase09r-rc1'
EVIDENCE = ROOT / 'docs/handoff/evidence/phase09r'
ROLE = 'phase09r-rc1'
CONTAINERS = {'source': 'northstar-english-phase09r-source', 'restore': 'northstar-english-phase09r-restore'}
PORTS = {'source': (3311, 8086, 3101), 'restore': (3312, 8087, 3102)}
IMAGE = 'mysql:8.4.9@sha256:c36050afdca850f23cef85703f84c7531a5ae155a11b5ee1c60acb09937c4084'
SCHEMA = 'northstar_phase01_test'


def environment(kind='source'):
    env = local.environment()
    ports = PORTS[kind]
    if set(map(str, ports)) & {env[k] for k in ('MYSQL_PORT', 'API_PORT', 'WEB_PORT')}:
        raise RuntimeError('Acceptance ports overlap main services')
    env.update(MYSQL_PORT=str(ports[0]), API_PORT=str(ports[1]), WEB_PORT=str(ports[2]),
               DB_NAME=SCHEMA, NORTHSTAR_DB_TEST='1', NORTHSTAR_PHASE09R='1',
               NORTHSTAR_PHASE09R_KIND=kind,
               NORTHSTAR_BASE_URL='http://127.0.0.1:'+str(ports[2]),
               NORTHSTAR_RECORDING_ROOT=str(STATE/kind/'media'),
               PYTHONDONTWRITEBYTECODE='1')
    for config in sorted((Path.home()/'.npm/_npx').glob('*/node_modules/@playwright/cli/package.json')):
        if json.loads(config.read_text()).get('version')=='0.1.22':
            env['NORTHSTAR_PLAYWRIGHT_CLI_JS']=str(config.parent/'playwright-cli.js')
            break
    # The production build and Maven output live only in an isolated copy.
    return env


def clean(text):
    for key, value in local.read_env(ROOT/'.env').items():
        if 'PASSWORD' in key:
            text = text.replace(value, '<REDACTED>')
    return text.replace(str(ROOT), '<PROJECT_ROOT>').replace(str(Path.home()), '<HOME>')


def recorded(name, argv, env=None, cwd=ROOT, timeout=600):
    """Append-only records; subprocess exit is never inferred from log text."""
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    token = str(time.time_ns())
    started = time.monotonic()
    proc = subprocess.Popen(argv, cwd=cwd, env=env or environment(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    timed_out = False
    try:
        output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.terminate()
        try:
            output, _ = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            output, _ = proc.communicate()
    log = name+'-'+token+'.log'
    (EVIDENCE/log).write_text(clean(output.decode(errors='replace')))
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    row = {'id':name, 'argv':argv, 'cwd':str(cwd), 'startedAt':stamp,
           'exitCode':proc.returncode, 'timedOut':timed_out, 'seconds':round(time.monotonic()-started,3),
           'gitSha':commit, 'log':log}
    with (EVIDENCE/'commands.jsonl').open('a') as f:
        f.write(clean(json.dumps(row, ensure_ascii=False))+'\n')
    print(json.dumps({'id':name,'exitCode':proc.returncode,'timedOut':timed_out,'log':log}), flush=True)
    if proc.returncode or timed_out:
        raise RuntimeError('Command failed; evidence retained: '+name)
    return output


def verify(kind='source'):
    env = environment(kind)
    result = subprocess.run(['docker','inspect',CONTAINERS[kind]], env=env, capture_output=True, text=True, check=True)
    item = json.loads(result.stdout)[0]
    if item['Config'].get('Labels',{}).get('local.northstar.role') != ROLE+'-'+kind:
        raise RuntimeError('Acceptance container identity mismatch')
    if item['Config']['Labels'].get('local.northstar.project') != local.IDENTITY:
        raise RuntimeError('Acceptance project mismatch')
    if item['HostConfig']['PortBindings'].get('3306/tcp') != [{'HostIp':'127.0.0.1','HostPort':env['MYSQL_PORT']}]:
        raise RuntimeError('Acceptance binding mismatch')
    if not any(m.get('Name')==CONTAINERS[kind]+'-data' and m['Destination']=='/var/lib/mysql' for m in item['Mounts']):
        raise RuntimeError('Acceptance volume mismatch')
    return env


def sql(kind, text, schema=None):
    env=verify(kind)
    args=['docker','exec','-i',CONTAINERS[kind],'sh','-c',
          'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot --default-character-set=utf8mb4 -N --batch --raw'+(' '+schema if schema else '')]
    result=subprocess.run(args, input=text, env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Isolated SQL failed (response withheld)')
    return result.stdout


def database(kind):
    env=environment(kind)
    exists=subprocess.run(['docker','inspect',CONTAINERS[kind]],env=env,capture_output=True).returncode==0
    if exists:
        verify(kind)
        recorded(kind+'-db-start',['docker','start',CONTAINERS[kind]],env)
    else:
        # Refuse adopting ANY existing volume, even if labelled: this is a new acceptance run.
        if subprocess.run(['docker','volume','inspect',CONTAINERS[kind]+'-data'],env=env,capture_output=True).returncode==0:
            raise RuntimeError('Existing acceptance volume without container; refusing adoption')
        if not local.available(int(env['MYSQL_PORT'])):
            raise RuntimeError('Acceptance MySQL port occupied')
        recorded(kind+'-volume-create',['docker','volume','create','--label','local.northstar.role='+ROLE+'-'+kind,
                 '--label','local.northstar.project='+local.IDENTITY,CONTAINERS[kind]+'-data'],env)
        recorded(kind+'-db-create',['docker','run','-d','--name',CONTAINERS[kind],
                 '--label','local.northstar.role='+ROLE+'-'+kind,'--label','local.northstar.project='+local.IDENTITY,
                 '-p','127.0.0.1:'+env['MYSQL_PORT']+':3306',
                 '-e','MYSQL_ROOT_PASSWORD','-e','DB_PASSWORD','-e','DB_MIGRATION_PASSWORD',
                 '-v',CONTAINERS[kind]+'-data:/var/lib/mysql',
                 '-v',str(ROOT/'infra/mysql-init.sh')+':/docker-entrypoint-initdb.d/01-northstar.sh:ro',
                 IMAGE,'--character-set-server=utf8mb4','--collation-server=utf8mb4_0900_ai_ci','--default-time-zone=+00:00'],env)
    for _ in range(90):
        try:
            if sql(kind,'SELECT project_key FROM project_identity;',SCHEMA).strip()==local.IDENTITY:
                print('Dedicated MySQL identity ready: '+kind)
                return
        except (RuntimeError,subprocess.CalledProcessError):
            pass
        time.sleep(1)
    raise RuntimeError('Dedicated MySQL readiness timeout')


def workspace(kind):
    target=STATE/kind/'workspace'
    target.mkdir(parents=True,exist_ok=True)
    for folder in ('apps/web','apps/api'):
        shutil.copytree(ROOT/folder,target/folder,dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('node_modules','.next','target','*.tsbuildinfo'))
    for name in ('package.json','package-lock.json'):
        shutil.copy2(ROOT/name,target/name)
    link=target/'node_modules'
    if not link.exists(): link.symlink_to(ROOT/'node_modules',target_is_directory=True)
    return target


def grant(kind, schema=SCHEMA):
    if schema!=SCHEMA and not __import__('re').fullmatch(r'northstar_restore_[0-9]{14}',schema):
        raise RuntimeError('Invalid isolated grant schema')
    if sql(kind,'SELECT project_key FROM project_identity;',schema).strip()!=local.IDENTITY:
        raise RuntimeError('Schema identity mismatch')
    statements=[]
    for table in ('study_resume','user_setting','command_receipt','study_stage','exercise_draft','review_item','vocabulary_favorite','reading_progress','writing_draft','personal_recording','practice_progress','quiz_progress'):
        statements.append(f"GRANT INSERT,UPDATE ON `{schema}`.`{table}` TO 'northstar_app'@'%';")
    for table in ('exercise_attempt','learning_evidence','study_event','review_source','reading_answer','writing_revision','recording_observation','quiz_run','quiz_answer','review_result'):
        statements.append(f"GRANT INSERT ON `{schema}`.`{table}` TO 'northstar_app'@'%';")
    sql(kind,'\n'.join(statements))
    print('Granted only isolated runtime table writes')


def runtime(kind, action, schema):
    env=verify(kind)
    if schema!=SCHEMA:
        if not __import__('re').fullmatch(r'northstar_restore_[0-9]{14}',schema): raise RuntimeError('Invalid schema')
        env.update(DB_NAME=schema,NORTHSTAR_ALLOW_RESTORE_DB='true')
    media=STATE/kind/'media'
    media.mkdir(parents=True,exist_ok=True)
    local.LOCAL=STATE/kind
    spec=importlib.util.spec_from_file_location('runtime09',ROOT/'scripts/regression-runtime.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if action=='stop':
        module.stop('phase09r-web');module.stop('phase09r-api');return
    if action=='restart': module.stop('phase09r-api')
    target=STATE/kind/'workspace'
    jar=target/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    for service,key in (('api','API_PORT'),('web','WEB_PORT')):
        path=local.LOCAL/('phase09r-'+service+'.json')
        owned=path.exists() and local.owns_process(json.loads(path.read_text()))
        if not owned and not local.available(int(env[key])): raise RuntimeError('Port owned by another process')
    local.start_process('phase09r-api',[shutil.which('java',path=env['PATH']),'-jar',str(jar),
        '--northstar.content-root='+str(ROOT/'content'),'--northstar.recording-root='+str(media)],target/'apps/api',env,str(jar))
    local.wait_health('http://127.0.0.1:'+env['API_PORT']+'/api/v1/health')
    local.start_process('phase09r-web',[shutil.which('node',path=env['PATH']),str(ROOT/'node_modules/next/dist/bin/next'),
        'start','--hostname','127.0.0.1','--port',env['WEB_PORT']],target/'apps/web',env,'next')
    local.wait_health(env['NORTHSTAR_BASE_URL']+'/api/v1/health')


def candidate():
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0')
    files={p.decode():hashlib.sha256((ROOT/p.decode()).read_bytes()).hexdigest() for p in paths if p and (ROOT/p.decode()).is_file()
           and not p.decode().startswith(('docs/handoff/evidence/phase09r/','docs/evidence/'))}
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    document={'candidate':'phase-09r-rc1','gitSha':sha,'files':files,
              'categories':{category:[p for p in files if predicate(p)] for category,predicate in (
                  ('dependencyLocks',lambda p:p.endswith(('package-lock.json','pom.xml','maven-wrapper.properties'))),
                  ('migrations',lambda p:'/db/migration/' in p),
                  ('content',lambda p:p.startswith('content/')),
                  ('testScripts',lambda p:p.startswith('scripts/'))) }}
    with (EVIDENCE/'candidate.json').open('x') as f: json.dump(document,f,ensure_ascii=False,indent=2)
    print(sha)


def migration_probe(kind, real=False):
    env=local.environment() if real else verify(kind)
    if real:
        local.verify_container(env)
        env['DB_NAME']='northstar_english'
    import zipfile
    libs=STATE/'probe-libs'
    libs.mkdir(exist_ok=True)
    jar=STATE/'source/workspace/apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    with zipfile.ZipFile(jar) as archive:
        for name in archive.namelist():
            if name.startswith('BOOT-INF/lib/') and name.endswith('.jar'):
                (libs/Path(name).name).write_bytes(archive.read(name))
    recorded('real-metadata-readonly' if real else kind+'-migration-validate',
             ['java','-cp',str(libs/'*'),str(ROOT/'scripts/phase09r/MigrationProbe.java'),
              str(ROOT/'apps/api/src/main/resources/db/migration')],env)


def counts(kind, schema):
    env=verify(kind)
    with urllib.request.urlopen('http://127.0.0.1:'+env['API_PORT']+'/api/v1/reports') as response:
        report=json.load(response)
    queries={('dictation','submitted'):"SELECT COUNT(*) FROM exercise_attempt a JOIN exercise e ON e.id=a.exercise_id WHERE e.kind='dictation'",
             ('reading','submitted'):'SELECT COUNT(*) FROM reading_answer',
             ('writing','versions'):'SELECT COUNT(*) FROM writing_revision',
             ('quiz','runs'):'SELECT COUNT(*) FROM quiz_run',
             ('quiz','correct'):'SELECT COALESCE(SUM(correct_count),0) FROM quiz_run',
             ('recordings','available'):"SELECT COUNT(*) FROM personal_recording WHERE status='ready'",
             ('selfRatings','submitted'):'SELECT COUNT(*) FROM review_result'}
    for (group,key),query in queries.items():
        actual=int(sql(kind,query,schema).strip())
        assert report['metrics'][group][key]==actual,(group,key)
        print(group+'.'+key+'='+str(actual)+' matches SQL')
    assert int(sql(kind,"SELECT COUNT(*) FROM practice_progress WHERE kind='speaking' AND current_state='skipped'",schema))>0,'Skip projection exists'
    print('PASS: report counts equal real isolated records; skipped speaking remains separate')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['db','workspace','grant','start','stop','restart','candidate','exec','verify','db-stop','metadata','real-metadata','migrate','counts'])
    parser.add_argument('--kind',choices=CONTAINERS,default='source')
    parser.add_argument('--schema',default=SCHEMA)
    parser.add_argument('--name',default='command')
    parser.add_argument('--cwd',type=Path,default=ROOT)
    raw=sys.argv[1:]
    divider=raw.index('--') if '--' in raw else len(raw)
    args=parser.parse_args(raw[:divider])
    command=raw[divider+1:]
    if args.action=='db': database(args.kind)
    elif args.action=='workspace': print(workspace(args.kind))
    elif args.action=='grant': grant(args.kind,args.schema)
    elif args.action in ('start','stop','restart'): runtime(args.kind,args.action,args.schema)
    elif args.action=='candidate': candidate()
    elif args.action in ('metadata','real-metadata'): migration_probe(args.kind,args.action=='real-metadata')
    elif args.action=='counts': counts(args.kind,args.schema)
    elif args.action=='migrate':
        env=verify(args.kind)
        recorded(args.kind+'-migrate',['java','-jar',str(STATE/args.kind/'workspace/apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'),
            '--spring.main.web-application-type=none','--northstar.content-root='+str(ROOT/'content'),
            '--northstar.recording-root='+str(STATE/args.kind/'media')],env)
    elif args.action=='verify': verify(args.kind);print('Verified acceptance identity')
    elif args.action=='db-stop':
        verify(args.kind);recorded(args.kind+'-db-stop',['docker','stop',CONTAINERS[args.kind]],environment(args.kind))
    else:
        argv=command
        if not argv: parser.error('exec requires command after --')
        recorded(args.name,argv,environment(args.kind),args.cwd.resolve())


if __name__=='__main__':
    main()
