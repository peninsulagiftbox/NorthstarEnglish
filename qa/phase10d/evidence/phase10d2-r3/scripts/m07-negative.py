#!/usr/bin/env python3
"""QA-EXEC R3 D02-M07: direct-SQL cross-concept / cross-version concept_review_source
negative cases. Each must be rejected by the five-column composite FK."""
import json, os, subprocess, sys

CREDS = "/Users/wangshiqi/.codex/worktrees/worktree-10d-d02-qa/NorthstarEnglish/.local/qa-r3/credentials.json"
PORT, SCHEMA = "3350", "northstar_phase01_test"
CARD = "f87999e5-8838-4981-b2a2-c616c5d3eb96"  # existing card for cr-bank-fin

def sql(q):
    c = json.load(open(CREDS))
    r = subprocess.run(["/usr/local/mysql/bin/mysql", "--protocol=TCP", "-h127.0.0.1", "-P" + PORT,
        "-N", "-s", "-unorthstar_app", "--database=" + SCHEMA],
        input=q, capture_output=True, text=True, env=dict(os.environ, MYSQL_PWD=c["app"]))
    return r.returncode, r.stdout.strip(), r.stderr.strip()

cases = [
    ("M07-N1-cross-concept", CARD,
     "INSERT INTO concept_review_source(card_id,attempt_id,occurrence_id,exercise_id,version_id,concept_id) "
     "VALUES ('%s','4d90eb92-fb7f-49af-9781-b84633cccced','cr-oc-riv','cr-read-2','cr-b-v1','cr-bank-riv');" % CARD,
     "1452"),
    ("M07-N2-cross-version", CARD,
     "INSERT INTO concept_review_source(card_id,attempt_id,occurrence_id,exercise_id,version_id,concept_id) "
     "VALUES ('%s','4d90eb92-fb7f-49af-9781-b84633cccced','cr-oc-bank-a','cr-read-1','cr-b-v1','cr-bank-fin');" % CARD,
     "1452"),
]
fails = []
for name, card, stmt, expect in cases:
    rc, out, err = sql(stmt)
    errno = ""
    for part in err.replace("'", "").split():
        if part.isdigit() and len(part) == 4: errno = part; break
    got = errno if rc else "SUCCESS(no-rejection)"
    status = "PASS" if rc and errno == expect else "FAIL"
    print("%s expect=%s got=%s rc=%d => %s" % (name, expect, got, rc, status))
    if status == "FAIL": fails.append(name)
# verify no new rows were inserted
rc, out, _ = sql("SELECT COUNT(*) FROM concept_review_source;")
print("source_count_after=%s (expected 3)" % out)
if out != "3": fails.append("count")
print("M07_RESULT=" + ("PASS" if not fails else "FAIL " + ",".join(fails)))
sys.exit(0 if not fails else 1)
