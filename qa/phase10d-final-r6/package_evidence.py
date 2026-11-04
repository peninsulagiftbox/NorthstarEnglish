#!/usr/bin/env python3
"""Package only the R6 synthetic QA record and reviewed source excerpts."""

import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "output/review/northstar-phase10d-r6-final-sanitized-evidence.zip"
REPORTS = [
    "docs/qa/phase10d/10D_D02_QA_R6_FINAL.md",
    "docs/qa/phase10d/10D_FINAL_ACCEPTANCE.md",
    "docs/progress/PHASE_10D_2_QA_R6.md",
]
SOURCE = [
    "apps/api/src/main/java/local/northstar/exercise/ConceptReviewController.java",
    "apps/api/src/main/java/local/northstar/knowledge/ConceptReviewSources.java",
    "apps/api/src/main/java/local/northstar/knowledge/KnowledgeRegistrationCli.java",
    "apps/api/src/test/java/local/northstar/knowledge/ConceptReviewIntegrationTest.java",
    "apps/api/src/test/java/local/northstar/knowledge/KnowledgeSourcesIntegrationTest.java",
    "apps/web/src/components/review/ConceptReviewQueue.tsx",
    "apps/web/src/components/review/ConceptReviewCard.tsx",
    "apps/web/src/lib/review/conceptQueue.ts",
    "apps/web/tests/conceptQueue.test.ts",
    "scripts/data-transfer.py", "docs/openapi.yaml",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def files():
    selected = {ROOT / name for name in REPORTS + SOURCE}
    selected.update((ROOT / "apps/api/src/main/resources/db/migration").glob("V012_*.sql"))
    qa = ROOT / "qa/phase10d-final-r6"
    selected.update(path for path in qa.rglob("*") if path.is_file()
                    and "__pycache__" not in path.parts and path.suffix in {".py", ".cjs", ".json", ".jsonl", ".log", ".sha256"})
    selected.update((ROOT / "output/playwright/phase10d-final-r6").glob("*.png"))
    return sorted(selected)


def main():
    if DEST.exists():
        raise RuntimeError("R6 evidence ZIP already exists; retain immutable delivery")
    selected = files()
    missing = [str(path) for path in selected if not path.is_file()]
    if missing:
        raise RuntimeError("missing evidence files: " + ", ".join(missing))
    credentials = []
    for name in (".local/qa-final-r6/credentials.json", ".local/qa-browser-r6/credentials.json"):
        values = json.loads((ROOT / name).read_text())
        credentials.extend(value.encode() for value in values.values())
    entries = {}
    for path in selected:
        name = str(path.relative_to(ROOT))
        if any(part in {".env", ".local", "node_modules", "target", ".next"} for part in path.parts):
            raise RuntimeError("unsafe path: " + name)
        data = path.read_bytes()
        if any(secret in data for secret in credentials):
            raise RuntimeError("R6 credential present in " + name)
        if path.name != "package_evidence.py" and path.suffix not in {".png", ".zip"} and re.search(rb"(?i)(authorization:\s*bearer\s+\S+|cookie:\s*\S+|sk-proj-[a-z0-9_-]{20,})", data):
            raise RuntimeError("credential-shaped text in " + name)
        entries[name] = data
    sums = "".join(f"{sha(data)}  {name}\n" for name, data in sorted(entries.items()))
    verifier = b'''#!/usr/bin/env python3
import hashlib,sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    expected={name:hash_value for hash_value,name in (line.split("  ",1) for line in archive.read("SHA256SUMS").decode().splitlines())}
    actual=set(archive.namelist())-{"SHA256SUMS","verify.py"}
    assert actual==set(expected),(len(actual),len(expected))
    for name,hash_value in expected.items():
        assert hashlib.sha256(archive.read(name)).hexdigest()==hash_value,name
    print("PASS",len(expected),"members")
'''
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DEST, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(entries.items()):
            archive.writestr(name, data)
        archive.writestr("SHA256SUMS", sums)
        archive.writestr("verify.py", verifier)
    with zipfile.ZipFile(DEST) as archive:
        assert set(archive.namelist()) == set(entries) | {"SHA256SUMS", "verify.py"}
        for name, data in entries.items():
            assert sha(archive.read(name)) == sha(data)
    sidecar = DEST.with_suffix(DEST.suffix + ".sha256")
    sidecar.write_text(f"{sha(DEST.read_bytes())}  {DEST.name}\n")
    print(json.dumps({"zip": str(DEST), "sha256": sha(DEST.read_bytes()),
                      "members": len(entries) + 2, "size": DEST.stat().st_size}))


if __name__ == "__main__":
    main()
