#!/usr/bin/env python3
"""Approved source pause + read-only static backup; always resume the same processes."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
RUN=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y%m%dT%H%M%S')
OUT=BASE/('backup-'+RUN)
PRIVATE=ROOT/'.local/phase10b1-backups'/RUN
CONTAINER='bbf8c3f55c023dd7e16377417e31b54c742cb3ecf109fd57f22c152babc58fd0'
DOCKER='/Applications/Docker.app/Contents/Resources/bin/docker'
RECORDS=[]


def save(path,value):
    with path.open('x') as f: f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    path.chmod(0o600)


def call(argv,query=None,private=False):
    record=dict(argv=argv,started=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat())
    if query: record['stdinSql']=query
    try:
        p=subprocess.run(argv,input=query,text=True,capture_output=True,timeout=15)
        record.update(returncode=p.returncode,stderr=p.stderr,stdout='[private backup metadata processed in memory]' if private else p.stdout)
        RECORDS.append(record)
        assert p.returncode==0,'Backup read command failed'
        return p.stdout
    except subprocess.TimeoutExpired:
        record.update(returncode=None,stderr='TIMEOUT; no process exit code obtained'); RECORDS.append(record)
        raise RuntimeError('Backup read timeout')


def sql(query,private=False):
    shell='MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot --database=northstar_english --batch --raw --skip-column-names'
    return call([DOCKER,'exec','-i',CONTAINER,'sh','-c',shell],
                "SET SESSION time_zone='+00:00';\nSTART TRANSACTION READ ONLY;\n"+query+';\nROLLBACK;\n',private)


def snapshot():
    tables=sql('SHOW TABLES').splitlines()
    result={}
    for table in tables:
        assert re.fullmatch('[a-z_]+',table)
        names=sql("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='"+table+"' ORDER BY ORDINAL_POSITION").splitlines()
        pk=sql("SELECT COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='"+table+"' AND INDEX_NAME='PRIMARY' ORDER BY SEQ_IN_INDEX").splitlines()
        assert pk and all(re.fullmatch('[a-z][a-z0-9_]*',name) for name in names+pk)
        expression=','.join('HEX(CAST(`'+name+'` AS BINARY))' for name in names)
        order=','.join('`'+name+'`' for name in pk)
        rows=[json.loads(s) for s in sql('SELECT JSON_ARRAY('+expression+') FROM `'+table+'` ORDER BY '+order,True).splitlines()]
        create=sql('SHOW CREATE TABLE `'+table+'`').split('\t',1)[1].strip()
        result[table]=dict(columns=names,primaryKey=pk,rows=rows,createSql=create)
    return result


def restore_sql(snapshot):
    # Create a NEW target with all checks/FKs enabled. Only the known lesson/version
    # cycle is deferred until both tables exist, as in original V002 initialization.
    fk_pattern=r'CONSTRAINT `([^`]+)` FOREIGN KEY \(([^)]+)\) REFERENCES `([^`]+)` \(([^)]+)\)'
    dependencies={}
    self_keys={}
    creates={}
    deferred=None
    for table,data in snapshot.items():
        refs=[]; self_keys[table]=[]
        create=data['createSql']
        for match in re.finditer(fk_pattern,create):
            name,cols,target,target_cols=match.groups()
            if name=='fk_current_version':
                assert table=='lesson' and target=='lesson_version'
                deferred=match.group(0)
            elif target==table:
                self_keys[table].append((re.findall(r'`([^`]+)`',cols),re.findall(r'`([^`]+)`',target_cols)))
            else: refs.append(target)
        if table=='lesson':
            lines=[line for line in create.splitlines() if 'CONSTRAINT `fk_current_version`' not in line]
            for i,line in enumerate(lines):
                if line.startswith(')'):
                    lines[i-1]=lines[i-1].rstrip(',')
            create='\n'.join(lines)
        dependencies[table]=set(refs); creates[table]=create
    assert deferred,'Expected current-version FK missing'
    order=[]; pending=set(snapshot)
    while pending:
        ready=sorted(t for t in pending if not (dependencies[t]&pending))
        assert ready,'Unresolved schema dependency cycle'
        order.extend(ready); pending-=set(ready)
    lines=["SET NAMES utf8mb4;","SET SESSION time_zone='+00:00';"]
    lines.extend(creates[t]+';' for t in order)
    lines.append('START TRANSACTION;')
    pointer_updates=[]
    def literal(value): return 'NULL' if value is None else "CONVERT(X'"+value+"' USING utf8mb4)"
    for table in order:
        data=snapshot[table]; cols=data['columns']; rows=list(data['rows'])
        inserted=[]
        while rows:
            progress=False
            for row in list(rows):
                blocked=False
                for src,dst in self_keys[table]:
                    fk=tuple(row[cols.index(c)] for c in src)
                    if None not in fk and any(tuple(other[cols.index(c)] for c in dst)==fk and other is not row for other in rows):
                        blocked=True
                if blocked: continue
                values=list(row)
                if table=='lesson':
                    index=cols.index('current_version_id')
                    if values[index] is not None:
                        pointer_updates.append('UPDATE `lesson` SET `current_version_id`='+literal(values[index])+' WHERE `id`='+literal(values[cols.index('id')])+';')
                        values[index]=None
                lines.append('INSERT INTO `'+table+'` ('+','.join('`'+c+'`' for c in cols)+') VALUES ('+','.join(literal(v) for v in values)+');')
                rows.remove(row); inserted.append(row); progress=True
            assert progress,'Unresolved self-referencing row cycle'
    lines.extend(pointer_updates)
    lines.extend(['COMMIT;','ALTER TABLE `lesson` ADD '+deferred+';'])
    return '\n'.join(lines)+'\n'


def main():
    assert sys.argv[1:]==['--execute-approved-window'],'Explicit approved-window flag required'
    OUT.mkdir(mode=0o700,exist_ok=False); PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('runtime',BASE/'runtime_media_preflight.py')
    runtime=importlib.util.module_from_spec(spec); spec.loader.exec_module(runtime)
    expected=json.loads((BASE/'readiness-20261027-attempt3/runtime.json').read_text())
    held=[]; result={'status':'BLOCKED','sourceDataWrites':False,'sourceSpringRestarted':False}
    watchdog_state=PRIVATE/'resume-watchdog.json'
    try:
        # No dump or signal before fresh container, server, account and project verification.
        item=json.loads(call([DOCKER,'inspect','--format','{"labels":{{json .Config.Labels}},"ports":{{json .HostConfig.PortBindings}},"mounts":{{json .Mounts}}}',CONTAINER]))
        assert item['labels']['local.northstar.project']=='northstar-english-local-v1'
        assert item['ports']['3306/tcp']==[{'HostIp':'127.0.0.1','HostPort':'3308'}]
        assert any(m.get('Name')=='northstar_english_mysql_01_data' and m['Destination']=='/var/lib/mysql' for m in item['mounts'])
        identity=json.loads(sql("SELECT JSON_OBJECT('uuid',@@server_uuid,'schema',DATABASE(),'project',(SELECT project_key FROM project_identity),'account',CURRENT_USER())"))
        assert identity=={'uuid':'104d5d9d-cd3f-11f1-8da4-920f115cf5cb','schema':'northstar_english','project':'northstar-english-local-v1','account':'root@%'},'Source identity mismatch'
        expected_process={p['pid']:p for p in expected['processes']}
        # Only listener children are suspended; supervisors remain alive. No shutdown or restart.
        for pid in [17635,9117]:
            args,env=runtime.process_config(pid)
            assert hashlib.sha256(json.dumps(args).encode()).hexdigest()==expected_process[pid]['argumentsSha256'],'PID/argv changed'
            cwd=call(['lsof','-a','-p',str(pid),'-d','cwd','-Fn'])
            assert '\nn'+expected_process[pid]['cwd']+'\n' in cwd,'PID cwd changed'
        save(watchdog_state,[expected_process[p] for p in [9117,17635]])
        guard=subprocess.Popen([sys.executable,str(BASE/'resume_watchdog.py'),str(watchdog_state)],
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        RECORDS.append(dict(action='start-resume-watchdog',pid=guard.pid,deadlineSeconds=180))
        def timeout_handler(signum,frame): raise RuntimeError('Maintenance window interrupted or timed out')
        signal.signal(signal.SIGALRM,timeout_handler); signal.signal(signal.SIGTERM,timeout_handler); signal.signal(signal.SIGINT,timeout_handler)
        signal.alarm(160)
        for pid in [17635,9117]:
            os.kill(pid,signal.SIGSTOP); held.append(pid)
            RECORDS.append(dict(action='SIGSTOP',pid=pid,at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),returncode=0))
        active=int(sql('SELECT COUNT(*) FROM information_schema.INNODB_TRX WHERE trx_mysql_thread_id<>CONNECTION_ID()'))
        assert active==0,'Existing transaction detected after pause; resume immediately instead of taking static backup'
        sessions=sql("SELECT ID,USER,HOST,DB,COMMAND FROM information_schema.PROCESSLIST WHERE ID<>CONNECTION_ID() AND DB='northstar_english'")
        assert all(line.split('\t')[-1]=='Sleep' for line in sessions.splitlines()),'Another active source connection exists'
        before=snapshot()
        save(PRIVATE/'source-snapshot.json',before)
        safe_sql=PRIVATE/'restore.sql'
        safe_sql.write_text(restore_sql(before)); safe_sql.chmod(0o600)
        # Dump is a private backup artifact, not executed; target restore must not execute FK-disabling directives.
        dump_shell='MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump --protocol=TCP -h127.0.0.1 -uroot --single-transaction --skip-lock-tables --no-tablespaces --set-gtid-purged=OFF --hex-blob --order-by-primary --skip-add-drop-table --skip-add-locks --skip-disable-keys --skip-dump-date northstar_english'
        dump_path=PRIVATE/'source.sql'
        with dump_path.open('xb') as f:
            p=subprocess.run([DOCKER,'exec',CONTAINER,'sh','-c',dump_shell],stdout=f,stderr=subprocess.PIPE,timeout=30)
        dump_path.chmod(0o600)
        RECORDS.append(dict(argv=[DOCKER,'exec',CONTAINER,'sh','-c',dump_shell],returncode=p.returncode,stderr=p.stderr.decode(),stdout='[private source.sql]',at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()))
        assert p.returncode==0 and dump_path.stat().st_size>0,'SQL backup failed'
        manifests={}
        for role,key in [('recordings','mediaRoot'),('content','contentRoot')]:
            source=Path(expected[key]); rows=runtime.inventory(source)
            shutil.copytree(source,PRIVATE/role,symlinks=False)
            copied=runtime.inventory(PRIVATE/role)
            assert copied==rows,'Copied media differs from source'
            manifests[role]=rows
        after=snapshot()
        assert before==after,'Source rows/schema changed during static window'
        for role,key in [('recordings','mediaRoot'),('content','contentRoot')]:
            assert runtime.inventory(Path(expected[key]))==manifests[role],'Source media changed during window'
        assert not watchdog_state.with_suffix('.triggered').exists(),'Watchdog resumed service before backup completed'
        save(PRIVATE/'media-manifest.json',manifests)
        hashes=[]
        for path in sorted(PRIVATE.rglob('*')):
            if path.is_file():
                path.chmod(0o600)
                with path.open('rb') as durable: os.fsync(durable.fileno())
                hashes.append(dict(path=str(path.relative_to(PRIVATE)),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        save(PRIVATE/'SHA256SUMS.json',hashes)
        (PRIVATE/'COMPLETE').write_text('Static source SQL, canonical old rows and full media copied and verified. Restore not yet verified.\n')
        (PRIVATE/'COMPLETE').chmod(0o600)
        result.update(status='BACKUP_CREATED_NOT_YET_RESTORE_VERIFIED',backupId=RUN,privateBackup=str(PRIVATE.relative_to(ROOT)),
            identity=identity,tableCounts={t:len(v['rows']) for t,v in before.items()},
            files=len(hashes),totalBytes=sum(x['bytes'] for x in hashes),manifestSha256=hashlib.sha256((PRIVATE/'SHA256SUMS.json').read_bytes()).hexdigest(),
            staticRowsAndSchemaBeforeAfterIdentical=True,sourceMediaBeforeAfterIdentical=True,
            rawDumpRestorePolicy='Do not directly execute session directives that disable FK; restore from canonical snapshot with FK enabled and dependency-aware insertion',
            restoreVerified=False)
    except Exception as e:
        result['reason']=type(e).__name__+': '+str(e)
    finally:
        signal.alarm(0)
        failures=[]
        for pid in reversed(held):
            try:
                args,env=runtime.process_config(pid)
                assert hashlib.sha256(json.dumps(args).encode()).hexdigest()==expected_process[pid]['argumentsSha256'],'PID changed before resume'
                os.kill(pid,signal.SIGCONT)
                RECORDS.append(dict(action='SIGCONT',pid=pid,returncode=0,at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()))
            except Exception as e: failures.append(dict(pid=pid,reason=type(e).__name__+': '+str(e)))
        result['resumeFailures']=failures
        result['sameProcessResume']=not failures and bool(held)
        if not failures: watchdog_state.with_suffix('.done').write_text('Controller completed; same verified processes resumed.\n')
        if failures: result['status']='BLOCKED'
        if held and not failures:
            try:
                states={str(pid):call(['ps','-p',str(pid),'-o','stat=']).strip() for pid in held}
                assert all('T' not in value for value in states.values()),'Process remains suspended'
                with urllib.request.urlopen('http://127.0.0.1:8085/api/v1/health',timeout=10) as response:
                    health=json.load(response)
                assert health.get('status')=='UP' and health.get('project')=='northstar-english-local-v1'
                result['resumeVerification']=dict(processStates=states,apiHealth=health)
            except Exception as e:
                result.update(status='BLOCKED',resumeVerificationError=type(e).__name__+': '+str(e))
        save(OUT/'result.json',result); save(OUT/'commands.json',RECORDS)
    print(json.dumps(dict(status=result['status'],evidence=str(OUT.relative_to(ROOT)),sameProcessResume=result['sameProcessResume'])))
    return 0 if result['status']=='BACKUP_CREATED_NOT_YET_RESTORE_VERIFIED' else 2


if __name__=='__main__':
    sys.exit(main())
