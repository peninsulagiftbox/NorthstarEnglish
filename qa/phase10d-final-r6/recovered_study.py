#!/usr/bin/env python3
"""Continue learning on the restored R6 schema, then restart and compare rows."""

import json
import uuid
from pathlib import Path

import b08_b09 as audit

q = audit.q
OUT = q.OUT
restore = json.loads((OUT / "r6-restore-result.json").read_text())
target = restore["targetSchema"]
q.API_PORT = 8199
q.WEB_PORT = 3206
q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
original_env = q.env
q.env = lambda: dict(original_env(), DB_NAME=target, NORTHSTAR_ALLOW_RESTORE_DB="true")
TABLES = ("concept_review_card", "concept_review_source", "concept_review_result",
          "command_receipt", "attempt_knowledge", "review_item", "review_source", "review_result")


def snapshot(label):
    return {table: q.sql(f"SELECT * FROM `{table}` ORDER BY 1", schema=target,
                         label="r6-recovered-" + label + "-" + table)
            for table in TABLES}


def main():
    api = q.start_api()
    try:
        lessons = audit.request("M-recovered-lessons", "/lessons")
        concepts = audit.request("M-recovered-concepts", "/knowledge/concepts")
        old_card = audit.scalar("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin'")
        sources = audit.request("M-recovered-sources", f"/concept-reviews/{old_card}/sources?limit=20")
        assert lessons["status"] == concepts["status"] == sources["status"] == 200
        assert len(sources["response"]["items"]) == 8
        before = snapshot("before-new")
        attempt = audit.reading("M-recovered-new-wrong-attempt", "cr-b", "cr-b-v1", "cr-read-3", "cr3-a")
        assert attempt["status"] == 200 and attempt["response"]["result"]["correct"] is False
        river = q.sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-riv'", schema=target,
                      label="r6-recovered-new-card-id")
        assert river
        rated = audit.rating("M-recovered-new-rating", river, 1)
        assert rated["status"] == 200, rated
        replay = audit.rating("M-recovered-rating-replay", river, 1,
                              rated["request"]["eventId"])
        assert replay["status"] == 200 and replay["response"] == rated["response"]
        after = snapshot("after-new")
        for table in ("review_item", "review_source", "review_result"):
            assert set(before[table].splitlines()) <= set(after[table].splitlines()), table
    finally:
        q.stop(api)

    api = q.start_api()
    try:
        restarted = snapshot("after-restart")
        assert after == restarted
        assert audit.request("M-recovered-health", "/health")["response"]["migrationVersion"] == "012.11"
        (OUT / "r6-recovered-study-result.json").write_text(json.dumps({
            "status": "PASS", "targetSchema": target, "oldSources": 8,
            "newAttemptId": attempt["response"]["attemptId"],
            "newCardId": river, "newRatingEvent": rated["request"]["eventId"],
            "replayAddedResult": False, "restartRowsEqual": True,
            "oldSentenceRowsEqual": True,
            "beforeTableSha256": {name: __import__("hashlib").sha256(value.encode()).hexdigest()
                                     for name, value in before.items()},
            "afterTableSha256": {name: __import__("hashlib").sha256(value.encode()).hexdigest()
                                    for name, value in after.items()},
            "http": audit.EVENTS}, ensure_ascii=False, indent=2) + "\n")
    finally:
        q.stop(api)


def finalize():
    def old_log(table):
        matches = list(OUT.glob("*-r6-recovered-before-new-" + table + ".log"))
        assert len(matches) == 1, (table, len(matches))
        return matches[0].read_text().split("\nSTDERR\n", 1)[0].strip().splitlines()[1:]

    before = {table: old_log(table) for table in TABLES}
    after = snapshot("finalize-before-restart")
    for table in ("review_item", "review_source", "review_result"):
        assert set(before[table]) <= set(after[table].splitlines()), table
    river = q.sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-riv'", schema=target,
                  label="r6-recovered-final-card-id")
    rating_event = q.sql(f"SELECT event_id FROM concept_review_result WHERE card_id='{river}'", schema=target,
                         label="r6-recovered-final-rating-event")
    assert rating_event
    api = q.start_api()
    try:
        replay = audit.rating("M-recovered-final-replay", river, 1, rating_event)
        assert replay["status"] == 200, replay
        assert after == snapshot("finalize-after-replay")
    finally:
        q.stop(api)
    api = q.start_api()
    try:
        restarted = snapshot("finalize-after-restart")
        assert after == restarted
        health = audit.request("M-recovered-final-health", "/health")
        assert health["status"] == 200 and health["response"]["migrationVersion"] == "012.11"
        (OUT / "r6-recovered-study-result.json").write_text(json.dumps({
            "status": "PASS", "targetSchema": target, "newCardId": river,
            "ratingEvent": rating_event, "replayAddedResult": False,
            "restartRowsEqual": True, "oldSentenceRowsEqual": True,
            "newSentenceRowsExpected": True,
            "firstRunHarnessFailure": "whole review_item equality rejected a legitimate new sentence card",
            "afterTableSha256": {name: __import__("hashlib").sha256(value.encode()).hexdigest()
                                    for name, value in after.items()},
            "http": audit.EVENTS}, ensure_ascii=False, indent=2) + "\n")
    finally:
        q.stop(api)


if __name__ == "__main__":
    {"run": main, "finalize": finalize}[__import__("sys").argv[1] if len(__import__("sys").argv) > 1 else "run"]()
