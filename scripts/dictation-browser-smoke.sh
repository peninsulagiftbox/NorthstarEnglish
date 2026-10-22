#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p output/playwright docs/evidence/phase-04/screenshots
python3 - <<'PY'
import os, urllib.request, urllib.parse
base = os.getenv('NORTHSTAR_BASE_URL', 'http://127.0.0.1:' + os.getenv('WEB_PORT', '3100'))
assert urllib.parse.urlparse(base).hostname in ('127.0.0.1', 'localhost'), 'E2E must use loopback'
with urllib.request.urlopen(base + '/api/v1/health', timeout=8) as response:
    assert response.headers.get('X-Northstar-Test-Database') == 'true', 'Write E2E requires the verified isolated test database'
PY
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase04 open "${NORTHSTAR_BASE_URL:-http://127.0.0.1:${WEB_PORT:-3100}}/lesson/demo-01?tab=dictation"
trap 'npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase04 close' EXIT
npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase04 snapshot
for script in dictation-browser-smoke player-recovery-browser-smoke; do
  npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase04 run-code "$(cat "scripts/$script.js")" > "output/playwright/$script-result.txt"
  python3 - "$script" <<'PY'
import json, pathlib, re, sys
s = pathlib.Path('output/playwright/' + sys.argv[1] + '-result.txt').read_text()
assert re.search(r'"passed"\s*:\s*true', s) and '### Error' not in s, s[:1500]
match = re.search(r'### Result\n(.*?)\n### ', s, re.S)
print(match.group(1) if match else 'PASS: ' + sys.argv[1])
PY
done
