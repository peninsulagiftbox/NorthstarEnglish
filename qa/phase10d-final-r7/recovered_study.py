#!/usr/bin/env python3
"""Prove restored R7 API can read old data, continue, replay, and restart."""

import hashlib
import json
import os
import urllib.request
import uuid

from independent_restore import TARGET, SCHEMA, mysql
from run import q, OUT, PRIVATE, sha

identity = json.loads((TARGET / "identity.json").read_text())
secret = json.loads((TARGET / "credentials.json").read_text())["root"]
original_env = q.env
q.API_PORT = 8203
q.WEB_PORT = 3210
q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
q.env = lambda: dict(original_env(), MYSQL_PORT=str(identity["port"]), DB_NAME=SCHEMA,
                     NORTHSTAR_EXPECTED_DB_UUID=identity["uuid"],
                     NORTHSTAR_CONTENT_ROOT=str(TARGET / "content"),
                     NORTHSTAR_RECORDING_ROOT=str(TARGET / "recordings"))

TABLES = ("attempt_knowledge", "concept_review_card", "concept_review_source",
          "concept_review_result", "command_receipt", "review_item", "review_source",
          "review_result", "quiz_run", "quiz_run_item", "writing_draft", "writing_revision",
          "personal_recording")


def snapshot():
    return {table: hashlib.sha256(mysql("SELECT * FROM `" + SCHEMA + "`.`" + table + "` ORDER BY 1;",
                                   identity, secret, table).encode()).hexdigest() for table in TABLES}


def request(path, payload=None):
    status, body = q.request(path, payload)
    assert status == 200, (path, status, body)
    return body


def main():
    recording = json.loads((OUT / "r7-recording-source.json").read_text())
    old = snapshot()
    app = q.start_api()
    try:
        lessons = request("/lessons")
        concepts = request("/knowledge/concepts")
        card = mysql("SELECT id FROM `" + SCHEMA + "`.concept_review_card WHERE concept_id='cr-bank-fin';",
                     identity, secret, "card")
        sources = request("/concept-reviews/" + card + "/sources?limit=20")
        assert len(sources["items"]) >= 8
        with urllib.request.urlopen(q.API + "/recordings/" + recording["recordingId"] + "/audio") as response:
            audio = response.read()
            assert response.status == 200 and hashlib.sha256(audio).hexdigest() == recording["sha256"]
        event = str(uuid.uuid4())
        payload = {"eventId": event, "lessonId": "cr-b", "versionId": "cr-b-v1",
                   "optionId": "cr3-a", "clientOccurredAt": "2026-11-04T00:00:00Z"}
        first = request("/reading/cr-read-3/attempts", payload)
        replay = request("/reading/cr-read-3/attempts", payload)
        assert replay == first
        new = snapshot()
        assert old["quiz_run"] == new["quiz_run"] and old["quiz_run_item"] == new["quiz_run_item"]
        assert old["personal_recording"] == new["personal_recording"]
    finally:
        q.stop(app)
    app = q.start_api()
    try:
        restarted = snapshot()
        assert new == restarted
        assert request("/health")["migrationVersion"] == "012.11"
        with urllib.request.urlopen(q.API + "/recordings/" + recording["recordingId"] + "/audio") as response:
            assert hashlib.sha256(response.read()).hexdigest() == recording["sha256"]
    finally:
        q.stop(app)
    result = {"status": "PASS", "databaseUuid": identity["uuid"], "oldSources": len(sources["items"]),
              "oldRecordingSha256": recording["sha256"], "newEventId": event,
              "newAttemptId": first["attemptId"], "replaySameReceipt": True,
              "restartRowsEqual": True, "oldQuizUnchanged": True,
              "before": old, "after": new, "lessonsRead": len(lessons), "conceptsRead": len(concepts)}
    (OUT / "r7-recovered-study-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in {"before", "after"}}))


if __name__ == "__main__":
    main()
