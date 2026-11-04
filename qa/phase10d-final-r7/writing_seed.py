#!/usr/bin/env python3
"""Create real synthetic Demo draft and immutable revision chain before final restore."""

import json
import urllib.request
import uuid

from run import q, OUT


def send(method, path, payload=None):
    request = urllib.request.Request(q.API + path, method=method,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Origin": q.WEB, "X-Northstar-Request": "local-workspace",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        assert response.status == 200
        return json.load(response)


def main():
    app = q.start_api()
    try:
        before = send("GET", "/writing?lessonId=demo-01&versionId=demo-01-v2")
        assert before["draft"]["rowVersion"] == 0 and not before["revisions"]
        first_text = "I can help in the garden. Please put the plants beside the bench."
        second_text = first_text + " I will bring water tomorrow."
        draft = {"lessonId": "demo-01", "versionId": "demo-01-v2", "text": first_text, "rowVersion": 0}
        assert send("PUT", "/writing/draft", draft)["rowVersion"] == 1
        first = send("POST", "/writing/revisions", {"eventId": str(uuid.uuid4()),
                     "lessonId": "demo-01", "versionId": "demo-01-v2", "text": first_text,
                     "draftVersion": 1})
        draft.update(text=second_text, rowVersion=1)
        assert send("PUT", "/writing/draft", draft)["rowVersion"] == 2
        second = send("POST", "/writing/revisions", {"eventId": str(uuid.uuid4()),
                      "lessonId": "demo-01", "versionId": "demo-01-v2", "text": second_text,
                      "draftVersion": 2, "parentRevisionId": first["id"]})
        after = send("GET", "/writing?lessonId=demo-01&versionId=demo-01-v2")
        assert after["draft"]["rowVersion"] == 2 and len(after["revisions"]) == 2
        assert after["revisions"][1]["parentRevisionId"] == first["id"]
        result = {"status": "PASS", "databaseUuid": q.identity()["uuid"],
                  "taskId": before["taskId"], "draftVersion": 2,
                  "revisionIds": [first["id"], second["id"]], "parentChainValid": True}
        (OUT / "r7-writing-source.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
    finally:
        q.stop(app)


if __name__ == "__main__":
    main()
