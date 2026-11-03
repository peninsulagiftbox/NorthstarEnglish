#!/usr/bin/env python3
"""16 concurrent HTTP writers, 10 rounds; replay every successful command."""
import concurrent.futures,datetime,json,time,uuid
import qa_runtime as q
out=q.OUT/'logs/concurrency.jsonl'
def save(x):
    with out.open('a') as f:f.write(json.dumps(x,ensure_ascii=False)+'\n')
def counts():
    return list(map(int,q.db("SELECT (SELECT COUNT(*) FROM concept_review_source),(SELECT COUNT(*) FROM concept_review_result),(SELECT COUNT(*) FROM command_receipt),(SELECT COUNT(*) FROM exercise_attempt),(SELECT COUNT(*) FROM quiz_run); ").split()))
def card():return q.db("SELECT id,row_version,reps FROM concept_review_card WHERE concept_id='cr-bank-fin' AND owner_key='local'").split()
def main():
    p=q.start_api()
    try:
        base=counts();cid,rv,reps=card();rv,reps=int(rv),int(reps)
        save({'before':base,'card':[cid,rv,reps],'identity':q.state()})
        for roundno in range(10):
            q.db("UPDATE concept_review_card SET due_at=UTC_TIMESTAMP(3) WHERE id='%s'"%cid)
            jobs=[]
            for i in range(16):
                body={'eventId':str(uuid.uuid4()),'clientOccurredAt':'2026-11-02T00:00:00Z'}
                if i<8:body.update(lessonId='cr-a',versionId='cr-a-v1',optionId='cr1-a');path='/reading/cr-read-1/attempts'
                else:body.update(rowVersion=rv,rating='good',answerRevealed=True);path='/concept-reviews/'+cid+'/results'
                jobs.append((path,body))
            import threading
            barrier=threading.Barrier(16)
            def run(job):
                barrier.wait();start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();status,response=q.request(*job)
                return dict(path=job[0],body=job[1],start=start,ms=round((time.monotonic()-t)*1000,2),status=status,response=response)
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:results=list(ex.map(run,jobs))
            for x in results:save(dict(round=roundno,**x))
            assert all(x['status']==200 for x in results[:8]),results[:8]
            assert [x['status'] for x in results[8:]].count(200)==1,results[8:]
            assert all(x['status'] in (200,409) for x in results[8:]),results[8:]
            for x in results:
                if x['status']==200:
                    status,response=q.request(x['path'],x['body']);assert status==200 and response==x['response']
            rv+=1;reps+=1;assert card()==[cid,str(rv),str(reps)]
            expected=[base[0]+8*(roundno+1),base[1]+roundno+1,base[2]+9*(roundno+1),base[3]+8*(roundno+1),base[4]]
            assert counts()==expected,(counts(),expected)
            checks=q.db("SELECT (SELECT COUNT(*) FROM (SELECT card_id,attempt_id,occurrence_id,COUNT(*) n FROM concept_review_source GROUP BY 1,2,3 HAVING n>1) d),(SELECT COUNT(*) FROM concept_review_result r LEFT JOIN concept_review_card c ON r.card_id=c.id WHERE c.id IS NULL),(SELECT COUNT(*) FROM concept_review_card WHERE concept_id='cr-bank-fin'),(SELECT COUNT(*) FROM concept_review_result r JOIN concept_review_card c ON c.id=r.card_id WHERE r.event_id=(SELECT event_id FROM concept_review_result ORDER BY recorded_at DESC LIMIT 1) AND r.next_due_at=c.due_at)")
            assert checks=='0\t0\t1\t1',checks
            save({'round':roundno,'after':counts(),'rv':rv,'reps':reps,'checks':checks});print('round',roundno,'PASS',flush=True)
        save({'result':'PASS','requests':160,'replays':90,'after':counts(),'exit_code':0})
    finally:q.stop(p)
if __name__=='__main__':main()
