#!/usr/bin/env python3
"""Drop the client response after a real committed R6 rating, then replay."""

import http.client
import http.server
import json
import socket
import threading
import urllib.request
import uuid

import b08_b09 as audit

q = audit.q
OUT = q.OUT


def main():
    card = audit.scalar(audit.CARD_SQL)
    audit.due(card)
    version = int(audit.scalar(f"SELECT row_version FROM concept_review_card WHERE id='{card}'"))
    before = int(audit.scalar(f"SELECT COUNT(*) FROM concept_review_result WHERE card_id='{card}'"))
    event_id = str(uuid.uuid4())
    payload = {"eventId": event_id, "rowVersion": version, "rating": "good",
               "answerRevealed": True, "clientOccurredAt": "2026-11-01T00:00:00Z"}
    observed = {}
    api = q.start_api()
    try:
        class DropAfterCommit(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                upstream = urllib.request.Request(q.API + self.path, data=body,
                    headers={"Content-Type": "application/json", "Origin": q.WEB,
                             "X-Northstar-Request": "local-workspace"})
                with urllib.request.urlopen(upstream, timeout=20) as result:
                    observed["upstreamStatus"] = result.status
                    observed["upstreamResponse"] = json.load(result)
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()

            def log_message(self, fmt, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), DropAfterCommit)
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=20)
        try:
            connection.request("POST", f"/concept-reviews/{card}/results", json.dumps(payload),
                               {"Content-Type": "application/json"})
            try:
                connection.getresponse()
                raise AssertionError("response unexpectedly reached client")
            except http.client.RemoteDisconnected:
                observed["clientError"] = "RemoteDisconnected"
        finally:
            connection.close()
            thread.join(timeout=20)
            server.server_close()
        assert observed["upstreamStatus"] == 200
        assert int(audit.scalar(f"SELECT COUNT(*) FROM concept_review_result WHERE event_id='{event_id}'")) == 1
        retry = audit.request("B08-07-real-response-loss-retry", f"/concept-reviews/{card}/results", payload)
        assert retry["status"] == 200 and retry["response"] == observed["upstreamResponse"]
        assert int(audit.scalar(f"SELECT COUNT(*) FROM concept_review_result WHERE card_id='{card}'")) == before + 1
        assert int(audit.scalar(f"SELECT row_version FROM concept_review_card WHERE id='{card}'")) == version + 1
        (OUT / "r6-b08-07-response-loss.json").write_text(json.dumps({
            "status": "PASS", "cardId": card, "eventId": event_id,
            "beforeResultCount": before, "afterResultCount": before + 1,
            "beforeRowVersion": version, "afterRowVersion": version + 1,
            "proxyUpstreamStatus": observed["upstreamStatus"],
            "clientError": observed["clientError"], "retryStatus": retry["status"],
            "replayedExactReceipt": True}, indent=2) + "\n")
    finally:
        q.stop(api)


if __name__ == "__main__":
    main()
