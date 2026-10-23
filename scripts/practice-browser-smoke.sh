#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p output/playwright docs/evidence/phase-06/screenshots
python3 - <<'PY'
import os, json, pathlib, urllib.request, urllib.parse
base=os.getenv('NORTHSTAR_BASE_URL','http://127.0.0.1:'+os.getenv('WEB_PORT','3100'))
assert urllib.parse.urlparse(base).hostname in ('127.0.0.1','localhost'), 'E2E requires loopback'
with urllib.request.urlopen(base+'/api/v1/health',timeout=8) as r:
 assert r.headers.get('X-Northstar-Test-Database')=='true', 'Write E2E requires verified isolated database'
launch={'headless':True,'args':['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']}
if os.getenv('NORTHSTAR_CHROMIUM'): launch['executablePath']=os.environ['NORTHSTAR_CHROMIUM']
pathlib.Path('output/playwright/phase06.config.json').write_text(json.dumps({'browser':{'browserName':'chromium','isolated':True,'launchOptions':launch,'contextOptions':{'permissions':['microphone']}}}))
PY
cli() {
 if [ -n "${NORTHSTAR_PLAYWRIGHT_CLI_JS:-}" ]; then node "$NORTHSTAR_PLAYWRIGHT_CLI_JS" --session=northstar-phase06 "$@"
 else npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase06 "$@"; fi
}
cli open "${NORTHSTAR_BASE_URL:-http://127.0.0.1:${WEB_PORT:-3100}}/lesson/demo-01?tab=speaking" --config=output/playwright/phase06.config.json
trap 'cli close' EXIT
cli snapshot
for script in practice-browser-smoke practice-failure-browser-smoke; do
cli run-code "$(cat "scripts/$script.js")" > "output/playwright/$script-result.txt"
python3 - "$script" <<'PY'
import pathlib,re,sys
s=pathlib.Path('output/playwright/'+sys.argv[1]+'-result.txt').read_text()
assert re.search(r'"passed"\s*:\s*true',s) and '### Error' not in s,s[:1500]
m=re.search(r'### Result\n(.*?)\n### ',s,re.S); print(m.group(1) if m else 'PASS')
PY
done
