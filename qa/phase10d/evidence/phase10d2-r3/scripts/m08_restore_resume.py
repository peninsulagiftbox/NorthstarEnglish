#!/usr/bin/env python3
"""QA-EXEC R3 D02-M08: real continued learning on the restored schema, idempotent
replay, restart, and value-level snapshot comparison. API port 8178 (QA-owned only)."""
import json, os, subprocess, sys, time, urllib.request, uuid

API = "http://127.0.0.1:8178/api/v1"
CREDS = "/Users/wangshiqi/.codex/worktrees/worktree-10d-d02-qa/NorthstarEnglish/.local/qa-r3/credentials.json"
SCHEMA = "northstar_restore_20261101202000"
RESTORE_UUID = "ac693853-d5ee-11f1-8540-3267e5db2ba0"
JAR = "/Users/wangshiqi/Project/NorthstarEnglish/apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar"
JDK = "/Users/wangshiqi/Project/NorthstarEnglish/.local/jdk21/jdk-21.0.12.1+1/Contents/Home/bin/java"
HEADERS = {"Content-Type": "application/json", "Origin": "http://127.0.0.1:3198",
           "X-Northstar-Request": "local-workspace"}

def creds(): return json.load(open(CREDS))

def app_env():
    c = creds(); qa = os.path.dirname(CREDS)
    return dict(os.environ, DB_NAME=SCHEMA, MYSQL_PORT="3351", DB_PASSWORD=c["app"],
        DB_MIGRATION_PASSWORD=c["migrator"], NORTHSTAR_DB_TEST="1",
        NORTHSTAR_EXPECTED_DB_UUID=RESTORE_UUID,
        NORTHSTAR_ALLOW_RESTORE_DB="true",
        NORTHSTAR_CONTENT_ROOT=qa + "/content", NORTHSTAR_RECORDING_ROOT=qa + "/recordings-restore",
        API_PORT="8178", WEB_PORT="3198")

def sql(query):
    env = dict(os.environ, MYSQL_PWD=creds()["app"])
    return subprocess.run(["/usr/local/mysql/bin/mysql", "--protocol=TCP", "-h127.0.0.1", "-P3351",
        "-unorthstar_app", "--database=" + SCHEMA, "-Nse", query], capture_output=True, text=True, env=env)

def post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())

def health():
    try:
        with urllib.request.urlopen(API + "/health", timeout=2) as r: return json.loads(r.read())
    except Exception: return None

def wait_health():
    for _ in range(60):
        h = health()
        if h and h.get("migrationVersion") == "012.11": return True
        time.sleep(1)
    return False

def stop_api():
    out = subprocess.run(["lsof", "-nP", "-iTCP:8178", "-sTCP:LISTEN"], capture_output=True, text=True).stdout
    pids = {l.split()[1] for l in out.splitlines()[1:] if l.strip()}
    if not pids: return
    for pid in pids:
        cmd = subprocess.run(["ps", "-p", pid, "-o", "command="], capture_output=True, text=True).stdout
        assert "northstar-api-0.1.0-SNAPSHOT.jar" in cmd, "refusing to stop a non-QA process: " + cmd
        subprocess.run(["kill", pid])
    for _ in range(30):
        if not subprocess.run(["lsof", "-nP", "-iTCP:8178", "-sTCP:LISTEN"], capture_output=True, text=True).stdout.strip(): return
        time.sleep(1)

def start_api():
    subprocess.Popen([JDK, "-jar", JAR], env=app_env(), stdout=open("/private/tmp/qa-r3/api-m08.log", "ab"),
        stderr=subprocess.STDOUT, start_new_session=True)
    assert wait_health(), "API did not become healthy on 8178"

def snap():
    q = ("SELECT * FROM concept_review_card ORDER BY id;"
         "SELECT * FROM concept_review_source ORDER BY card_id,attempt_id,occurrence_id;"
         "SELECT * FROM concept_review_result ORDER BY event_id;"
         "SELECT event_id,payload_hash,response_json FROM command_receipt ORDER BY event_id;"
         "SELECT id,due_at,reps,row_version,status FROM review_item ORDER BY id;"
         "SELECT * FROM review_result ORDER BY event_id;"
         "SELECT id,event_id FROM exercise_attempt ORDER BY id")
    r = sql(q); assert r.returncode == 0, r.stderr
    return r.stdout

def main():
    print("BASELINE sources=%s cards=%s attempts=%s" % (
        sql("SELECT COUNT(*) FROM concept_review_source").stdout.strip(),
        sql("SELECT COUNT(*) FROM concept_review_card").stdout.strip(),
        sql("SELECT COUNT(*) FROM exercise_attempt").stdout.strip()), flush=True)
    start_api()
    print("API healthy on 8178", flush=True)
    cid = sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin' AND owner_key='local'").stdout.strip()
    assert cid, "card missing"
    ev_new, ev_riv = str(uuid.uuid4()), str(uuid.uuid4())
    # 1. idempotent replay of a restored attempt (same eventId, same payload).
    r_replay = post("/reading/cr-read-1/attempts", {"eventId": "37468976-adf3-48d6-9e8a-c80b8c3220b2",
        "lessonId": "cr-a", "versionId": "cr-a-v1", "optionId": "cr1-a", "clientOccurredAt": "2026-11-01T00:00:00Z"})
    print("replay-restored-attempt", r_replay[0], flush=True)
    # 2. new wrong attempt on bank (source append) on restored card.
    r_bank = post("/reading/cr-read-1/attempts", {"eventId": ev_new, "lessonId": "cr-a", "versionId": "cr-a-v1",
        "optionId": "cr1-a", "clientOccurredAt": "2026-11-01T00:00:00Z"})
    print("new-bank-attempt", r_bank[0], r_bank[1].get("attemptId"), flush=True)
    # 3. new wrong attempt on river concept -> NEW card must be created on the restored target.
    r_riv = post("/reading/cr-read-3/attempts", {"eventId": ev_riv, "lessonId": "cr-b", "versionId": "cr-b-v1",
        "optionId": "cr3-a", "clientOccurredAt": "2026-11-01T00:00:00Z"})
    print("new-river-attempt", r_riv[0], r_riv[1].get("attemptId"), flush=True)
    # 4. replay the new bank attempt (same eventId).
    r_new_replay = post("/reading/cr-read-1/attempts", {"eventId": ev_new, "lessonId": "cr-a", "versionId": "cr-a-v1",
        "optionId": "cr1-a", "clientOccurredAt": "2026-11-01T00:00:00Z"})
    print("replay-new-attempt", r_new_replay[0], r_new_replay[1].get("attemptId") == r_bank[1].get("attemptId"), flush=True)
    # 5. replay the new river attempt.
    r_riv_replay = post("/reading/cr-read-3/attempts", {"eventId": ev_riv, "lessonId": "cr-b", "versionId": "cr-b-v1",
        "optionId": "cr3-a", "clientOccurredAt": "2026-11-01T00:00:00Z"})
    print("replay-river-attempt", r_riv_replay[0], r_riv_replay[1].get("attemptId") == r_riv[1].get("attemptId"), flush=True)
    ok = all(x[0] == 200 for x in (r_replay, r_bank, r_riv, r_new_replay, r_riv_replay))
    assert ok, "some requests failed"
    src = sql("SELECT COUNT(*) FROM concept_review_source").stdout.strip()
    cards = sql("SELECT COUNT(*) FROM concept_review_card").stdout.strip()
    attempts = sql("SELECT COUNT(*) FROM exercise_attempt").stdout.strip()
    print("AFTER sources=%s cards=%s attempts=%s" % (src, cards, attempts), flush=True)
    check = (src == "5" and cards == "2" and attempts == "5")
    print("CONTINUE_WRITES=" + ("PASS" if check else "FAIL"), flush=True)
    s0 = snap()
    stop_api(); print("API stopped; restarting", flush=True)
    start_api()
    s1 = snap()
    print("SNAPSHOT_IDENTICAL=" + str(s0 == s1), flush=True)
    if s0 != s1:
        import difflib
        open("/private/tmp/qa-r3/m08-snapshot-diff.txt", "w").write(
            "".join(difflib.unified_diff(s0.splitlines(1), s1.splitlines(1))))
    # post-restart replay: must add nothing new.
    r_replay2 = post("/reading/cr-read-1/attempts", {"eventId": ev_new, "lessonId": "cr-a", "versionId": "cr-a-v1",
        "optionId": "cr1-a", "clientOccurredAt": "2026-11-01T00:00:00Z"})
    r_riv_replay2 = post("/reading/cr-read-3/attempts", {"eventId": ev_riv, "lessonId": "cr-b", "versionId": "cr-b-v1",
        "optionId": "cr3-a", "clientOccurredAt": "2026-11-01T00:00:00Z"})
    s2 = snap()
    print("POSTREPLAY_IDENTICAL=" + str(s1 == s2), flush=True)
    print("POSTREPLAY_STABLE=" + str(r_replay2[0] == 200 and r_riv_replay2[0] == 200), flush=True)
    verdict = check and s0 == s1 and s1 == s2 and r_replay2[0] == 200 and r_riv_replay2[0] == 200
    print("M08_RESULT=" + ("PASS" if verdict else "FAIL"))
    stop_api()
    sys.exit(0 if verdict else 1)

main()
