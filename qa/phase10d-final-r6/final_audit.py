#!/usr/bin/env python3
"""Read-only final R6 card, receipt and objective-attempt audit."""

import json

import run

q = run.q


def scalar(label, statement):
    return q.sql(statement, label="r6-final-" + label)


def main():
    identity = q.identity()
    assert scalar("uuid", "SELECT @@server_uuid") == identity["uuid"]
    card = scalar("card-id", "SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin'")
    data = {
        "candidateManifestSha256": json.loads((q.OUT / "candidate-identity-final.json").read_text())["completeManifestSha256"],
        "databaseUuid": identity["uuid"], "cardId": card,
        "cardCount": int(scalar("card-count", "SELECT COUNT(*) FROM concept_review_card WHERE concept_id='cr-bank-fin'")),
        "sourceCount": int(scalar("source-count", f"SELECT COUNT(*) FROM concept_review_source WHERE card_id='{card}'")),
        "distinctSourceCount": int(scalar("distinct-source", f"SELECT COUNT(DISTINCT CONCAT(attempt_id,':',occurrence_id)) FROM concept_review_source WHERE card_id='{card}'")),
        "resultCount": int(scalar("result-count", f"SELECT COUNT(*) FROM concept_review_result WHERE card_id='{card}'")),
        "missingReceiptCount": int(scalar("missing-receipts", "SELECT COUNT(*) FROM concept_review_result r LEFT JOIN command_receipt c ON c.event_id=r.event_id WHERE c.event_id IS NULL")),
        "objectiveAttemptCount": int(scalar("attempt-count", "SELECT COUNT(*) FROM exercise_attempt WHERE lesson_id IN ('cr-a','cr-b')")),
        "oldSentenceResultCount": int(scalar("old-sentence-results", "SELECT COUNT(*) FROM review_result WHERE item_id='cr-kp-3-reading'")),
        "schedule": scalar("schedule", f"SELECT row_version,reps,due_at FROM concept_review_card WHERE id='{card}'"),
        "flywayVersion": scalar("flyway-version", "SELECT version FROM flyway_schema_history WHERE success=1 ORDER BY installed_rank DESC LIMIT 1"),
    }
    assert data["cardCount"] == 1 and data["sourceCount"] == data["distinctSourceCount"] == 8
    assert data["resultCount"] == 5 and data["missingReceiptCount"] == 0
    assert data["objectiveAttemptCount"] == 8 and data["oldSentenceResultCount"] == 1
    assert data["flywayVersion"] == "012.11"
    data["status"] = "PASS"
    (q.OUT / "r6-final-db-audit.json").write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
