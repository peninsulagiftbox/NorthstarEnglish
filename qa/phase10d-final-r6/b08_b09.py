#!/usr/bin/env python3
"""R6 isolated HTTP concurrency and restart audit; only synthetic fixture IDs."""

import concurrent.futures
import datetime
import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import run

q = run.q
OUT = q.OUT
CARD_SQL = "SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin' AND owner_key='local'"
TABLES = ("concept_review_card", "concept_review_source", "concept_review_result",
          "command_receipt", "attempt_knowledge", "review_item", "review_source", "review_result")
EVENTS = []


def event():
    return str(uuid.uuid4())


def request(label, path, payload=None):
    started = time.time_ns()
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(q.API + path, data=data,
        headers={"Content-Type": "application/json", "Origin": q.WEB,
                 "X-Northstar-Request": "local-workspace"})
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            status, body = response.status, json.load(response)
    except urllib.error.HTTPError as error:
        status, body = error.code, json.load(error)
    result = {"case": label, "path": path, "request": payload, "status": status,
              "response": body, "startNs": started, "endNs": time.time_ns()}
    EVENTS.append(result)
    return result


def reading(label, lesson="cr-a", version="cr-a-v1", exercise="cr-read-1",
            option="cr1-a", event_id=None):
    event_id = event_id or event()
    return request(label, f"/reading/{exercise}/attempts", {
        "eventId": event_id, "lessonId": lesson, "versionId": version,
        "optionId": option, "clientOccurredAt": datetime.datetime.now(datetime.timezone.utc).isoformat()})


def rating(label, card, version, event_id=None, value="good"):
    return request(label, f"/concept-reviews/{card}/results", {
        "eventId": event_id or event(), "rowVersion": version, "rating": value,
        "answerRevealed": True, "clientOccurredAt": "2026-11-01T00:00:00Z"})


def scalar(sql):
    return q.sql(sql, label="r6-sql-" + uuid.uuid4().hex[:12]).splitlines()[-1]


def snapshot(label):
    data = {"serverUuid": scalar("SELECT @@server_uuid"), "tables": {}}
    for table in TABLES:
        data["tables"][table] = q.sql(f"SELECT * FROM {table} ORDER BY 1",
                                       label="r6-snapshot-" + label + "-" + table + "-" + uuid.uuid4().hex[:6]).splitlines()
    (OUT / f"r6-{label}-snapshot.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return data


def race(case, jobs):
    barrier = threading.Barrier(len(jobs))
    def wrapped(job):
        barrier.wait(timeout=10)
        return job()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = [pool.submit(wrapped, job) for job in jobs]
        results = [future.result(timeout=45) for future in futures]
    overlap = max(result["startNs"] for result in results) < min(result["endNs"] for result in results)
    assert overlap, f"{case}: HTTP requests did not overlap"
    return results


def due(card):
    q.sql(f"UPDATE concept_review_card SET due_at=UTC_TIMESTAMP(3) WHERE id='{card}'",
          label="r6-set-fixture-due-" + uuid.uuid4().hex[:8])


def counts(card):
    return {name: int(scalar(f"SELECT COUNT(*) FROM {name} WHERE card_id='{card}'"))
            for name in ("concept_review_source", "concept_review_result")}


def main():
    app = q.start_api()
    try:
        assert reading("B08-baseline-A")["status"] == 200
        assert reading("B08-baseline-B", "cr-b", "cr-b-v1", "cr-read-2", "cr2-a")["status"] == 200
        card = scalar(CARD_SQL)
        assert counts(card)["concept_review_source"] == 2
        baseline = snapshot("b08-baseline")

        one = race("B08-01", [lambda: reading("B08-01-source"),
                                lambda: rating("B08-01-rating", card, 1)])
        assert sorted(item["status"] for item in one) == [200, 200]
        assert counts(card) == {"concept_review_source": 3, "concept_review_result": 1}

        due(card)
        two = race("B08-02", [lambda: rating("B08-02-left", card, 2),
                                lambda: rating("B08-02-right", card, 2)])
        assert sorted(item["status"] for item in two) == [200, 409]
        assert int(scalar(f"SELECT row_version FROM concept_review_card WHERE id='{card}'")) == 3

        same_event = event()
        same_payload = {"eventId": same_event, "lessonId": "cr-a", "versionId": "cr-a-v1",
                        "optionId": "cr1-a", "clientOccurredAt": "2026-11-03T00:00:00Z"}
        three = race("B08-03", [lambda: request("B08-03-left", "/reading/cr-read-1/attempts", same_payload),
                                  lambda: request("B08-03-right", "/reading/cr-read-1/attempts", same_payload)])
        assert [item["status"] for item in three] == [200, 200]
        assert three[0]["response"]["attemptId"] == three[1]["response"]["attemptId"]
        assert int(scalar(f"SELECT COUNT(*) FROM command_receipt WHERE event_id='{same_event}'")) == 1

        fourth_event = event()
        left = dict(same_payload, eventId=fourth_event)
        right = dict(left, optionId="cr1-c")
        four = race("B08-04", [lambda: request("B08-04-left", "/reading/cr-read-1/attempts", left),
                                 lambda: request("B08-04-right", "/reading/cr-read-1/attempts", right)])
        assert sorted(item["status"] for item in four) == [200, 409]

        five = race("B08-05", [lambda: reading("B08-05-source"),
                                 lambda: rating("B08-05-stale-rating", card, 2)])
        assert sorted(item["status"] for item in five) == [200, 409]
        assert reading("B08-06-source-after-rating")["status"] == 200

        due(card)
        lost_event = event()
        first = rating("B08-07-lost-response", card, 3, lost_event)
        assert first["status"] == 200
        replay = rating("B08-07-retry", card, 3, lost_event)
        assert replay["status"] == 200 and replay["response"] == first["response"]
        assert int(scalar(f"SELECT COUNT(*) FROM concept_review_result WHERE event_id='{lost_event}'")) == 1

        fault_event = event()
        q.sql("CREATE TRIGGER r6_fail_receipt BEFORE INSERT ON command_receipt FOR EACH ROW "
              "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='R6 injected precommit fault'",
              label="r6-inject-precommit-trigger")
        try:
            failed = reading("B08-08-injected-failure", event_id=fault_event)
            assert failed["status"] >= 400
            assert int(scalar(f"SELECT COUNT(*) FROM exercise_attempt WHERE event_id='{fault_event}'")) == 0
            assert int(scalar(f"SELECT COUNT(*) FROM command_receipt WHERE event_id='{fault_event}'")) == 0
        finally:
            q.sql("DROP TRIGGER r6_fail_receipt", label="r6-remove-precommit-trigger")
        retried = reading("B08-08-retry", event_id=fault_event)
        assert retried["status"] == 200
        assert int(scalar(f"SELECT COUNT(*) FROM command_receipt WHERE event_id='{fault_event}'")) == 1

        after = snapshot("b08-after")
        assert baseline["serverUuid"] == after["serverUuid"]
        assert int(scalar(f"SELECT COUNT(*) FROM concept_review_card WHERE concept_id='cr-bank-fin'")) == 1
        assert int(scalar(f"SELECT COUNT(*) FROM concept_review_source WHERE card_id='{card}'")) == 8
        assert int(scalar(f"SELECT COUNT(*) FROM concept_review_source WHERE card_id='{card}'")) == int(scalar(
            f"SELECT COUNT(DISTINCT CONCAT(attempt_id,':',occurrence_id)) FROM concept_review_source WHERE card_id='{card}'"))
        assert int(scalar(f"SELECT row_version FROM concept_review_card WHERE id='{card}'")) == 4
        assert int(scalar(f"SELECT COUNT(*) FROM concept_review_result WHERE card_id='{card}'")) == 3
        (OUT / "r6-b08-result.json").write_text(json.dumps({"status": "PASS", "card": card,
            "sourceCount": 8, "resultCount": 3, "rowVersion": 4, "http": EVENTS}, ensure_ascii=False, indent=2) + "\n")
    finally:
        q.stop(app)
        (OUT / "r6-b08-http.json").write_text(json.dumps(EVENTS, ensure_ascii=False, indent=2) + "\n")


def finalize():
    events = json.loads((OUT / "r6-b08-http.json").read_text())
    card = scalar(CARD_SQL)
    expected = {row["response"]["attemptId"] for row in events
                if row["status"] == 200 and row["response"].get("result", {}).get("correct") is False}
    actual = set(q.sql(f"SELECT attempt_id FROM concept_review_source WHERE card_id='{card}' ORDER BY attempt_id",
                       label="r6-final-source-ids").splitlines())
    assert len(expected) == 8 and actual == expected
    assert int(scalar(f"SELECT COUNT(*) FROM concept_review_result WHERE card_id='{card}'")) == 3
    assert int(scalar(f"SELECT row_version FROM concept_review_card WHERE id='{card}'")) == 4
    assert int(scalar(f"SELECT reps FROM concept_review_card WHERE id='{card}'")) == 3
    result = {"status": "PASS", "card": card, "sourceCount": len(actual),
              "resultCount": 3, "rowVersion": 4, "attemptIdsMatchSources": True,
              "firstRunHarnessFailure": "expected 7 sources; 8 real wrong attempts succeeded",
              "http": events}
    (OUT / "r6-b08-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("B08 data assertions PASS, 8 sources, 3 ratings")


if __name__ == "__main__":
    {"run": main, "finalize": finalize}[__import__("sys").argv[1] if len(__import__("sys").argv) > 1 else "run"]()
