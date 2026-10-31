#!/usr/bin/env python3
"""Phase10C2 resources only; reuse the established container/UUID/backup guards."""
import json,os,sys,time,shutil,subprocess,urllib.request
from pathlib import Path
import phase10c2 as setup
import phase10c1_isolated as base
r=setup.runner
base.r=r
r.STATE=r.ROOT/'.local/phase10c2'
r.COPY=r.STATE/'source'
r.OUT=r.ROOT/'docs/handoff/evidence/phase10c2'

def campaign():
    c=base.campaign()
    c.NAMESPACE='northstar-phase10c2-20261031a'
    c.ROLES=['reserved'+str(i) for i in range(20)]+['upgrade','empty','fault-ddl','fault-dml','fault-history','recovery']
    return c

def env(c,role,schema='northstar_english'):
    e=base.env(c,role,schema)
    e.update(API_PORT='8175',WEB_PORT='3195',NORTHSTAR_C2_TEST='1')
    return e

def grant(c,role,schema='northstar_english'):
    if schema=='northstar_english':base.grant(c,role)
    c.sql(role,"GRANT SELECT ON "+schema+".* TO 'northstar_app'@'%'; GRANT INSERT ON "+schema+".quiz_run_item TO 'northstar_app'@'%';")

def snap(c,role,tag):
    path=c.PRIVATE/role/(tag+'.json')
    if path.exists():return json.loads(path.read_text())
    summary=c.OUT/(role+'-'+tag+'-summary.json')
    if summary.exists():summary.unlink()
    return c.snapshot(role,tag)

def ensure_db(c,role):
    d=c.verify(role)
    running=c.call(role+'-running',[c.DOCKER,'inspect','-f','{{.State.Running}}',d['containerId']]).stdout.decode().strip()=='true'
    if not running:c.call('start-owned-'+role,[c.DOCKER,'start',d['containerId']])
    for _ in range(60):
        try:
            c.sql(role,'SELECT 1',readonly=True);return
        except BaseException:time.sleep(.5)
    raise RuntimeError(role+' database not ready')

def migrate(c,role,target=None,initialize=False,fault=False,expected=(0,)):
    c.sql(role,"SET GLOBAL log_bin_trust_function_creators=1; GRANT TRIGGER ON northstar_english.* TO 'northstar_migrator'@'%'; GRANT TRIGGER ON northstar_english.* TO 'northstar_fault_migrator'@'%';")
    return base.migrate(c,role,target,initialize,fault,expected)

def start(c,role,initialize=False,schema='northstar_english',content=None):
    e=env(c,role,schema)
    if content:e['NORTHSTAR_CONTENT_ROOT']=str(content)
    port=int(e['API_PORT']);assert c.available(port)
    args=[str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--server.port='+str(port),'--northstar.content-root='+e['NORTHSTAR_CONTENT_ROOT'],'--northstar.recording-root='+e['NORTHSTAR_RECORDING_ROOT']]
    if initialize:args.append('--northstar.initialize-content=true')
    stream=(c.PRIVATE/role/('api-'+str(time.time_ns())+'.log')).open('xb')
    p=subprocess.Popen(args,cwd=r.COPY/'apps/api',env=e,stdout=stream,stderr=subprocess.STDOUT);handle=(p,stream,port,int(e['WEB_PORT']))
    try:
        for _ in range(150):
            if p.poll() is not None:raise RuntimeError('Isolated API exited; private log retained')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/health',timeout=1) as response:health=json.load(response)
                if health['migrationVersion']=='011.09':
                    if not initialize:
                        return handle
                    for _ in range(150):
                        if p.poll() is not None:raise RuntimeError('Isolated API exited before content initialization completed')
                        try:
                            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/lessons/demo-01',timeout=1) as response:
                                if response.status==200:return handle
                        except OSError:pass
                        time.sleep(.3)
                    raise RuntimeError('Content initialization readiness timeout')
            except OSError:pass
            time.sleep(.3)
        raise RuntimeError('Readiness timeout')
    except BaseException:c.end_api(role,handle);raise

def main():
    action=sys.argv[1];c=campaign()
    if action=='migrations':
        for role in ('upgrade','empty'):
            ensure_db(c,role)
            if not (c.PRIVATE/role/'state.json').exists():
                c.create(role)
            else:
                c.verify(role)
            if not (c.PRIVATE/role/'content').exists():
                c.prepare_files(role)
            if role=='upgrade':
                history=c.sql(role,'SELECT version FROM flyway_schema_history WHERE success=1 ORDER BY installed_rank',readonly=True).stdout.decode()
                if '010.06' not in history:
                    c.restore(role);before=snap(c,role,'fixed-backup');migrate(c,role,'010.06');baseline=snap(c,role,'v01006');base.compare_old(before,baseline)
                else:
                    before=json.loads((c.PRIVATE/role/'fixed-backup.json').read_text());baseline=snap(c,role,'v01006');base.compare_old(before,baseline)
            else:before=baseline=None
            if '011.09' not in history:migrate(c,role,initialize=role=='empty')
            grant(c,role)
            if baseline:
                after=snap(c,role,'v01109')
                base.compare_old(baseline,after)
            needs_initialize=role=='empty' and c.sql(role,'SELECT COUNT(*) FROM lesson_version',readonly=True).stdout.decode().strip()=='0'
            h=start(c,role,needs_initialize);c.end_api(role,h);first=snap(c,role,'first-start')
            h=start(c,role);c.end_api(role,h);assert first==snap(c,role,'second-start')
            c.save(c.OUT/(role+'-acceptance.json'),dict(status='PASS',oldCellsExact=True,restartsExact=True,targetVersion='011.09'),exclusive=False)
            c.stop(role)
    elif action=='start-db':
        role=sys.argv[2];d=c.verify(role);c.call('start-owned-'+role,[c.DOCKER,'start',d['containerId']]);print(role)
    elif action=='prepare-tests':
        role='empty';ensure_db(c,role)
        test_content=r.STATE/'database'/'test-content'
        if test_content.exists():shutil.rmtree(test_content)
        shutil.copytree(r.ROOT/'.local'/'phase10c1'/'database'/'fault-history'/'content',test_content)
        test_env=env(c,role,'northstar_phase01_test');test_env['NORTHSTAR_CONTENT_ROOT']=str(test_content)
        c.sql(role,'SET GLOBAL log_bin_trust_function_creators=1; DROP DATABASE IF EXISTS northstar_phase01_test')
        c.sql(role,"CREATE DATABASE IF NOT EXISTS northstar_phase01_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; CREATE TABLE IF NOT EXISTS northstar_phase01_test.project_identity (project_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)));")
        c.sql(role,"INSERT INTO northstar_phase01_test.project_identity(project_key) SELECT 'northstar-english-local-v1' WHERE NOT EXISTS(SELECT 1 FROM northstar_phase01_test.project_identity)")
        c.sql(role,"GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON northstar_phase01_test.* TO 'northstar_migrator'@'%'; GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON northstar_phase01_test.* TO 'northstar_app'@'%';")
        c.call('test-schema-init',[str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--spring.main.web-application-type=none','--northstar.initialize-content=true'],env=test_env,private=True,timeout=600)
        c.sql(role,"REVOKE ALL PRIVILEGES ON northstar_phase01_test.* FROM 'northstar_app'@'%';")
        for line in json.loads((base.BASE/'recovery-20261027/a1/grants.json').read_text())['app'].splitlines():
            if 'northstar_phase01_test' in line:c.sql(role,line+';')
        c.sql(role,"GRANT SELECT ON northstar_phase01_test.* TO 'northstar_app'@'%'; GRANT SELECT ON northstar_phase01_test.lesson_audio TO 'northstar_app'@'%'; GRANT SELECT ON northstar_phase01_test.audio_alignment TO 'northstar_app'@'%'; GRANT INSERT ON northstar_phase01_test.quiz_run_item TO 'northstar_app'@'%';")
        h=start(c,role,schema='northstar_phase01_test',content=test_content);c.end_api(role,h)
        print('test schema ready')
    elif action=='run-tests':
        e=env(c,'empty','northstar_phase01_test');e['NORTHSTAR_DB_TEST']='1'
        e['NORTHSTAR_CONTENT_ROOT']=str(r.STATE/'database'/'test-content')
        r.record(sys.argv[2],sys.argv[3:],env=e,cwd=r.COPY)
    elif action=='web-build':
        e=env(c,'empty','northstar_phase01_test')
        r.record('web-build-c2',['sh','-c','cd apps/web && npm run build'],env={**r.environment(),'API_PORT':e['API_PORT']},cwd=r.COPY)
    elif action=='probe':
        role=sys.argv[2]
        print(c.sql(role,'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()',readonly=True).stdout.decode())
        print(c.sql(role,'SELECT version,success FROM flyway_schema_history ORDER BY installed_rank',readonly=True).stdout.decode())
    elif action=='serve':
        role='empty';ensure_db(c,role)
        test_content=r.STATE/'database'/'test-content'
        e=env(c,role,'northstar_phase01_test');e['NORTHSTAR_CONTENT_ROOT']=str(test_content)
        recordings=e['NORTHSTAR_RECORDING_ROOT']
        api=subprocess.Popen([str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--server.port='+e['API_PORT'],'--northstar.content-root='+str(test_content),'--northstar.recording-root='+str(recordings)],cwd=r.COPY/'apps/api',env=e,stdout=(r.STATE/'database'/'serve-api.log').open('wb'),stderr=subprocess.STDOUT,start_new_session=True)
        web=subprocess.Popen([str(r.COPY/'node_modules/.bin/next'),'start','-p',e['WEB_PORT']],cwd=r.COPY/'apps/web',env={**e,'API_PORT':e['API_PORT']},stdout=(r.STATE/'database'/'serve-web.log').open('wb'),stderr=subprocess.STDOUT,start_new_session=True)
        try:
            for _ in range(150):
                if api.poll() is not None:raise RuntimeError('serve API exited; see serve-api.log')
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{e['API_PORT']}/api/v1/health",timeout=1) as response:
                        health=json.load(response)
                        if health['migrationVersion']=='011.09' and response.headers.get('X-Northstar-Test-Database')=='true':break
                except OSError:pass
                time.sleep(.3)
            else:raise RuntimeError('serve API readiness timeout')
            for _ in range(100):
                if web.poll() is not None:raise RuntimeError('serve web exited; see serve-web.log')
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{e['WEB_PORT']}/api/v1/health",timeout=1) as response:
                        if response.status==200:break
                except OSError:pass
                time.sleep(.3)
            else:raise RuntimeError('serve web readiness timeout')
            (r.STATE/'database'/'serve-pids.json').write_text(json.dumps(dict(api=api.pid,web=web.pid,apiPort=int(e['API_PORT']),webPort=int(e['WEB_PORT']))))
            print(json.dumps(dict(api=api.pid,web=web.pid,apiPort=int(e['API_PORT']),webPort=int(e['WEB_PORT']))))
        except BaseException:
            for p in (api,web):
                if p.poll() is None:p.kill()
            raise
    elif action=='stop-serve':
        import signal
        for file in ('serve-pids.json','serve-restored-pids.json'):
            path=r.STATE/'database'/file
            if not path.exists():continue
            state=json.loads(path.read_text())
            for name,pid in (state.items() if isinstance(state,dict) else []):
                if not isinstance(pid,int):continue
                command=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout.strip()
                if 'northstar-api' in command or 'next-server' in command or 'next start' in command:
                    os.kill(pid,signal.SIGTERM);print('stopped',name,pid)
                else:print('skip',name,pid,command[:80])
    elif action=='serve-restored':
        import re
        target=sys.argv[2]
        if not re.fullmatch(r'northstar_restore_[0-9]{14}',target):raise SystemExit('invalid restore schema')
        role='empty';ensure_db(c,role)
        e=env(c,role,target);e['NORTHSTAR_CONTENT_ROOT']=str(r.STATE/'database'/'test-content')
        e['NORTHSTAR_ALLOW_RESTORE_DB']='true'
        port='8176';assert c.available(int(port))
        api=subprocess.Popen([str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--server.port='+port,'--northstar.content-root='+e['NORTHSTAR_CONTENT_ROOT'],'--northstar.recording-root='+e['NORTHSTAR_RECORDING_ROOT']],cwd=r.COPY/'apps/api',env={**e,'API_PORT':port},stdout=(r.STATE/'database'/'serve-restored-api.log').open('wb'),stderr=subprocess.STDOUT,start_new_session=True)
        try:
            for _ in range(150):
                if api.poll() is not None:raise RuntimeError('restored API exited; see serve-restored-api.log')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/health',timeout=1) as response:
                        if response.status==200:break
                except OSError:pass
                time.sleep(.3)
            else:raise RuntimeError('restored API readiness timeout')
            (r.STATE/'database'/'serve-restored-pids.json').write_text(json.dumps(dict(api=api.pid,apiPort=int(port))))
            print(json.dumps(dict(api=api.pid,apiPort=int(port))))
        except BaseException:
            if api.poll() is None:api.kill()
            raise
    else:raise SystemExit('migrations | start-db | prepare-tests | run-tests | serve | stop-serve | probe ROLE')
if __name__=='__main__':main()
