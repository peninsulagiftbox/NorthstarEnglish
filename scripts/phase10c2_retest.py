#!/usr/bin/env python3
"""Repeatable acceptance gaps; writes only to the UUID-checked C2 test schema/new containers."""
import copy,hashlib,json,os,sys,time,uuid,urllib.request,urllib.error,shutil
from pathlib import Path
import phase10c2_isolated as iso
r=iso.r
FIXTURES=r.STATE/'retest-fixtures.json'
def sql(c,q,expected=(0,)):
    return c.sql('empty','USE northstar_phase01_test; SET NAMES utf8mb4; '+q,expected=expected,private=True).stdout.decode()
def lit(s):return "CONVERT(X'"+str(s).encode().hex()+"' USING utf8mb4)"
def seed():
    c=iso.campaign();iso.ensure_db(c,'empty');fixtures=[];tag=uuid.uuid4().hex[:8]
    tone=Path(iso.env(c,'empty')['NORTHSTAR_TEST_AUDIO']);content=r.STATE/'database/test-content'
    for count,lesson,number in [(5,'c2-'+tag+'-a',1),(12,'c2-'+tag+'-a',2),(100,'c2-'+tag+'-b',1)]:
        version=lesson+'-v'+str(number);setid=str(uuid.uuid4());pi=str(uuid.uuid4());si=str(uuid.uuid4())
        key='retest/'+version+'.mp3';(content/'retest').mkdir(exist_ok=True);shutil.copyfile(tone,content/key)
        payload=dict(id=lesson,versionId=version,title='Original quiz acceptance '+str(count),version=number,exercises=[],vocabulary=[])
        license={'id':version+'-license','sourceType':'original','sourceRef':'self-authored:isolated-quiz-retest:'+version,'reviewStatus':'confirmed','medium':'text and synthetic test tone'}
        q=['START TRANSACTION;']
        if number==1:q.append(f"INSERT INTO lesson(id,slug,kind,availability) VALUES ('{lesson}','{lesson}','original','available');")
        q += [f"INSERT INTO content_license(id,source_type,source_ref,review_status,details_json) VALUES ('{version}-license','original','self-authored:isolated-quiz-retest:{version}','confirmed',{lit(json.dumps(license))});",
          f"INSERT INTO lesson_version(id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,release_ready,publication_state) VALUES ('{version}','{lesson}',{number},'{version}-license',REPEAT('0',64),REPEAT('0',64),{lit(json.dumps(payload))},TRUE,'published');",
          f"INSERT INTO paragraph_identity(id,lesson_id,registry_key) VALUES ('{pi}','{lesson}','{pi}');",
          f"INSERT INTO paragraph(id,version_id,lesson_id,identity_id,stable_key,sequence_no) VALUES ('{version}-p','{version}','{lesson}','{pi}','p',1);",
          f"INSERT INTO sentence_identity(id,lesson_id,registry_key) VALUES ('{si}','{lesson}','{si}');",
          f"INSERT INTO audio_asset(id,lesson_version_id,license_id,source_kind,storage_key,mime_type,byte_size,duration_ms,sha256,status) VALUES ('{version}-a','{version}','{version}-license','original_recording','{key}','audio/mpeg',{tone.stat().st_size},2000,'{hashlib.sha256(tone.read_bytes()).hexdigest()}','ready');",
          f"INSERT INTO sentence(id,lesson_id,lesson_version_id,stable_key,sequence_no,speaker,text,translation,explanation,focus,audio_asset_id,start_ms,end_ms,paragraph_id,identity_id) VALUES ('{version}-s','{lesson}','{version}','s',1,'Writer','I write original questions.','原创测试句','本地预置讲解','original','{version}-a',0,2000,'{version}-p','{si}');",
          f"INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES ('{version}-kp','{lesson}','{version}','{version}-s','original','原创','本地预置讲解','Original quiz.');"]
        for n in range(1,count+1):
            ex=version+'-q'+str(n).zfill(3);question=dict(id=ex,prompt='Original question '+str(n),options=[dict(id=ex+'-a',text='Choice A '+str(n)),dict(id=ex+'-b',text='Choice B '+str(n))],answerKey=ex+'-a',explanation='本地预置讲解')
            q += [f"INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES ('{ex}','{lesson}','{version}','{version}-s','quiz_choice','quiz_choice_v1');",f"INSERT INTO quiz_question(exercise_id,version_id,sentence_id,knowledge_point_id,payload_json) VALUES ('{ex}','{version}','{version}-s','{version}-kp',{lit(json.dumps(question))});"]
        q += [f"INSERT INTO exercise_set(id,version_id,purpose,protocol_version,snapshot_origin) VALUES ('{setid}','{version}','practice','quiz_choice_v1','version_content');",
          f"INSERT INTO exercise_set_item(set_id,exercise_id,version_id,sentence_id,knowledge_point_id,ordinal,question_json,item_hash) SELECT '{setid}',exercise_id,version_id,sentence_id,knowledge_point_id,ROW_NUMBER() OVER(ORDER BY exercise_id),payload_json,SHA2(CONCAT(HEX(exercise_id),':',CAST(SUBSTRING_INDEX(exercise_id,'q',-1) AS UNSIGNED),':',HEX(sentence_id),':',HEX(knowledge_point_id),':',HEX(CAST(payload_json AS CHAR CHARACTER SET utf8mb4))),256) FROM quiz_question WHERE version_id='{version}';",
          f"SET SESSION group_concat_max_len=65535; UPDATE exercise_set SET set_hash=SHA2(CONCAT('quiz-set-v1:',HEX(version_id),':practice:quiz_choice_v1::',(SELECT GROUP_CONCAT(item_hash ORDER BY ordinal SEPARATOR '') FROM exercise_set_item WHERE set_id='{setid}')),256),frozen=TRUE WHERE id='{setid}';",
          f"UPDATE lesson SET current_version_id='{version}' WHERE id='{lesson}'; COMMIT;"]
        sql(c,'\n'.join(q));fixtures.append(dict(lessonId=lesson,versionId=version,total=count,setId=setid))
    FIXTURES.write_text(json.dumps(fixtures));print(json.dumps(dict(fixtures=fixtures)))
def api(path,body=None):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request('http://127.0.0.1:8175/api/v1'+path,data=data,headers={'Origin':'http://127.0.0.1:3195','X-Northstar-Request':'local-workspace','Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=30) as response:return response.status,json.load(response)
    except urllib.error.HTTPError as error:return error.code,json.load(error)
def api_gaps():
    c=iso.campaign();fixtures=json.loads(FIXTURES.read_text());f=fixtures[0];v=f['versionId'];lesson=f['lessonId']
    code,q=api(f'/quiz?lessonId={lesson}&versionId={v}');assert code==200
    body=dict(protocolVersion='quiz-submit-v2',eventId=str(uuid.uuid4()),lessonId=lesson,versionId=v,setId=q['setId'],setHash=q['setHash'],answers={x['id']:x['id']+'-a' for x in q['questions']},clientOccurredAt='2026-10-31T00:00:00Z')
    path='/quiz/sets/'+q['setId']+'/attempts'
    def counts():
        return {t:sql(c,f'SELECT COUNT(*) FROM {t};').strip() for t in ('quiz_run','quiz_run_item','quiz_answer','exercise_attempt','learning_evidence','command_receipt','review_source','quiz_progress')}
    tests=[]
    for label,patch,status in [('empty-answers',{'answers':{}},422),('cross-lesson',{'lessonId':fixtures[-1]['lessonId']},422),('cross-version',{'versionId':fixtures[1]['versionId']},422),('stale-hash',{'setHash':'0'*64},409),('invalid-choice',{'answers':{**body['answers'],q['questions'][0]['id']:'unknown'}},422)]:
        before=counts();actual,_=api(path,{**body,**patch,'eventId':str(uuid.uuid4())});assert actual==status,(label,actual);assert counts()==before;tests.append(label)
    before=counts();assert api('/quiz/sets/'+str(uuid.uuid4())+'/attempts',body)[0]==422;assert counts()==before;tests.append('path-body-set-mismatch')
    for change,restore,status,label in [(f"UPDATE lesson_version SET publication_state='withdrawn' WHERE id='{v}';",f"UPDATE lesson_version SET publication_state='published' WHERE id='{v}';",410,'withdrawn'),(f"UPDATE content_license SET review_status='pending_review' WHERE id='{v}-license';",f"UPDATE content_license SET review_status='confirmed' WHERE id='{v}-license';",409,'rights-unavailable')]:
        sql(c,change)
        try:
            before=counts();assert api(path,{**body,'eventId':str(uuid.uuid4())})[0]==status;assert counts()==before;tests.append(label)
        finally:sql(c,restore)
    # Constraint probes are rolled back and use the real relational guards.
    probeid=str(uuid.uuid4());sql(c,f"INSERT INTO exercise_set(id,version_id,purpose,protocol_version,snapshot_origin) VALUES ('{probeid}','demo-01-v1','practice','quiz_choice_v1','version_content');",expected=(1,))
    tests.append('one-default-set-per-version')
    status,report=api('/reports?lessonId='+lesson)
    assert status==200 and report['metrics']['quiz']['total']==34 and report['metrics']['quiz']['correct']==17
    assert report['metrics']['quiz']['accuracy']==0.5
    status,filtered=api('/reports?setId='+q['setId'])
    assert filtered['quizScope']['setId']==q['setId'] and filtered['metrics']['quiz']['total']==10
    for action in ('pause','skip'):
        assert api('/quiz/events',dict(eventId=str(uuid.uuid4()),lessonId=lesson,versionId=v,action=action,clientOccurredAt='2026-10-31T00:00:00Z'))[0]==200
    assert api('/reports?lessonId='+lesson)[1]['metrics']['quiz']==report['metrics']['quiz']
    assert api('/reports?lessonId='+lesson+'&from=2050-01-01T00:00:00Z')[1]['metrics']['quiz']['total']==0
    assert api('/reports?purpose=unknown')[0]==422
    tests += ['mixed-5-12-version-denominator','set-scope','pause-skip-excluded','empty-time-window','unsupported-purpose']
    print(json.dumps(dict(status='PASS',checks=tests)))
def browser():
    cli=['node','/Users/wangshiqi/.npm/_npx/31e32ef8478fbf80/node_modules/@playwright/cli/playwright-cli.js','--session=c2-retest']
    e=r.environment();out=r.OUT
    try:
        r.record('retest-browser-open',cli+['open','about:blank'],env=e,cwd=r.ROOT)
        script=(r.ROOT/'scripts/phase10c2-scale-ui.js').read_text().replace('__FIXTURES__',json.dumps(json.loads(FIXTURES.read_text())))
        p=r.record('retest-browser-scale',cli+['run-code',script],env=e,cwd=r.ROOT)
        assert b'"passed":true' in p.stdout,'CLI did not report successful acceptance'
    finally:r.record('retest-browser-close',cli+['close'],env=e,cwd=r.ROOT)
if __name__=='__main__':
    action=sys.argv[1]
    if not action.startswith('_'):
        r.record('retest-'+action,[sys.executable,str(Path(__file__).resolve()),'_'+action],cwd=r.ROOT)
    else:{'_seed':seed,'_api':api_gaps,'_browser':browser}[action]()
