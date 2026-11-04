#!/usr/bin/env python3
"""Preflight failure checks against copied synthetic R7 backups."""

import datetime
import json
import shutil

from run import q, OUT, PRIVATE

import sys
sys.path.insert(0, str(q.ROOT / "qa/phase10d-final-r6"))
import restore as transfer


def main():
    valid = json.loads((OUT / "r7-data-transfer-result.json").read_text())
    original = __import__("pathlib").Path(valid["backup"])
    assert (original / "COMPLETE").is_file()
    api = q.start_api()
    results = {}
    try:
        for index, case in enumerate(("truncated", "checksum", "missing_media", "no_complete")):
            folder = PRIVATE / ("r7-backup-fault-" + case)
            assert not folder.exists()
            shutil.copytree(original, folder)
            snapshot = folder / "learning.json"
            if case == "truncated":
                data = snapshot.read_bytes()
                snapshot.write_bytes(data[:len(data) // 2])
            elif case == "checksum":
                envelope = json.loads(snapshot.read_text())
                envelope["payloadJson"] += " "
                snapshot.write_text(json.dumps(envelope))
            elif case == "missing_media":
                media = next((folder / "media").glob("*.audio"))
                media.unlink()
            else:
                (folder / "COMPLETE").unlink()
            target = "northstar_restore_" + (datetime.datetime.now(datetime.timezone.utc) +
                      datetime.timedelta(seconds=index + 4)).strftime("%Y%m%d%H%M%S")
            try:
                transfer.invoke("restore", snapshot, target)
                results[case] = {"rejected": False, "target": target}
            except SystemExit as failure:
                assert failure.code == 1
                results[case] = {"rejected": True, "target": target,
                                 "targetCreated": q.sql("SELECT COUNT(*) FROM information_schema.schemata "
                                      "WHERE schema_name='" + target + "'", label="r7-fault-target-" + case) != "0"}
            if case != "no_complete":
                assert results[case]["rejected"] and not results[case]["targetCreated"]
        (OUT / "r7-backup-faults-result.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps(results))
    finally:
        q.stop(api)


if __name__ == "__main__":
    main()
