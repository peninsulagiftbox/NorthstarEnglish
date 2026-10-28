#!/usr/bin/env python3
"""Fresh static backup and restore verification. Source is strictly READ ONLY."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zlib

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'phase10b1'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def main():
    assert sys.argv[1:]==['--backup-and-verify-isolated']
    os.umask(0o077)
    run=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y%m%dT%H%M%S')
    out=HERE/run; private=ROOT/'.local/personal-migration'/run
    out.mkdir(); private.mkdir(parents=True)
    backup=private/'backup'; backup.mkdir()
    m=load('backup',OLD/'maintenance_backup.py')
    runtime=load('runtime',OLD/'runtime_media_preflight.py')
    c=load('campaign',OLD/'isolated_rehearsal.py')
    c.OLD_JAR=ROOT/'.local/personal-migration/20261027T204151/original-app.jar'
    shutil.copyfile(__file__,out/'prepare-at-execution.py')
    result={'status':'BLOCKED','sourceWrites':False,'run':run,'privateBackup':str(backup.relative_to(ROOT))}
    target_created=False
    def save(path,value):
        with path.open('x') as f: json.dump(value,f,ensure_ascii=False,indent=2)
    try:
        # Confirm the existing source before issuing even SELECTs.
        item=json.loads(m.call([m.DOCKER,'inspect','--format','{"id":{{json .Id}},"labels":{{json .Config.Labels}},"ports":{{json .HostConfig.PortBindings}},"mounts":{{json .Mounts}},"status":{{json .State.Status}}}',m.CONTAINER]))
        assert item['id']==m.CONTAINER and item['status']=='running'
        assert item['labels']['local.northstar.project']=='northstar-english-local-v1'
        assert item['labels']['com.docker.compose.project']=='northstar-english-local-01'
        assert item['ports']['3306/tcp']==[{'HostIp':'127.0.0.1','HostPort':'3308'}]
        assert any(x.get('Name')=='northstar_english_mysql_01_data' and x['Destination']=='/var/lib/mysql' for x in item['mounts'])
        identity=json.loads(m.sql("SELECT JSON_OBJECT('uuid',@@server_uuid,'schema',DATABASE(),'project',(SELECT project_key FROM project_identity),'account',CURRENT_USER())"))
        assert identity=={'uuid':c.SOURCE_UUID,'schema':'northstar_english','project':'northstar-english-local-v1','account':'root@%'}
        result['identity']=identity
        # There must be no running project service and no other DB session.
        for port in [8085,3100]:
            p=subprocess.run(['lsof','-nP','-iTCP:'+str(port),'-sTCP:LISTEN'],capture_output=True,text=True)
            assert p.returncode==1 and not p.stdout,'A service is listening; stop for a separately approved window'
        for name in ['api','web']:
            record=json.loads((ROOT/'.local'/f'{name}.json').read_text())
            p=subprocess.run(['ps','-p',str(record['pid']),'-o','pid='],capture_output=True,text=True)
            assert p.returncode==1 and not p.stdout,'Recorded supervisor still running'
        assert int(m.sql('SELECT COUNT(*) FROM information_schema.INNODB_TRX WHERE trx_mysql_thread_id<>CONNECTION_ID()'))==0
        assert int(m.sql("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID<>CONNECTION_ID() AND DB='northstar_english'"))==0
        assert shutil.disk_usage(ROOT).free>6*1024**3,'Insufficient backup/restore headroom'
        manifest=json.loads((OLD/'candidate/candidate-manifest.json').read_text())
        for f in manifest['files']:
            p=ROOT/f['path']; assert p.stat().st_size==f['bytes'] and c.digest(p)==f['sha256']
        assert c.digest(c.OLD_JAR)=='99a3c24103d382c2330a872667c5d0b6d53494de9fd14c320c322cc14ef22619'
        assert c.digest(c.PATCHED_JAR)=='0aa22702023aa20d33405c2572e0469707fc41948ff985a687dc7fcec3ce3005'
        before=m.snapshot()
        history=c.objects(before['flyway_schema_history']) if hasattr(c,'objects') else [dict(zip(before['flyway_schema_history']['columns'],[None if v is None else bytes.fromhex(v).decode() for v in row])) for row in before['flyway_schema_history']['rows']]
        sql_history=[h for h in history if h['type']=='SQL']
        assert [h['version'] for h in sql_history]==[f'{i:03}' for i in range(1,9)]
        assert all(h['success']=='1' for h in history)
        for h in sql_history:
            path=ROOT/'apps/api/src/main/resources/db/migration'/h['script']; crc=0
            for line in path.read_text(encoding='utf-8-sig').splitlines(): crc=zlib.crc32(line.encode(),crc)
            assert int(h['checksum'])==(crc if crc<2**31 else crc-2**32)
            assert path.read_bytes()==subprocess.run(['git','show','HEAD:'+str(path.relative_to(ROOT))],capture_output=True,check=True).stdout
        assert set(before)==set(json.loads((ROOT/'.local/phase10b1-backups/20261027T154428/source-snapshot.json').read_text()))
        assert m.sql('SELECT COUNT(*) FROM lesson').strip()=='1','Expected the single Demo lesson; catalog-only books are not lessons'
        assert m.sql("SELECT GROUP_CONCAT(id ORDER BY id) FROM lesson_version").strip()=='demo-01-v1,demo-01-v2'
        assert m.sql('SELECT COUNT(*) FROM sentence').strip()=='20'
        save(backup/'source-snapshot.json',before)
        (backup/'restore.sql').write_text(m.restore_sql(before))
        dump_shell='MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump --protocol=TCP -h127.0.0.1 -uroot --single-transaction --skip-lock-tables --no-tablespaces --set-gtid-purged=OFF --hex-blob --order-by-primary --skip-add-drop-table --skip-add-locks --skip-disable-keys --skip-dump-date northstar_english'
        with (backup/'source.sql').open('xb') as f:
            p=subprocess.run([m.DOCKER,'exec',m.CONTAINER,'sh','-c',dump_shell],stdout=f,stderr=subprocess.PIPE,timeout=30)
        m.RECORDS.append({'argv':[m.DOCKER,'exec',m.CONTAINER,'sh','-c',dump_shell],'returncode':p.returncode,'stderr':p.stderr.decode(),'stdout':'[private SQL backup]'})
        assert p.returncode==0
        paths={'recordings':Path.home()/'Library/Application Support/NorthstarEnglish/recordings/northstar_english','content':ROOT/'content'}
        media={}
        for name,src in paths.items():
            media[name]=runtime.inventory(src); shutil.copytree(src,backup/name)
            assert runtime.inventory(backup/name)==media[name]
        assert m.snapshot()==before,'Source changed during backup'
        assert all(runtime.inventory(src)==media[name] for name,src in paths.items())
        save(backup/'media-manifest.json',media)
        sums=[{'path':str(p.relative_to(backup)),'bytes':p.stat().st_size,'sha256':c.digest(p)} for p in sorted(backup.rglob('*')) if p.is_file()]
        save(backup/'SHA256SUMS.json',sums)
        c.PRIVATE=private/'isolated'; c.PRIVATE.mkdir()
        c.OUT=out/'isolated'; c.OUT.mkdir()
        c.NAMESPACE='northstar-personal-check-'+run.lower()
        c.BACKUP=backup
        c.ROLES=['reserved'+str(i) for i in range(17)]+['fresh'] # DB3330/API8110, unrelated ports untouched.
        role='fresh'
        c.create(role); target_created=True
        c.prepare_files(role); c.restore(role)
        c.compare(before,c.snapshot(role,'restored-v008'))
        handle=c.start_api(role)
        try:c.read_application(role,handle)
        finally:c.end_api(role,handle)
        c.compare(before,c.snapshot(role,'after-old-start'))
        original_chain=private/'original-migrations'; original_chain.mkdir()
        for h in sql_history:
            shutil.copyfile(ROOT/'apps/api/src/main/resources/db/migration'/h['script'],original_chain/h['script'])
        for version in manifest['versions']:
            state=c.verify(role); credentials=json.loads((c.PRIVATE/role/'credentials.json').read_text())
            env=dict(os.environ,TARGET_MYSQL_PORT=str(state['port']),EXPECTED_TARGET_UUID=state['uuid'],TARGET_PASSWORD=credentials['migrator'],TARGET_USER='northstar_migrator',MIGRATION_TARGET=version)
            c.call(role+'-flyway-'+version,[str(c.JAVA),'-cp',str(c.CLASSES)+os.pathsep+str(c.LIB/'*'),'MigrationHarness',str(original_chain),str(OLD/'candidate')],env=env,private=True,timeout=90)
            c.compare(before,c.snapshot(role,'after-'+version),allow_new=True,paragraph_column_required=version!='009.01')
        c.candidate_assertions(role)
        for n in range(2):
            handle=c.start_api(role,patched=True)
            try:c.read_application(role,handle)
            finally:c.end_api(role,handle)
            c.compare(before,c.snapshot(role,'after-new-start-'+str(n)),allow_new=True)
        c.media_check(role)
        assert m.snapshot()==before,'Source changed during isolated verification'
        result.update(status='FRESH_BACKUP_RESTORE_AND_CANDIDATE_PASS',backupManifestSha256=c.digest(backup/'SHA256SUMS.json'),tables=len(before),counts={t:len(v['rows']) for t,v in before.items()},mediaFiles={k:len(v) for k,v in media.items()},isolated=c.state(role),sourceStillV008=True)
    except Exception as error:
        result['reason']=type(error).__name__+': '+str(error)
    finally:
        if target_created:
            try:c.stop('fresh'); result['isolatedStopped']=True
            except Exception as error: result['isolatedStopError']=type(error).__name__
        save(out/'source-readonly-commands.json',m.RECORDS)
        save(out/'isolated-commands.json',c.RECORDS)
        save(out/'result.json',result)
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result['status']=='FRESH_BACKUP_RESTORE_AND_CANDIDATE_PASS' else 2

if __name__=='__main__':sys.exit(main())
