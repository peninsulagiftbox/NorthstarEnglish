#!/usr/bin/env python3
"""Read-only preservation after the P1 stop gate. No new business tests."""
import hashlib,json,subprocess
import run as q

q.sql("SELECT version,description,checksum,success FROM flyway_schema_history ORDER BY installed_rank",label='failure-flyway-history')
tables=['concept_review_card','concept_review_source','concept_review_result','command_receipt','exercise_attempt','attempt_knowledge','review_item','review_source','review_result','learning_evidence','quiz_run','quiz_run_item']
snap={}
for table in tables:
    text=q.sql('SELECT * FROM `'+table+'` ORDER BY 1,2',label='failure-state-'+table)
    snap[table]={'rowText':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'lineCount':len(text.splitlines()) if text else 0}
q.save('failure-db-key-values.json',snap)
q.sql("SELECT COUNT(*),COUNT(DISTINCT attempt_id),COUNT(DISTINCT card_id) FROM concept_review_source; SELECT concept_id,owner_key,row_version,reps,due_at FROM concept_review_card; SELECT COUNT(*) FROM command_receipt; SELECT COUNT(*) FROM concept_review_result; SELECT COUNT(*) FROM knowledge_occurrence WHERE location_guard IS NOT NULL",label='failure-counts')
q.run('failure-db-logical-dump',[q.DOCKER,'exec',q.identity()['containerId'],'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --no-tablespaces --set-gtid-purged=OFF '+q.SCHEMA])
# Keep the full dump private; do not include account/definer or wider fixture payloads in the evidence zip.
dump=q.OUT/'failure-db-logical-dump.log';private=q.PRIVATE/'failure-db-logical-dump.log';dump.rename(private)
q.save('private-dump-identity.json',{'sha256':q.sha(private),'path':str(private),'includedInEvidence':False})
binding={}
for name,expected in json.loads((q.ROOT/'qa/phase10d2-p1/evidence/candidate-inputs.json').read_text()).items():
    binding[name]={'expected':expected,'current':q.sha(q.ROOT/name),'testedCopy':q.sha(q.SOURCE/name)}
assert all(x['expected']==x['current']==x['testedCopy'] for x in binding.values())
q.save('p1-336-input-binding.json',binding)
runtime=json.loads((q.OUT/'browser-runtime.json').read_text())
q.run('owned-processes-after-stop',['ps','-p',str(runtime['apiPid'])+','+str(runtime['webPid']),'-o','pid=,command='],check=False)
q.run('qa-ports-after-stop',['lsof','-nP','-iTCP:8191','-iTCP:3198','-sTCP:LISTEN'],check=False)
q.run('retained-qa-container',[q.DOCKER,'inspect','--format','{"id":{{json .Id}},"running":{{json .State.Running}},"mounts":{{json .Mounts}}}',q.identity()['containerId']])
print('Failure state preserved; no product changes',flush=True)
