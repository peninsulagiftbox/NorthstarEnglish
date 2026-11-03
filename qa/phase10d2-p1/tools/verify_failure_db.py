#!/usr/bin/env python3
"""Read-only pagination, field-pruning and audio checks on the preserved 3364 failure DB."""
import hashlib,json,sys
import qa_runtime as q
cid='f87999e5-8838-4981-b2a2-c616c5d3eb96'
allowed={'attemptId','occurrenceId','lessonId','versionId','recordedAt','visible','restricted'}
def snapshot():
    out={}
    for table in q.db('SHOW TABLES').split():
        cols=q.db("SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE table_schema=DATABASE() AND table_name='%s' AND constraint_name='PRIMARY' ORDER BY ordinal_position"%table).split()
        order=' ORDER BY '+','.join('`'+c+'`' for c in cols) if cols else ''
        out[table]=hashlib.sha256(q.db('SELECT * FROM `'+table+'`'+order).encode()).hexdigest()
    return out
before=snapshot();responses={}
expected=set(q.db('SELECT CONCAT(attempt_id,\':\',occurrence_id) FROM concept_review_source WHERE card_id=\''+cid+'\'').split())
for size in [None,1,20,83,100]:
    seen=set();cursor=None;pages=[]
    while True:
        path='/concept-reviews/'+cid+'/sources?'+('limit='+str(size)+'&' if size else '')
        if cursor:path+='cursor='+cursor
        status,body=q.request(path);assert status==200,(status,body)
        pages.append(body)
        for source in body['items']:
            key=source['attemptId']+':'+source['occurrenceId'];assert key not in seen;seen.add(key)
            if source['restricted']:assert set(source)<=allowed and source['visible'] is False
        next_cursor=body['nextCursor']
        if next_cursor is None:break
        assert cursor is None or next_cursor>cursor
        cursor=next_cursor
    assert expected==seen,(size,len(expected),len(seen))
    responses[str(size)]={'status':200,'page_count':len(pages),'sources':len(seen),'pages':pages}
status,card=q.request('/concept-reviews/'+cid);assert status==200 and card['visibleSourceCount']==1
status,audio=q.request('/audio/cr-a-v1-a1');assert status in (403,404,410),status
status,lesson=q.request('/lessons/cr-a?version=cr-a-v1');assert status in (403,404,410),status
after=snapshot();assert before==after,'read checks changed database'
(q.OUT/'failure-db-read-checks.json').write_text(json.dumps({'identity':q.state(),'version':q.db('SELECT VERSION()'),'pagination':responses,'card':card,'audio_status':audio,'lesson_status':lesson,'before_sha256_by_table':before,'after_sha256_by_table':after,'database_unchanged':True,'result':'PASS'},ensure_ascii=False,indent=2))
print('PASS preserved 3364: all pagination, restricted fields, aggregate, audio/lesson denial; all table hashes unchanged')
