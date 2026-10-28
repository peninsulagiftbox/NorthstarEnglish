#!/usr/bin/env python3
"""Approved Phase10B2 isolated migration/initialization runner. Personal source is never addressed."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import phase10b2 as run

ROOT=run.ROOT
BASE=ROOT/'docs/handoff/evidence/phase10b1'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def campaign():
    c=load('phase10b1_isolated_library',BASE/'isolated_rehearsal.py')
    c.PRIVATE=run.STATE/'database-20261028b';c.PRIVATE.mkdir(parents=True,exist_ok=True)
    c.OUT=run.OUT/'migration-execution-20261028b';c.OUT.mkdir(exist_ok=True)
    c.NAMESPACE='northstar-phase10b2-20261028b'
    c.ROLES=['reserved'+str(i) for i in range(37)]+['upgrade','empty','fault','recovery']
    c.PATCHED_JAR=run.COPY/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    original_call=c.call
    invocation=str(time.time_ns())
    def unique_call(name,*args,**kwargs):return original_call(invocation+'-'+name,*args,**kwargs)
    c.call=unique_call
    return c


def migrate(c,role,target=None,initialize=False,expected=(0,)):
    d=c.verify(role);cred=json.loads((c.PRIVATE/role/'credentials.json').read_text())
    env=run.environment()
    env.update(TARGET_MYSQL_PORT=str(d['port']),EXPECTED_TARGET_UUID=d['uuid'],TARGET_PASSWORD=cred['migrator'],TARGET_USER='northstar_migrator')
    env.pop('MIGRATION_TARGET',None)
    if target:env['MIGRATION_TARGET']=target
    if initialize:env['INITIALIZE_EMPTY_IDENTITY']='true'
    return c.call(role+'-flyway-'+str(target),[str(c.JAVA),'-cp',str(c.CLASSES)+os.pathsep+str(c.LIB/'*'),'MigrationHarness',str(ROOT/'apps/api/src/main/resources/db/migration')],env=env,private=True,expected=expected,timeout=120)


def start(c,role,initialize=False,schema='northstar_english'):
    d=c.verify(role);cred=json.loads((c.PRIVATE/role/'credentials.json').read_text())
    api=8093+c.ROLES.index(role);web=3113+c.ROLES.index(role)
    assert c.available(api) and schema in ['northstar_english','northstar_phase01_test']
    env=run.environment();env.update(MYSQL_PORT=str(d['port']),DB_NAME=schema,DB_PASSWORD=cred['app'],DB_MIGRATION_PASSWORD=cred['migrator'],API_PORT=str(api),WEB_PORT=str(web))
    argv=[str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--server.port='+str(api),'--northstar.content-root='+str(c.PRIVATE/role/'content'),'--northstar.recording-root='+str(c.PRIVATE/role/'recordings')]
    if initialize:argv.append('--northstar.initialize-content=true')
    log=c.PRIVATE/role/('new-api-'+str(time.time_ns())+'.log');stream=log.open('xb')
    p=subprocess.Popen(argv,env=env,cwd=run.COPY/'apps/api',stdout=stream,stderr=subprocess.STDOUT)
    c.RECORDS.append(dict(name=role+'-new-api',argv=argv,pid=p.pid,jarSha256=c.digest(c.PATCHED_JAR),log=str(log.relative_to(ROOT))))
    try:
        for _ in range(80):
            if p.poll() is not None:raise RuntimeError('New API exited; private log '+str(log.relative_to(ROOT)))
            try:
                with urllib.request.urlopen('http://127.0.0.1:'+str(api)+'/api/v1/health',timeout=1) as r:
                    health=json.load(r)
                if health['migrationVersion']=='009.05':
                    if initialize:
                        with urllib.request.urlopen('http://127.0.0.1:'+str(api)+'/api/v1/lessons/demo-01',timeout=2) as r: assert json.load(r)['versionId']=='demo-01-v2'
                    return (p,stream,api,web)
            except OSError:pass
            time.sleep(.5)
        raise RuntimeError('API readiness timeout')
    except BaseException:
        c.end_api(role,(p,stream,api,web));raise


def compare_order(before,after,allow_redundant_book_index_drop=False):
    assert set(before)==set(after), 'Unexpected new or missing table'
    for table,data in before.items():
        actual=after[table]; columns=data['columns']
        assert actual['primaryKey']==data['primaryKey']
        assert set(actual['columns'])-set(columns)==({'sequence_no','display_number'} if table=='lesson' else set())
        projected=[[r[actual['columns'].index(col)] for col in columns] for r in actual['rows']]
        if table=='flyway_schema_history':
            pk_index=columns.index('installed_rank'); old_ids={r[pk_index] for r in data['rows']}
            projected=[r for r in projected if r[pk_index] in old_ids]
        assert projected==data['rows'], table+': old cells changed'
        def normalize(sql,added):
            lines=sql.splitlines()
            if added: lines=[line for line in lines if not any(key in line for key in ['`sequence_no`','`display_number`','`uq_lesson_book_sequence`','`ck_lesson_sequence`'])]
            return sorted(line.strip().rstrip(',') for line in lines)
        old_sql=data['createSql']
        if table=='lesson' and allow_redundant_book_index_drop:
            # A source InnoDB auto-created FK index may disappear when the new index covers its prefix.
            # Restoring SHOW CREATE makes that old index explicit, so the restored path can retain it.
            compact=''.join(actual['createSql'].replace('`','').lower().split())
            assert 'uniquekeyuq_lesson_book_sequence(book_id,sequence_no)' in compact
            old_index=lambda line:line.strip().rstrip(',')=='KEY `book_id` (`book_id`)'
            assert sum(old_index(line) for line in old_sql.splitlines())==1
            assert not any(old_index(line) for line in actual['createSql'].splitlines())
            old_sql='\n'.join(line for line in old_sql.splitlines() if not old_index(line))
        assert normalize(old_sql,False)==normalize(actual['createSql'],table=='lesson'), table+': unexpected schema change'


def main():
    assert sys.argv[1:]==['migrations']
    signoff=json.loads((run.OUT/'INDEPENDENT_10B1_SIGNOFF.json').read_text())
    assert 'PASS' in json.dumps(signoff)
    c=campaign();m=load('backup_sql',BASE/'maintenance_backup.py')
    results={};created=[]
    try:
        for role in ['upgrade','empty','fault','recovery']:
            c.create(role);created.append(role);c.prepare_files(role)
            if role=='empty':
                migrate(c,role,initialize=True);c.grant_app(role)
                handle=start(c,role,True)
                try:
                    c.http(role,handle,'/lessons/demo-01')
                finally:c.end_api(role,handle)
                before=c.snapshot(role,'new-initialized')
                for i in range(2):
                    handle=start(c,role)
                    try:c.http(role,handle,'/lessons/demo-01?versionId=demo-01-v1')
                    finally:c.end_api(role,handle)
                    c.compare(before,c.snapshot(role,'ordinary-restart-'+str(i)))
                # Copy this verified clean Demo baseline to a NEW empty integration schema, FK enabled.
                restore=m.restore_sql(before)
                c.sql(role,'CREATE DATABASE northstar_phase01_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; USE northstar_phase01_test;'+restore,private=True)
                grants=json.loads((BASE/'recovery-20261027/a1/grants.json').read_text())['app']
                target='\n'.join(line.replace('`northstar_english`','`northstar_phase01_test`')+';' for line in grants.splitlines() if ' ON `northstar_english`.' in line)
                c.sql(role,target+"\nGRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON northstar_phase01_test.* TO 'northstar_migrator'@'%';")
                results[role]=dict(status='PASS',freshLatestSchemaExplicitInitialization=True,ordinaryRestartsNoChanges=True)
            else:
                c.restore(role);migrate(c,role,'009.04')
                before=c.snapshot(role,'before-new-order')
                if role=='fault':
                    # Single atomic DDL succeeds; explicit following error simulates interruption before history registration.
                    ddl=(ROOT/'apps/api/src/main/resources/db/migration/V009_05__lesson_catalog_order.sql').read_text()
                    failure=c.sql(role,ddl+"\nSIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='phase10b2 injected after order DDL';",expected=(1,))
                    assert failure.returncode==1
                    after=c.snapshot(role,'after-injected-failure')
                    assert before['flyway_schema_history']==after['flyway_schema_history']
                    compare_order(before,after)
                    assert 'sequence_no' in after['lesson']['columns']
                    results[role]=dict(status='PASS',ddlCommittedHistoryNotRegistered=True,oldCellsExact=True,failedTargetRetained=True)
                else:
                    migrate(c,role,'009.05');after=c.snapshot(role,'after-new-order')
                    compare_order(before,after)
                    assert all(row[after['lesson']['columns'].index('sequence_no')] is None for row in after['lesson']['rows'])
                    # A legal previous version must not be reset by ordinary startup.
                    c.sql(role,"UPDATE lesson SET current_version_id='demo-01-v1' WHERE id='demo-01'")
                    stable=c.snapshot(role,'preserved-v1-baseline')
                    for i in range(2):
                        handle=start(c,role)
                        try:
                            lesson=c.http(role,handle,'/lessons/demo-01')
                            assert lesson['versionId']=='demo-01-v1'
                        finally:c.end_api(role,handle)
                        c.compare(stable,c.snapshot(role,'new-restart-'+str(i)))
                    c.media_check(role)
                    results[role]=dict(status='PASS',oldCellsExact=True,mediaExact=True,currentV1Preserved=True,repeatedStartupNoChanges=True,fromOriginalBackup=True)
            c.stop(role)
            c.save(c.OUT/(role+'-acceptance.json'),results[role])
        c.save(c.OUT/'result.json',dict(status='PASS',roles=results,sourceDatabaseAddressed=False,migrationSha256=c.digest(ROOT/'apps/api/src/main/resources/db/migration/V009_05__lesson_catalog_order.sql')))
    finally:
        for role in created:
            try:
                d=c.verify(role)
                c.call(role+'-ensure-stop',[c.DOCKER,'stop','--time','10',d['containerId']],timeout=30)
            except Exception:pass
        c.save(c.OUT/'commands.json',c.RECORDS,exclusive=False)

if __name__=='__main__':main()
