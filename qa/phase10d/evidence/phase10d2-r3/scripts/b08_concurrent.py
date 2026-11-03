#!/usr/bin/env python3
"""QA-EXEC R3 D02-B08 driver: real HTTP concurrency on the isolated QA stack.
Flow: card with 2 sources -> concurrent (wrong-attempt source append + CAS rating)
-> replay same eventId -> stale rowVersion. Asserts DB state, prints a timeline."""
import json, os, subprocess, sys, threading, time, urllib.request, uuid

API="http://127.0.0.1:8177/api/v1"
MYSQL_PORT="3350"
HEADERS={"Content-Type":"application/json","Origin":"http://127.0.0.1:3197","X-Northstar-Request":"local-workspace"}
timeline=[]

def log(msg):
    timeline.append("%s %s"%(time.strftime("%H:%M:%S.%f")[:-3],msg)); print(timeline[-1],flush=True)

def sql(query,schema="northstar_phase01_test"):
    env=dict(os.environ,MYSQL_PWD=json.load(open("/Users/wangshiqi/.codex/worktrees/worktree-10d-d02-qa/NorthstarEnglish/.local/qa-r3/credentials.json"))["app"])
    return subprocess.run(["/usr/local/mysql/bin/mysql","--protocol=TCP","-h127.0.0.1","-P"+MYSQL_PORT,
        "-unorthstar_app","--database="+schema,"-Nse",query],capture_output=True,text=True,env=env)

def post(path,body):
    req=urllib.request.Request(API+path,data=json.dumps(body).encode(),headers=HEADERS,method="POST")
    try:
        with urllib.request.urlopen(req,timeout=30) as r: return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code,json.loads(e.read())

def card():
    row=sql("SELECT id,row_version,reps,CAST(UNIX_TIMESTAMP(due_at) AS SIGNED),status FROM concept_review_card WHERE concept_id='cr-bank-fin' AND owner_key='local'").stdout
    lines=[l.split("\t") for l in row.strip().splitlines() if l]
    assert len(lines)==1,("card must be unique",lines)
    cid,rv,reps,due,status=lines[0]; return cid,int(rv),int(reps),int(due),status

def counts():
    cid,_,_,_,_=card()
    q=("SELECT (SELECT COUNT(*) FROM concept_review_source WHERE card_id='"+cid+"'),"
       "(SELECT COUNT(*) FROM concept_review_result WHERE card_id='"+cid+"'),"
       "(SELECT COUNT(*) FROM command_receipt WHERE event_id IN (SELECT event_id FROM exercise_attempt UNION SELECT event_id FROM concept_review_result)),"
       "(SELECT COUNT(*) FROM exercise_attempt),"
       "(SELECT COUNT(*) FROM attempt_knowledge ak JOIN exercise_attempt a ON a.id=ak.attempt_id JOIN concept_review_source s ON s.attempt_id=a.id),"
       "(SELECT COUNT(*) FROM quiz_run)")
    vals=sql(q).stdout.split()
    sources,results,receipts,attempts,linked,quiz=map(int,vals)
    orphans=sql("SELECT COUNT(*) FROM concept_review_result r LEFT JOIN concept_review_card c ON c.id=r.card_id WHERE c.id IS NULL").stdout.strip()
    return dict(sources=sources,results=results,receipts=receipts,attempts=attempts,linked=linked,quiz=quiz,orphans=int(orphans))

def attempt(event):
    t0=time.time()
    code,body=post("/reading/cr-read-1/attempts",{"eventId":event,"lessonId":"cr-a","versionId":"cr-a-v1","optionId":"cr1-a","clientOccurredAt":"2026-11-01T00:00:00Z"})
    log("attempt %s -> %s (%.0f ms)"%(event[:8],code,(time.time()-t0)*1000)); return code,body

def rating(event,rv):
    t0=time.time()
    code,body=post("/concept-reviews/%s/results"%card()[0],{"eventId":event,"rowVersion":rv,"rating":"good","answerRevealed":True,"clientOccurredAt":"2026-11-01T00:00:00Z"})
    log("rating %s rv=%d -> %s (%.0f ms)"%(event[:8],rv,code,(time.time()-t0)*1000)); return code,body

def cleanup():
    env=dict(os.environ,MYSQL_PWD=json.load(open("/Users/wangshiqi/.codex/worktrees/worktree-10d-d02-qa/NorthstarEnglish/.local/qa-r3/credentials.json"))["app"])
    r=subprocess.run(["/usr/local/mysql/bin/mysql","--protocol=TCP","-h127.0.0.1","-P"+MYSQL_PORT,
        "-unorthstar_app"],stdin=open("/private/tmp/qa-r3/cleanup-cr.sql"),capture_output=True,text=True,env=env)
    assert r.returncode==0,r.stderr

def main():
    assert sql("SELECT 1").returncode==0,"DB unreachable"
    cleanup()
    # Phase 1: sequential real attempts -> card with 2 sources.
    a1=attempt(str(uuid.uuid4()))
    assert a1[0]==200,a1
    a2body=post("/reading/cr-read-2/attempts",{"eventId":str(uuid.uuid4()),"lessonId":"cr-b","versionId":"cr-b-v1","optionId":"cr2-a","clientOccurredAt":"2026-11-01T00:00:00Z"})
    assert a2body[0]==200,a2body
    sql("UPDATE concept_review_card SET due_at=UTC_TIMESTAMP(3) WHERE concept_id='cr-bank-fin' AND owner_key='local'")
    cid,v0,reps,due,status=card()
    assert (v0,reps)==(1,0),(v0,reps)
    before=counts(); assert before["sources"]==2 and before["results"]==0,before
    log("BEFORE %s card=%s rv=%d"%(json.dumps(before,sort_keys=True),cid,v0))

    # Phase 2: concurrent source append + CAS rating on the same card.
    ev_source,ev_rating=str(uuid.uuid4()),str(uuid.uuid4())
    barrier=threading.Barrier(2); out={}
    def run_source():
        barrier.wait(); out["source"]=attempt(ev_source)
    def run_rating():
        barrier.wait(); out["rating"]=rating(ev_rating,v0)
    t1,t2=threading.Thread(target=run_source),threading.Thread(target=run_rating)
    t1.start(); t2.start(); t1.join(); t2.join()
    assert out["source"][0]==200,out
    assert out["rating"][0]==200,out["CAS rating must succeed once"]

    # Phase 3: replay same eventId; then stale rowVersion.
    replay=attempt(ev_source); assert replay[0]==200 and replay[1].get("attemptId")==out["source"][1].get("attemptId"),replay
    stale=rating(str(uuid.uuid4()),v0); assert stale[0]==409,stale

    # Phase 4: DB assertions.
    cid,rv1,reps1,due1,status=card()
    after=counts(); log("AFTER %s rv=%d reps=%d due=%d"%(json.dumps(after,sort_keys=True),rv1,reps1,due1))
    ok=True
    def check(name,cond,detail):
        nonlocal ok
        log(("PASS " if cond else "FAIL ")+name+" "+detail); ok=ok and cond
    check("card-unique",len(sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin'").stdout.split())==1,"")
    check("sources-kept",after["sources"]==3,str(after))
    check("no-dup-source",sql("SELECT COUNT(*) FROM (SELECT attempt_id,occurrence_id,exercise_id,version_id,concept_id,COUNT(*) n FROM concept_review_source GROUP BY 1,2,3,4,5 HAVING n>1) x").stdout.strip()=="0","")
    check("row-version",rv1==v0+1,"rv %d -> %d"%(v0,rv1))
    check("reps",reps1==reps+1,"reps %d -> %d"%(reps,reps1))
    check("single-result",after["results"]==1,str(after))
    check("no-orphan-result",after["orphans"]==0,"")
    check("receipts",after["receipts"]==before["receipts"]+2,"+%d receipts for 2 new commands"%(after["receipts"]-before["receipts"]))
    check("attempts",after["attempts"]==before["attempts"]+1,"rating must not create attempts")
    check("objective-quiz-unchanged",after["quiz"]==before["quiz"],"")
    check("sources-linked",after["linked"]==after["sources"],"every source links a real attempt")
    print("B08_RESULT="+("PASS" if ok else "FAIL"))
    open("/private/tmp/qa-r3/b08-timeline.txt","w").write("\n".join(timeline)+"\n")
    sys.exit(0 if ok else 1)

main()
