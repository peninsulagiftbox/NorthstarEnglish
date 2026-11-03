import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from run import q


def preserve():
    history = q.OUT / "history"
    history.mkdir(exist_ok=True)
    for name in ("10D_D02_QA_R4_FINAL.md", "10D_FINAL_ACCEPTANCE.md"):
        destination = history / name
        assert not destination.exists()
        shutil.copy2(q.ROOT / "docs/qa/phase10d" / name, destination)
    original = q.ROOT / "output/review/northstar-phase10d-final-qa-sanitized-evidence.zip"
    archived = q.ROOT / "output/review/northstar-phase10d-r4-archived-evidence.zip"
    assert not archived.exists()
    shutil.copy2(original, archived)
    assert q.sha(original) == q.sha(archived)
    Path(str(archived) + ".sha256").write_text(q.sha(archived) + "  " + archived.name + "\n")
    q.save("r4-archive.json", dict(originalSha256=q.sha(original), archive=str(archived.relative_to(q.ROOT)), archiveSha256=q.sha(archived)))
    manifest_path = q.OUT / "qa-final-candidate-manifest.sha256"
    initial = manifest_path.read_text()
    (q.OUT / "candidate-at-test-start.sha256").write_text(initial)
    initial_files = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in initial.splitlines()}
    binding = {}
    for name, checksum in initial_files.items():
        binding[name] = dict(expected=checksum, current=q.sha(q.ROOT / name), testedCopy=q.sha(q.SOURCE / name))
        assert len(set(binding[name].values())) == 1, name
    additions = {}
    for name in ("queue_recheck.cjs", "queue_recheck.py", "closeout.py"):
        relative = "qa/phase10d-final-r5/" + name
        additions[relative] = q.sha(q.TOOLS / name)
        shutil.copy2(q.TOOLS / name, q.SOURCE / relative)
    final = {**initial_files, **additions}
    manifest_path.write_text("".join(checksum + "  " + name + "\n" for name, checksum in sorted(final.items())))
    q.save("candidate-binding-final.json", dict(
        initialManifestSha256=hashlib.sha256(initial.encode()).hexdigest(),
        finalManifestSha256=q.sha(manifest_path), finalCount=len(final),
        unchangedInitialInputs=binding, addedQaTools=additions,
        reason="Only read-only defect confirmation and closeout tools added; no original candidate byte changed.",
        fixtureCopies={name: q.sha(q.SOURCE / "apps/api/src/test/java/local/northstar/knowledge" / name) for name in ("FinalQaFixture.java", "QueueQaFixture.java")},
    ))
    q.sql("SELECT version,description,checksum,success FROM flyway_schema_history ORDER BY installed_rank", label="final-flyway-history")
    q.sql("SELECT COUNT(*),COUNT(DISTINCT attempt_id),COUNT(DISTINCT card_id) FROM concept_review_source; SELECT COUNT(*) FROM concept_review_card; SELECT COUNT(*) FROM concept_review_result; SELECT COUNT(*) FROM command_receipt; SELECT COUNT(*) FROM knowledge_occurrence WHERE location_guard IS NOT NULL", label="final-counts")
    q.run("failure-db-logical-dump", [q.DOCKER, "exec", q.identity()["containerId"], "sh", "-c", 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --no-tablespaces --set-gtid-purged=OFF ' + q.SCHEMA])
    dump = q.PRIVATE / "failure-db-logical-dump.log"
    (q.OUT / "failure-db-logical-dump.log").rename(dump)
    q.save("private-dump-identity.json", dict(path=str(dump), sha256=q.sha(dump), includedInEvidence=False, restoreTest=False))
    q.run("qa-ports-after-stop", ["/usr/sbin/lsof", "-nP", "-iTCP:8192", "-iTCP:3199", "-sTCP:LISTEN"], check=False)
    q.run("retained-qa-container", [q.DOCKER, "inspect", "--format", '{"id":{{json .Id}},"running":{{json .State.Running}},"mounts":{{json .Mounts}}}', q.identity()["containerId"]])
    q.save("launch-failures.json", [{
        "command": "python3 qa/phase10d-final-r5/run.py create",
        "exitCode": 1, "reason": "Sandbox denied loopback binding; port search exhausted at assert port<=3399.",
        "resolution": "Approved rerun outside sandbox created a new QA container on 3382; no prior database was adopted."
    }])
    print("PRESERVED", len(final), q.sha(manifest_path), flush=True)


def package():
    files = {}
    for line in (q.OUT / "qa-final-candidate-manifest.sha256").read_text().splitlines():
        checksum, name = line.split("  ", 1)
        path = q.ROOT / name
        assert q.sha(path) == checksum, name
        if name.startswith(".local/") or path.suffix.lower() in (".mp3", ".wav", ".ogg", ".opus", ".m4a", ".webm", ".png", ".jpg", ".jpeg", ".zip", ".jar"):
            continue
        files["source/" + name] = path
    for path in q.OUT.iterdir():
        if path.is_file() and path.suffix in (".log", ".json", ".jsonl", ".sha256"):
            assert "dump" not in path.name or path.name == "private-dump-identity.json"
            files["evidence/" + path.name] = path
    for path in (q.OUT / "history").glob("*.md"):
        files["history/" + path.name] = path
    for name in ("sources-fixed.png", "queue-header.png", "concept-queue-only.png", "concept-queue-only.txt", "browser-trace.zip", "queue-recheck-trace.zip"):
        files["playwright/" + name] = q.ROOT / "output/playwright/phase10d-final-r5" / name
    for name in ("10D_D02_QA_R5_FINAL.md", "10D_D02_QA_R4_FINAL.md", "10D_FINAL_ACCEPTANCE.md"):
        files["docs/" + name] = q.ROOT / "docs/qa/phase10d" / name
    files["docs/PHASE_10D_QA_R5.md"] = q.ROOT / "docs/progress/PHASE_10D_QA_R5.md"
    secrets = list(q.credentials().values())
    sums = {}
    bundle = q.ROOT / "output/review/northstar-phase10d-final-qa-sanitized-evidence.zip"
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            assert not any(part in (".env", "credentials.json", "learning.json") for part in Path(name).parts)
            data = path.read_bytes()
            assert not any(secret.encode() in data for secret in secrets), name
            if path.suffix == ".zip":
                with zipfile.ZipFile(path) as trace:
                    assert all(not any(secret.encode() in trace.read(member) for secret in secrets) for member in trace.namelist())
            archive.writestr(name, data)
            sums[name] = hashlib.sha256(data).hexdigest()
        archive.writestr("SHA256SUMS.json", json.dumps(sums, indent=2, sort_keys=True) + "\n")
        archive.writestr("verify.py", """import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent
files=json.loads((root/'SHA256SUMS.json').read_text())
bad=[name for name,checksum in files.items() if not (root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=checksum]
if bad:raise SystemExit('FAIL '+str(bad))
print('PASS',len(files),'allowlisted files')
""")
    Path(str(bundle) + ".sha256").write_text(q.sha(bundle) + "  " + bundle.name + "\n")
    with tempfile.TemporaryDirectory(prefix="northstar-r5-verify-") as directory:
        with zipfile.ZipFile(bundle) as archive:
            archive.extractall(directory)
        q.run("bundle-independent-verification", [sys.executable, Path(directory) / "verify.py"])
    print("BUNDLE", len(files), q.sha(bundle), flush=True)


if __name__ == "__main__":
    {"preserve": preserve, "package": package}[sys.argv[1]]()
