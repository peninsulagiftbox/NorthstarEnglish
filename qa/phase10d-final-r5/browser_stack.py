import json
import socket
import subprocess
import time
import urllib.request
import uuid
from run import q


def main():
    api = q.start_api()
    web = None
    try:
        assert q.sql("SELECT COUNT(*) FROM concept_review_source") == "0"
        for index in range(83):
            lesson, version, exercise, option = ("cr-b", "cr-b-v1", "cr-read-2", "cr2-a") if index == 1 else ("cr-a", "cr-a-v1", "cr-read-1", "cr1-a")
            status, body = q.request("/reading/" + exercise + "/attempts", dict(eventId=str(uuid.uuid4()), lessonId=lesson, versionId=version, optionId=option, clientOccurredAt="2026-11-02T10:00:00Z"))
            assert status == 200, (status, body)
        for index in range(1, 22):
            sentence = "qa-r5-queue-v1-s" + str(index)
            status, body = q.request("/exercises/" + sentence + "-dictation/attempts", dict(eventId=str(uuid.uuid4()), lessonId="qa-r5-queue", versionId="qa-r5-queue-v1", sentenceId=sentence, text="wrong answer", audioPlayed=True, answerExposed=False, clientOccurredAt="2026-11-02T10:00:00Z"))
            assert status == 200, (status, body)
        q.sql("UPDATE lesson SET availability='withdrawn' WHERE id='cr-a'", label="withdraw-qa-course-a")
        card_id = q.sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin'")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", q.WEB_PORT))
        log = (q.PRIVATE / "web.log").open("wb")
        web = subprocess.Popen([q.NODE + "/node", str(q.ROOT / "node_modules/next/dist/bin/next"), "start", "--hostname", "127.0.0.1", "--port", str(q.WEB_PORT)], cwd=q.SOURCE / "apps/web", env=q.env(), stdout=log, stderr=subprocess.STDOUT)
        for attempt in range(100):
            assert web.poll() is None
            try:
                with urllib.request.urlopen(q.WEB + "/api/v1/health", timeout=2) as response:
                    if json.load(response).get("migrationVersion") == "012.11":
                        break
            except OSError:
                pass
            time.sleep(.3)
        else:
            raise RuntimeError("QA Web readiness timeout")
        q.save("browser-runtime.json", dict(root=str(q.ROOT), api=q.API, web=q.WEB, cardId=card_id, apiPid=api.pid, webPid=web.pid, jarSha256=q.JAR_SHA, buildId=(q.SOURCE / "apps/web/.next/BUILD_ID").read_text().strip(), database=q.identity()))
        q.run("browser", [q.NODE + "/node", q.TOOLS / "browser.cjs"], env=q.env(), timeout=240)
    finally:
        for table in ("concept_review_card", "concept_review_source", "concept_review_result", "command_receipt", "exercise_attempt", "attempt_knowledge", "review_item", "review_source", "review_result", "learning_evidence", "quiz_run", "flyway_schema_history"):
            q.sql("SELECT * FROM `" + table + "` ORDER BY 1", label="final-state-" + table)
        if web:
            q.stop(web)
        q.stop(api)
        q.save("stop-state.json", dict(apiExit=api.returncode, webExit=None if web is None else web.returncode))


if __name__ == "__main__":
    main()
