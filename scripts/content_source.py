#!/usr/bin/env python3
"""Offline source inventory and append-only human proofreading records."""
import argparse
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unicodedata

MAX_BYTES = 64 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def transcript(texts):
    return ("\n".join(unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
                      .strip(" \t\n") for text in texts) + "\n").encode("utf-8")


def checked(root, name):
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or "\\" in name or "%" in name:
        raise ValueError("PATH_OUTSIDE_ROOT")
    target = (root / relative).resolve(strict=True)
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError("PATH_OUTSIDE_ROOT")
    if target.stat().st_size > MAX_BYTES:
        raise ValueError("SOURCE_TOO_LARGE")
    return target


def inspect(root, name):
    path = checked(root, name)
    raw = path.read_bytes()
    extension = path.suffix.lower()
    if extension == ".pdf" and raw.startswith(b"%PDF-"):
        kind = "pdf"
    elif extension == ".mp3" and (raw.startswith(b"ID3") or
                                (len(raw) > 2 and raw[0] == 255 and raw[1] & 224 == 224)):
        kind = "mp3"
    elif extension in {".txt", ".json"}:
        text = raw.decode("utf-8")
        if text.startswith("\ufeff") or "\x00" in text:
            raise ValueError("ENCODING_INVALID")
        if extension == ".json":
            json.loads(text)
        kind = extension[1:]
    else:
        raise ValueError("FILE_TYPE_MISMATCH")
    return {"sourceId": digest(raw), "sourceRef": name, "originalFilename": path.name,
            "byteSize": len(raw), "sha256": digest(raw), "inputType": kind,
            "rightsStatus": "pending_review", "rightsScope": None, "reviewer": None,
            "reviewedAt": None, "expiresAt": None, "lessonId": None}


def extract(root, name):
    source = inspect(root, name)
    path = checked(root, name)
    if source["inputType"] == "pdf":
        helper = os.environ.get("NORTHSTAR_PDF_HELPER")
        if not helper or not Path(helper).is_file():
            raise ValueError("PDF_HELPER_REQUIRED")
        result = subprocess.run([helper, str(path)], capture_output=True, timeout=120)
        if result.returncode:
            raise ValueError("PDF_EXTRACTION_FAILED")
        extracted = json.loads(result.stdout)
    elif source["inputType"] in {"txt", "json"}:
        extracted = {"tool": "python-utf8", "toolVersion": sys.version.split()[0],
                     "pages": [{"page": 1, "rawText": path.read_text(encoding="utf-8"),
                                "status": "needs_review", "blocks": []}]}
    else:
        extracted = {"tool": "inventory-only", "pages": [],
                     "status": "transcription_required"}
    raw = "\n".join(page["rawText"] for page in extracted["pages"])
    return {"source": source, "extraction": extracted, "rawTranscript": raw,
            "correctedTranscript": raw, "status": "unreviewed", "revision": 0,
            "sourceSha256": source["sha256"], "correctedSha256": digest(raw.encode()),
            "reviewer": None, "reviewedAt": None, "audit": []}


def review(candidate, corrected, reviewer, summary, status):
    if not reviewer.strip() or not summary.strip():
        raise ValueError("REVIEWER_AND_SUMMARY_REQUIRED")
    result = dict(candidate)
    revision = candidate["revision"] + 1
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    audit = {"revision": revision, "reviewer": reviewer, "reviewedAt": now,
             "summary": summary, "status": status,
             "previousSha256": candidate["correctedSha256"],
             "correctedSha256": digest(corrected.encode()),
             "diff": "".join(difflib.unified_diff(
                 candidate["correctedTranscript"].splitlines(True), corrected.splitlines(True),
                 fromfile="previous", tofile="corrected"))}
    result.update(correctedTranscript=corrected, correctedSha256=audit["correctedSha256"],
                  reviewer=reviewer, reviewedAt=now, revision=revision, status=status,
                  audit=candidate["audit"] + [audit])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["inspect", "extract", "review"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--corrected")
    parser.add_argument("--reviewer")
    parser.add_argument("--summary")
    parser.add_argument("--status", choices=["in_review", "confirmed", "rejected"], default="in_review")
    args = parser.parse_args()
    if args.command == "review":
        if not all((args.corrected, args.reviewer, args.summary)):
            parser.error("review requires --corrected --reviewer --summary")
        candidate = json.loads(checked(args.root, args.input).read_text())
        result = review(candidate, checked(args.root, args.corrected).read_text(encoding="utf-8"),
                        args.reviewer, args.summary, args.status)
    else:
        result = (inspect if args.command == "inspect" else extract)(args.root, args.input)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write("\n")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"code": str(error) if isinstance(error, ValueError) else type(error).__name__,
                          "path": "/input", "severity": "error",
                          "message": "来源提取或校对失败", "suggestion": "检查受限根、文件格式、工具和校对参数。"}))
        sys.exit(2)
