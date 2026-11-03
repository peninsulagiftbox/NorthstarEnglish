#!/usr/bin/env python3
"""Own only newly spawned QA API/Web processes; retain synthetic failure state."""
import json, os, subprocess, time, uuid
import run as q

api=q.start_api(); web=None
try:
    rows=q.sql("SELECT COUNT(*) FROM concept_review_source").strip()
    assert rows=='0','refuse to reseed a nonempty QA source fixture'
    events=[]
    for n in range(83):
        lesson,version,exercise,option=('cr-b','cr-b-v1','cr-read-2','cr2-a') if n==1 else ('cr-a','cr-a-v1','cr-read-1','cr1-a')
        event=str(uuid.uuid4())
        status,body=q.request('/reading/'+exercise+'/attempts',dict(eventId=event,lessonId=lesson,versionId=version,optionId=option,clientOccurredAt='2026-11-02T10:00:00Z'))
        assert status==200,(status,body)
        events.append({'eventId':event,'attemptId':body.get('attemptId'),'lessonId':lesson})
    card=q.sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin'").strip()
    q.save('83-source-fixture.json',dict(cardId=card,events=events,sources=q.sql("SELECT card_id,attempt_id,occurrence_id,exercise_id,version_id,concept_id FROM concept_review_source ORDER BY attempt_id,occurrence_id")))
    q.sql("UPDATE lesson SET availability='withdrawn' WHERE id='cr-a'",label='withdraw-original-qa-course-a')
    with __import__('socket').socket() as s:s.bind(('127.0.0.1',q.WEB_PORT))
    log=(q.PRIVATE/'web.log').open('wb')
    web=subprocess.Popen([q.NODE+'/node',str(q.ROOT/'node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port',str(q.WEB_PORT)],cwd=q.SOURCE/'apps/web',env=q.env(),stdout=log,stderr=subprocess.STDOUT)
    for _ in range(100):
        assert web.poll() is None,'QA web exited'
        try:
            with __import__('urllib.request',fromlist=['urlopen']).urlopen(q.WEB+'/review',timeout=2) as r:
                if r.status==200:break
        except OSError:pass
        time.sleep(.3)
    else:raise RuntimeError('web readiness timeout')
    q.save('browser-runtime.json',dict(apiPid=api.pid,webPid=web.pid,api=q.API,web=q.WEB,jarSha256=q.JAR_SHA,buildId=(q.SOURCE/'apps/web/.next/BUILD_ID').read_text().strip(),database=q.identity(),cardId=card))
    print('BROWSER_READY',card,flush=True)
    for _ in range(1800):
        if (q.PRIVATE/'stop-browser').exists():break
        assert api.poll() is None and web.poll() is None
        time.sleep(1)
finally:
    if web:q.stop(web)
    q.stop(api)
    print('OWNED_CHILDREN_STOPPED',flush=True)
