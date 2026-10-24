#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p output/playwright docs/evidence/phase-08/screenshots
python3 - <<'PY'
import os,json,pathlib,urllib.request,urllib.parse
base=os.getenv('NORTHSTAR_BASE_URL','http://127.0.0.1:3101')
assert urllib.parse.urlparse(base).hostname in ('127.0.0.1','localhost')
with urllib.request.urlopen(base+'/api/v1/health',timeout=8) as r:assert r.headers.get('X-Northstar-Test-Database')=='true','Write E2E requires isolated schema'
launch={'headless':True}
if os.getenv('NORTHSTAR_CHROMIUM'):launch['executablePath']=os.environ['NORTHSTAR_CHROMIUM']
pathlib.Path('output/playwright/phase08.config.json').write_text(json.dumps({'browser':{'browserName':'chromium','isolated':True,'launchOptions':launch}}))
PY
cli() {
 if [ -n "${NORTHSTAR_PLAYWRIGHT_CLI_JS:-}" ]; then node "$NORTHSTAR_PLAYWRIGHT_CLI_JS" --session=northstar-phase08 "$@"
 else npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase08 "$@"; fi
}
cli open "${NORTHSTAR_BASE_URL:-http://127.0.0.1:3101}/dashboard" --config=output/playwright/phase08.config.json
trap 'cli close' EXIT
cli snapshot
cli run-code "$(cat scripts/reports-browser-smoke.js)" > output/playwright/reports-browser-result.txt
python3 - <<'PY'
import pathlib,re
s=pathlib.Path('output/playwright/reports-browser-result.txt').read_text()
assert re.search(r'"passed"\s*:\s*true',s) and '### Error' not in s,s[:2500]
m=re.search(r'### Result\n(.*?)\n### ',s,re.S);print(m.group(1) if m else 'PASS')
PY
