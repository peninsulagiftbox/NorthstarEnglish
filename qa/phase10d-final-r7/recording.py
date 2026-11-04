#!/usr/bin/env python3
"""Upload and read a synthetic browser recording on the guarded R7 source."""

import base64
import datetime
import hashlib
import json
import urllib.request
import uuid

from run import q, OUT, PRIVATE


def main():
    source = PRIVATE / "synthetic/original-qa.webm"
    data = source.read_bytes()
    assert len(data) > 32 and data[:4] == bytes.fromhex("1a45dfa3")
    sentence, lesson, version = q.sql(
        "SELECT id,lesson_id,lesson_version_id FROM sentence WHERE lesson_id='demo-01' ORDER BY sequence_no LIMIT 1",
        label="r7-recording-sentence").split("\t")
    event = str(uuid.uuid4())
    payload = {"eventId": event, "lessonId": lesson, "versionId": version,
               "sentenceId": sentence, "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "mimeType": "audio/webm;codecs=opus", "durationMs": 900,
               "audioBase64": base64.b64encode(data).decode()}
    app = q.start_api()
    try:
        status, receipt = q.request("/recordings", payload)
        assert status == 200, (status, receipt)
        recording_id = receipt["id"]
        request = urllib.request.Request(q.API + "/recordings/" + recording_id + "/audio")
        with urllib.request.urlopen(request, timeout=20) as response:
            read = response.read()
            assert response.status == 200 and response.headers["Content-Type"].startswith("audio/webm")
        assert data == read
        row = q.sql("SELECT id,lesson_id,version_id,sentence_id,event_id,byte_size,sha256,status "
                    f"FROM personal_recording WHERE id='{recording_id}'", label="r7-recording-db-row")
        assert recording_id in row and "ready" in row and hashlib.sha256(data).hexdigest() in row
        result = {"status": "PASS", "recordingId": recording_id, "eventId": event,
                  "lessonId": lesson, "versionId": version, "sentenceId": sentence,
                  "byteSize": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                  "databaseUuid": q.identity()["uuid"], "apiReadMatches": True,
                  "mediaGenerator": "Chromium MediaRecorder, 440 Hz original test tone"}
        (OUT / "r7-recording-source.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
    finally:
        q.stop(app)


if __name__ == "__main__":
    main()
