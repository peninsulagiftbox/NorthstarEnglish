#!/usr/bin/env python3
"""Compare full synthetic review rows across two real API restarts."""

import json
import uuid

import b08_b09 as audit

q = audit.q
OUT = q.OUT


def main():
    card = audit.scalar(audit.CARD_SQL)
    old = audit.scalar("SELECT id FROM review_item WHERE id='cr-kp-3-reading'")
    assert old == "cr-kp-3-reading"
    old_row = int(audit.scalar(f"SELECT row_version FROM review_item WHERE id='{old}'"))
    old_event = str(uuid.uuid4())
    audit.q.sql(f"UPDATE review_item SET due_at=UTC_TIMESTAMP(3) WHERE id='{old}'",
                label="r6-b09-old-card-due")
    api = q.start_api()
    try:
        old_payload = {"eventId": old_event, "lessonId": "cr-a", "versionId": "cr-a-v1",
                       "sentenceId": "cr-a-v1-s3", "rowVersion": old_row,
                       "rating": "again", "answerRevealed": True,
                       "clientOccurredAt": "2026-11-03T00:00:00Z"}
        rated_old = audit.request("B09-old-sentence-rating", f"/reviews/{old}/results", old_payload)
        assert rated_old["status"] == 200, rated_old
        before = audit.snapshot("b09-before-restart-1")
        assert len(before["tables"]["concept_review_source"]) >= 3
        assert len(before["tables"]["concept_review_result"]) >= 2
        assert len(before["tables"]["review_result"]) >= 1
    finally:
        q.stop(api)

    api = q.start_api()
    try:
        after = audit.snapshot("b09-after-restart-1")
        assert before == after, "rows drifted after first API restart"
        replay_old = audit.request("B09-old-rating-replay", f"/reviews/{old}/results", old_payload)
        assert replay_old["status"] == 200 and replay_old["response"] == rated_old["response"]
        b08_events = json.loads((OUT / "r6-b08-http.json").read_text())
        prior = next(row for row in b08_events if row["case"] == "B08-07-lost-response")
        concept_replay = audit.request("B09-concept-rating-replay", prior["path"], prior["request"])
        assert concept_replay["status"] == 200 and concept_replay["response"] == prior["response"]
        after_replay = audit.snapshot("b09-after-replay")
        assert after == after_replay, "event replay mutated history"
        audit.due(card)
        row_version = int(audit.scalar(f"SELECT row_version FROM concept_review_card WHERE id='{card}'"))
        new_rating = audit.rating("B09-new-concept-rating", card, row_version)
        assert new_rating["status"] == 200, new_rating
        advanced = audit.snapshot("b09-before-restart-2")
        for table in ("review_item", "review_source", "review_result"):
            assert advanced["tables"][table] == after["tables"][table], table
    finally:
        q.stop(api)

    api = q.start_api()
    try:
        final = audit.snapshot("b09-after-restart-2")
        assert advanced == final, "rows drifted after second API restart"
        assert int(audit.scalar(f"SELECT row_version FROM concept_review_card WHERE id='{card}'")) == row_version + 1
        assert int(audit.scalar(f"SELECT COUNT(*) FROM concept_review_result WHERE card_id='{card}'")) == 4
        assert int(audit.scalar(f"SELECT COUNT(*) FROM review_result WHERE event_id='{old_event}'")) == 1
        (OUT / "r6-b09-result.json").write_text(json.dumps({
            "status": "PASS", "card": card, "oldSentenceItem": old,
            "beforeFirstRestartEqualsAfter": True, "replayMutatedHistory": False,
            "beforeSecondRestartEqualsAfter": True, "conceptRowVersion": row_version + 1,
            "conceptResultCount": 4, "oldReviewResultCount": 1,
            "http": audit.EVENTS}, ensure_ascii=False, indent=2) + "\n")
    finally:
        q.stop(api)


if __name__ == "__main__":
    main()
