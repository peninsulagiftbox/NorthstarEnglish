#!/usr/bin/env python3
"""Exercise actual PDFKit and local Vision OCR, preserving candidates and failures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import content_source
import phase10e

r = phase10e.runner
out = r.OUT / "pdf"
out.mkdir(parents=True, exist_ok=True)
work = r.STATE / "pdf"
work.mkdir(parents=True, exist_ok=True)
helper = work / "extract"
r.record("pdf-helper-compile", ["swiftc", "-module-cache-path", str(work / "module-cache"),
         str(r.ROOT / "scripts/content_extract.swift"), "-o", str(helper)], cwd=r.ROOT)
r.record("pdf-fixtures", ["swift", "-module-cache-path", str(work / "module-cache"),
         str(r.ROOT / "scripts/phase10e/PdfFixtures.swift"), str(work / "fixtures")], cwd=r.ROOT)
os.environ["NORTHSTAR_PDF_HELPER"] = str(helper)
results = []
for name, method in [("text.pdf", "PDFKit.text"), ("scan.pdf", "Vision.OCR")]:
    candidate = content_source.extract(work / "fixtures", name)
    assert candidate["status"] == "unreviewed"
    assert candidate["extraction"]["pages"][0]["method"] == method
    assert "clock" in candidate["rawTranscript"].lower()
    assert candidate["extraction"]["pages"][0]["blocks"]
    (out / (name + ".candidate.json")).write_text(json.dumps(candidate, ensure_ascii=False, indent=2))
    results.append({"file": name, "method": method, "status": "PASS", "humanReview": "NOT VERIFIED"})
for name in ["encrypted.pdf", "over-limit.pdf"]:
    try:
        content_source.extract(work / "fixtures", name)
        raise AssertionError("Invalid PDF accepted")
    except ValueError as error:
        assert str(error) == "PDF_EXTRACTION_FAILED"
        results.append({"file": name, "status": "PASS", "rejected": str(error)})
for name in ["text.pdf", "scan.pdf", "scan.png", "original.txt"]:
    raw = (work / "fixtures" / name).read_bytes()
    (out / name).write_bytes(raw)
    results.append({"file": name, "sha256": hashlib.sha256(raw).hexdigest()})
(out / "result.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results))
