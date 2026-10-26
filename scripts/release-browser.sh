#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p output/playwright docs/evidence/phase-09/screenshots docs/evidence/phase-09/logs docs/evidence/phase-09r/screenshots docs/evidence/phase-09r/logs
python3 - "$@" <<'PY'
import json,os,pathlib,sys,urllib.request,urllib.parse
base=os.getenv('NORTHSTAR_BASE_URL','http://127.0.0.1:3101')
assert urllib.parse.urlparse(base).hostname in ('127.0.0.1','localhost')
phase09r_verified=False
if os.getenv('NORTHSTAR_PHASE09R')=='1':
 sys.path.insert(0,'scripts')
 import phase09r,local
 kind='source' if base=='http://127.0.0.1:3101' else 'restore'
 env=phase09r.verify(kind)
 assert base==env['NORTHSTAR_BASE_URL'],'Exact acceptance origin required'
 record=json.loads((phase09r.STATE/kind/'phase09r-api.json').read_text())
 assert local.owns_process(record),'Owned acceptance API required'
 phase09r_verified=True
 if sys.argv[1:]==['release-continue']:
  import subprocess
  subprocess.run([sys.executable,'scripts/check-snapshot.py',os.environ['NORTHSTAR_RESTORE_SNAPSHOT'],'--api','http://127.0.0.1:8087','--media'],check=True)
with urllib.request.urlopen(base+'/api/v1/health',timeout=8) as r:
 if r.headers.get('X-Northstar-Test-Database')!='true' and not phase09r_verified:
  if sys.argv[1:]==['release-continue'] and os.getenv('NORTHSTAR_CONTINUE_RESTORE')=='1':
   assert base=='http://127.0.0.1:3102','Restore continuation uses dedicated Web3102'
   sys.path.insert(0,'scripts')
   import local,recovery_mysql,subprocess
   recovery_mysql.verify(local.environment())
   record=json.loads((local.LOCAL/'phase09-restore-api.json').read_text())
   assert local.owns_process(record),'Owned recovery API required'
   snapshot=os.environ['NORTHSTAR_RESTORE_SNAPSHOT']
   subprocess.run([sys.executable,'scripts/check-snapshot.py',snapshot,'--api','http://127.0.0.1:8087','--media'],check=True)
  else:
   assert os.getenv('NORTHSTAR_READ_ONLY')=='1' and sys.argv[1:] and all(s in ('release-revisit','release-accessibility','release-fresh') for s in sys.argv[1:]),'Writes require isolated database; read-only scripts need explicit NORTHSTAR_READ_ONLY=1'
launch={'headless':True,'args':['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']}
if os.getenv('NORTHSTAR_CHROMIUM'):launch['executablePath']=os.environ['NORTHSTAR_CHROMIUM']
pathlib.Path('output/playwright/phase09.config.json').write_text(json.dumps({'browser':{'browserName':'chromium','isolated':True,'launchOptions':launch,'contextOptions':{'permissions':['microphone']}}}))
PY
cli() {
 if [ -n "${NORTHSTAR_PLAYWRIGHT_CLI_JS:-}" ]; then node "$NORTHSTAR_PLAYWRIGHT_CLI_JS" --session=northstar-phase09 "$@"
 else npx --yes --package=@playwright/cli@0.1.22 playwright-cli --session=northstar-phase09 "$@"; fi
}
cli open "${NORTHSTAR_BASE_URL:-http://127.0.0.1:3101}/dashboard" --config=output/playwright/phase09.config.json
trap 'cli tracing-stop; cli close' EXIT
cli snapshot
cli tracing-start
# Optional arguments select existing regression suites; default is the full learning loop.
if [ "$#" -eq 0 ]; then set -- full-learning-loop release-boundaries; fi
for script in "$@"; do
 case "$script" in *[!a-z0-9-]*|'') echo 'Invalid script name' >&2; exit 1;; esac
 evidence_phase=phase-09
 if [ "${NORTHSTAR_PHASE09R:-}" = 1 ]; then evidence_phase=phase-09r; fi
 result="docs/evidence/$evidence_phase/logs/$script-$(date +%Y%m%d%H%M%S).txt"
 cli run-code "$(cat "scripts/$script.js")" > "$result"
 python3 - "$result" <<'PY'
import pathlib,re,sys
s=pathlib.Path(sys.argv[1]).read_text()
assert re.search(r'"passed"\s*:\s*true',s) and '### Error' not in s,s[:3500]
print('PASS: '+sys.argv[1])
PY
done
