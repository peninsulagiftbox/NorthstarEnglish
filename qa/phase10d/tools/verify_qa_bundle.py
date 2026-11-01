#!/usr/bin/env python3
"""Phase 10D-QA bundle self-check: validates fixture JSON and reports SHA-256 of QA artifacts.

Usage: python3 verify_qa_bundle.py [repo_root]
No network, no DB access; safe to run anywhere.
"""
import hashlib
import json
import sys
from pathlib import Path

REQUIRED_FIXTURES = ["concepts_course_a.json", "concepts_course_b.json", "canonical_key_matrix.json"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
    fixtures = root / "qa" / "phase10d" / "fixtures"
    failures = []
    for name in REQUIRED_FIXTURES:
        path = fixtures / name
        if not path.exists():
            failures.append(f"missing fixture {name}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as error:
            failures.append(f"invalid JSON {name}: {error}")
            continue
        if name == "canonical_key_matrix.json":
            for case in data["cases"]:
                if "input" not in case or not ("expected" in case or "error" in case):
                    failures.append(f"matrix case incomplete: {case.get('case')}")
        else:
            if not data.get("reviewer") or not data.get("versionId"):
                failures.append(f"{name}: reviewer/versionId required")
            for occ in data.get("occurrences", []):
                if occ.get("scope") not in ("lesson", "paragraph", "sentence"):
                    failures.append(f"{name}: bad scope {occ.get('id')}")
                if occ.get("scope") == "lesson" and (occ.get("paragraphId") or occ.get("sentenceId")):
                    failures.append(f"{name}: lesson scope must not bind paragraph/sentence ({occ.get('id')})")
                if occ.get("scope") == "sentence" and not occ.get("sentenceId"):
                    failures.append(f"{name}: sentence scope requires sentenceId ({occ.get('id')})")
            for ek in data.get("exerciseKnowledge", []):
                if ek.get("role") not in ("target", "support"):
                    failures.append(f"{name}: bad exerciseKnowledge role {ek.get('occurrenceId')}")
    print("QA bundle root:", root)
    for path in sorted((root / "qa" / "phase10d").rglob("*")):
        if path.is_file():
            print(f"{sha256(path)}  {path.relative_to(root)}")
    for path in sorted((root / "docs" / "qa" / "phase10d").rglob("*")):
        if path.is_file():
            print(f"{sha256(path)}  {path.relative_to(root)}")
    if failures:
        print("FAIL")
        for item in failures:
            print(" -", item)
        return 1
    print("OK: fixture structure valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
