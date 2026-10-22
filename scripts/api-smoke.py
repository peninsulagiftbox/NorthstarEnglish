#!/usr/bin/env python3
"""Read-only contract checks against the real loopback API."""
import json
import urllib.error
import urllib.request
import uuid
import local

env = local.environment()
base = "http://127.0.0.1:" + env["API_PORT"] + "/api/v1"


def request(path, status=200, method="GET", headers=None):
    try:
        response = urllib.request.urlopen(urllib.request.Request(base + path, method=method, headers=headers or {}), timeout=8)
    except urllib.error.HTTPError as error:
        response = error
    assert response.code == status, (path, response.code, status)
    assert response.headers.get("Access-Control-Allow-Origin") is None
    body = json.load(response)
    if status != 200:
        assert "application/problem+json" in response.headers.get("Content-Type", "")
        assert body["status"] == status and isinstance(body["retryable"], bool)
        uuid.UUID(body["traceId"])
    return body, response.headers


health, headers = request("/health")
assert health["status"] == health["database"] == "UP"
assert health["project"] == local.IDENTITY and "no-store" in headers["Cache-Control"]
capabilities, _ = request("/capabilities")
assert capabilities == dict(phase="04", contentApiAvailable=True, learningContentAvailable=True, aiEnabled=False, asrEnabled=False, pronunciationScoringEnabled=False)
settings, headers = request("/settings")
assert set(settings) == {"timezone", "defaultSpeed", "showTranslation", "showHints", "shortcutEnabled", "recordingRetention", "rowVersion"}
assert isinstance(settings["showTranslation"], bool) and "no-store" in headers["Cache-Control"]
request("/missing", 404)
request("/settings", 405, method="POST", headers={"Origin": "http://127.0.0.1:" + env["WEB_PORT"], "X-Northstar-Request": "local-workspace", "Content-Type": "application/json"})
request("/health", 403, headers={"Origin": "https://untrusted.example"})
request("/health", 403, headers={"Host": "untrusted.example"})
print("PASS: actual health/capabilities/settings; cache headers; 404/405/403 Problem contract; Host/Origin rejection; no CORS wildcard")
