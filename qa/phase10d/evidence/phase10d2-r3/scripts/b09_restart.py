#!/usr/bin/env python3
"""QA-EXEC R3 D02-B09: value-level persistence across an API restart + idempotent replay.
Manages only the QA API process on port 8177 (never the personal services)."""
import json, os, subprocess, sys, time, urllib.request, uuid

API="http://127.0.0.1:8177/api/v1"
CREDS="/Users/wangshiqi/.codex/worktrees/worktree-10d-d02-qa/NorthstarEnglish/.local/qa-r3/credentials.json"
HEADERS={"Content-Type":"application/json","Origin":"http://127.0.0.1:3197","X-Northstar-Request":"local-workspace"}
JAR="/Users/wangshiqi/Project/NorthstarEnglish/apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar"
JDK="/Users/wangshiqi/Project/NorthstarEnglish/.local/jdk21/jdk-21.0.12.1+1/Contents/Home/bin/java"

def creds(): return json.load(open(CREDS))
def app_env():
    c=creds(); qa=os.path.dirname(CREDS)
    return dict(os.environ, DB_NAME="northstar_phase01_test", MYSQL_PORT="3350", DB_PASSWORD=c["app"],
        DB_MIGRATION_PASSWORD=c["migrator"], NORTHSTAR_DB_TEST="1",
        NORTHSTAR_EXPECTED_DB_UUID="6b1d2208-d5ea-11f1-afc1-aecb2137fbec",
        NORTHSTAR_CONTENT_ROOT=qa+"/content", NORTHSTAR_RECORDING_ROOT=qa+"/recordings",
        API_PORT="8177", WEB_PORT="3197")
def sql(query):
    env=dict(os.environ,MYSQL_PWD=creds()["app"])
    return subprocess.run(["/usr/local/mysql/bin/mysql","--protocol=TCP","-h127.0.0.1","-P3350",
        "-unorthstar_app","--database=northstar_phase01_test","-Nse",query],capture_output=True,text=True,env=env).stdout
def health():
    try:
        with urllib.request.urlopen(API+"/health",timeout=2) as r: return json.loads(r.read())
    except Exception: return None
def wait_health():
    for _ in range(60):
        if health() and health().get("migrationVersion")=="012.11": return True
        time.sleep(1)
    return False
def stop_api():
    out=subprocess.run(["lsof","-nP","-iTCP:8177","-sTCP:LISTEN"],capture_output=True,text=True).stdout
    pids={l.split()[1] for l in out.splitlines()[1:] if l.strip()}
    assert pids,"no listener on 8177"
    for pid in pids:
        cmd=subprocess.run(["ps","-p",pid,"-o","command="],capture_output=True,text=True).stdout
        assert "northstar-api-0.1.0-SNAPSHOT.jar" in cmd,"refusing to stop a non-QA process: "+cmd
        subprocess.run(["kill",pid])
    for _ in range(30):
        if not subprocess.run(["lsof","-nP","-iTCP:8177","-sTCP:LISTEN"],capture_output=True,text=True).stdout.strip(): return
        time.sleep(1)
def start_api():
    subprocess.Popen([JDK,"-jar",JAR],env=app_env(),stdout=open("/private/tmp/qa-r3/api-b09.log","ab"),
        stderr=subprocess.STDOUT,start_new_session=True)
    assert wait_health(),"API did not become healthy"
def post(path,body):
    req=urllib.request.Request(API+path,data=json.dumps(body).encode(),headers=HEADERS,method="POST")
    try:
        with urllib.request.urlopen(req,timeout=30) as r: return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code,json.loads(e.read())

SNAP=("SELECT * FROM concept_review_card WHERE concept_id IN ('cr-bank-fin','cr-bank-riv') ORDER BY id;"
      "SELECT * FROM concept_review_source ORDER BY card_id,attempt_id,occurrence_id;"
      "SELECT * FROM concept_review_result ORDER BY event_id;"
      "SELECT event_id,payload_hash,response_json FROM command_receipt WHERE event_id IN "
      "(SELECT event_id FROM exercise_attempt UNION SELECT event_id FROM concept_review_result) ORDER BY event_id;"
      "SELECT id,due_at,reps,row_version,status,target_key FROM review_item ORDER BY id;"
      "SELECT * FROM review_result ORDER BY event_id")

def dump(tag):
    env=dict(os.environ,MYSQL_PWD=creds()["app"])
    r=subprocess.run(["/usr/local/mysql/bin/mysql","--protocol=TCP","-h127.0.0.1","-P3350",
        "-unorthstar_app","--database=northstar_phase01_test","-Nse",SNAP],capture_output=True,text=True,env=env)
    assert r.returncode==0,r.stderr
    open("/private/tmp/qa-r3/b09-%s.txt"%tag,"w").write(r.stdout)
    return r.stdout

def row(query):
    lines=sql(query).strip().splitlines(); assert lines,query
    return lines[0].split("\t")

def main():
    if not health(): start_api()
    ok=True
    s1=dump("before")
    # Replay both live commands across the restart with byte-identical payloads.
    ev,rating_prev,rating_due,rating_rv,client=row("SELECT event_id,rating,UNIX_TIMESTAMP(next_due_at),previous_row_version,client_occurred_at FROM concept_review_result ORDER BY recorded_at DESC,event_id LIMIT 1")
    body={"eventId":ev,"rowVersion":int(rating_rv),"rating":rating_prev,"answerRevealed":True,"clientOccurredAt":client}
    r1=post("/concept-reviews/%s/results"%sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin'").strip(),body)
    print("replay-rating",r1[0],r1[1].get("nextDueAt"),flush=True)
    ev2=row("SELECT event_id FROM exercise_attempt WHERE lesson_id='cr-a' ORDER BY recorded_at DESC LIMIT 1")[0]
    r2=post("/reading/cr-read-1/attempts",{"eventId":ev2,"lessonId":"cr-a","versionId":"cr-a-v1","optionId":"cr1-a","clientOccurredAt":"2026-11-01T00:00:00Z"})
    print("replay-attempt",r2[0],r2[1].get("attemptId"),flush=True)
    ok=ok and r1[0]==200 and r2[0]==200

    stop_api(); print("API stopped; restarting",flush=True)
    start_api(); print("API restarted healthy",flush=True)

    s2=dump("after")
    same=(s1==s2); print("SNAPSHOT_IDENTICAL="+str(same),flush=True); ok=ok and same
    if not same:
        import difflib
        open("/private/tmp/qa-r3/b09-diff.txt","w").write("".join(difflib.unified_diff(s1.splitlines(1),s2.splitlines(1))))
    # Post-restart replays must still be idempotent and create nothing new.
    s3=dump("postreplay-snapshot-before")
    r3=post("/concept-reviews/%s/results"%sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin'").strip(),body)
    r4=post("/reading/cr-read-1/attempts",{"eventId":ev2,"lessonId":"cr-a","versionId":"cr-a-v1","optionId":"cr1-a","clientOccurredAt":"2026-11-01T00:00:00Z"})
    s4=dump("after-replay")
    ident=(s3==s4); print("POSTREPLAY_IDENTICAL="+str(ident),flush=True)
    print("REPLAY_RESPONSES_STABLE="+str(r3[0]==200 and r4[0]==200),flush=True)
    ok=ok and ident and r3[0]==200 and r4[0]==200
    print("B09_RESULT="+("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)

main()
