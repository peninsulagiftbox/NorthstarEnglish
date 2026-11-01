#!/usr/bin/env python3
"""R1/R2 browser acceptance against the UUID-checked C2 test database only."""
import hashlib,json,sys
from pathlib import Path
import phase10c2_isolated as iso
import phase10c2_retest as test
r=iso.r
PRIVATE=r.ROOT/'.local/phase10c2-r1'
FIXTURE=PRIVATE/'browser-fixture.json'
def receipts(c,events):
    import uuid
    for event in events:uuid.UUID(event)
    raw=test.sql(c,"SELECT HEX(event_id),HEX(payload_hash),HEX(CAST(response_json AS CHAR CHARACTER SET utf8mb4)) FROM command_receipt WHERE event_id IN ("+','.join("'"+event+"'" for event in events)+") ORDER BY event_id;")
    return hashlib.sha256(raw.encode()).hexdigest()
def seed():
    import uuid,datetime
    c=iso.campaign();iso.ensure_db(c,'empty')
    status,quiz=test.api('/quiz?lessonId=demo-01&versionId=demo-01-v2');assert status==200
    status,health=test.api('/health');assert status==200 and health['migrationVersion']=='011.09'
    fixtures=[]
    for mode in ('legacy-good','wrong-correct','wrong-hash'):
        event=str(uuid.uuid4());payload=dict(eventId=event,lessonId='demo-01',versionId='demo-01-v2',answers={q['id']:q['id']+'-a' for q in quiz['questions']},clientOccurredAt=datetime.datetime.now(datetime.timezone.utc).isoformat())
        if mode=='legacy-good':path='/quiz/attempts'
        else:
            path='/quiz/sets/'+quiz['setId']+'/attempts';payload.update(protocolVersion='quiz-submit-v2',setId=quiz['setId'],setHash=quiz['setHash'])
        status,result=test.api(path,payload);assert status==200,(mode,status)
        fixtures.append(dict(mode=mode,eventId=event,runId=result['runId'],path=path,payload=payload,result=result))
    test.sql(c,"UPDATE quiz_run SET correct_count=0 WHERE id='"+fixtures[1]['runId']+"'; UPDATE quiz_run SET set_hash=REPEAT('0',64) WHERE id='"+fixtures[2]['runId']+"';")
    status,report=test.api('/reports');assert status==200
    current={row['id']:row['verified'] for row in report['quizRuns']}
    assert current[fixtures[0]['runId']] and not current[fixtures[1]['runId']] and not current[fixtures[2]['runId']]
    data=dict(fixtures=fixtures,setId=quiz['setId'],metrics=report['metrics']['quiz'],receiptSha256=receipts(c,[f['eventId'] for f in fixtures]))
    PRIVATE.mkdir(exist_ok=True,parents=True);FIXTURE.write_text(json.dumps(data));print('R1 browser fixtures seeded: one legacy valid run, two invalid histories; test DB only')
def browser():
    c=iso.campaign();c.verify('empty');fixture=json.loads(FIXTURE.read_text())
    cli=['node','/Users/wangshiqi/.npm/_npx/31e32ef8478fbf80/node_modules/@playwright/cli/playwright-cli.js','--session=c2-r1']
    try:
        r.record('r1-browser-open',cli+['open','about:blank'],cwd=r.ROOT)
        script=(r.ROOT/'scripts/phase10c2-r1-browser.js').read_text().replace('__FIXTURE__',json.dumps(fixture))
        result=r.record('r1-browser-report-history',cli+['run-code',script],cwd=r.ROOT)
        assert b'"passed":true' in result.stdout
        assert receipts(c,[f['eventId'] for f in fixture['fixtures']])==fixture['receiptSha256'],'Read/replay changed an existing receipt'
        print('R1 browser PASS; original receipts byte-identical')
    finally:r.record('r1-browser-close',cli+['close'],cwd=r.ROOT)
def compat():
    c=iso.campaign();c.verify('empty');fixture=json.loads(FIXTURE.read_text())
    cli=['node','/Users/wangshiqi/.npm/_npx/31e32ef8478fbf80/node_modules/@playwright/cli/playwright-cli.js','--session=c2-r1-compat']
    try:
        r.record('r1-compat-open',cli+['open','http://127.0.0.1:3195/dashboard'],cwd=r.ROOT)
        r.record('r1-compat-ready',cli+['run-code',"async page => { await page.goto('http://127.0.0.1:3195/lesson/demo-01?version=demo-01-v2&tab=quiz'); await page.getByRole('radio').first().waitFor(); return {ready:true}; }"],cwd=r.ROOT)
        result=r.record('r1-browser-quiz-compat',cli+['run-code',(r.ROOT/'scripts/phase10c2-quiz-ui.js').read_text()],cwd=r.ROOT)
        assert b'"passed":true' in result.stdout
        assert receipts(c,[f['eventId'] for f in fixture['fixtures']])==fixture['receiptSha256']
    finally:r.record('r1-compat-close',cli+['close'],cwd=r.ROOT)
if __name__=='__main__':
    action=sys.argv[1]
    if not action.startswith('_'):r.record('r1-'+action,[sys.executable,str(Path(__file__).resolve()),'_'+action],cwd=r.ROOT)
    else:{'_seed':seed,'_browser':browser,'_compat':compat}[action]()
