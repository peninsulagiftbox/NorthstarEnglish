#!/usr/bin/env python3
"""New application/backup compatibility on isolated copies only, never source writes."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error

sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare import load,ROOT,HERE,OLD

def main():
    assert len(sys.argv)==2 and sys.argv[1].isalnum()
    run=sys.argv[1];os.umask(0o077)
    private=ROOT/'.local/personal-migration'/run
    out=HERE/run/'application-compatibility';out.mkdir()
    c=load('campaign',OLD/'isolated_rehearsal.py');m=load('backup',OLD/'maintenance_backup.py')
    c.PRIVATE=private/'isolated';c.OUT=out;c.BACKUP=private/'backup';c.NAMESPACE='northstar-personal-check-'+run.lower()
    # Command indices restart for this phase; keep raw logs in a distinct directory.
    original_call=c.call
    def scoped_call(*args,**kwargs):
        state_root=c.PRIVATE
        c.PRIVATE=private/'application-compatibility-logs'
        try:return original_call(*args,**kwargs)
        finally:c.PRIVATE=state_root
    c.call=scoped_call
    shutil.copyfile(__file__,out/'verify-at-execution.py')
    c.ROLES=['reserved'+str(i) for i in range(17)]+['fresh','fresh009']
    result={'status':'BLOCKED','sourceWrites':False};handle=None;started=[]
    try:
        d=c.verify('fresh');c.call('start-owned-fresh',[c.DOCKER,'start',d['containerId']]);started.append('fresh')
        for _ in range(40):
            probe=c.call('wait-fresh-ready',[c.DOCKER,'exec',d['containerId'],'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot --connect-timeout=2 -Nse "SELECT @@server_uuid"'],expected=(0,1),private=True)
            if probe.returncode==0:
                assert probe.stdout.decode().strip()==d['uuid'];break
            time.sleep(.5)
        else:raise RuntimeError('Fresh isolated MySQL did not become ready')
        baseline=c.snapshot('fresh','before-compatibility')
        for attempt in range(2):
            handle=c.start_api('fresh') # rebuilt JAR with unchanged SQL and paragraph content guard
            c.read_application('fresh',handle)
            envelope=c.http('fresh',handle,'/data/export')
            payload=json.loads(envelope['payloadJson']);assert payload['schemaVersion']=='009.04'
            assert hashlib.sha256(envelope['payloadJson'].encode()).hexdigest()==envelope['sha256']
            assert len(payload['tables']['paragraph']['rows'])==2
            assert c.http('fresh',handle,'/data/import-preview','POST',envelope)['valid']
            rows=payload['tables']['paragraph'];rows['rows'][0][rows['columns'].index('stable_key')]='tampered-paragraph'
            altered=json.dumps(payload,ensure_ascii=False,separators=(',',':'))
            bad={'format':envelope['format'],'payloadJson':altered,'sha256':hashlib.sha256(altered.encode()).hexdigest()}
            try:
                c.http('fresh',handle,'/data/import-preview','POST',bad)
                raise AssertionError('Modified paragraph must be rejected')
            except urllib.error.HTTPError as error:assert error.code==422
            if attempt==0:
                argv=[sys.executable,str(ROOT/'scripts/data-transfer.py'),'backup',str(private/'cli009-backup'),'--api','http://127.0.0.1:8110','--web-port','3130']
                c.call('cli009-backup',argv,timeout=90)
            c.end_api('fresh',handle);handle=None
            c.compare(baseline,c.snapshot('fresh','after-compatibility-'+str(attempt)))
        # Restore all V009 columns/constraints/media to another completely new MySQL.
        advanced=private/'v009-backup';advanced.mkdir()
        (advanced/'restore.sql').write_text(m.restore_sql(baseline))
        (advanced/'source-snapshot.json').write_text(json.dumps(baseline))
        shutil.copyfile(private/'backup/media-manifest.json',advanced/'media-manifest.json')
        for name in ['recordings','content']:shutil.copytree(private/'backup'/name,advanced/name)
        c.BACKUP=advanced;c.create('fresh009');started.append('fresh009');c.prepare_files('fresh009');c.restore('fresh009')
        c.compare(baseline,c.snapshot('fresh009','restored-v009'));c.media_check('fresh009')
        handle=c.start_api('fresh009');c.read_application('fresh009',handle);c.end_api('fresh009',handle);handle=None
        c.compare(baseline,c.snapshot('fresh009','after-restart-v009'))
        result.update(status='PASS',applicationJarSha256=c.digest(c.OLD_JAR),twoStartupOldCellsExact=True,exportSchema='009.04',paragraphTamperRejected422=True,cliBackupPass=True,fullV009RestoreAndRestartPass=True)
    except Exception as error:result['reason']=type(error).__name__+': '+str(error)
    finally:
        if handle is not None:
            try:c.end_api(started[-1],handle)
            except Exception:pass
        for role in reversed(started):
            try:c.stop(role)
            except Exception as error:result[role+'StopError']=type(error).__name__
        (out/'commands.json').write_text(json.dumps(c.RECORDS,ensure_ascii=False,indent=2))
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='PASS' else 2

if __name__=='__main__':sys.exit(main())
