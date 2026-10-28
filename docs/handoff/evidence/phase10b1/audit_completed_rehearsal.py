#!/usr/bin/env python3
"""Offline reconciliation only. Does not connect to any DB or control processes."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import zlib

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
OUT=BASE/'isolated-20261027t154428'
PRIVATE=ROOT/'.local/phase10b1-isolated/20261027t154428'
BACKUP=ROOT/'.local/phase10b1-backups/20261027T154428'


def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def decode(value): return None if value is None else bytes.fromhex(value).decode()
def objects(data): return [dict(zip(data['columns'],map(decode,row))) for row in data['rows']]
def compact(sql): return re.sub(r'\s+','',sql.replace('`','')).lower()


def main():
    spec=importlib.util.spec_from_file_location('campaign',BASE/'isolated_rehearsal.py')
    campaign=importlib.util.module_from_spec(spec); spec.loader.exec_module(campaign)
    source=read(BACKUP/'source-snapshot.json')
    rows=read(OUT/'commands.json')
    frozen=read(BASE/'candidate/candidate-manifest.json')
    for item in frozen['files']: assert sha(ROOT/item['path'])==item['sha256']
    for item in read(BACKUP/'SHA256SUMS.json'):
        p=BACKUP/item['path']; assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
    runtime=read(BASE/'isolated-final-runtime-check.json')
    assert runtime['all12TargetsStopped'] and len(runtime['targets'])==12
    assert len({d['uuid'] for d in runtime['targets']})==12
    assert all(d['uuid']!=campaign.SOURCE_UUID and d['status']=='exited' for d in runtime['targets'])
    assert runtime['sourceHealthGetOnly']['status']=='UP' and runtime['sourceHealthGetOnly']['migrationVersion']=='008'
    identities={d['id'] for d in runtime['targets']}
    for record in rows:
        assert campaign.SOURCE_CONTAINER not in record.get('argv',[]),'Campaign addressed source container'
        if record.get('rawLog'):
            assert sha(ROOT/record['rawLog'])==record['rawLogSha256']
    stage_results={role:read(OUT/(role+'-result.json')) for role in campaign.ROLES}
    assert all(d['status']=='PASS' for d in stage_results.values())
    for role in campaign.ROLES:
        state=read(PRIVATE/role/'state.json')
        assert state['containerId'] in identities and state['uuid']!=campaign.SOURCE_UUID
        campaign.media_check(role)

    upgrade=read(PRIVATE/'upgrade/candidate-baseline.json')
    for tag in ['v008-restored','old-app-read']:
        campaign.compare(source,read(PRIVATE/'upgrade'/(tag+'.json')))
    for version in ['009.01','009.02','009.03','009.04']:
        current=read(PRIVATE/'upgrade'/('after-'+version+'.json'))
        campaign.compare(source,current,True,paragraph_column_required=version!='009.01')
    for role in ['upgrade','empty']:
        final=read(PRIVATE/role/'candidate-baseline.json')
        for n in [1,2]: campaign.compare(final,read(PRIVATE/role/('candidate-start-'+str(n)+'.json')))
        psql=compact(final['paragraph']['createSql']); ssql=compact(final['sentence']['createSql'])
        for required in ['primarykey(id)','uniquekeyuq_paragraph_version(id,version_id)',
                         'uniquekeyuq_paragraph_key(version_id,stable_key)','uniquekeyuq_paragraph_sequence(version_id,sequence_no)',
                         'constraintfk_paragraph_versionforeignkey(version_id)referenceslesson_version(id)',
                         'constraintck_paragraph_sequencecheck((sequence_no>0))']:
            assert required in psql,'Paragraph definition missing '+required
        for required in ['keyix_sentence_paragraph_version(paragraph_id,lesson_version_id)',
                         'constraintfk_sentence_paragraph_versionforeignkey(paragraph_id,lesson_version_id)referencesparagraph(id,version_id)',
                         'paragraph_idvarchar(64)charactersetasciicollateascii_binnotnull']:
            assert required in ssql,'Sentence definition missing '+required
        expected_ids={'demo-01-v1':'af61b21b-371a-4550-85a2-8301db66a325','demo-01-v2':'a214bafb-e722-4f77-b5ed-62311f41b116'}
        paragraphs=objects(final['paragraph'])
        assert len(paragraphs)==2
        assert all(p['id']==expected_ids[p['version_id']] and p['stable_key']=='original-dialogue' and p['sequence_no']=='1' for p in paragraphs)
        sentences=objects(final['sentence']); assert len(sentences)==20
        assert all(s['paragraph_id']==expected_ids[s['lesson_version_id']] for s in sentences)
        history=objects(final['flyway_schema_history'])
        sql_history=[h for h in history if h['type']=='SQL']
        assert len(sql_history)==12 and all(h['success']=='1' for h in sql_history)
        for h in sql_history:
            path=(BASE/'candidate'/h['script']) if h['version'].startswith('009') else ROOT/'apps/api/src/main/resources/db/migration'/h['script']
            crc=0
            for line in path.read_text(encoding='utf-8-sig').splitlines(): crc=zlib.crc32(line.encode(),crc)
            signed=crc if crc<2**31 else crc-2**32
            assert int(h['checksum'])==signed,'Actual history checksum mismatch'
        assert sum(h['type']=='BASELINE' for h in history)==(0 if role=='empty' else 1)
        assert read(OUT/(role+'-constraints.json'))['status']=='PASS'
    empty_before=read(PRIVATE/'empty/v008-seeded.json')
    empty_final=read(PRIVATE/'empty/candidate-baseline.json')
    campaign.compare(empty_before,empty_final,True)
    assert {t:v['createSql'] for t,v in upgrade.items()}=={t:v['createSql'] for t,v in empty_final.items()}

    for fault in ['fault-ddl-01','fault-ddl-02','fault-ddl-04','fault-history','fault-dml']:
        before=read(PRIVATE/fault/'before-fault.json'); after=read(PRIVATE/fault/'after-fault.json')
        campaign.compare(source,before)
        for table,data in source.items():
            new=after[table]
            assert [[r[new['columns'].index(c)] for c in data['columns']] for r in new['rows']]==data['rows']
        assert after['flyway_schema_history']['rows']==source['flyway_schema_history']['rows']
        if fault in ['fault-ddl-01','fault-history']: assert 'paragraph_id' not in after['sentence']['columns']
        if fault in ['fault-ddl-02','fault-dml']:
            assert not after['paragraph']['rows']
            assert all(r[after['sentence']['columns'].index('paragraph_id')] is None for r in after['sentence']['rows'])
        if fault=='fault-ddl-04': assert after['sentence']['createSql']==upgrade['sentence']['createSql'] and len(after['paragraph']['rows'])==2
        recovery=fault.replace('fault-','recover-',1)
        for tag in ['restored-v008','old-read']: campaign.compare(source,read(PRIVATE/recovery/(tag+'.json')))
        continued=read(PRIVATE/recovery/'after-continuation.json')
        receipt=read(OUT/(recovery+'-continuation.json'))
        task=next(t for t in objects(source['writing_task']) if t['lesson_id']=='demo-01' and t['version_id']=='demo-01-v2')
        revisions=[r for r in objects(source['writing_revision']) if r['task_id']==task['id']]
        parent=max(revisions,key=lambda r:int(r['version_no']))['id'] if revisions else None
        info=dict(eventId=receipt['eventId'],revisionId=receipt['newRevisionId'],taskId=task['id'],parentId=parent,
                  text='Please put the small plants beside the bench. I can bring water for the garden.')
        campaign.verify_continuation_delta(source,continued,info)
        campaign.compare(continued,read(PRIVATE/recovery/'after-restart.json'))

    statement_counts={}
    export=[]
    secret_values=[]
    for path in PRIVATE.glob('*/credentials.json'): secret_values.extend(read(path).values())
    for line in (ROOT/'.env').read_text().splitlines():
        key,sep,value=line.partition('=')
        if sep and 'PASSWORD' in key and len(value)>=16: secret_values.append(value)
    private_text=[]
    for table in ['writing_draft','writing_revision','exercise_draft']:
        for item in objects(source[table]):
            private_text.extend(value for key,value in item.items() if key in ['raw_text','text','draft_text','answer_text'] and value and len(value)>=8)
    public=OUT/'public-logs'; public.mkdir(mode=0o700,exist_ok=False)
    for i,record in enumerate(rows):
        if '-flyway-' not in record.get('name',''): continue
        original=ROOT/record['rawLog']; raw=original.read_text()
        before=raw.count('CALLBACK BEFORE_EACH_MIGRATE_STATEMENT')
        after=raw.count('CALLBACK AFTER_EACH_MIGRATE_STATEMENT')
        statement_counts[record['name']]=dict(before=before,after=after,exitCode=record['returncode'])
        if record['name']=='fault-history-flyway-009.01':
            assert record['returncode']==1 and 'INSERT command denied' in raw and 'flyway_schema_history' in raw
        else: assert record['returncode']==0 and before==after and before>0
        redacted=raw; changes=0
        for value in secret_values+private_text:
            if value in redacted: changes+=redacted.count(value); redacted=redacted.replace(value,'[REDACTED]')
        dest=public/('flyway-'+str(i)+'.txt'); dest.write_text(redacted); dest.chmod(0o600)
        export.append(dict(name=record['name'],originalPrivateLog=record['rawLog'],originalSha256=sha(original),
             exported=str(dest.relative_to(ROOT)),exportedSha256=sha(dest),redactions=changes,
             byteIdenticalToOriginal=original.read_bytes()==dest.read_bytes(),exitCode=record['returncode']))
    result=dict(at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        status='FUNCTIONAL_PASS_WITH_CONTROLLER_NOTE_PENDING_INDEPENDENT_REVIEW',B01='PASS',B03='PASS',
        sixEvidence=dict(sourceIdentity='PASS',staticBackupAndMedia='PASS',v008Upgrade='PASS',v001EmptyInit='PASS',
                         failureRecovery='PASS',originalColumnsAndMedia='PASS'),
        stages={role:data['status'] for role,data in stage_results.items()},
        all12TargetsStopped=True,allTargetUuidsDistinctFromSource=True,sourceStillV008=True,
        allOldCellsCompared=True,sourcePrivateDataExported=False,statementCallbacks=statement_counts,
        publicFlywayLogs=export,rawCommandRecords=len(rows),
        controllerExitCode=1,controllerNote='All stage checks finished; exclusive aggregate writer collided with preserved prior failure result. No DB rerun. Historical failure retained; this is a separate offline audit.',
        auditDatabaseCommands=0,independentReview='PENDING',phase10B2Started=False)
    with (OUT/'final-audit.json').open('x') as f: f.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'B01':'PASS','B03':'PASS','stages':12,'publicFlywayLogs':len(export),'controllerExitCode':1,'auditExitCode':0}))


if __name__=='__main__': main()
