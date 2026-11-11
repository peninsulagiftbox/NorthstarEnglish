#!/usr/bin/env python3
"""Generate the approved core contract; do not hand edit the generated schema."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root / "docs/phase10/06_CONTENT_IMPORT_PIPELINE.md").read_text()
schema = json.loads(text.split("```json\n", 1)[1].split("\n```", 1)[0])
schema["title"] = "Northstar content package core-v1"
destination = root / "apps/api/src/main/resources/catalog/core-v1.schema.json"
destination.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n")
