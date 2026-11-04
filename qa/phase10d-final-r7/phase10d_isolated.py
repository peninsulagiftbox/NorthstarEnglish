#!/usr/bin/env python3
"""Expose the R7 source container to scripts/data-transfer.py --phase10d in a subprocess."""
import importlib.util
import os
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("r7_run", TOOLS / "run.py")
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)
q = run.q


class Campaign:
    PRIVATE = q.PRIVATE

    def verify(self, role):
        assert role == "."
        assert q.sql("SELECT @@server_uuid", label="r7-transfer-uuid") == q.identity()["uuid"]
        return q.identity()

    def sql(self, role, query, readonly=False):
        assert role == "." and readonly
        return q.sql(query, label="r7-transfer-identity")


def campaign():
    return Campaign()


def env(campaign, role, schema):
    assert role == "." and schema == "northstar_phase01_test"
    return dict(os.environ, MYSQL_ROOT_PASSWORD=q.credentials()["root"],
                API_PORT=str(q.API_PORT), WEB_PORT=str(q.WEB_PORT))


class _R:
    STATE = q.PRIVATE


r = _R()
